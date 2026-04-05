"""
Agent Attribution Analysis - Existing Evaluation Data
=====================================================
Analyzes which agent (Generator, Skeptic, Judge) is responsible for errors
or improvements in the multi-agent debate system.

Uses: results_filtered_highquality.csv (existing evaluation data)

Usage:
Run from analysis/: python scripts/agent_attribution_analysis.py
"""

import sys
import io
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from collections import defaultdict, Counter

# Get script directory and project paths
SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_DIR = SCRIPT_DIR.parent
RESULTS_DIR = PROJECT_DIR / "results"
OUTPUT_DIR = RESULTS_DIR / "agent_attribution"

# Configuration
INPUT_FILE = RESULTS_DIR / "results_filtered_highquality.csv"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================================
# ANSWER EXTRACTION (Same as in evaluation)
# ============================================================================

def extract_answer(raw_output: str, dataset: str) -> str:
    """Extract final answer from model output."""
    if not raw_output:
        return "unknown"

    text = raw_output.strip()
    last_line = text.split("\n")[-1].strip().lower()

    if dataset == "pubmedqa":
        # Check for yes/no/maybe
        for label in ["maybe", "yes", "no"]:
            if label == last_line or last_line == f"{label}.":
                return label

        # Check in full text
        if "maybe" in text.lower():
            return "maybe"
        elif "yes" in text.lower():
            return "yes"
        elif "no" in text.lower():
            return "no"

    else:  # MCQ (medqa, mmlu)
        # Check last line for letter
        if last_line in ["a", "b", "c", "d", "a.", "b.", "c.", "d."]:
            return last_line.rstrip(".").upper()

        # Check for pattern like "Answer: A" or "The answer is A"
        import re
        match = re.search(r'\b([A-D])\b', text[-100:])
        if match:
            return match.group(1)

    return "unknown"


# ============================================================================
# LOAD DATA
# ============================================================================

def load_existing_data():
    """Load existing evaluation results with debate logs."""
    if not INPUT_FILE.exists():
        print(f"ERROR: {INPUT_FILE} not found!")
        print(f"Expected location: {INPUT_FILE}")
        exit(1)

    print(f"Loading data from: {INPUT_FILE}")
    df = pd.read_csv(INPUT_FILE)

    print(f"Loaded {len(df)} predictions")
    print(f"Columns: {df.columns.tolist()}")

    # Parse debate_log JSON column
    df['debate_log_parsed'] = df['debate_log'].apply(lambda x: json.loads(x) if pd.notna(x) else {})

    return df


# ============================================================================
# AGENT ATTRIBUTION LOGIC
# ============================================================================

def categorize_debate_outcome(row: pd.Series) -> dict:
    """Categorize the outcome of debate for a single question.

    Returns dict with:
        - category: one of 4 types
        - generator_answer: extracted answer
        - judge_answer: extracted answer
        - gold_answer: correct answer
        - generator_correct: bool
        - judge_correct: bool
        - debate_helped: bool (did debate improve over generator?)
    """
    dataset = row['dataset']
    gold = row['gold']

    debate_log = row['debate_log_parsed']
    generator_output = debate_log.get('generator_output', '')
    judge_output = debate_log.get('judge_output', '')

    # Extract answers
    generator_answer = extract_answer(generator_output, dataset)
    judge_answer = extract_answer(judge_output, dataset) if judge_output else generator_answer

    # Check correctness
    generator_correct = (generator_answer == gold)
    judge_correct = (judge_answer == gold)

    # Categorize
    if generator_correct and judge_correct:
        category = "both_correct"
        debate_helped = False
    elif not generator_correct and judge_correct:
        category = "debate_fixed"
        debate_helped = True
    elif generator_correct and not judge_correct:
        category = "debate_broke"
        debate_helped = False
    else:  # both wrong
        category = "both_wrong"
        debate_helped = False

    return {
        'category': category,
        'generator_answer': generator_answer,
        'judge_answer': judge_answer,
        'gold_answer': gold,
        'generator_correct': generator_correct,
        'judge_correct': judge_correct,
        'debate_helped': debate_helped,
        'dataset': dataset,
        'question_id': row['question_id'],
        'experiment_id': row.get('experiment_id', ''),
    }


