"""FastAPI backend for Medical QA Benchmark."""

import asyncio
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
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

# Batch queue for sequential execution
_batch_queue: asyncio.Queue = asyncio.Queue()
_batch_running = False


class BenchmarkRequest(BaseModel):
    model: str
    generator_model: Optional[str] = None
    skeptic_model: Optional[str] = None
    judge_model: Optional[str] = None
    prompt_version: str
    dataset: str
    n_samples: int = 100
    n_stages: int = 3
    debate_style: str = "adversarial"  # "adversarial" | "independent"


class BatchRequest(BaseModel):
    configs: List[BenchmarkRequest]


class NotesRequest(BaseModel):
    notes: str


class TagsRequest(BaseModel):
    tags: List[str]


class PromptRequest(BaseModel):
    version: str
    generator: str
    skeptic: str
    judge: str


class CompareRequest(BaseModel):
    experiment_ids: List[str]


class ImportRequest(BaseModel):
    data: dict
    skip_existing: bool = True


def _make_experiment_id(dataset: str, prompt_version: str) -> str:
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
    return f"{dataset}_{prompt_version}_{ts}"


def _progress_callback(experiment_id: str, current: int, total: int):
    """Called by runner to report progress."""
    tracker.update_progress(experiment_id, current, total)


async def _run_benchmark_task(config: dict):
    """Background task to run a benchmark and save results."""
    try:
        runner = BenchmarkRunner(config, progress_callback=_progress_callback)
        experiment = await runner.run()
        tracker.save_experiment(experiment)
    except Exception as e:
        print(f"Benchmark failed: {e}")
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


async def _batch_worker():
    """Process batch queue one experiment at a time."""
    global _batch_running
    _batch_running = True
    try:
        while not _batch_queue.empty():
            config = await _batch_queue.get()
            await _run_benchmark_task(config)
            _batch_queue.task_done()
    finally:
        _batch_running = False


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
        "generator_model": request.generator_model,
        "skeptic_model": request.skeptic_model,
        "judge_model": request.judge_model,
        "prompt_version": request.prompt_version,
        "dataset": request.dataset,
        "n_samples": request.n_samples,
        "n_stages": request.n_stages,
        "debate_style": request.debate_style,
    }

    tracker.mark_experiment_running(experiment_id, config)
    background_tasks.add_task(_run_benchmark_task, config)

    return {"experiment_id": experiment_id, "status": "started"}


@app.post("/api/benchmark/batch")
async def run_batch(request: BatchRequest, background_tasks: BackgroundTasks):
    """Queue multiple experiments for sequential execution."""
    experiment_ids = []
    for req in request.configs:
        experiment_id = _make_experiment_id(req.dataset, req.prompt_version)
        # Add sub-second uniqueness
        import time
        time.sleep(0.01)
        experiment_id = _make_experiment_id(req.dataset, req.prompt_version)
        config = {
            "experiment_id": experiment_id,
            "model": req.model,
            "generator_model": req.generator_model,
            "skeptic_model": req.skeptic_model,
            "judge_model": req.judge_model,
            "prompt_version": req.prompt_version,
            "dataset": req.dataset,
            "n_samples": req.n_samples,
            "n_stages": req.n_stages,
            "debate_style": req.debate_style,
        }
        tracker.mark_experiment_running(experiment_id, config)
        await _batch_queue.put(config)
        experiment_ids.append(experiment_id)

    if not _batch_running:
        background_tasks.add_task(_batch_worker)

    return {"experiment_ids": experiment_ids, "status": "queued", "count": len(experiment_ids)}


@app.get("/api/experiments")
async def list_experiments():
    return tracker.get_all_experiments()


@app.get("/api/experiments/export")
async def export_experiments(ids: Optional[str] = None):
    """Export experiments as JSON. Use ?ids=id1,id2 to export specific ones."""
    experiment_ids = [i.strip() for i in ids.split(",")] if ids else None
    return tracker.export_experiments(experiment_ids)


@app.post("/api/experiments/import")
async def import_experiments(request: ImportRequest):
    """Import experiments from an export payload.

    Set skip_existing=false to force-overwrite existing experiments (will
    replace notes/tags with the imported values).
    """
    result = tracker.import_experiments(request.data, skip_existing=request.skip_existing)
    return result


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


@app.get("/api/experiments/{experiment_id}/progress")
async def get_experiment_progress(experiment_id: str):
    exp = tracker.get_experiment(experiment_id)
    if exp is None:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return {"progress": exp.get("progress"), "status": exp.get("status")}


@app.patch("/api/experiments/{experiment_id}/notes")
async def update_notes(experiment_id: str, request: NotesRequest):
    exp = tracker.get_experiment(experiment_id)
    if exp is None:
        raise HTTPException(status_code=404, detail="Experiment not found")
    tracker.update_notes(experiment_id, request.notes)
    return {"status": "updated"}


@app.patch("/api/experiments/{experiment_id}/tags")
async def update_tags(experiment_id: str, request: TagsRequest):
    exp = tracker.get_experiment(experiment_id)
    if exp is None:
        raise HTTPException(status_code=404, detail="Experiment not found")
    tracker.update_tags(experiment_id, request.tags)
    return {"status": "updated"}


@app.delete("/api/experiments/{experiment_id}")
async def delete_experiment(experiment_id: str):
    if not tracker.delete_experiment(experiment_id):
        raise HTTPException(status_code=404, detail="Experiment not found")
    return {"status": "deleted"}


@app.post("/api/experiments/compare")
async def compare_experiments(request: CompareRequest):
    return tracker.compare_experiments(request.experiment_ids)


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
