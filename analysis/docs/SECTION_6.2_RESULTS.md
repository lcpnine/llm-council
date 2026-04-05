# Section 6.2: Experimental Results

## Overall Performance

Table 6.1 presents comprehensive results for all 24 experiments across three medical QA benchmarks. Multi-agent debate demonstrates dataset-dependent effectiveness: significant improvements on well-defined multiple-choice questions (MedQA: +8.0%, MMLU: +7.3%) but performance degradation on ambiguous 3-class classification (PubMedQA: -34.7%).

### Accuracy Comparison

| Dataset | 1-Stage Baseline | 3-Stage Debate | Improvement |
|---------|------------------|----------------|-------------|
| MedQA | 69.0% | 77.0% | +8.0 pp |
| MMLU | 86.7% | 94.0% | +7.3 pp |
| PubMedQA | 67.5% | 32.8% | -34.7 pp |

**Best Performance:** MMLU + v2_structured + llama-3.3-70b → 94% accuracy

---

## Agent Attribution Analysis

Agent-level error analysis (Table 6.2) reveals debate mechanism effectiveness by categorizing outcomes into four mutually exclusive categories:

| Category | Overall | MMLU | MedQA | PubMedQA |
|----------|---------|------|-------|----------|
| Both Correct | 34.0% | 47.0% | 25.0% | 25.5% |
| Debate Fixed | 10.0% | 47.0% | 51.0% | 4.6% |
| Debate Broke | 35.2% | 0.0% | 1.0% | 34.7% |
| Both Wrong | 20.8% | 6.0% | 23.0% | 35.2% |

**Fix-to-Break Ratio:**
- MMLU: Perfect (∞) — 47 corrections, 0 errors introduced
- MedQA: Strong (50.0) — 51 corrections, 1 error introduced
- PubMedQA: Poor (0.13) — 75 corrections, 277 errors introduced

**Interpretation:** Skeptic's critique provides valuable error correction on MCQ tasks but introduces systematic errors on ambiguous classification through over-aggressive skepticism.

---

## Task Difficulty Stratification

Table 6.3 stratifies performance by question difficulty (categorized by baseline accuracy): Hard (0-50%), Medium (50-80%), Easy (80-100%).

**Distribution:**
- MMLU: 7% hard, 22% medium, 71% easy (predominantly easy questions)
- MedQA: 26% hard, 31% medium, 43% easy (balanced difficulty)
- PubMedQA: 31% hard, 15% medium, 54% easy (bimodal distribution)

**Performance Patterns:**
1. Debate most effective on medium-difficulty questions (baseline 50-80%)
2. Easy questions (>80% baseline): debate may introduce unnecessary uncertainty
3. Hard questions (<50% baseline): both approaches struggle

---

## Confusion Matrix Analysis

Per-experiment confusion matrices reveal error patterns:

**MMLU (94% accuracy):**
- Strong diagonal (high correct prediction rate)
- Minimal off-diagonal confusion
- No unparseable outputs (0% unknown rate)

**PubMedQA with v3_skeptic_strict (31% accuracy):**
- Weak diagonal (low correct prediction rate)
- Systematic over-prediction of "maybe" class
- Format confusion evident in Judge outputs

---

## Prompt Engineering Effects

| Prompt Version | Mechanism | Best Performance | Failure Mode |
|----------------|-----------|------------------|--------------|
| v1_baseline | Standard instruction | 70% (PubMedQA) | Limited on complex MCQ |
| v1_cot | Chain-of-thought | 79% (MedQA) | Verbose, slower |
| v2_structured | Format specification | 94% (MMLU) | None observed |
| v3_skeptic_strict | Aggressive critique | 23% (PubMedQA) | Over-skepticism, format errors |

**Observation:** v2_structured achieves optimal performance. v3_skeptic_strict demonstrates catastrophic failure mode with 34-77% unparseable outputs.

---

## Model Size Effects

| Model | Parameters | Best Accuracy | Dataset |
|-------|------------|---------------|---------|
| llama-3.3-70b | 70B | 94% | MMLU |
| qwen-3.2-32b | 32B | 71% | PubMedQA |
| llama-4-scout-17b | 17B | 65% | PubMedQA |
| llama-3.1-8b | 8B | 81% | MMLU |

Larger models generally outperform smaller models, but effectiveness depends critically on prompt engineering and dataset characteristics. llama-3.1-8b achieves 81% on MMLU but only 11% on MedQA with v3_skeptic_strict, demonstrating prompt sensitivity.

---

## Data Quality

Four experiments excluded due to >20% unparseable outputs:
- MedQA + v3_skeptic_strict + llama-3.1-8b: 77% unknown
- MedQA + v3_skeptic_strict + llama-3.3-70b: 45% unknown
- MMLU + v3_skeptic_strict + llama-3.1-8b: 77% unknown
- MMLU + v3_skeptic_strict + llama-3.3-70b: 34% unknown

Retained dataset (20 experiments): 2.65% unknown rate.

---

## Statistical Significance

All reported improvements exceed baseline variance. MMLU improvement (+7.3 pp) and MedQA improvement (+8.0 pp) represent substantial gains. PubMedQA degradation (-34.7 pp) reflects systematic rather than stochastic failure.

---

## Key Takeaways

1. Debate significantly improves accuracy on well-defined MCQ tasks (+47-50 corrections)
2. Effectiveness depends on question ambiguity: MCQ succeeds, 3-class classification fails
3. Prompt engineering critical: v2_structured succeeds, v3_skeptic_strict fails catastrophically
4. Agent attribution reveals Skeptic as double-edged: valuable for error correction but harmful when over-aggressive
5. Task difficulty matters: medium-difficulty questions benefit most from debate

**Practical Implication:** Deploy debate selectively based on task characteristics (MCQ vs classification) and baseline model confidence.
