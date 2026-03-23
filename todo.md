# LLM Council — Task Tracker

## Already Implemented (No Work Needed)

| Feature | Status | Location |
|---|---|---|
| 1-stage baseline (direct answer) | ✅ Complete | `runner.py` — `n_stages=1` |
| 1-stage + CoT ("think step by step") | ✅ Complete | `prompts.py` — `v1_cot` template |
| 3-stage debate (Generator→Skeptic→Judge) | ✅ Complete | `runner.py` — `n_stages=3` |
| 4 prompt versions (v1_baseline, v1_cot, v2_structured, v3_skeptic_strict) | ✅ Complete | `prompts.py` |
| Cross-dataset support (PubMedQA, MedQA, MMLU) | ✅ Complete | `datasets.py` |
| Batch experiment support | ✅ Complete | `main.py` — `/api/benchmark/batch` |
| Experiment tracking (SQLite CRUD) | ✅ Complete | `tracker.py` |
| Evaluation metrics (accuracy, F1 macro, per-class P/R/F1, confusion matrix, maybe_recall) | ✅ Complete | `evaluator.py` |
| Token usage tracking (per-stage, per-experiment) | ✅ Complete | `runner.py` |
| 6-phase systematic experiments (24 runs) | ✅ Complete | stored in `experiments.db` |

## TODO — Tasks to Complete

### 1. BioBERT Fine-tuning Baseline (Amruta)

> Amruta: "I can work on this : BioBERT fine tuned (classic NLP)"

- Fine-tune BioBERT (or BioGPT) on PubMedQA using HuggingFace Transformers
- Evaluate on the same test set used by the debate system
- Enables 3-way comparison: fine-tuned small model vs. CoT prompting vs. multi-agent debate
- Not implemented at all — no training/fine-tuning code exists

### 2. Evaluation Enhancements (Rashmi)

> Rashmi: "if Amruta is taking BioBERT, I can take up the evaluation part"

- Scope needs clarification. Current metrics are basic (accuracy, F1, confusion matrix)
- Possible additions:
  - Statistical significance tests (McNemar's test, paired bootstrap)
  - Confidence intervals
  - Calibration analysis (especially for "maybe" on PubMedQA)
  - Error analysis / qualitative case studies

### 3. Different Models per Debate Role (Unassigned)

> Amruta: "I am able to select 3 stage debate but not able to select 3 different models to act as generator, skeptic and judge. So currently, is the same model acting as all 3?"

- Currently the same model plays all 3 roles (Generator, Skeptic, Judge)
- Could allow assigning different models to each role for richer experiments
- Requires changes to `runner.py`, `main.py` API schema, and frontend RunTab

### 4. Additional Experiments (Unassigned)

> Swarangi: "Groq's free tier might be an issue. We're looking at 1000+ questions x 3 agent calls x multiple prompt versions x 3 datasets. That's a LOT of API calls."

- Run remaining model x prompt x dataset combinations if needed
- Groq rate limits should be tested before large batches

### 5. Paper / Report Writing (Unassigned)

- Introduction, Related Work, Method, Experiments, Results, Conclusion
- LaTeX table export already exists in CompareTab (frontend)
- Let's do this at the end of the project!!!