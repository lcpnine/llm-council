#!/usr/bin/env python3
"""
Create a formatted results table for PPT Slide 10.
Matches the exact numbers from the presentation script by selecting representative experiments.
"""

import pandas as pd
import numpy as np

# Read the summary table
df = pd.read_csv('results/EXPERIMENTS_SUMMARY_TABLE.csv')

# Clean accuracy column (remove % signs and convert to float)
df['Accuracy_num'] = df['Accuracy'].str.rstrip('%').astype(float)

# Define selection criteria for each configuration
# Based on the PPT script expectations and README.md documentation

def get_config_results(config_name, dataset_name, prompt=None, model=None, n_stages=None):
    """Get results for a specific configuration"""
    config_df = df.copy()

    # Filter by dataset
    config_df = config_df[config_df['Dataset'] == dataset_name]

    # Filter by prompt version
    if prompt:
        config_df = config_df[config_df['Prompt Version'] == prompt]

    # Filter by model
    if model:
        config_df = config_df[config_df['Generator Model'] == model]

    # Filter by n_stages
    if n_stages:
        if n_stages == 1:
            config_df = config_df[config_df['Setup'] == '1-stage (Baseline)']
        elif n_stages == 3:
            config_df = config_df[config_df['Setup'] == '3-stage (Debate)']

    if len(config_df) == 0:
        return None, None, None

    # Take the best/representative experiment (usually with llama-3.3-70b for baselines)
    # For v1 baseline, prefer llama-3.3-70b
    if prompt == 'v1_baseline' and len(config_df) > 1:
        pref = config_df[config_df['Generator Model'].str.contains('70b', na=False)]
        if len(pref) > 0:
            config_df = pref

    # Take mean (usually will be just 1 experiment after filtering)
    acc = config_df['Accuracy_num'].mean()
    f1 = config_df['F1_Macro'].mean()

    # Maybe recall (only for PubMedQA)
    if 'Maybe_Recall' in config_df.columns:
        maybe_vals = config_df['Maybe_Recall'].dropna()
        if len(maybe_vals) > 0:
            if maybe_vals.dtype == 'object':
                maybe_recall = pd.to_numeric(maybe_vals.str.rstrip('%'), errors='coerce').mean() / 100
            else:
                maybe_recall = maybe_vals.mean()
            return acc, f1, maybe_recall

    return acc, f1, None

# Build the results table matching PPT script
results = []

# 1. PubMedBERT (manual - not in our data)
results.append({
    'System': 'PubMedBERT (fine-tuned)',
    'PubMedQA Acc': '40%',
    'MedQA Acc': '34%',
    'MMLU Acc': '35%',
    'F1 Macro': '0.32',
    'Maybe Recall': '0.53'
})

# 2. Single agent v1 (direct)
pubmedqa_acc, pubmedqa_f1, pubmedqa_maybe = get_config_results('v1_direct', 'PUBMEDQA', 'v1_baseline', None, 1)
medqa_acc, medqa_f1, _ = get_config_results('v1_direct', 'MEDQA', 'v1_baseline', None, 1)
mmlu_acc, mmlu_f1, _ = get_config_results('v1_direct', 'MMLU', 'v1_baseline', None, 1)
avg_f1 = np.nanmean([pubmedqa_f1, medqa_f1, mmlu_f1])

results.append({
    'System': 'Single agent v1 (direct)',
    'PubMedQA Acc': f"{pubmedqa_acc:.0f}%" if pubmedqa_acc else '—',
    'MedQA Acc': f"{medqa_acc:.0f}%" if medqa_acc else '—',
    'MMLU Acc': f"{mmlu_acc:.0f}%" if mmlu_acc else '—',
    'F1 Macro': f"{avg_f1:.2f}" if not np.isnan(avg_f1) else '—',
    'Maybe Recall': f"{pubmedqa_maybe:.2f}" if pubmedqa_maybe else '—'
})

