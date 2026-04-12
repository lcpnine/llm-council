"""
Comprehensive Analysis Generation Script

This is the SINGLE master script for generating ALL analysis outputs:
1. Adds 23 missing columns to EXPERIMENTS_SUMMARY_TABLE.csv:
   - Per-class precision/recall/F1 for yes/no/maybe (9 columns - PubMedQA)
   - Per-class precision/recall/F1 for A/B/C/D (12 columns - MedQA/MMLU)
   - Token usage metrics (2 columns)
2. Generates all visualizations (confusion matrices, bar charts)
3. Creates comparison tables (per-dataset summaries, statistical comparisons)

Extends: update_all_metrics.py
Version: 2.1.0
Date: 2026-04-12
"""

import pandas as pd
import numpy as np
import json
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
from sklearn.metrics import confusion_matrix, ConfusionMatrixDisplay
import warnings
import os
from pathlib import Path
warnings.filterwarnings('ignore')

# Set style for all visualizations
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (10, 8)
plt.rcParams['font.size'] = 11


class ComprehensiveAnalysisGenerator:
    """Master class for generating complete analysis with all metrics and visualizations."""

    def __init__(self):
        self.summary_df = None
        self.db_experiments_df = None
        self.results_df = None
        self.json_experiments = []  # Store full JSON experiments for v5 data
        self.exp_lookup = {}
        self.matched_count = 0

        # Output directories
        self.dirs = {
            'confusion': Path('results/confusion_matrices'),
            'charts': Path('results/charts'),
            'tables': Path('results/comparison_tables')
        }

    # =========================================================================
    # SETUP: CREATE DIRECTORIES AND LOAD DATA
    # =========================================================================

    def setup(self):
        """Create output directories and load all data sources."""
        print("=" * 80)
        print("COMPREHENSIVE ANALYSIS GENERATOR")
        print("=" * 80)
        print("\nCreating output directories...")

        for name, path in self.dirs.items():
            path.mkdir(parents=True, exist_ok=True)
            print(f"  [OK] {path}")

        print("\nLoading data sources...")

        # Load summary table
        self.summary_df = pd.read_csv('results/EXPERIMENTS_SUMMARY_TABLE.csv')
        print(f"  [OK] EXPERIMENTS_SUMMARY_TABLE.csv ({len(self.summary_df)} experiments)")

        # Load db_experiments for token usage and full metrics
        self.db_experiments_df = pd.read_csv('results/db_experiments.csv')
        print(f"  [OK] db_experiments.csv ({len(self.db_experiments_df)} experiments)")

        # Load detailed results for per-question analysis
        self.results_df = pd.read_csv('results/results_filtered_highquality.csv')
        print(f"  [OK] results_filtered_highquality.csv ({len(self.results_df)} questions)")

        return self

    # =========================================================================
    # STEP 1: BUILD EXPERIMENT LOOKUP FROM MULTIPLE SOURCES
    # =========================================================================

    def build_experiment_lookup(self):
        """Build comprehensive lookup with per-class metrics and token usage."""
        print("\n[STEP 1/8] Building experiment lookup...")

        # First, load from JSON file (has all 47 experiments with per-class metrics)
        json_path = '../data/exports/experiments_all_2026-04-10-4.json'
        with open(json_path, 'r', encoding='utf-8') as f:
            json_data = json.load(f)

        json_exps = json_data.get('experiments', json_data)

        # Store all JSON experiments for later use (v5 per-question data)
        self.json_experiments = json_exps

        for exp in json_exps:
            exp_id = exp.get('id', '')
            dataset = exp.get('dataset', '').upper()
            prompt = exp.get('prompt_version', '')

            # Get per-class metrics from full_metrics
            per_class_metrics = {}
            if 'full_metrics' in exp and isinstance(exp['full_metrics'], dict):
                if 'per_class' in exp['full_metrics']:
                    per_class_metrics = exp['full_metrics']['per_class']

            # Get config
            config = exp.get('config', {})
            gen_model = config.get('generator_model', config.get('model', ''))
            n_stages = exp.get('n_stages', 1)

            # Normalize model name
            if gen_model and '/' in gen_model:
                gen_model = gen_model.split('/')[1]

            self.exp_lookup[exp_id] = {
                'dataset': dataset,
                'prompt': prompt,
                'n_stages': int(n_stages),
                'gen_model': gen_model,
                'per_class': per_class_metrics,
                'total_tokens': None  # Will be filled from db_experiments
            }

        print(f"      Loaded {len(self.exp_lookup)} experiments from JSON")

        # Second, supplement with token usage from db_experiments.csv
        token_count = 0
        for _, exp in self.db_experiments_df.iterrows():
            exp_id = exp['id']
            total_tokens = exp['total_tokens'] if pd.notna(exp['total_tokens']) else None

            if exp_id in self.exp_lookup and total_tokens is not None:
                self.exp_lookup[exp_id]['total_tokens'] = total_tokens
                token_count += 1

        print(f"      Added token usage for {token_count} experiments from db_experiments.csv")
        return self

    # =========================================================================
    # STEP 2: ADD PER-CLASS METRICS (9 COLUMNS)
    # =========================================================================

    def add_per_class_metrics(self):
        """Add precision, recall, F1 for all classes (yes/no/maybe AND A/B/C/D)."""
        print("\n[STEP 2/8] Adding per-class metrics...")

        # Initialize columns for yes/no/maybe (PubMedQA)
        for class_name in ['yes', 'no', 'maybe']:
            self.summary_df[f'Precision_{class_name}'] = None
            self.summary_df[f'Recall_{class_name}'] = None
            self.summary_df[f'F1_{class_name}'] = None

        # Initialize columns for A/B/C/D (MedQA, MMLU)
        for class_name in ['A', 'B', 'C', 'D']:
            self.summary_df[f'Precision_{class_name}'] = None
            self.summary_df[f'Recall_{class_name}'] = None
            self.summary_df[f'F1_{class_name}'] = None

        matched = 0

        for idx, row in self.summary_df.iterrows():
            dataset = str(row['Dataset']).upper()
            prompt = str(row['Prompt Version'])
            setup = str(row['Setup'])
            gen_model = str(row['Generator Model'])

            if pd.isna(gen_model) or gen_model == 'nan':
                continue

            # Normalize
            if '/' in gen_model:
                gen_model = gen_model.split('/')[1]

            # Determine n_stages
            expected_stages = 1 if '1-stage' in setup else 3

            # Match experiment
            best_match = self._find_best_match(dataset, prompt, expected_stages, gen_model)

            if best_match:
                per_class = self.exp_lookup[best_match]['per_class']

                # Extract metrics based on dataset type
                if dataset == 'PUBMEDQA':
                    # Yes/no/maybe labels for clinical questions
                    for class_name in ['yes', 'no', 'maybe']:
                        if class_name in per_class:
                            class_metrics = per_class[class_name]
                            self.summary_df.at[idx, f'Precision_{class_name}'] = class_metrics.get('precision')
                            self.summary_df.at[idx, f'Recall_{class_name}'] = class_metrics.get('recall')
                            self.summary_df.at[idx, f'F1_{class_name}'] = class_metrics.get('f1')
                elif dataset in ['MEDQA', 'MMLU']:
                    # A/B/C/D labels for multiple choice
                    for class_name in ['A', 'B', 'C', 'D']:
                        if class_name in per_class:
                            class_metrics = per_class[class_name]
                            self.summary_df.at[idx, f'Precision_{class_name}'] = class_metrics.get('precision')
                            self.summary_df.at[idx, f'Recall_{class_name}'] = class_metrics.get('recall')
                            self.summary_df.at[idx, f'F1_{class_name}'] = class_metrics.get('f1')

                matched += 1

        print(f"      Added per-class metrics for {matched}/{len(self.summary_df)} experiments")
        print(f"        - PubMedQA: yes/no/maybe columns")
        print(f"        - MedQA/MMLU: A/B/C/D columns")
        return self

    # =========================================================================
    # STEP 2B: FILL MISSING F1_MACRO FROM RESULTS_FILTERED
    # =========================================================================

    def fill_missing_f1_from_results_filtered(self):
        """Calculate F1_Macro for experiments missing it from results_filtered CSV."""
        from sklearn.metrics import f1_score

        print("\n[STEP 2B/8] Filling missing F1_Macro from results_filtered...")

        # Check how many are missing
        missing_count = self.summary_df['F1_Macro'].isna().sum()
        if missing_count == 0:
            print("      No missing F1_Macro values")
            return self

        print(f"      Found {missing_count} experiments with missing F1_Macro")

        # Calculate F1 for each unique experiment in results_filtered
        f1_lookup = {}
        for exp_id in self.results_df['experiment_id'].unique():
            exp_df = self.results_df[self.results_df['experiment_id'] == exp_id]

            y_true = exp_df['gold']
            y_pred = exp_df['predicted']

            # Get unique labels
            labels = sorted(set(y_true) | set(y_pred))

            try:
                f1 = f1_score(y_true, y_pred, average='macro', labels=labels)
                acc = (y_true == y_pred).mean()

                # Extract metadata from experiment_id (format: dataset_promptversion_timestamp_id)
                parts = exp_id.split('_')
                dataset = parts[0]

                # Find where timestamp starts (8-digit YYYYMMDD format)
                timestamp_idx = None
                for i, part in enumerate(parts):
                    if len(part) == 8 and part.isdigit():
                        timestamp_idx = i
                        break

                # Extract prompt version (everything between dataset and timestamp)
                if timestamp_idx and timestamp_idx > 1:
                    prompt = '_'.join(parts[1:timestamp_idx])
                else:
                    # Fallback: assume last 3 parts are timestamp_HHMMSS_id
                    prompt = '_'.join(parts[1:-3]) if len(parts) > 4 else parts[1]

                n_stages = exp_df['n_stages'].iloc[0]

                f1_lookup[exp_id] = {
                    'dataset': dataset,
                    'prompt': prompt,
                    'n_stages': n_stages,
                    'accuracy': acc,
                    'f1_macro': f1
                }
            except Exception as e:
                print(f"      Warning: Could not calculate F1 for {exp_id}: {e}")
                continue

        print(f"      Calculated F1 for {len(f1_lookup)} experiments from results_filtered")

        # Match and fill missing F1 values
        filled = 0
        for idx, row in self.summary_df.iterrows():
            if pd.notna(row['F1_Macro']):
                continue  # Skip if F1 already exists

            dataset = str(row['Dataset']).lower()
            prompt = str(row['Prompt Version'])
            accuracy = float(str(row['Accuracy']).replace('%', '')) / 100
            setup = str(row['Setup'])
            n_stages = 1 if '1-stage' in setup else 3

            # Find matching experiment in f1_lookup
            matches = [
                (exp_id, data) for exp_id, data in f1_lookup.items()
                if data['dataset'].lower() == dataset
                and data['prompt'] == prompt
                and data['n_stages'] == n_stages
                and abs(data['accuracy'] - accuracy) < 0.01  # Match accuracy within 1%
            ]

            if len(matches) == 1:
                exp_id, data = matches[0]
                self.summary_df.at[idx, 'F1_Macro'] = data['f1_macro']
                filled += 1
                print(f"      Filled F1={data['f1_macro']:.4f} for row {idx+1}: {dataset} {prompt} {accuracy:.0%}")
            elif len(matches) > 1:
                # Multiple matches - pick the first one
                exp_id, data = matches[0]
                self.summary_df.at[idx, 'F1_Macro'] = data['f1_macro']
                filled += 1
                print(f"      Filled F1={data['f1_macro']:.4f} for row {idx+1}: {dataset} {prompt} (multiple matches, used first)")

        remaining = self.summary_df['F1_Macro'].isna().sum()
        print(f"      Filled {filled} missing F1_Macro values")
        if remaining > 0:
            print(f"      Still missing: {remaining} experiments (not in results_filtered)")

        return self

    # =========================================================================
    # STEP 3: ADD TOKEN USAGE METRICS (2 COLUMNS)
    # =========================================================================

    def add_token_usage_metrics(self):
        """Add total tokens and tokens per question."""
        print("\n[STEP 3/8] Adding token usage metrics...")

        # Initialize columns
        self.summary_df['Total_Tokens'] = None
        self.summary_df['Tokens_per_Question'] = None

        matched = 0

        for idx, row in self.summary_df.iterrows():
            dataset = str(row['Dataset']).upper()
            prompt = str(row['Prompt Version'])
            setup = str(row['Setup'])
            gen_model = str(row['Generator Model'])
            samples = row['Samples']

            if pd.isna(gen_model) or gen_model == 'nan':
                continue

            # Normalize
            if '/' in gen_model:
                gen_model = gen_model.split('/')[1]

            # Determine n_stages
            expected_stages = 1 if '1-stage' in setup else 3

            # Match experiment
            best_match = self._find_best_match(dataset, prompt, expected_stages, gen_model)

            if best_match:
                total_tokens = self.exp_lookup[best_match]['total_tokens']

                if total_tokens is not None and pd.notna(total_tokens):
                    self.summary_df.at[idx, 'Total_Tokens'] = int(total_tokens)

                    # Calculate tokens per question
                    if pd.notna(samples) and samples > 0:
                        tokens_per_q = total_tokens / samples
                        self.summary_df.at[idx, 'Tokens_per_Question'] = round(tokens_per_q, 1)

                matched += 1

        token_count = self.summary_df['Total_Tokens'].notna().sum()
        print(f"      Added token usage for {token_count}/{len(self.summary_df)} experiments")
        return self

    # =========================================================================
    # STEP 4: GENERATE CONFUSION MATRICES
    # =========================================================================

    def generate_confusion_matrices(self):
        """Generate confusion matrices for key experiments (including v5)."""
        print("\n[STEP 4/8] Generating confusion matrices...")

        # Key experiments to visualize (including v5)
        key_configs = [
            ('MEDQA', 'v1_baseline', 1),
            ('MEDQA', 'v1_baseline', 3),
            ('MEDQA', 'v2_structured', 3),
            ('MEDQA', 'v3_skeptic_strict', 3),
            ('MEDQA', 'v5_angel_devil', 3),
            ('MMLU', 'v1_baseline', 1),
            ('MMLU', 'v2_structured', 3),
            ('MMLU', 'v3_skeptic_strict', 3),
            ('PUBMEDQA', 'v1_baseline', 1),
            ('PUBMEDQA', 'v2_structured', 3),
            ('PUBMEDQA', 'v3_skeptic_strict', 3),
            ('PUBMEDQA', 'v5_angel_devil', 3),
        ]

        generated = 0

        for dataset, prompt, n_stages in key_configs:
            # Try CSV data first (v1/v2/v3)
            confusion_generated = self._generate_from_csv(dataset, prompt, n_stages)

            # If not found in CSV, try JSON (v5)
            if not confusion_generated:
                confusion_generated = self._generate_from_json(dataset, prompt, n_stages)

            if confusion_generated:
                generated += 1

        print(f"      Generated {generated} confusion matrices")
        return self

    def _generate_from_csv(self, dataset, prompt, n_stages):
        """Generate confusion matrix from CSV data (v1/v2/v3)."""
        # Find matching experiments in results_df
        mask = (
            (self.results_df['dataset'] == dataset.lower()) &
            (self.results_df['n_stages'] == n_stages)
        )

        exp_data = self.results_df[mask]

        if len(exp_data) == 0:
            return False

        # Get experiment_id to check prompt version
        exp_ids = exp_data['experiment_id'].unique()

        for exp_id in exp_ids:
            if prompt.lower() not in exp_id.lower():
                continue

            exp_subset = exp_data[exp_data['experiment_id'] == exp_id]

            if len(exp_subset) < 10:  # Need sufficient samples
                continue

            # Extract predictions and gold labels
            y_true = exp_subset['gold'].values
            y_pred = exp_subset['predicted'].values

            # Create and save confusion matrix
            return self._create_confusion_matrix(dataset, prompt, n_stages, y_true, y_pred)

        return False

    def _generate_from_json(self, dataset, prompt, n_stages):
        """Generate confusion matrix from JSON data (v5 experiments)."""
        # Find matching experiment in JSON
        for exp in self.json_experiments:
            if (exp.get('dataset', '').upper() == dataset.upper() and
                exp.get('prompt_version', '') == prompt and
                exp.get('n_stages', 0) == n_stages):

                # Check if experiment has results
                if 'results' not in exp or not exp['results']:
                    continue

                results = exp['results']
                if len(results) < 10:  # Need sufficient samples
                    continue

                # Extract predictions and gold labels
                y_true = [r['gold'] for r in results]
                y_pred = [r['predicted'] for r in results]

                # Create and save confusion matrix
                return self._create_confusion_matrix(dataset, prompt, n_stages, y_true, y_pred)

        return False

    def _create_confusion_matrix(self, dataset, prompt, n_stages, y_true, y_pred):
        """Create and save confusion matrix plot."""
        # Determine which labels actually exist in the data
        unique_true = set(y_true)
        unique_pred = set(y_pred)
        all_labels = unique_true.union(unique_pred)

        # Filter to standard labels that exist
        # For multiple choice datasets, use A/B/C/D; for PubMedQA use yes/no/maybe
        if dataset in ['MEDQA', 'MMLU']:
            possible_labels = ['A', 'B', 'C', 'D']
        else:
            possible_labels = ['yes', 'no', 'maybe']

        labels = [l for l in possible_labels if l in all_labels]

        if len(labels) < 2:  # Need at least 2 labels for meaningful confusion matrix
            return False

        # Create confusion matrix
        cm = confusion_matrix(y_true, y_pred, labels=labels)

        # Plot
        fig, ax = plt.subplots(figsize=(8, 6))
        disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=labels)
        disp.plot(cmap='Blues', ax=ax, values_format='d')

        stage_type = '1-stage' if n_stages == 1 else '3-stage'
        ax.set_title(f'{dataset} - {prompt} ({stage_type})', fontsize=14, fontweight='bold')
        ax.set_xlabel('Predicted', fontsize=12)
        ax.set_ylabel('True', fontsize=12)

        # Save
        filename = f'confusion_matrix_{dataset.lower()}_{prompt}_{stage_type}.png'
        filepath = self.dirs['confusion'] / filename
        plt.tight_layout()
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()

        return True

    # =========================================================================
    # STEP 5: GENERATE BAR CHARTS
    # =========================================================================

    def generate_bar_charts(self):
        """Generate comparison bar charts."""
        print("\n[STEP 5/8] Generating bar charts...")

        charts_generated = []

        # Chart 1: Accuracy by Dataset and Prompt
        self._chart_accuracy_by_dataset()
        charts_generated.append("accuracy_by_dataset.png")

        # Chart 2: F1 Macro Comparison
        self._chart_f1_comparison()
        charts_generated.append("f1_macro_comparison.png")

        # Chart 3: Effect Size Distribution
        self._chart_effect_sizes()
        charts_generated.append("effect_size_distribution.png")

        # Chart 4: Agent Attribution
        self._chart_agent_attribution()
        charts_generated.append("agent_attribution_summary.png")

        # Chart 5: Token Efficiency
        self._chart_token_efficiency()
        charts_generated.append("token_efficiency.png")

        # Chart 6: Task Difficulty Class Accuracy
        self._chart_task_difficulty_class()
        charts_generated.append("task_difficulty_class_accuracy_filtered.png")

        # Chart 7: Task Difficulty Stratified
        self._chart_task_difficulty_stratified()
        charts_generated.append("task_difficulty_stratified_filtered.png")

        print(f"      Generated {len(charts_generated)} bar charts")
        return self

    def _chart_accuracy_by_dataset(self):
        """Bar chart: Accuracy comparison by dataset."""
        # Filter 3-stage debate experiments
        debate_df = self.summary_df[self.summary_df['Setup'].str.contains('3-stage', na=False)].copy()

        if len(debate_df) == 0:
            return

        # Parse accuracy
        debate_df['Acc_Numeric'] = debate_df['Accuracy'].apply(self._parse_percentage)

        # Group by dataset and prompt
        grouped = debate_df.groupby(['Dataset', 'Prompt Version'])['Acc_Numeric'].mean().reset_index()

        # Plot
        fig, ax = plt.subplots(figsize=(12, 6))

        datasets = grouped['Dataset'].unique()
        prompts = grouped['Prompt Version'].unique()
        x = np.arange(len(datasets))
        width = 0.25

        for i, prompt in enumerate(prompts):
            data = grouped[grouped['Prompt Version'] == prompt]
            values = [data[data['Dataset'] == ds]['Acc_Numeric'].values[0] * 100
                      if len(data[data['Dataset'] == ds]) > 0 else 0
                      for ds in datasets]
            ax.bar(x + i * width, values, width, label=prompt)

        ax.set_xlabel('Dataset', fontsize=12, fontweight='bold')
        ax.set_ylabel('Accuracy (%)', fontsize=12, fontweight='bold')
        ax.set_title('Accuracy Comparison: 3-Stage Debate by Dataset', fontsize=14, fontweight='bold')
        ax.set_xticks(x + width)
        ax.set_xticklabels(datasets)
        ax.legend()
        ax.grid(axis='y', alpha=0.3)

        plt.tight_layout()
        plt.savefig(self.dirs['charts'] / 'accuracy_by_dataset.png', dpi=150, bbox_inches='tight')
        plt.close()

    def _chart_f1_comparison(self):
        """Bar chart: F1 Macro comparison."""
        # Get experiments with F1 values
        f1_df = self.summary_df[self.summary_df['F1_Macro'].notna()].copy()

        if len(f1_df) == 0:
            return

        # Group by dataset
        grouped = f1_df.groupby('Dataset')['F1_Macro'].agg(['mean', 'std']).reset_index()

        fig, ax = plt.subplots(figsize=(10, 6))

        x = np.arange(len(grouped))
        ax.bar(x, grouped['mean'], yerr=grouped['std'], capsize=5, alpha=0.7, color='steelblue')

        ax.set_xlabel('Dataset', fontsize=12, fontweight='bold')
        ax.set_ylabel('F1 Macro (Mean ± SD)', fontsize=12, fontweight='bold')
        ax.set_title('F1 Macro Score by Dataset', fontsize=14, fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels(grouped['Dataset'])
        ax.grid(axis='y', alpha=0.3)

        plt.tight_layout()
        plt.savefig(self.dirs['charts'] / 'f1_macro_comparison.png', dpi=150, bbox_inches='tight')
        plt.close()

    def _chart_effect_sizes(self):
        """Bar chart: Effect size distribution."""
        effect_df = self.summary_df[self.summary_df['Effect_Size'].notna()]

        if len(effect_df) == 0:
            return

        effect_counts = effect_df['Effect_Size'].value_counts()

        fig, ax = plt.subplots(figsize=(10, 6))

        colors = {'negligible': 'lightgray', 'small': 'skyblue',
                  'medium': 'orange', 'large': 'tomato'}

        x = np.arange(len(effect_counts))
        bars = ax.bar(x, effect_counts.values, color=[colors.get(e, 'gray') for e in effect_counts.index])

        ax.set_xlabel('Effect Size', fontsize=12, fontweight='bold')
        ax.set_ylabel('Number of Experiments', fontsize=12, fontweight='bold')
        ax.set_title("Cohen's d Effect Size Distribution", fontsize=14, fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels(effect_counts.index)
        ax.grid(axis='y', alpha=0.3)

        # Add value labels on bars
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{int(height)}',
                   ha='center', va='bottom')

        plt.tight_layout()
        plt.savefig(self.dirs['charts'] / 'effect_size_distribution.png', dpi=150, bbox_inches='tight')
        plt.close()

    def _chart_agent_attribution(self):
        """Bar chart: Agent attribution summary."""
        # Get experiments with agent attribution
        attr_df = self.summary_df[self.summary_df['Both Correct'].notna()].copy()

        if len(attr_df) == 0:
            return

        # Calculate totals
        both_correct = attr_df['Both Correct'].sum()
        fixed = attr_df['Fixed by Debate'].sum()
        broke = attr_df['Broke by Debate'].sum()
        both_wrong = attr_df['Both Wrong'].sum()

        fig, ax = plt.subplots(figsize=(10, 6))

        categories = ['Both Correct', 'Fixed by Debate', 'Broke by Debate', 'Both Wrong']
        values = [both_correct, fixed, broke, both_wrong]
        colors = ['green', 'blue', 'red', 'gray']

        bars = ax.bar(categories, values, color=colors, alpha=0.7)

        ax.set_ylabel('Count', fontsize=12, fontweight='bold')
        ax.set_title('Agent Attribution Analysis (All Experiments)', fontsize=14, fontweight='bold')
        ax.grid(axis='y', alpha=0.3)

        # Add value labels
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{int(height)}',
                   ha='center', va='bottom')

        plt.xticks(rotation=15, ha='right')
        plt.tight_layout()
        plt.savefig(self.dirs['charts'] / 'agent_attribution_summary.png', dpi=150, bbox_inches='tight')
        plt.close()

    def _chart_token_efficiency(self):
        """Bar chart: Token efficiency analysis."""
        token_df = self.summary_df[self.summary_df['Tokens_per_Question'].notna()].copy()

        if len(token_df) == 0:
            return

        # Compare 1-stage vs 3-stage
        token_df['Stage_Type'] = token_df['Setup'].apply(
            lambda x: '1-stage' if '1-stage' in str(x) else '3-stage'
        )

        grouped = token_df.groupby('Stage_Type')['Tokens_per_Question'].agg(['mean', 'std']).reset_index()

        fig, ax = plt.subplots(figsize=(8, 6))

        x = np.arange(len(grouped))
        ax.bar(x, grouped['mean'], yerr=grouped['std'], capsize=5, alpha=0.7, color='purple')

        ax.set_xlabel('Setup Type', fontsize=12, fontweight='bold')
        ax.set_ylabel('Tokens per Question (Mean ± SD)', fontsize=12, fontweight='bold')
        ax.set_title('Token Efficiency: 1-Stage vs 3-Stage Debate', fontsize=14, fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels(grouped['Stage_Type'])
        ax.grid(axis='y', alpha=0.3)

        plt.tight_layout()
        plt.savefig(self.dirs['charts'] / 'token_efficiency.png', dpi=150, bbox_inches='tight')
        plt.close()

    def _chart_task_difficulty_class(self):
        """Bar chart: Accuracy broken down by difficulty class (Easy/Medium/Hard)."""
        df = self.summary_df.copy()

        # Filter experiments with difficulty data
        difficulty_df = df[(df['Easy %'].notna()) & (df['Medium %'].notna()) & (df['Hard %'].notna())].copy()

        if len(difficulty_df) == 0:
            return

        # Parse percentages
        difficulty_df['Easy_Numeric'] = difficulty_df['Easy %'].apply(self._parse_percentage)
        difficulty_df['Medium_Numeric'] = difficulty_df['Medium %'].apply(self._parse_percentage)
        difficulty_df['Hard_Numeric'] = difficulty_df['Hard %'].apply(self._parse_percentage)

        # Group by dataset
        grouped = difficulty_df.groupby('Dataset')[['Easy_Numeric', 'Medium_Numeric', 'Hard_Numeric']].mean().reset_index()

        fig, ax = plt.subplots(figsize=(10, 6))

        datasets = sorted(grouped['Dataset'].unique())
        x = np.arange(len(datasets))
        width = 0.25

        easy_vals = [grouped[grouped['Dataset'] == ds]['Easy_Numeric'].values[0] * 100 if len(grouped[grouped['Dataset'] == ds]) > 0 else 0 for ds in datasets]
        medium_vals = [grouped[grouped['Dataset'] == ds]['Medium_Numeric'].values[0] * 100 if len(grouped[grouped['Dataset'] == ds]) > 0 else 0 for ds in datasets]
        hard_vals = [grouped[grouped['Dataset'] == ds]['Hard_Numeric'].values[0] * 100 if len(grouped[grouped['Dataset'] == ds]) > 0 else 0 for ds in datasets]

        ax.bar(x - width, easy_vals, width, label='Easy', color='lightgreen')
        ax.bar(x, medium_vals, width, label='Medium', color='gold')
        ax.bar(x + width, hard_vals, width, label='Hard', color='tomato')

        ax.set_xlabel('Dataset', fontsize=12, fontweight='bold')
        ax.set_ylabel('Accuracy (%)', fontsize=12, fontweight='bold')
        ax.set_title('Accuracy by Task Difficulty Class', fontsize=14, fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels(datasets)
        ax.legend()
        ax.grid(axis='y', alpha=0.3)
        ax.set_ylim(0, 100)

        plt.tight_layout()
        plt.savefig(Path('results') / 'task_difficulty_class_accuracy_filtered.png', dpi=150, bbox_inches='tight')
        plt.close()

    def _chart_task_difficulty_stratified(self):
        """Stacked bar chart: Difficulty stratification (Easy/Medium/Hard distribution)."""
        df = self.summary_df.copy()

        # Filter experiments with difficulty data
        difficulty_df = df[(df['Easy %'].notna()) & (df['Medium %'].notna()) & (df['Hard %'].notna())].copy()

        if len(difficulty_df) == 0:
            return

        # Parse percentages
        difficulty_df['Easy_Numeric'] = difficulty_df['Easy %'].apply(self._parse_percentage)
        difficulty_df['Medium_Numeric'] = difficulty_df['Medium %'].apply(self._parse_percentage)
        difficulty_df['Hard_Numeric'] = difficulty_df['Hard %'].apply(self._parse_percentage)

        # Group by dataset and get averages
        grouped = difficulty_df.groupby('Dataset')[['Easy_Numeric', 'Medium_Numeric', 'Hard_Numeric']].mean().reset_index()

        fig, ax = plt.subplots(figsize=(10, 6))

        datasets = sorted(grouped['Dataset'].unique())
        easy = [grouped[grouped['Dataset'] == ds]['Easy_Numeric'].values[0] * 100 for ds in datasets]
        medium = [grouped[grouped['Dataset'] == ds]['Medium_Numeric'].values[0] * 100 for ds in datasets]
        hard = [grouped[grouped['Dataset'] == ds]['Hard_Numeric'].values[0] * 100 for ds in datasets]

        x = np.arange(len(datasets))

        ax.bar(x, easy, label='Easy', color='lightgreen')
        ax.bar(x, medium, bottom=easy, label='Medium', color='gold')
        ax.bar(x, hard, bottom=[e + m for e, m in zip(easy, medium)], label='Hard', color='tomato')

        ax.set_xlabel('Dataset', fontsize=12, fontweight='bold')
        ax.set_ylabel('Accuracy (%)', fontsize=12, fontweight='bold')
        ax.set_title('Task Difficulty Stratification', fontsize=14, fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels(datasets)
        ax.legend(loc='upper right')
        ax.grid(axis='y', alpha=0.3)
        ax.set_ylim(0, 100)

        plt.tight_layout()
        plt.savefig(Path('results') / 'task_difficulty_stratified_filtered.png', dpi=150, bbox_inches='tight')
        plt.close()

    # =========================================================================
    # STEP 6: GENERATE PER-DATASET TABLES
    # =========================================================================

    def generate_per_dataset_tables(self):
        """Generate summary tables for each dataset."""
        print("\n[STEP 6/8] Generating per-dataset tables...")

        datasets = self.summary_df['Dataset'].unique()

        for dataset in datasets:
            dataset_df = self.summary_df[self.summary_df['Dataset'] == dataset].copy()

            # Select key columns
            cols = ['Setup', 'Prompt Version', 'Generator Model', 'Accuracy',
                    'F1_Macro', 'Δ Accuracy', 'p-value', 'Cohens_d', 'Effect_Size']

            output_df = dataset_df[cols].copy()

            # Sort by accuracy
            output_df = output_df.sort_values('Accuracy', ascending=False)

            # Save
            filename = f'{dataset}_summary.csv'
            filepath = self.dirs['tables'] / filename
            output_df.to_csv(filepath, index=False)

        print(f"      Generated {len(datasets)} per-dataset tables")
        return self

    # =========================================================================
    # STEP 7: GENERATE STATISTICAL COMPARISON TABLE
    # =========================================================================

    def generate_statistical_comparisons(self):
        """Generate statistical comparison table (baseline vs debate)."""
        print("\n[STEP 7/8] Generating statistical comparison table...")

        comparisons = []

        # Find all debate experiments
        debate_df = self.summary_df[self.summary_df['Setup'].str.contains('3-stage', na=False)]

        for _, debate_row in debate_df.iterrows():
            dataset = debate_row['Dataset']
            prompt = debate_row['Prompt Version']
            model = debate_row['Generator Model']

            # Find matching baseline
            baseline_mask = (
                (self.summary_df['Dataset'] == dataset) &
                (self.summary_df['Prompt Version'] == prompt) &
                (self.summary_df['Generator Model'] == model) &
                (self.summary_df['Setup'].str.contains('1-stage', na=False))
            )

            baseline_rows = self.summary_df[baseline_mask]

            if len(baseline_rows) == 0:
                continue

            baseline_row = baseline_rows.iloc[0]

            comparisons.append({
                'Dataset': dataset,
                'Prompt': prompt,
                'Model': model,
                'Baseline_Accuracy': baseline_row['Accuracy'],
                'Debate_Accuracy': debate_row['Accuracy'],
                'Delta': debate_row['Δ Accuracy'],
                'p-value': debate_row['p-value'],
                'Cohens_d': debate_row['Cohens_d'],
                'Effect_Size': debate_row['Effect_Size'],
                'Net_Impact': debate_row['Net Impact']
            })

        if len(comparisons) > 0:
            comp_df = pd.DataFrame(comparisons)
            filepath = self.dirs['tables'] / 'statistical_comparisons.csv'
            comp_df.to_csv(filepath, index=False)
            print(f"      Generated comparison table with {len(comp_df)} comparisons")
        else:
            print("      No comparisons found")

        return self

    # =========================================================================
    # STEP 8: GENERATE TOKEN EFFICIENCY TABLE
    # =========================================================================

    def generate_token_efficiency_table(self):
        """Generate token efficiency analysis table."""
        print("\n[STEP 8/8] Generating token efficiency table...")

        token_df = self.summary_df[self.summary_df['Total_Tokens'].notna()].copy()

        if len(token_df) == 0:
            print("      No token data available")
            return self

        # Select relevant columns
        cols = ['Dataset', 'Setup', 'Prompt Version', 'Total_Tokens',
                'Tokens_per_Question', 'Accuracy', 'Samples']

        output_df = token_df[cols].copy()

        # Calculate efficiency score (accuracy per 1000 tokens)
        output_df['Efficiency_Score'] = (
            output_df['Accuracy'].apply(self._parse_percentage) * 1000 /
            output_df['Tokens_per_Question']
        )
        # Convert to numeric and round
        output_df['Efficiency_Score'] = pd.to_numeric(output_df['Efficiency_Score'], errors='coerce').round(3)

        # Sort by efficiency
        output_df = output_df.sort_values('Efficiency_Score', ascending=False)

        # Save
        filepath = self.dirs['tables'] / 'token_efficiency.csv'
        output_df.to_csv(filepath, index=False)

        print(f"      Generated token efficiency table with {len(output_df)} experiments")
        return self

    # =========================================================================
    # FINALIZE: SAVE UPDATED SUMMARY TABLE
    # =========================================================================

    def save_updated_summary(self):
        """Save the updated summary table with all new columns."""
        print("\n[FINAL] Saving updated EXPERIMENTS_SUMMARY_TABLE.csv...")

        # Count new columns
        original_cols = 26
        new_cols = len(self.summary_df.columns) - original_cols

        # Save
        self.summary_df.to_csv('results/EXPERIMENTS_SUMMARY_TABLE.csv', index=False)

        print(f"      Total columns: {len(self.summary_df.columns)} (added {new_cols} new columns)")
        print(f"      Saved to: results/EXPERIMENTS_SUMMARY_TABLE.csv")
        return self

    # =========================================================================
    # REPORTING
    # =========================================================================

    def print_final_summary(self):
        """Print comprehensive summary of all outputs."""
        print("\n" + "=" * 80)
        print("GENERATION COMPLETE - SUMMARY")
        print("=" * 80)

        # Column summary
        print("\n1. UPDATED SUMMARY TABLE:")
        print(f"   Total experiments: {len(self.summary_df)}")
        print(f"   Total columns: {len(self.summary_df.columns)}")
        print(f"\n   New columns added:")
        print(f"   • Per-class for PubMedQA (yes/no/maybe):")
        print(f"     - Precision: {self.summary_df['Precision_yes'].notna().sum()} filled")
        print(f"     - Recall: {self.summary_df['Recall_yes'].notna().sum()} filled")
        print(f"     - F1: {self.summary_df['F1_yes'].notna().sum()} filled")
        print(f"   • Per-class for MedQA/MMLU (A/B/C/D):")
        print(f"     - Precision: {self.summary_df['Precision_A'].notna().sum()} filled")
        print(f"     - Recall: {self.summary_df['Recall_A'].notna().sum()} filled")
        print(f"     - F1: {self.summary_df['F1_A'].notna().sum()} filled")
        print(f"   • Token usage:")
        print(f"     - Total Tokens: {self.summary_df['Total_Tokens'].notna().sum()} filled")
        print(f"     - Tokens per Question: {self.summary_df['Tokens_per_Question'].notna().sum()} filled")

        # Visualizations
        print("\n2. VISUALIZATIONS GENERATED:")
        confusion_count = len(list(self.dirs['confusion'].glob('*.png')))
        chart_count = len(list(self.dirs['charts'].glob('*.png')))
        print(f"   • Confusion matrices: {confusion_count} files")
        print(f"   • Bar charts: {chart_count} files")

        # Tables
        print("\n3. COMPARISON TABLES GENERATED:")
        table_count = len(list(self.dirs['tables'].glob('*.csv')))
        print(f"   • Total tables: {table_count} files")
        for table_file in self.dirs['tables'].glob('*.csv'):
            print(f"     - {table_file.name}")

        print("\n" + "=" * 80)
        print("[SUCCESS] Complete analysis generated")
        print("=" * 80)

    # =========================================================================
    # UTILITY METHODS
    # =========================================================================

    def _find_best_match(self, dataset, prompt, n_stages, gen_model):
        """Find best matching experiment using scoring system."""
        best_match = None
        best_score = 0

        for exp_id, exp_info in self.exp_lookup.items():
            score = 0

            # Must match dataset
            if exp_info['dataset'] != dataset:
                continue

            # Must match prompt
            if exp_info['prompt'] != prompt:
                continue

            # Must match n_stages
            if exp_info['n_stages'] != n_stages:
                continue

            # Must match generator model
            if exp_info['gen_model'] and gen_model in exp_info['gen_model']:
                score += 3
            elif exp_info['gen_model'] and exp_info['gen_model'] in gen_model:
                score += 2
            else:
                continue

            if score > best_score:
                best_score = score
                best_match = exp_id

        return best_match if best_score >= 3 else None

    @staticmethod
    def _parse_percentage(val):
        """Convert percentage string to float (0-1 range)."""
        if pd.isna(val):
            return None
        if isinstance(val, str):
            return float(val.strip('%')) / 100
        return float(val)


# =============================================================================
# MAIN EXECUTION
# =============================================================================

def main():
    """Main execution function."""
    try:
        generator = ComprehensiveAnalysisGenerator()

        generator.setup() \
            .build_experiment_lookup() \
            .add_per_class_metrics() \
            .fill_missing_f1_from_results_filtered() \
            .add_token_usage_metrics() \
            .generate_confusion_matrices() \
            .generate_bar_charts() \
            .generate_per_dataset_tables() \
            .generate_statistical_comparisons() \
            .generate_token_efficiency_table() \
            .save_updated_summary() \
            .print_final_summary()

        print("\n[NEXT STEP] Review outputs, then clean up old files")
        return 0

    except Exception as e:
        print(f"\n[ERROR] {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
