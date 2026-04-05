# Section 6.6: Limitations and Future Work

## Experimental Limitations

### 1. Data Quality and Filtering

Four experiments exhibited >20% unparseable outputs, requiring exclusion from detailed analysis:
- v3_skeptic_strict + llama-3.1-8b: 77% unknown rate (MedQA, MMLU)
- v3_skeptic_strict + llama-3.3-70b: 34-45% unknown rate (MedQA, MMLU)

**Cause:** Format confusion where Judge outputs "maybe" (PubMedQA format) for MCQ questions expecting A/B/C/D responses.

**Impact:** Attribution analysis limited to 20 of 24 experiments. Primary accuracy results remain valid.

### 2. Homogeneous Architecture

All agents (Generator, Skeptic, Judge) use identical models. Heterogeneous councils with diverse models (e.g., large Generator + small Skeptic) remain unexplored. Homogeneous setup provides controlled comparison but may not represent optimal configuration.

### 3. Scale Constraints

100 questions per dataset per experiment, 2,000 total predictions after filtering. Moderate sample size may not capture full performance distribution. Multiple experiments per configuration provide replication and consistency.

### 4. Task Format Ambiguity

PubMedQA 3-class classification creates boundary ambiguity. Debate systematically over-triggers "maybe" responses, degrading decisive accuracy despite improved maybe recall.

### 5. Prompt Sensitivity

System performance highly sensitive to prompt engineering:
- v2_structured: 94% accuracy (MMLU)
- v3_skeptic_strict: 11% accuracy (MedQA), 77% unknown rate

Poorly engineered prompts degrade performance below baseline through over-aggressive skepticism.

### 6. Computational Cost

Token usage, latency, and computational cost not systematically analyzed. 3-stage debate incurs approximately 3x token cost compared to 1-stage baseline.

---

## Methodological Considerations

**Answer Extraction:** Regex-based with conservative handling of ambiguous outputs. 2.65% unknown rate suggests adequate performance.

**Baseline Selection:** Generator-only configuration isolates debate contribution without confounding factors.

**Difficulty Categorization:** Hard (0-50%), Medium (50-80%), Easy (80-100%) based on baseline accuracy. Thresholds chosen for interpretability: 50% separates random from better performance, 80% separates moderate from high confidence.

---

## Generalization Concerns

**Domain Specificity:** All datasets medical QA. Debate effectiveness in non-medical domains (mathematics, code generation) unknown.

**Model Specificity:** Primary experiments use LLaMA families. Limited cross-validation with Qwen (32B) and LLaMA-4-scout (17B) shows similar patterns.

**Language and Culture:** English-only with Western medical paradigms.

---

## Future Directions

**Immediate:**
1. Heterogeneous councils with diverse model combinations
2. Larger scale (500+ questions per dataset)
3. Prompt optimization to minimize over-skepticism
4. Cost-benefit analysis quantifying computational trade-offs

**Long-term:**
1. Domain expansion (mathematics, code generation, commonsense reasoning)
2. Medical expert evaluation of debate-corrected answers
3. Dynamic debate mechanisms (adaptive deployment based on baseline confidence)
4. Multi-round iterative refinement
5. Clinical deployment validation

---

## Validity Assessment

Results provide valid evidence for:

1. **Primary Claim:** Debate improves MCQ accuracy (+7-8 pp) — consistent across models and prompts
2. **Task Dependence:** Effectiveness varies by question type — systematic dataset comparison
3. **Failure Modes:** Over-skepticism degrades performance — evidenced by v3_skeptic_strict and PubMedQA
4. **Mechanism:** Error correction through critique — validated by agent attribution

**Confidence:** High for MCQ improvement, high for PubMedQA challenges, moderate for optimal prompts, low for heterogeneous architectures.

---

## Practitioner Recommendations

**Deploy debate when:**
- Well-defined MCQ tasks with baseline uncertainty
- Careful reasoning required (medical diagnosis, legal analysis)
- Accuracy gains justify computational cost

**Avoid debate when:**
- Ambiguous classification tasks
- High baseline confidence (>80%)
- Resource-constrained or time-sensitive applications

**Best Practices:**
1. Engineer prompts to balance skepticism and decisiveness
2. Monitor output quality for format confusion
3. Validate on target domain before deployment
4. Consider computational cost relative to accuracy gains