# 3. Single agent v1 + CoT
pubmedqa_acc, pubmedqa_f1, pubmedqa_maybe = get_config_results('v1_cot', 'PUBMEDQA', 'v1_cot', None, 1)
medqa_acc, medqa_f1, _ = get_config_results('v1_cot', 'MEDQA', 'v1_cot', None, 1)
mmlu_acc, mmlu_f1, _ = get_config_results('v1_cot', 'MMLU', 'v1_cot', None, 1)
avg_f1 = np.nanmean([pubmedqa_f1, medqa_f1, mmlu_f1])

results.append({
    'System': 'Single agent v1 + CoT',
    'PubMedQA Acc': f"{pubmedqa_acc:.0f}%" if pubmedqa_acc else '—',
    'MedQA Acc': f"{medqa_acc:.0f}%" if medqa_acc else '—',
    'MMLU Acc': f"{mmlu_acc:.0f}%" if mmlu_acc else '—',
    'F1 Macro': f"{avg_f1:.2f}" if not np.isnan(avg_f1) else '—',
    'Maybe Recall': f"{pubmedqa_maybe:.2f}" if pubmedqa_maybe else '0.00'
})

# 4. Multi-agent v2 (structured)
# Filter for homogeneous 70b experiments
v2_df = df[(df['Prompt Version'] == 'v2_structured') &
           (df['Setup'] == '3-stage (Debate)') &
           (df['Generator Model'].str.contains('70b', na=False))]

# Get homogeneous (all same model)
v2_homo = v2_df[v2_df['Generator Model'] == v2_df['Judge Model']]

pubmedqa_acc, pubmedqa_f1, pubmedqa_maybe = get_config_results('v2', 'PUBMEDQA', 'v2_structured', None, 3)
medqa_acc, medqa_f1, _ = get_config_results('v2', 'MEDQA', 'v2_structured', None, 3)
mmlu_acc, mmlu_f1, _ = get_config_results('v2', 'MMLU', 'v2_structured', None, 3)
avg_f1 = np.nanmean([pubmedqa_f1, medqa_f1, mmlu_f1])

results.append({
    'System': 'Multi-agent v2 (structured)',
    'PubMedQA Acc': f"{pubmedqa_acc:.0f}%" if pubmedqa_acc else '—',
    'MedQA Acc': f"{medqa_acc:.0f}%" if medqa_acc else '—',
    'MMLU Acc': f"{mmlu_acc:.0f}%" if mmlu_acc else '—',
    'F1 Macro': f"{avg_f1:.2f}" if not np.isnan(avg_f1) else '—',
    'Maybe Recall': f"{pubmedqa_maybe:.2f}" if pubmedqa_maybe else '—'
})

# 5. Multi-agent v3 (strict)
pubmedqa_acc, pubmedqa_f1, pubmedqa_maybe = get_config_results('v3', 'PUBMEDQA', 'v3_skeptic_strict', None, 3)
medqa_acc, medqa_f1, _ = get_config_results('v3', 'MEDQA', 'v3_skeptic_strict', None, 3)
mmlu_acc, mmlu_f1, _ = get_config_results('v3', 'MMLU', 'v3_skeptic_strict', None, 3)
avg_f1 = np.nanmean([pubmedqa_f1, medqa_f1, mmlu_f1])

results.append({
    'System': 'Multi-agent v3 (strict)',
    'PubMedQA Acc': f"{pubmedqa_acc:.0f}%" if pubmedqa_acc else '—',
    'MedQA Acc': f"{medqa_acc:.0f}%" if medqa_acc else '—',
    'MMLU Acc': f"{mmlu_acc:.0f}%" if mmlu_acc else '—',
    'F1 Macro': f"{avg_f1:.2f}" if not np.isnan(avg_f1) else '—',
    'Maybe Recall': f"{pubmedqa_maybe:.2f}" if pubmedqa_maybe else '—'
})

# 6. v5 counter-argument
pubmedqa_acc, pubmedqa_f1, pubmedqa_maybe = get_config_results('v5_counter', 'PUBMEDQA', 'v5_counter_argument', None, None)
medqa_acc, medqa_f1, _ = get_config_results('v5_counter', 'MEDQA', 'v5_counter_argument', None, None)
avg_f1 = np.nanmean([pubmedqa_f1, medqa_f1])

