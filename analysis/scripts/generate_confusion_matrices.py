#!/usr/bin/env python3
"""
Generate confusion matrices for key experiments from EXPERIMENTS_SUMMARY_TABLE.csv
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import json
from pathlib import Path

# Read data
results_dir = Path(__file__).parent.parent / 'results' / 'analysis_results'
db_exp = pd.read_csv(results_dir / 'db_experiments.csv')

# Parse full_metrics to get confusion matrices
def get_confusion_matrix(experiment_id):
    """Extract confusion matrix from experiment"""
    row = db_exp[db_exp['id'] == experiment_id]
    if len(row) == 0:
        return None

    metrics = json.loads(row.iloc[0]['full_metrics'])
    conf_matrix = metrics.get('confusion_matrix', {})

    if not conf_matrix:
        return None

    # Get all unique labels
    all_labels = set()
    for true_label, predictions in conf_matrix.items():
        all_labels.add(true_label)
        all_labels.update(predictions.keys())

    # Remove 'unknown' from labels for cleaner visualization
    labels = sorted([l for l in all_labels if l != 'unknown'])

    # Build matrix
    matrix = np.zeros((len(labels), len(labels)))
    for i, true_label in enumerate(labels):
        if true_label in conf_matrix:
            for j, pred_label in enumerate(labels):
                matrix[i, j] = conf_matrix[true_label].get(pred_label, 0)

    return matrix, labels

# Key experiments to visualize
experiments = [
    # Best performance - MMLU
    {
        'id': 'mmlu_v2_structured_20260318_010349_539406',  # Need to find actual ID
        'title': 'MMLU - Best Performance (94%)',
        'dataset': 'mmlu',
        'prompt': 'v2_structured',
        'model': 'llama-3.3-70b-versatile'
    },
    # Worst performance - PubMedQA
    {
        'id': 'pubmedqa_v3_skeptic_strict_20260318_012407_660127',
        'title': 'PubMedQA - Worst Performance (31%)',
        'dataset': 'pubmedqa',
        'prompt': 'v3_skeptic_strict',
        'model': 'qwen/qwen3-32b'
    },
]

# Find actual experiment IDs
print("Available experiments in database:")
print(db_exp[['id', 'dataset', 'prompt_version', 'model', 'accuracy']].to_string())
print("\n")

# Generate confusion matrices for all 3-stage experiments with good quality
good_experiments = db_exp[
    (db_exp['n_stages'] == 3) &
    (db_exp['status'] == 'completed')
].copy()

# Create output directory
output_dir = results_dir / 'confusion_matrices'
output_dir.mkdir(exist_ok=True)

print(f"Generating confusion matrices for {len(good_experiments)} experiments...\n")

for idx, row in good_experiments.iterrows():
    exp_id = row['id']
    dataset = row['dataset']
    prompt = row['prompt_version']
    model = row['model']
    accuracy = row['accuracy']

    result = get_confusion_matrix(exp_id)
    if result is None:
        continue

    matrix, labels = result

    # Create figure
    fig, ax = plt.subplots(figsize=(8, 6))

    # Plot heatmap
    sns.heatmap(matrix, annot=True, fmt='g', cmap='Blues',
                xticklabels=labels, yticklabels=labels,
                cbar_kws={'label': 'Count'}, ax=ax)

    ax.set_xlabel('Predicted Label')
    ax.set_ylabel('True Label')
    ax.set_title(f'{dataset.upper()} - {prompt}\n{model}\nAccuracy: {accuracy*100:.0f}%')

    # Save
    filename = f'confusion_matrix_{dataset}_{prompt}_{model.replace("/", "_")}.png'
    filepath = output_dir / filename
    plt.tight_layout()
    plt.savefig(filepath, dpi=150, bbox_inches='tight')
    plt.close()

    print(f"Saved: {filename}")

print(f"\nAll confusion matrices saved to: {output_dir}")
