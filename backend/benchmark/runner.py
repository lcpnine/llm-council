"""Benchmark runner for the Generator-Skeptic-Judge pipeline."""

import asyncio
import json
from datetime import datetime
from typing import Dict

from ..openrouter import query_model
from .datasets import load_dataset, Question
from .prompts import get_prompt
from .evaluator import extract_answer, compute_metrics


class BenchmarkRunner:
    def __init__(self, config: Dict):
        """
        config keys: model, prompt_version, dataset, n_samples, experiment_id
        Optional: n_stages (1 = generator only, 3 = full pipeline)
        """
        self.model = config["model"]
        self.prompt_version = config["prompt_version"]
        self.dataset_name = config["dataset"]
        self.n_samples = config.get("n_samples", 100)
        self.experiment_id = config["experiment_id"]
        self.n_stages = config.get("n_stages", 3)
        self.config = config

    async def _run_question(self, question: Question) -> Dict:
        """Run the debate pipeline on a single question."""
        debate_log = {}

        # Stage 1: Generator
        generator_prompt = get_prompt(
            self.prompt_version, "generator", question=question.question_text
        )
        gen_response = await query_model(
            self.model, [{"role": "user", "content": generator_prompt}]
        )
        generator_output = gen_response["content"] if gen_response else ""
        debate_log["generator_output"] = generator_output

        # For single-stage baselines, use generator output directly
        if self.n_stages == 1:
            predicted = extract_answer(generator_output, question.dataset)
            return {
                "question_id": question.id,
                "predicted": predicted,
                "gold": question.gold_answer,
                "correct": int(predicted == question.gold_answer),
                "debate_log": debate_log,
            }

        await asyncio.sleep(0.5)  # Rate limit

        # Stage 2: Skeptic
        skeptic_prompt = get_prompt(
            self.prompt_version, "skeptic",
            question=question.question_text, answer=generator_output
        )
        skeptic_response = await query_model(
            self.model, [{"role": "user", "content": skeptic_prompt}]
        )
        skeptic_output = skeptic_response["content"] if skeptic_response else ""
        debate_log["skeptic_output"] = skeptic_output

        await asyncio.sleep(0.5)  # Rate limit

        # Stage 3: Judge
        judge_prompt = get_prompt(
            self.prompt_version, "judge",
            question=question.question_text,
            answer=generator_output,
            critique=skeptic_output
        )
        judge_response = await query_model(
            self.model, [{"role": "user", "content": judge_prompt}]
        )
        judge_output = judge_response["content"] if judge_response else ""
        debate_log["judge_output"] = judge_output

        predicted = extract_answer(judge_output, question.dataset)

        return {
            "question_id": question.id,
            "predicted": predicted,
            "gold": question.gold_answer,
            "correct": int(predicted == question.gold_answer),
            "debate_log": debate_log,
        }

    async def run(self) -> Dict:
        """Run the full benchmark and return experiment results."""
        print(f"[{self.experiment_id}] Loading {self.dataset_name} ({self.n_samples} samples)...")
        questions = load_dataset(self.dataset_name, self.n_samples)

        results = []
        errors = []
        for i, question in enumerate(questions):
            print(f"[{self.experiment_id}] Processing {i + 1}/{len(questions)}...")
            try:
                result = await self._run_question(question)
                results.append(result)
            except Exception as e:
                print(f"[{self.experiment_id}] Error on question {question.id}: {e}")
                errors.append({"question_id": question.id, "error": str(e)})
                results.append({
                    "question_id": question.id,
                    "predicted": "unknown",
                    "gold": question.gold_answer,
                    "correct": 0,
                    "debate_log": {"error": str(e)},
                })

            await asyncio.sleep(0.3)  # Rate limit between questions

        # Compute metrics
        metrics_input = [
            {"predicted": r["predicted"], "gold": r["gold"], "dataset": self.dataset_name}
            for r in results
        ]
        metrics = compute_metrics(metrics_input)

        status = "failed" if len(errors) == len(questions) else "completed"

        experiment = {
            "id": self.experiment_id,
            "timestamp": datetime.utcnow().isoformat(),
            "model": self.model,
            "prompt_version": self.prompt_version,
            "dataset": self.dataset_name,
            "n_samples": len(questions),
            "n_stages": self.n_stages,
            "status": status,
            "metrics": metrics,
            "results": results,
            "config": self.config,
            "errors": errors if errors else None,
        }

        print(f"[{self.experiment_id}] Done. Accuracy: {metrics['accuracy']:.2%}")
        return experiment