def analyze_3stage_data(df: pd.DataFrame) -> pd.DataFrame:
    """Extract and categorize 3-stage experiment results."""

    # Filter to 3-stage experiments only
    df_3stage = df[df['n_stages'] == 3].copy()

    print(f"\nFiltered to {len(df_3stage)} 3-stage predictions")
    print(f"Datasets: {df_3stage['dataset'].unique()}")

    # Apply categorization
    analysis_results = df_3stage.apply(categorize_debate_outcome, axis=1)
    analysis_df = pd.DataFrame(analysis_results.tolist())

    return analysis_df


# ============================================================================
# STATISTICS & REPORTING
# ============================================================================

def compute_attribution_stats(df: pd.DataFrame) -> dict:
    """Compute agent attribution statistics."""

    stats = {}

    # Overall
    stats['total_questions'] = len(df)
    stats['category_counts'] = df['category'].value_counts().to_dict()
    stats['category_percentages'] = (df['category'].value_counts(normalize=True) * 100).to_dict()

    # By dataset
    stats['by_dataset'] = {}
    for dataset in df['dataset'].unique():
        dataset_df = df[df['dataset'] == dataset]
        stats['by_dataset'][dataset] = {
            'total': len(dataset_df),
            'category_counts': dataset_df['category'].value_counts().to_dict(),
            'category_percentages': (dataset_df['category'].value_counts(normalize=True) * 100).to_dict(),
            'generator_accuracy': (dataset_df['generator_correct'].mean() * 100),
            'judge_accuracy': (dataset_df['judge_correct'].mean() * 100),
        }

    # Debate effectiveness
    stats['debate_helped_count'] = df['debate_helped'].sum()
    stats['debate_helped_percentage'] = (df['debate_helped'].mean() * 100)

    # Error analysis
    stats['generator_errors'] = (~df['generator_correct']).sum()
    stats['generator_accuracy'] = (df['generator_correct'].mean() * 100)

    stats['judge_errors'] = (~df['judge_correct']).sum()
    stats['judge_accuracy'] = (df['judge_correct'].mean() * 100)

    stats['accuracy_change'] = stats['judge_accuracy'] - stats['generator_accuracy']

    return stats


