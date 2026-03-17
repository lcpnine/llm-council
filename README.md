# Multi-Agent Debate for Ambiguous Biomedical QA

**AI6127 Deep Neural Networks for NLP — Final Project**

## Project Goal

This project investigates whether **multi-agent debate improves LLM performance on ambiguous medical question answering**, especially on "maybe" cases where evidence is insufficient for a definitive yes/no answer.

The core research question: *Can a Generator-Skeptic-Judge debate pipeline produce more calibrated, evidence-aware answers than a single LLM pass on biomedical QA benchmarks?*

## How It Works

The system implements a 3-stage debate pipeline:

1. **Generator** — An LLM reads the medical context and question, then produces an initial answer with reasoning.
2. **Skeptic** — A second LLM pass critically reviews the generator's answer, checking for overconfidence, unsupported claims, statistical issues, and logical gaps.
3. **Judge** — A final LLM pass weighs the original answer against the critique and produces the final answer, penalizing overconfidence when evidence is weak.

This is compared against single-agent baselines (zero-shot, chain-of-thought) to measure whether the debate stages improve accuracy and calibration.

## Datasets

| Dataset | Task | Labels | Source |
|---------|------|--------|--------|
| **PubMedQA** | Evidence-based medical QA | yes / no / maybe | `qiaojin/PubMedQA` (HuggingFace) |
| **MedQA** | Medical licensing exam MCQ | A / B / C / D | `bigbio/med_qa` (HuggingFace) |
| **MMLU (Medical)** | Clinical knowledge, genetics, anatomy, professional medicine | A / B / C / D | `cais/mmlu` (HuggingFace) |

## Evaluation Metrics

- **Accuracy** — overall correctness
- **Macro F1** — class-balanced performance
- **Maybe Recall** (PubMedQA) — ability to correctly identify ambiguous cases
- **Per-class Precision/Recall/F1** — breakdown by answer type
- **Confusion Matrix** — error pattern analysis
- **Token Usage** — cost-effectiveness of multi-agent vs single-agent

## Setup

### Prerequisites

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- Node.js 18+ and npm

### 1. Install Dependencies

```bash
# Backend
uv sync

# Frontend
cd frontend
npm install
cd ..
```

### 2. Configure API Key

Create a `.env` file in the project root:

```bash
GROQ_API_KEY=gsk_...
```

Get a free API key at [console.groq.com](https://console.groq.com/).

### 3. Configure Models (Optional)

Edit `backend/config.py` to change available models:

```python
AVAILABLE_MODELS = [
    "llama-3.1-70b-versatile",
    "llama-3.1-8b-instant",
    "mixtral-8x7b-32768",
    "gemma2-9b-it",
]
```

## Running the Application

**Option 1: Use the start script**
```bash
./start.sh
```

**Option 2: Run manually**

Terminal 1 (Backend):
```bash
uv run python -m backend.main
```

Terminal 2 (Frontend):
```bash
cd frontend
npm run dev
```

Then open http://localhost:5173 in your browser.

## Using the Dashboard

### Run Experiment
Select a model, prompt version, dataset, sample count, and number of stages (1 = single-agent, 3 = full debate). Click "Run Experiment" to start. Use **Batch Mode** to run a matrix of experiments (models x prompts x datasets x stages) in one click.

### Results
View all experiment results in a sortable, filterable table. Filter by model, prompt version, dataset, stages, status, or tags. Select multiple experiments and click "Compare Selected" to open the comparison view.

### Compare
Side-by-side metrics comparison across experiments. Shows per-question disagreements (where one experiment got it right and another didn't). Export comparison as a LaTeX table for your paper.

### Charts
Visualize results with bar charts for accuracy, per-class F1, and token usage. Each chart can be exported as PNG for paper figures.

### Detail View
Drill into any experiment to see per-class metrics, confusion matrix, and per-question results with full debate logs (generator/skeptic/judge outputs). Add notes and tags to organize experiments by research phase.

### Prompts
View built-in prompt versions or create custom ones. Available versions:
- `v1_baseline` — Direct answer, no reasoning
- `v1_cot` — Chain-of-thought reasoning
- `v2_structured` — Evidence-based structured analysis
- `v3_skeptic_strict` — Adversarial skeptic with strict critique checklist

## Project Structure

```
backend/
  config.py              # Groq API config and model list
  groq_client.py         # Groq API client with token tracking
  main.py                # FastAPI endpoints
  benchmark/
    runner.py            # Generator-Skeptic-Judge pipeline
    datasets.py          # PubMedQA, MedQA, MMLU loaders
    evaluator.py         # Answer extraction and metrics
    prompts.py           # Versioned prompt templates
    baselines.py         # Baseline experiment configs
  experiments/
    tracker.py           # SQLite experiment storage

frontend/
  src/
    api.js               # Backend API client
    components/
      Dashboard.jsx      # Tab shell
      RunTab.jsx         # Experiment launcher + batch mode
      ResultsTab.jsx     # Filterable results table
      DetailTab.jsx      # Single experiment detail view
      CompareTab.jsx     # Side-by-side comparison + LaTeX export
      ChartsTab.jsx      # Accuracy, F1, token charts (recharts)
      PromptsTab.jsx     # Prompt viewer/editor
```

## Tech Stack

- **Backend:** FastAPI, Python 3.10+, async httpx, Groq API
- **Frontend:** React 19 + Vite, recharts for visualization
- **Storage:** SQLite (experiments + results)
- **LLM Provider:** Groq (free tier, OpenAI-compatible API)
- **Package Management:** uv (Python), npm (JavaScript)
