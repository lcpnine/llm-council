#!/usr/bin/env python3
"""
Add Δ Accuracy column to EXPERIMENTS_SUMMARY_TABLE.csv
"""
import pandas as pd
from pathlib import Path

# Read the CSV
results_dir = Path(__file__).parent.parent / 'results' / 'analysis_results'
csv_path = results_dir / 'EXPERIMENTS_SUMMARY_TABLE.csv'
df = pd.read_csv(csv_path)

# Calculate baseline averages for each dataset
baselines = {}
for dataset in df['Dataset'].unique():
    baseline_rows = df[(df['Dataset'] == dataset) & (df['Setup'] == '1-stage (Baseline)')]
    # Convert accuracy strings to floats
    accuracies = baseline_rows['Accuracy'].str.rstrip('%').astype(float)
    baselines[dataset] = accuracies.mean()

print("Baseline averages:")
for dataset, avg in baselines.items():
    print(f"  {dataset}: {avg:.1f}%")

# Add Δ Accuracy column
delta_accuracy = []
for idx, row in df.iterrows():
    if row['Setup'] == '1-stage (Baseline)':
        delta_accuracy.append('-')
    else:
        # 3-stage experiment
        current_acc = float(row['Accuracy'].rstrip('%'))
        baseline_acc = baselines[row['Dataset']]
        delta = current_acc - baseline_acc
        delta_accuracy.append(f"{delta:+.1f}%")

# Insert the new column after "Accuracy"
acc_col_idx = df.columns.get_loc('Accuracy')
df.insert(acc_col_idx + 1, 'Δ Accuracy', delta_accuracy)

# Save the updated CSV
df.to_csv(csv_path, index=False)
print(f"\nUpdated CSV saved to: {csv_path}")
print(f"Added 'Δ Accuracy' column after 'Accuracy'")
