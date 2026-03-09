"""FastAPI backend for Medical QA Benchmark."""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from .benchmark.runner import BenchmarkRunner
from .benchmark.prompts import get_all_prompts, list_versions, add_custom_version
from .benchmark.baselines import BASELINES
from .experiments import tracker
from .config import AVAILABLE_MODELS

app = FastAPI(title="Medical QA Benchmark API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class BenchmarkRequest(BaseModel):
    model: str
    prompt_version: str
    dataset: str
    n_samples: int = 100
    n_stages: int = 3


class PromptRequest(BaseModel):
    version: str
    generator: str
    skeptic: str
    judge: str


def _make_experiment_id(dataset: str, prompt_version: str) -> str:
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M")
    return f"{dataset}_{prompt_version}_{ts}"


async def _run_benchmark_task(config: dict):
    """Background task to run a benchmark and save results."""
    try:
        runner = BenchmarkRunner(config)
        experiment = await runner.run()
        tracker.save_experiment(experiment)
    except Exception as e:
        print(f"Benchmark failed: {e}")
        # Mark as failed in DB
        tracker.save_experiment({
            "id": config["experiment_id"],
            "timestamp": datetime.utcnow().isoformat(),
            "model": config.get("model", ""),
            "prompt_version": config.get("prompt_version", ""),
            "dataset": config.get("dataset", ""),
            "n_samples": config.get("n_samples", 0),
            "n_stages": config.get("n_stages", 3),
            "status": "failed",
            "metrics": {"error": str(e)},
            "results": [],
            "config": config,
        })


@app.get("/")
async def root():
    return {"status": "ok", "service": "Medical QA Benchmark API"}


@app.get("/api/models")
async def get_models():
    return AVAILABLE_MODELS


@app.post("/api/benchmark/run")
async def run_benchmark(request: BenchmarkRequest, background_tasks: BackgroundTasks):
    experiment_id = _make_experiment_id(request.dataset, request.prompt_version)
    config = {
        "experiment_id": experiment_id,
        "model": request.model,
        "prompt_version": request.prompt_version,
        "dataset": request.dataset,
        "n_samples": request.n_samples,
        "n_stages": request.n_stages,
    }

    # Mark as running
    tracker.mark_experiment_running(experiment_id, config)

    # Run in background
    background_tasks.add_task(_run_benchmark_task, config)

    return {"experiment_id": experiment_id, "status": "started"}


@app.get("/api/experiments")
async def list_experiments():
    return tracker.get_all_experiments()


@app.get("/api/experiments/{experiment_id}")
async def get_experiment(experiment_id: str):
    exp = tracker.get_experiment(experiment_id)
    if exp is None:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return exp


@app.get("/api/experiments/{experiment_id}/results")
async def get_experiment_results(experiment_id: str):
    exp = tracker.get_experiment(experiment_id)
    if exp is None:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return tracker.get_results(experiment_id)


@app.get("/api/prompts")
async def get_prompts():
    return get_all_prompts()


@app.post("/api/prompts")
async def create_prompt(request: PromptRequest):
    add_custom_version(request.version, request.generator, request.skeptic, request.judge)
    return {"status": "saved", "version": request.version}


@app.get("/api/baselines")
async def get_baselines():
    return BASELINES


@app.post("/api/baselines/run")
async def run_all_baselines(background_tasks: BackgroundTasks, dataset: str = "pubmedqa", n_samples: int = 100):
    experiment_ids = []
    for baseline in BASELINES:
        experiment_id = _make_experiment_id(dataset, baseline["prompt_version"])
        # Append baseline name slug to avoid collisions
        experiment_id += f"_{baseline['name'].replace(' ', '_').lower()}"
        config = {
            "experiment_id": experiment_id,
            "model": baseline["model"],
            "prompt_version": baseline["prompt_version"],
            "dataset": dataset,
            "n_samples": n_samples,
            "n_stages": baseline["n_stages"],
            "baseline_name": baseline["name"],
        }
        tracker.mark_experiment_running(experiment_id, config)
        background_tasks.add_task(_run_benchmark_task, config)
        experiment_ids.append(experiment_id)

    return {"experiment_ids": experiment_ids, "status": "started"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
