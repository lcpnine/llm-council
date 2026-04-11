"""PubMedBERT classifier for medical QA benchmarks."""

import os
import json
import torch
import numpy as np
from transformers import AutoTokenizer, AutoModelForSequenceClassification, AutoModelForMultipleChoice

from ..config import MODELS_DIR

# Map dataset name to model subfolder
DATASET_MODEL_MAP = {
    "pubmedqa": "pubmedbert-pubmedqa",
    "medqa":    "pubmedbert-medqa",
    "mmlu":     "pubmedbert-mmlu",
}

# Cache loaded models so we don't reload on every question
_model_cache = {}


def _load_model(dataset: str):
    """Load the correct model and tokenizer for the dataset. Cached after first load."""
    if dataset in _model_cache:
        return _model_cache[dataset]

    folder = DATASET_MODEL_MAP.get(dataset)
    if not folder:
        raise ValueError(f"No PubMedBERT model configured for dataset: {dataset}")

    model_path = os.path.join(MODELS_DIR, folder)
    if not os.path.exists(model_path):
        raise FileNotFoundError(
            f"PubMedBERT model not found at {model_path}. "
            f"Download and unzip the model folder into the models/ directory."
        )

    # Load label map
    label_map_path = os.path.join(model_path, "label_map.json")
    with open(label_map_path) as f:
        label_map = json.load(f)  # e.g. {"0": "yes", "1": "no", "2": "maybe"}

    tokenizer = AutoTokenizer.from_pretrained(model_path)

    # PubMedQA uses SequenceClassification, MedQA/MMLU use MultipleChoice
    if dataset == "pubmedqa":
        model = AutoModelForSequenceClassification.from_pretrained(model_path)
    else:
        model = AutoModelForMultipleChoice.from_pretrained(model_path)

    model.eval()

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = model.to(device)

    _model_cache[dataset] = (model, tokenizer, label_map, device)
    return _model_cache[dataset]


def predict(question_text: str, dataset: str, options: list = None) -> str:
    """
    Run PubMedBERT inference on a single question.

    Args:
        question_text: The full question text (with context for PubMedQA)
        dataset: "pubmedqa", "medqa", or "mmlu"
        options: List of 4 option strings for medqa/mmlu. Not needed for pubmedqa.

    Returns:
        Predicted answer string: "yes"/"no"/"maybe" for pubmedqa, "A"/"B"/"C"/"D" for others
    """
    model, tokenizer, label_map, device = _load_model(dataset)

    with torch.no_grad():
        if dataset == "pubmedqa":
            enc = tokenizer(
                question_text,
                truncation=True,
                padding="max_length",
                max_length=512,
                return_tensors="pt",
            )
            enc = {k: v.to(device) for k, v in enc.items()}
            logits = model(**enc).logits
            pred_idx = int(torch.argmax(logits, dim=-1).item())

        else:
            # MultipleChoice: tokenize each (question, option) pair
            if not options or len(options) != 4:
                raise ValueError(f"Expected 4 options for {dataset}, got: {options}")

            encodings = tokenizer(
                [question_text] * 4,
                options,
                truncation=True,
                padding="max_length",
                max_length=512,
                return_tensors="pt",
            )
            # Reshape to [1, 4, seq_len]
            enc = {k: v.unsqueeze(0).to(device) for k, v in encodings.items()}
            logits = model(**enc).logits
            pred_idx = int(torch.argmax(logits, dim=-1).item())

    return label_map[str(pred_idx)]
