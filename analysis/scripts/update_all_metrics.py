"""
Production Script: Update All Metrics in EXPERIMENTS_SUMMARY_TABLE.csv

This is the SINGLE authoritative script for adding all evaluation metrics.
Run this script to update or recalculate all metrics in one pass.

Metrics calculated:
- F1 Macro: Macro-averaged F1 score across all classes
- Maybe Recall: Recall for "maybe" class in PubMedQA
- CI (95%): Wilson score confidence intervals
- Cohen's d: Effect size for debate experiments

Author: Analysis Team
Version: 1.0.0
Date: 2026-04-12
"""

import pandas as pd
import numpy as np
import json
from scipy import stats
from sklearn.metrics import f1_score, precision_recall_fscore_support
import warnings
warnings.filterwarnings('ignore')


class MetricsCalculator:
    """Main class for calculating and updating all metrics."""

    def __init__(self):
        self.summary_df = None
        self.exp_lookup = {}
        self.matched_count = 0

    # =========================================================================
    # STEP 1: BUILD EXPERIMENT LOOKUP FROM JSON
    # =========================================================================

    def build_experiment_lookup(self, json_path='../data/exports/experiments_all_2026-04-10-4.json'):
        """
        Build lookup dictionary with experiment config and metrics.
        This includes f1_macro and maybe_recall directly from JSON.
        """
        print("[1/5] Building experiment lookup from JSON...")

        with open(json_path, 'r', encoding='utf-8') as f:
            json_file = json.load(f)

        experiments = json_file.get('experiments', json_file)

        for exp in experiments:
            exp_id = exp.get('id', '')
            config = exp.get('config', {})
            dataset = exp.get('dataset', '').upper()
            prompt = exp.get('prompt_version', '')
            n_stages = exp.get('n_stages', 1)

            # Get model names from config
            gen_model = config.get('generator_model', config.get('model', ''))
            skep_model = config.get('skeptic_model', '')
            judge_model = config.get('judge_model', '')

            # Normalize model names (remove provider prefix)
            def normalize_model(m):
                if not m:
                    return None
                if '/' in m:
                    return m.split('/')[1]
                return m

            gen_model = normalize_model(gen_model)
            skep_model = normalize_model(skep_model) if skep_model else None
            judge_model = normalize_model(judge_model) if judge_model else None

            # Get metrics directly from JSON
            f1_macro = exp.get('f1_macro')
            maybe_recall = exp.get('maybe_recall')

            self.exp_lookup[exp_id] = {
                'dataset': dataset,
                'prompt': prompt,
                'n_stages': n_stages,
                'gen_model': gen_model,
                'skep_model': skep_model,
                'judge_model': judge_model,
                'f1_macro': f1_macro,
                'maybe_recall': maybe_recall
            }

        print(f"      Created lookup for {len(self.exp_lookup)} experiments")
        return self

    # =========================================================================
    # STEP 2: MATCH AND UPDATE F1 METRICS
    # =========================================================================

    def match_and_update_f1(self):
        """
        Match summary table rows to experiment lookup using robust algorithm.
        Updates F1_Macro and Maybe_Recall columns.
        """
        print("[2/5] Matching experiments and updating F1 metrics...")

        # Initialize columns if they don't exist
        if 'F1_Macro' not in self.summary_df.columns:
            self.summary_df['F1_Macro'] = None
        if 'Maybe_Recall' not in self.summary_df.columns:
            self.summary_df['Maybe_Recall'] = None

        self.matched_count = 0

        for idx, row in self.summary_df.iterrows():
            dataset = str(row['Dataset']).upper()
            prompt = str(row['Prompt Version'])
            setup = str(row['Setup'])
            gen_model = str(row['Generator Model'])

            if pd.isna(gen_model) or gen_model == 'nan':
                continue

            # Normalize gen_model
            if '/' in gen_model:
                gen_model = gen_model.split('/')[1]

            # Determine expected n_stages
            if '1-stage' in setup:
                expected_stages = 1
            else:
                expected_stages = 3

            # Find best matching experiment using scoring system
            best_match = None
            best_score = 0

            for exp_id, exp_info in self.exp_lookup.items():
                score = 0

                # Must match dataset
                if exp_info['dataset'] != dataset:
                    continue

                # Must match prompt version
                if exp_info['prompt'] != prompt:
                    continue

                # Must match n_stages
                if exp_info['n_stages'] != expected_stages:
                    continue

                # Must match generator model
                if exp_info['gen_model'] and gen_model in exp_info['gen_model']:
                    score += 3
                elif exp_info['gen_model'] and exp_info['gen_model'] in gen_model:
                    score += 2
                else:
                    continue  # Must match generator

                # Check if heterogeneous matches
                if 'Heterogeneous' in setup:
                    skep_model_summary = str(row.get('Skeptic Model', ''))
                    judge_model_summary = str(row.get('Judge Model', ''))

                    if '/' in skep_model_summary:
                        skep_model_summary = skep_model_summary.split('/')[1]
                    if '/' in judge_model_summary:
                        judge_model_summary = judge_model_summary.split('/')[1]

                    # Check skeptic and judge match
                    if exp_info['skep_model'] and skep_model_summary in exp_info['skep_model']:
                        score += 1
                    if exp_info['judge_model'] and judge_model_summary in exp_info['judge_model']:
                        score += 1

                if score > best_score:
                    best_score = score
                    best_match = exp_id

            # Update if good match found
            if best_match and best_score >= 3:
                match_info = self.exp_lookup[best_match]
                self.summary_df.at[idx, 'F1_Macro'] = match_info['f1_macro']
                self.summary_df.at[idx, 'Maybe_Recall'] = match_info['maybe_recall']
                self.matched_count += 1

        print(f"      Matched {self.matched_count}/{len(self.summary_df)} experiments")
        return self

    # =========================================================================
    # STEP 3: CALCULATE CONFIDENCE INTERVALS
    # =========================================================================

    def calculate_confidence_intervals(self):
        """Calculate Wilson score 95% confidence intervals for all experiments."""
        print("[3/5] Calculating 95% confidence intervals...")

        # Initialize columns
        self.summary_df['CI_Lower'] = None
        self.summary_df['CI_Upper'] = None
        self.summary_df['CI_Width'] = None

        for idx, row in self.summary_df.iterrows():
            acc = self._parse_percentage(row['Accuracy'])

            if acc is not None:
                ci_lower, ci_upper = self._wilson_score_interval(acc, n=100)
                self.summary_df.at[idx, 'CI_Lower'] = ci_lower
                self.summary_df.at[idx, 'CI_Upper'] = ci_upper
                self.summary_df.at[idx, 'CI_Width'] = ci_upper - ci_lower

        ci_count = self.summary_df['CI_Lower'].notna().sum()
        print(f"      Calculated CI for {ci_count}/{len(self.summary_df)} experiments")
        return self

    # =========================================================================
    # STEP 4: CALCULATE EFFECT SIZES
    # =========================================================================

    def calculate_effect_sizes(self):
        """Calculate Cohen's d effect sizes for debate experiments."""
        print("[4/5] Calculating Cohen's d effect sizes...")

        # Initialize columns
        self.summary_df['Cohens_d'] = None
        self.summary_df['Effect_Size'] = None

        for idx, row in self.summary_df.iterrows():
            setup = row['Setup']

            # Only for debate experiments
            if '3-stage' not in setup and 'Debate' not in setup:
                continue

            acc = self._parse_percentage(row['Accuracy'])
            delta_acc = row['Δ Accuracy']

            if acc is None or pd.isna(delta_acc):
                continue

            # Parse delta
            if isinstance(delta_acc, str):
                delta_val = float(delta_acc.strip('%').replace('+', '')) / 100
            else:
                delta_val = float(delta_acc)

            # Calculate baseline accuracy
            baseline_acc = acc - delta_val

            # Calculate Cohen's d
            cohens_d = self._cohens_d_for_proportions(baseline_acc, acc)
            self.summary_df.at[idx, 'Cohens_d'] = cohens_d
            self.summary_df.at[idx, 'Effect_Size'] = self._interpret_effect_size(cohens_d)

        # Convert to numeric
        self.summary_df['Cohens_d'] = pd.to_numeric(self.summary_df['Cohens_d'], errors='coerce')
        self.summary_df['CI_Lower'] = pd.to_numeric(self.summary_df['CI_Lower'], errors='coerce')
        self.summary_df['CI_Upper'] = pd.to_numeric(self.summary_df['CI_Upper'], errors='coerce')
        self.summary_df['CI_Width'] = pd.to_numeric(self.summary_df['CI_Width'], errors='coerce')

        cohens_count = self.summary_df['Cohens_d'].notna().sum()
        print(f"      Calculated Cohen's d for {cohens_count} debate experiments")
        return self

    # =========================================================================
    # STEP 5: ORGANIZE AND SAVE
    # =========================================================================

    def organize_and_save(self, output_path='results/EXPERIMENTS_SUMMARY_TABLE.csv'):
        """Organize columns and save to file."""
        print("[5/5] Organizing columns and saving...")

        # Organize column order
        cols = self.summary_df.columns.tolist()

        if 'p-value' in cols:
            pval_idx = cols.index('p-value')
            stat_cols = ['CI_Lower', 'CI_Upper', 'CI_Width', 'Cohens_d', 'Effect_Size']

            # Remove stat columns from current position
            for col in stat_cols:
                if col in cols:
                    cols.remove(col)

            # Insert after p-value
            cols = cols[:pval_idx+1] + stat_cols + cols[pval_idx+1:]
            self.summary_df = self.summary_df[cols]

        # Save
        self.summary_df.to_csv(output_path, index=False)
        print(f"      Saved to: {output_path}")
        return self

    # =========================================================================
    # UTILITY METHODS
    # =========================================================================

    @staticmethod
    def _parse_percentage(val):
        """Convert percentage string to float (0-1 range)."""
        if pd.isna(val):
            return None
        if isinstance(val, str):
            return float(val.strip('%')) / 100
        return float(val)

    @staticmethod
    def _wilson_score_interval(p, n=100, confidence=0.95):
        """Wilson score confidence interval (more accurate than normal approximation)."""
        if p is None or pd.isna(p):
            return None, None

        z = stats.norm.ppf((1 + confidence) / 2)
        denominator = 1 + z**2/n
        centre = (p + z**2/(2*n)) / denominator
        offset = z * np.sqrt(p*(1-p)/n + z**2/(4*n**2)) / denominator

        return centre - offset, centre + offset

    @staticmethod
    def _cohens_d_for_proportions(p1, p2):
        """Calculate Cohen's d for two proportions."""
        if p1 is None or p2 is None or pd.isna(p1) or pd.isna(p2):
            return None

        pooled_sd = np.sqrt((p1*(1-p1) + p2*(1-p2)) / 2)
        if pooled_sd == 0:
            return 0.0

        return (p2 - p1) / pooled_sd

    @staticmethod
    def _interpret_effect_size(d):
        """Interpret Cohen's d using standard thresholds."""
        if d is None or pd.isna(d):
            return None

        abs_d = abs(d)
        if abs_d < 0.2:
            return 'negligible'
        elif abs_d < 0.5:
            return 'small'
        elif abs_d < 0.8:
            return 'medium'
        else:
            return 'large'

    # =========================================================================
    # REPORTING
    # =========================================================================

    def print_summary(self):
        """Print summary statistics."""
        print("\n" + "=" * 80)
        print("METRICS SUMMARY")
        print("=" * 80)

        print(f"\nTotal experiments: {len(self.summary_df)}")
        print(f"  F1 Macro:          {self.summary_df['F1_Macro'].notna().sum()}/{len(self.summary_df)}")
        print(f"  Maybe Recall:      {self.summary_df['Maybe_Recall'].notna().sum()}/{len(self.summary_df)} (PubMedQA only)")
        print(f"  Confidence Intervals: {self.summary_df['CI_Lower'].notna().sum()}/{len(self.summary_df)}")
        print(f"  Cohen's d:         {self.summary_df['Cohens_d'].notna().sum()}/{len(self.summary_df)} (debate only)")

        # Effect size distribution
        print("\nEffect Size Distribution:")
        effect_counts = self.summary_df['Effect_Size'].value_counts()
        for effect, count in effect_counts.items():
            print(f"  {effect:12s}: {count:2d} experiments")

        # Notable results
        debate_df = self.summary_df[self.summary_df['Cohens_d'].notna()]

        if len(debate_df) > 0:
            print("\nTop 3 Positive Effects:")
            best = debate_df.nlargest(3, 'Cohens_d')
            for _, row in best.iterrows():
                print(f"  {row['Dataset']:10s} + {row['Prompt Version']:20s}")
                print(f"    d={row['Cohens_d']:.3f} ({row['Effect_Size']}), Acc={row['Accuracy']}, Delta={row['Δ Accuracy']}")

            print("\nTop 3 Negative Effects:")
            worst = debate_df.nsmallest(3, 'Cohens_d')
            for _, row in worst.iterrows():
                print(f"  {row['Dataset']:10s} + {row['Prompt Version']:20s}")
                print(f"    d={row['Cohens_d']:.3f} ({row['Effect_Size']}), Acc={row['Accuracy']}, Delta={row['Δ Accuracy']}")


