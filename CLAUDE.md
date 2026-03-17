# CLAUDE.md - Technical Notes for Medical QA Benchmark

## Project Overview

AI6127 NLP Final Project: Multi-Agent Debate System for Ambiguous Biomedical QA. The system uses a Generator-Skeptic-Judge pipeline where multiple LLM passes collaboratively answer medical questions. The key hypothesis is that adversarial review (skeptic) followed by arbitration (judge) improves calibration on ambiguous cases.

## Architecture

### Backend (`backend/`)

**`config.py`**
- Groq API configuration (`GROQ_API_KEY`, `GROQ_API_URL`)
- `AVAILABLE_MODELS`: Groq-hosted models (llama-3.1-70b, llama-3.1-8b, mixtral-8x7b, gemma2-9b)
- Backend runs on **port 8001**

**`groq_client.py`**
- `query_model()`: Single async model query via Groq's OpenAI-compatible API
- Returns `content`, optional `reasoning_details`, and `token_usage` (prompt/completion/total tokens)
- Graceful degradation: returns None on failure

**`benchmark/runner.py`** — Core Pipeline
- `BenchmarkRunner`: Runs Generator-Skeptic-Judge pipeline on each question
- Tracks token usage per stage (generator/skeptic/judge) per question
- Accumulates total token usage across all questions
- `progress_callback` reports current/total for live progress updates
- `n_stages=1`: generator only (baseline), `n_stages=3`: full debate

**`benchmark/datasets.py`**
- Loads PubMedQA, MedQA, MMLU from HuggingFace datasets
- Returns `Question` dataclass with `id`, `dataset`, `question_text`, `gold_answer`

**`benchmark/evaluator.py`**
- `extract_answer()`: Parses LLM output into normalized labels (yes/no/maybe or A/B/C/D)
- `compute_metrics()`: Accuracy, F1 macro, per-class P/R/F1, confusion matrix, maybe_recall

**`benchmark/prompts.py`**
- 4 built-in versions: v1_baseline, v1_cot, v2_structured, v3_skeptic_strict
- Custom versions persisted to `data/custom_prompts.json`

**`experiments/tracker.py`**
- SQLite storage in `data/experiments.db`
- Experiments table: id, model, prompt_version, dataset, metrics, total_tokens, notes, tags, progress
- Results table: per-question predicted/gold/correct/debate_log/token_usage
- CRUD: save, get, delete, update notes/tags/progress, compare

**`main.py`**
- FastAPI with CORS for localhost:5173 and :3000
- Key endpoints:
  - `POST /api/benchmark/run` — single experiment
  - `POST /api/benchmark/batch` — sequential queue of experiments
  - `POST /api/experiments/compare` — multi-experiment comparison
  - `PATCH .../notes`, `PATCH .../tags`, `DELETE`, `GET .../progress`

### Frontend (`frontend/src/`)

**Dashboard** — Thin shell with tab routing (Run, Results, Compare, Charts, Prompts, Detail)

**RunTab** — Single experiment form + batch mode (matrix selector: models x prompts x datasets x stages)

**ResultsTab** — Sortable table with dropdown filters (model, prompt, dataset, stages, status, tags). Checkbox selection for comparison. Delete experiments.

**DetailTab** — Full metrics, confusion matrix, per-question results with debate logs. Editable notes and tags.

**CompareTab** — Side-by-side metrics table, per-question diff (highlights disagreements), LaTeX table export.

**ChartsTab** — recharts bar charts: accuracy, per-class F1, token usage. PNG export via SVG-to-canvas.

## Key Design Decisions

### Prompt Strategy
- v1_baseline/v1_cot: Simple prompts for baseline comparison
- v2_structured: Evidence-based reasoning with explicit steps
- v3_skeptic_strict: Adversarial skeptic that assumes the answer is wrong — designed to catch overconfidence and improve "maybe" recall on PubMedQA

### API Provider
Groq (free tier) instead of OpenRouter — matches project budget constraints, fast inference, OpenAI-compatible format.

### Token Tracking
Every API call returns token usage. Accumulated per-stage and per-experiment for cost-effectiveness analysis in the paper.

## Important Details

### Running the App
- Backend: `uv run python -m backend.main` from project root (relative imports require `-m`)
- Frontend: `cd frontend && npm run dev`
- Or: `./start.sh`

### Port Configuration
- Backend: 8001
- Frontend: 5173 (Vite default)

### Database
SQLite at `data/experiments.db`. Auto-creates tables and runs migrations on startup.

## Common Gotchas

1. **Module imports**: Always run backend as `python -m backend.main` from project root
2. **CORS**: Frontend must match allowed origins in `main.py`
3. **Answer parsing**: If LLM doesn't follow format, fallback regex extracts patterns
4. **Rate limits**: 0.5s delay between stages, 0.3s between questions (Groq free tier)