def generate_summary_report(df: pd.DataFrame, stats: dict):
    """Generate comprehensive text summary."""

    lines = []
    lines.append("="*70)
    lines.append("AGENT ATTRIBUTION ANALYSIS - EXISTING EVALUATION DATA")
    lines.append("="*70)
    lines.append("")
    lines.append(f"Total 3-Stage Questions Analyzed: {stats['total_questions']}")
    lines.append("")

    # Category breakdown
    lines.append("-"*70)
    lines.append("DEBATE OUTCOME CATEGORIES")
    lines.append("-"*70)
    lines.append("")

    categories = [
        ("both_correct", "✅ Both Correct", "Generator and judge both answered correctly"),
        ("debate_fixed", "🔧 Debate Fixed Error", "Generator wrong → Judge correct (DEBATE HELPED)"),
        ("debate_broke", "❌ Debate Broke Answer", "Generator correct → Judge wrong (DEBATE HURT)"),
        ("both_wrong", "⚠️  Both Wrong", "Generator and judge both answered incorrectly"),
    ]

    for cat_key, cat_name, description in categories:
        count = stats['category_counts'].get(cat_key, 0)
        pct = stats['category_percentages'].get(cat_key, 0)
        lines.append(f"{cat_name}")
        lines.append(f"  Count: {count} ({pct:.1f}%)")
        lines.append(f"  {description}")
        lines.append("")

    # Key metrics
    lines.append("-"*70)
    lines.append("KEY METRICS")
    lines.append("-"*70)
    lines.append("")
    lines.append(f"Generator Accuracy: {stats['generator_accuracy']:.1f}% ({stats['total_questions'] - stats['generator_errors']}/{stats['total_questions']})")
    lines.append(f"Judge Accuracy: {stats['judge_accuracy']:.1f}% ({stats['total_questions'] - stats['judge_errors']}/{stats['total_questions']})")
    lines.append(f"Accuracy Change: {stats['accuracy_change']:+.1f} percentage points")
    lines.append("")
    lines.append(f"Debate Helped (Fixed Errors): {stats['debate_helped_count']} times ({stats['debate_helped_percentage']:.1f}%)")
    lines.append("")

    # Effectiveness ratio
    debate_fixed = stats['category_counts'].get('debate_fixed', 0)
    debate_broke = stats['category_counts'].get('debate_broke', 0)

    if debate_broke > 0:
        ratio = debate_fixed / debate_broke
        lines.append(f"Fix-to-Break Ratio: {ratio:.2f}:1")
        lines.append(f"  (For every error introduced, debate fixed {ratio:.2f} errors)")
    else:
        lines.append(f"Fix-to-Break Ratio: ∞ (no errors introduced)")
    lines.append("")

    # Dataset breakdown
    lines.append("-"*70)
    lines.append("BY DATASET")
    lines.append("-"*70)
    lines.append("")

    for dataset, dataset_stats in stats['by_dataset'].items():
        lines.append(f"{dataset.upper()}:")
        lines.append(f"  Total: {dataset_stats['total']} questions")
        lines.append(f"  Generator Accuracy: {dataset_stats['generator_accuracy']:.1f}%")
        lines.append(f"  Judge Accuracy: {dataset_stats['judge_accuracy']:.1f}%")
        lines.append("")

        for cat_key, cat_name, _ in categories:
            count = dataset_stats['category_counts'].get(cat_key, 0)
            pct = dataset_stats['category_percentages'].get(cat_key, 0)
            lines.append(f"  {cat_name}: {count} ({pct:.1f}%)")
        lines.append("")

    # Interpretation
    lines.append("-"*70)
    lines.append("INTERPRETATION")
    lines.append("-"*70)
    lines.append("")

    if stats['accuracy_change'] > 0:
        lines.append(f"✅ Overall: Debate IMPROVED accuracy by {stats['accuracy_change']:.1f} percentage points")
    elif stats['accuracy_change'] < 0:
        lines.append(f"⚠️  Overall: Debate DECREASED accuracy by {abs(stats['accuracy_change']):.1f} percentage points")
    else:
        lines.append(f"➖ Overall: Debate had NO NET EFFECT on accuracy")

    lines.append("")

    if debate_fixed > debate_broke:
        lines.append(f"✅ Debate fixed {debate_fixed} errors but only broke {debate_broke} correct answers")
        lines.append(f"   → Skeptic/Judge are net positive for error correction")
    elif debate_broke > debate_fixed:
        lines.append(f"⚠️  Debate broke {debate_broke} correct answers but only fixed {debate_fixed} errors")
        lines.append(f"   → Skeptic introduces too much doubt (over-cautious)")
    else:
        lines.append(f"➖ Debate fixed and broke equal numbers of answers ({debate_fixed} each)")

    lines.append("")
    lines.append("="*70)

    summary_text = "\n".join(lines)
    print(summary_text)

    # Save report
    with open(OUTPUT_DIR / "attribution_report.txt", "w", encoding='utf-8') as f:
        f.write(summary_text)
    print(f"\n✓ Saved: {OUTPUT_DIR / 'attribution_report.txt'}")


# ============================================================================
# EXAMPLE EXTRACTION
# ============================================================================