# =============================================================================
# MAIN EXECUTION
# =============================================================================

def main():
    """Main execution function."""
    print("=" * 80)
    print("UPDATE ALL METRICS - PRODUCTION SCRIPT")
    print("=" * 80)
    print("\nThis script updates EXPERIMENTS_SUMMARY_TABLE.csv with all metrics:")
    print("  • F1 Macro and Maybe Recall (from JSON experiment data)")
    print("  • 95% Confidence Intervals (Wilson score method)")
    print("  • Cohen's d Effect Sizes (for debate experiments)")
    print("=" * 80 + "\n")

    try:
        # Load summary table
        summary_df = pd.read_csv('results/EXPERIMENTS_SUMMARY_TABLE.csv')
        print(f"[0/5] Loaded EXPERIMENTS_SUMMARY_TABLE.csv ({len(summary_df)} experiments)\n")

        # Create calculator and run pipeline
        calculator = MetricsCalculator()
        calculator.summary_df = summary_df

        calculator \
            .build_experiment_lookup() \
            .match_and_update_f1() \
            .calculate_confidence_intervals() \
            .calculate_effect_sizes() \
            .organize_and_save()

        # Report
        calculator.print_summary()

        print("\n" + "=" * 80)
        print("[SUCCESS] All metrics updated successfully")
        print("=" * 80)
        print(f"\nTotal columns: {len(calculator.summary_df.columns)}")
        print("\nColumns updated:")
        print("  • F1_Macro: Macro-averaged F1 score")
        print("  • Maybe_Recall: Recall for 'maybe' class (PubMedQA)")
        print("  • CI_Lower, CI_Upper, CI_Width: 95% confidence intervals")
        print("  • Cohens_d, Effect_Size: Effect sizes for debate experiments")
        print("=" * 80 + "\n")

        return 0

    except Exception as e:
        print(f"\n[ERROR] {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
