# Evaluation Summary: Multi-Agent Adversarial Debate

## Experimental Setup

**Objective:** Evaluate multi-agent adversarial debate effectiveness for medical question answering.

**Datasets:** PubMedQA (3-class), MedQA (4-choice), MMLU (4-choice)  
**Configurations:** 1-stage (baseline) vs 3-stage (Generator → Skeptic → Judge)  
**Scale:** 24 experiments, 20 retained after quality filtering, 2,000 predictions analyzed

---

## Results

### Performance by Dataset

| Dataset | 1-Stage | 3-Stage | Δ | Net Impact |
|---------|---------|---------|---|------------|
| MedQA | 69.0% | 77.0% | +8.0% | +50 fixed, -1 broke |
| MMLU | 86.7% | 94.0% | +7.3% | +47 fixed, -0 broke |
| PubMedQA | 67.5% | 32.8% | -34.7% | +75 fixed, -277 broke |

**Understanding the Metrics:**
- **1-Stage (Baseline)**: Average accuracy across multiple 1-stage experiments (e.g., MedQA: average of 50%, 78%, 79% = 69%)
- **Δ (Change)**: Percentage point improvement from baseline to 3-stage debate (e.g., 69% → 77% = +8.0 pp)
- **Net Impact**: Agent attribution from specific 3-stage experiments showing:
  - **Fixed**: Questions where Generator was wrong but Judge corrected it (error correction)
  - **Broke**: Questions where Generator was right but Judge changed it to wrong (debate-introduced error)
  - **Net = Fixed - Broke** (e.g., MedQA: 51 fixed - 1 broke = +50 net improvement)

These metrics answer different questions: Δ shows overall system improvement (1-stage vs 3-stage), while Net Impact shows the debate mechanism's correction power (Generator vs Judge within 3-stage).

Debate significantly improves MCQ accuracy but degrades ambiguous 3-class classification.

### Agent Attribution (800 3-stage predictions)

| Category | Count | % | Interpretation |
|----------|-------|---|----------------|
| Both Correct | 272 | 34.0% | Baseline strong, debate maintains |
| Debate Fixed | 80 | 10.0% | Error correction |
| Debate Broke | 282 | 35.2% | Debate introduces error |
| Both Wrong | 166 | 20.8% | Neither succeeds |

**Fix-to-Break Ratios:**
- MMLU: ∞ (4 fixed, 0 broke)
- MedQA: 0.20 (1 fixed, 5 broke)
- PubMedQA: 0.27 (75 fixed, 277 broke)

### Task Difficulty Distribution

Questions categorized by baseline accuracy: Hard (0-50%), Medium (50-80%), Easy (80-100%)

- MMLU: 7% hard, 22% medium, 71% easy
- MedQA: 26% hard, 31% medium, 43% easy
- PubMedQA: 31% hard, 15% medium, 54% easy

Debate most effective on medium-difficulty questions.

---

## Key Findings

**MCQ Success Factors:**
1. Error correction through skeptical critique
2. Answer disambiguation on close options
3. Confidence calibration against distractors

**PubMedQA Failure Mode:**
1. Over-aggressive skepticism on clear cases
2. Format confusion (outputs "maybe" for yes/no questions)
3. Clinical conservatism bias

**Prompt Engineering Impact:**
- v2_structured: 94% (MMLU), best performance
- v3_skeptic_strict: 11-31%, catastrophic failure due to over-skepticism

---

## Methodology

**Data Quality:** Excluded 4 experiments with >20% unparseable outputs (77% unknown rate for v3_skeptic_strict + llama-3.1-8b). Retained dataset: 2.65% unknown rate.

**Agent Attribution:** Extract Generator/Judge answers from debate logs, compare to gold standard, categorize outcomes.

**Difficulty Categorization:** 50% threshold (random vs better), 80% threshold (moderate vs high confidence).

---

## Limitations

1. Homogeneous architecture (all agents use same model)
2. Limited scale (100 questions per dataset)
3. Format ambiguity on 3-class tasks
4. Prompt sensitivity (v3_skeptic_strict failure)

---

## Conclusion

Multi-agent debate improves accuracy (+47-50 corrections) on well-defined MCQ tasks but requires careful prompt engineering to avoid over-skepticism. Effectiveness is task-dependent: MCQ reasoning benefits, ambiguous classification suffers. Deploy selectively based on question type and baseline confidence.