def extract_examples(df: pd.DataFrame):
    """Extract examples for each category."""

    examples = {}

    for category in ['debate_fixed', 'debate_broke', 'both_wrong']:
        category_df = df[df['category'] == category].head(10)  # Top 10 examples

        examples[category] = []
        for _, row in category_df.iterrows():
            examples[category].append({
                'dataset': row['dataset'],
                'question_id': row['question_id'],
                'gold_answer': row['gold_answer'],
                'generator_answer': row['generator_answer'],
                'judge_answer': row['judge_answer'],
            })

    # Save as JSON
    with open(OUTPUT_DIR / "attribution_examples.json", "w") as f:
        json.dump(examples, f, indent=2)
    print(f"✓ Saved: {OUTPUT_DIR / 'attribution_examples.json'}")

    return examples


# ============================================================================
# VISUALIZATIONS
# ============================================================================

def create_visualizations(df: pd.DataFrame, stats: dict):
    """Generate attribution visualizations."""

    print("\n" + "="*70)
    print("GENERATING VISUALIZATIONS")
    print("="*70)

    sns.set_style("whitegrid")

    # 1. Overall category distribution
    fig, ax = plt.subplots(figsize=(10, 6))

    category_names = {
        'both_correct': 'Both Correct\n(No Error)',
        'debate_fixed': 'Debate Fixed\n(Skeptic Caught Error)',
        'debate_broke': 'Debate Broke\n(Skeptic Introduced Doubt)',
        'both_wrong': 'Both Wrong\n(Couldn\'t Fix)',
    }

    category_counts = df['category'].value_counts()
    category_counts.index = category_counts.index.map(category_names)
    colors = ['#2ecc71', '#3498db', '#e74c3c', '#f39c12']

    category_counts.plot(kind='bar', ax=ax, color=colors)
    ax.set_title('Agent Attribution: Debate Outcome Categories', fontsize=14, fontweight='bold')
    ax.set_xlabel('Category')
    ax.set_ylabel('Number of Questions')
    ax.set_xticklabels(ax.get_xticklabels(), rotation=45, ha='right')

    # Add percentage labels on bars
    for i, (idx, val) in enumerate(category_counts.items()):
        pct = (val / len(df)) * 100
        ax.text(i, val + 10, f'{pct:.1f}%', ha='center', va='bottom', fontweight='bold')

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "attribution_categories.png", dpi=300, bbox_inches='tight')
    print(f"✓ Saved: {OUTPUT_DIR / 'attribution_categories.png'}")
    plt.close()

    # 2. By dataset comparison
    datasets = sorted(df['dataset'].unique())
    fig, axes = plt.subplots(1, len(datasets), figsize=(5*len(datasets), 5))

    if len(datasets) == 1:
        axes = [axes]

    for idx, dataset in enumerate(datasets):
        dataset_df = df[df['dataset'] == dataset]
        category_counts = dataset_df['category'].value_counts()
        category_counts.index = category_counts.index.map(category_names)

        category_counts.plot(kind='bar', ax=axes[idx], color=colors)
        axes[idx].set_title(f'{dataset.upper()}', fontsize=12, fontweight='bold')
        axes[idx].set_xlabel('')
        axes[idx].set_ylabel('Count' if idx == 0 else '')
        axes[idx].set_xticklabels(axes[idx].get_xticklabels(), rotation=45, ha='right', fontsize=8)

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "attribution_by_dataset.png", dpi=300, bbox_inches='tight')
    print(f"✓ Saved: {OUTPUT_DIR / 'attribution_by_dataset.png'}")
    plt.close()

    # 3. Generator vs Judge accuracy comparison
    fig, ax = plt.subplots(figsize=(10, 6))

    dataset_stats = []
    for dataset in sorted(df['dataset'].unique()):
        dataset_df = df[df['dataset'] == dataset]
        dataset_stats.append({
            'Dataset': dataset.upper(),
            'Generator': dataset_df['generator_correct'].mean() * 100,
            'Judge': dataset_df['judge_correct'].mean() * 100,
        })

    comparison_df = pd.DataFrame(dataset_stats)
    comparison_df.set_index('Dataset', inplace=True)

    comparison_df.plot(kind='bar', ax=ax, color=['#3498db', '#e74c3c'])
    ax.set_title('Generator vs Judge Accuracy by Dataset', fontsize=14, fontweight='bold')
    ax.set_xlabel('Dataset')
    ax.set_ylabel('Accuracy (%)')
    ax.set_xticklabels(ax.get_xticklabels(), rotation=0)
    ax.legend(['Generator (1-stage)', 'Judge (3-stage)'])
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f'{y:.0f}%'))
    ax.set_ylim(0, 100)

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "generator_vs_judge.png", dpi=300, bbox_inches='tight')
    print(f"✓ Saved: {OUTPUT_DIR / 'generator_vs_judge.png'}")
    plt.close()


