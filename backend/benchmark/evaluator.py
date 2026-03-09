"""Answer extraction and metrics computation."""

import re
from typing import List, Dict
from collections import defaultdict
from sklearn.metrics import f1_score, confusion_matrix as sk_confusion_matrix


def extract_answer(raw_output: str, dataset: str) -> str:
    """Parse LLM output into a normalized label.

    For pubmedqa: returns "yes", "no", or "maybe"
    For medqa/mmlu: returns "A", "B", "C", or "D"
    If extraction fails, returns "unknown"
    """
    if not raw_output:
        return "unknown"

    text = raw_output.strip()

    if dataset == "pubmedqa":
        # Check last line first (structured prompts put answer there)
        last_line = text.split("\n")[-1].strip().lower()
        for label in ["maybe", "yes", "no"]:
            if label == last_line:
                return label

        # Regex: look for standalone yes/no/maybe
        match = re.search(r'\b(yes|no|maybe)\b', text.lower())
        if match:
            return match.group(1)

        # Check first word
        first_word = text.split()[0].lower().rstrip(".,;:!") if text.split() else ""
        if first_word in ("yes", "no", "maybe"):
            return first_word

        return "unknown"

    else:  # medqa, mmlu
        # Check last line first
        last_line = text.split("\n")[-1].strip().upper()
        match = re.match(r'^([A-D])\b', last_line)
        if match:
            return match.group(1)

        # Regex: look for standalone letter answer patterns
        # "The answer is B", "Answer: C", just "B"
        match = re.search(r'(?:answer\s*(?:is|:)\s*)([A-D])\b', text, re.IGNORECASE)
        if match:
            return match.group(1).upper()

        match = re.search(r'\b([A-D])\)', text)
        if match:
            return match.group(1).upper()

        # Check if entire response is just a letter
        if text.upper().rstrip(".,;:!") in ("A", "B", "C", "D"):
            return text.upper().rstrip(".,;:!")

        # First word
        first_word = text.split()[0].upper().rstrip(".,;:!") if text.split() else ""
        if first_word in ("A", "B", "C", "D"):
            return first_word

        return "unknown"


def compute_metrics(results: List[Dict]) -> Dict:
    """Compute accuracy, F1, and confusion matrix from results.

    Each result: {"predicted": str, "gold": str, "dataset": str}
    """
    if not results:
        return {"accuracy": 0.0, "f1_macro": 0.0, "total": 0}

    dataset = results[0]["dataset"]
    predicted = [r["predicted"] for r in results]
    gold = [r["gold"] for r in results]

    # Accuracy
    correct = sum(1 for p, g in zip(predicted, gold) if p == g)
    accuracy = correct / len(results)

    # Determine label set
    if dataset == "pubmedqa":
        labels = ["yes", "no", "maybe"]
    else:
        labels = ["A", "B", "C", "D"]

    # F1 macro (handle unknown predictions by treating them as a wrong class)
    all_labels = labels + (["unknown"] if any(p == "unknown" for p in predicted) else [])
    f1 = f1_score(gold, predicted, labels=labels, average="macro", zero_division=0)

    # Per-class metrics
    per_class = {}
    for label in labels:
        tp = sum(1 for p, g in zip(predicted, gold) if p == label and g == label)
        fp = sum(1 for p, g in zip(predicted, gold) if p == label and g != label)
        fn = sum(1 for p, g in zip(predicted, gold) if p != label and g == label)
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1_class = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
        per_class[label] = {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1_class, 4),
            "support": sum(1 for g in gold if g == label),
        }

    # Confusion matrix
    cm_labels = all_labels
    cm = defaultdict(lambda: defaultdict(int))
    for p, g in zip(predicted, gold):
        cm[g][p] += 1
    # Convert to regular dict
    confusion = {g: dict(preds) for g, preds in cm.items()}

    metrics = {
        "accuracy": round(accuracy, 4),
        "f1_macro": round(f1, 4),
        "per_class": per_class,
        "confusion_matrix": confusion,
        "total": len(results),
        "correct": correct,
    }

    # PubMedQA-specific: maybe recall
    if dataset == "pubmedqa" and "maybe" in per_class:
        metrics["maybe_recall"] = per_class["maybe"]["recall"]

    return metrics
