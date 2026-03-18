"""Dataset loaders for medical QA benchmarks."""

from dataclasses import dataclass, asdict
from typing import List
from datasets import load_dataset as hf_load_dataset


@dataclass
class Question:
    id: str
    dataset: str          # "pubmedqa" | "medqa" | "mmlu"
    question_text: str    # formatted prompt ready to send to LLM
    gold_answer: str      # "yes"/"no"/"maybe" or "A"/"B"/"C"/"D"
    raw: dict             # original record for reference


def _load_pubmedqa(n_samples: int, seed: int) -> List[Question]:
    ds = hf_load_dataset("qiaojin/PubMedQA", "pqa_labeled", split="train")
    ds = ds.shuffle(seed=seed).select(range(min(n_samples, len(ds))))

    questions = []
    for row in ds:
        # Concatenate abstract texts from the contexts dict
        contexts = row.get("context", {})
        abstract_texts = contexts.get("contexts", [])
        if isinstance(abstract_texts, list):
            context_str = "\n".join(abstract_texts)
        else:
            context_str = str(abstract_texts)

        prompt = f"Context:\n{context_str}\n\nQuestion: {row['question']}"

        questions.append(Question(
            id=str(row.get("pubid", len(questions))),
            dataset="pubmedqa",
            question_text=prompt,
            gold_answer=row["final_decision"].lower(),
            raw=dict(row),
        ))
    return questions


def _load_medqa(n_samples: int, seed: int) -> List[Question]:
    ds = hf_load_dataset("GBaker/MedQA-USMLE-4-options", split="test")
    ds = ds.shuffle(seed=seed).select(range(min(n_samples, len(ds))))

    questions = []
    for idx, row in enumerate(ds):
        options = row.get("options", {})
        options_text = "\n".join(
            f"{key}) {value}" for key, value in sorted(options.items())
        )
        prompt = f"{row['question']}\n\n{options_text}"

        answer_idx = row.get("answer_idx", "")

        questions.append(Question(
            id=f"medqa_{idx}",
            dataset="medqa",
            question_text=prompt,
            gold_answer=answer_idx.upper(),
            raw=dict(row),
        ))
    return questions


def _load_mmlu(n_samples: int, seed: int) -> List[Question]:
    configs = ["clinical_knowledge", "medical_genetics", "anatomy", "professional_medicine"]
    int_to_letter = {0: "A", 1: "B", 2: "C", 3: "D"}

    all_rows = []
    for config in configs:
        ds = hf_load_dataset("cais/mmlu", config, split="test")
        for row in ds:
            all_rows.append((config, dict(row)))

    # Shuffle and sample
    import random
    rng = random.Random(seed)
    rng.shuffle(all_rows)
    all_rows = all_rows[:min(n_samples, len(all_rows))]

    questions = []
    for idx, (config, row) in enumerate(all_rows):
        choices = row.get("choices", [])
        letters = ["A", "B", "C", "D"]
        options_text = "\n".join(
            f"{letters[i]}) {choices[i]}" for i in range(len(choices))
        )
        prompt = f"{row['question']}\n\n{options_text}"

        gold = int_to_letter.get(row.get("answer", -1), "unknown")

        questions.append(Question(
            id=f"mmlu_{config}_{idx}",
            dataset="mmlu",
            question_text=prompt,
            gold_answer=gold,
            raw=row,
        ))
    return questions


def load_dataset(name: str, n_samples: int = 100, seed: int = 42) -> List[Question]:
    """Load a medical QA dataset by name.

    Args:
        name: "pubmedqa", "medqa", or "mmlu"
        n_samples: Number of samples to load
        seed: Random seed for reproducibility

    Returns:
        List of Question dataclass instances
    """
    loaders = {
        "pubmedqa": _load_pubmedqa,
        "medqa": _load_medqa,
        "mmlu": _load_mmlu,
    }
    if name not in loaders:
        raise ValueError(f"Unknown dataset: {name}. Choose from: {list(loaders.keys())}")
    return loaders[name](n_samples, seed)