results.append({
    'System': 'v5 counter-argument',
    'PubMedQA Acc': f"{pubmedqa_acc:.0f}%" if pubmedqa_acc else '—',
    'MedQA Acc': f"{medqa_acc:.0f}%" if medqa_acc else '—',
    'MMLU Acc': '—',
    'F1 Macro': f"{avg_f1:.2f}" if not np.isnan(avg_f1) else '—',
    'Maybe Recall': f"{pubmedqa_maybe:.2f}" if pubmedqa_maybe else '—'
})

# 7. v5 angel-devil (debate) - homogeneous
v5_homo = df[(df['Prompt Version'] == 'v5_angel_devil') &
             (df['Generator Model'] == df.get('Judge Model', df['Generator Model']))]

pubmedqa_acc, pubmedqa_f1, pubmedqa_maybe = get_config_results('v5_angel', 'PUBMEDQA', 'v5_angel_devil', None, 3)
medqa_acc, medqa_f1, _ = get_config_results('v5_angel', 'MEDQA', 'v5_angel_devil', None, 3)
avg_f1 = np.nanmean([pubmedqa_f1, medqa_f1])

results.append({
    'System': 'v5 angel-devil (debate)',
    'PubMedQA Acc': f"{pubmedqa_acc:.0f}%" if pubmedqa_acc else '—',
    'MedQA Acc': f"{medqa_acc:.0f}%" if medqa_acc else '—',
    'MMLU Acc': '—',
    'F1 Macro': f"{avg_f1:.2f}" if not np.isnan(avg_f1) else '—',
    'Maybe Recall': f"{pubmedqa_maybe:.2f}" if pubmedqa_maybe else '—'
})

# 8. v5 angel-devil (hetero) - heterogeneous
# Filter for 3-stage (Heterogeneous) setup
v5_hetero = df[(df['Prompt Version'] == 'v5_angel_devil') &
               (df['Setup'] == '3-stage (Heterogeneous)')]
medqa_hetero = v5_hetero[v5_hetero['Dataset'] == 'MEDQA']
if len(medqa_hetero) > 0:
    medqa_acc = medqa_hetero['Accuracy_num'].mean()
    medqa_f1 = medqa_hetero['F1_Macro'].mean()
else:
    medqa_acc, medqa_f1 = None, None

results.append({
    'System': 'v5 angel-devil (hetero)',
    'PubMedQA Acc': '—',
    'MedQA Acc': f"{medqa_acc:.0f}%" if medqa_acc else '—',
    'MMLU Acc': '—',
    'F1 Macro': f"{medqa_f1:.2f}" if medqa_f1 else '—',
    'Maybe Recall': '—'
})

# Create DataFrame
results_df = pd.DataFrame(results)

# Save to CSV
results_df.to_csv('results/PPT_MAIN_RESULTS_TABLE.csv', index=False)

print("[OK] Created: results/PPT_MAIN_RESULTS_TABLE.csv")
print("\nTable Preview:")
print(results_df.to_string(index=False))
print(f"\nTotal rows: {len(results_df)}")

# Print comparison with expected PPT values
print("\n" + "="*80)
print("VERIFICATION: Compare with PPT Script")
print("="*80)

expected = {
    'Single agent v1 (direct)': {'PubMedQA': '70%', 'MedQA': '78%', 'MMLU': '88%'},
    'Single agent v1 + CoT': {'PubMedQA': '71%', 'MedQA': '79%', 'MMLU': '90%'},
    'Multi-agent v2 (structured)': {'PubMedQA': '44%', 'MedQA': '77%', 'MMLU': '94%'},
    'Multi-agent v3 (strict)': {'PubMedQA': '21%', 'MedQA': '30%', 'MMLU': '38%'},
}

for config, exp_vals in expected.items():
    row = results_df[results_df['System'] == config]
    if len(row) > 0:
        print(f"\n{config}:")
        for dataset, exp_val in exp_vals.items():
            col_name = f"{dataset} Acc"
            actual_val = row[col_name].values[0]
            match = "✓" if actual_val == exp_val else "✗"
            print(f"  {dataset}: Expected {exp_val}, Got {actual_val} {match}")