# ============================================================================
# EXPORT TABLES
# ============================================================================

def export_tables(df: pd.DataFrame, stats: dict):
    """Export paper-ready tables."""

    # Table 1: Overall attribution
    table1_data = []
    for category in ['both_correct', 'debate_fixed', 'debate_broke', 'both_wrong']:
        count = stats['category_counts'].get(category, 0)
        pct = stats['category_percentages'].get(category, 0)
        table1_data.append({
            'Category': category.replace('_', ' ').title(),
            'Count': count,
            'Percentage': f"{pct:.1f}%",
        })

    table1_df = pd.DataFrame(table1_data)
    table1_df.to_csv(OUTPUT_DIR / "attribution_table.csv", index=False)

    # LaTeX version
    latex_table = table1_df.to_latex(index=False, escape=False)
    with open(OUTPUT_DIR / "attribution_table.tex", "w") as f:
        f.write(latex_table)

    print(f"✓ Saved: {OUTPUT_DIR / 'attribution_table.csv'}")
    print(f"✓ Saved: {OUTPUT_DIR / 'attribution_table.tex'}")

    # Table 2: By dataset
    table2_data = []
    for dataset, dataset_stats in stats['by_dataset'].items():
        for category in ['both_correct', 'debate_fixed', 'debate_broke', 'both_wrong']:
            count = dataset_stats['category_counts'].get(category, 0)
            pct = dataset_stats['category_percentages'].get(category, 0)
            table2_data.append({
                'Dataset': dataset.upper(),
                'Category': category.replace('_', ' ').title(),
                'Count': count,
                'Percentage': f"{pct:.1f}%",
            })

    table2_df = pd.DataFrame(table2_data)
    table2_df.to_csv(OUTPUT_DIR / "attribution_by_dataset_table.csv", index=False)
    print(f"✓ Saved: {OUTPUT_DIR / 'attribution_by_dataset_table.csv'}")


# ============================================================================
# MAIN
# ============================================================================

def main():
    print("="*70)
    print("AGENT ATTRIBUTION ANALYSIS - EXISTING EVALUATION DATA")
    print("="*70)

    # Load data
    df_raw = load_existing_data()

    # Analyze 3-stage experiments
    print("\nAnalyzing 3-stage debate outcomes...")
    df = analyze_3stage_data(df_raw)

    if len(df) == 0:
        print("ERROR: No 3-stage experiments found in data!")
        exit(1)

    print(f"Analyzed {len(df)} questions from 3-stage experiments")

    # Compute statistics
    stats = compute_attribution_stats(df)

    # Generate report
    generate_summary_report(df, stats)

    # Extract examples
    extract_examples(df)

    # Create visualizations
    create_visualizations(df, stats)

    # Export tables
    export_tables(df, stats)

    print("\n" + "="*70)
    print("✅ ANALYSIS COMPLETE")
    print("="*70)
    print(f"\nAll results saved to: {OUTPUT_DIR}/")
    print("\nGenerated files:")
    print("  - attribution_report.txt (full summary)")
    print("  - attribution_examples.json (sample cases)")
    print("  - attribution_categories.png (overall chart)")
    print("  - attribution_by_dataset.png (dataset comparison)")
    print("  - generator_vs_judge.png (accuracy comparison)")
    print("  - attribution_table.csv + .tex (paper table)")
    print("  - attribution_by_dataset_table.csv (detailed breakdown)")
    print("\n📊 Ready for your report!")


if __name__ == "__main__":
    main()
