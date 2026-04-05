"""Baseline experiment configurations for comparison."""

BASELINES = [
    {
        "name": "Single Agent Zero-Shot",
        "description": "Single LLM, no debate, no CoT",
        "model": "llama-3.3-70b-versatile",
        "prompt_version": "v1_baseline",
        "n_stages": 1,
    },
    {
        "name": "Single Agent CoT",
        "description": "Single LLM with chain-of-thought, no debate",
        "model": "llama-3.3-70b-versatile",
        "prompt_version": "v1_cot",
        "n_stages": 1,
    },
    {
        "name": "Multi-Agent v1",
        "description": "Full 3-stage debate with baseline prompts",
        "model": "llama-3.3-70b-versatile",
        "prompt_version": "v1_baseline",
        "n_stages": 3,
    },
    {
        "name": "Multi-Agent v2",
        "description": "Full 3-stage debate with structured evidence-based prompts",
        "model": "llama-3.3-70b-versatile",
        "prompt_version": "v2_structured",
        "n_stages": 3,
    },
    {
        "name": "Multi-Agent v3",
        "description": "Full 3-stage debate with strict skeptic prompts",
        "model": "llama-3.3-70b-versatile",
        "prompt_version": "v3_skeptic_strict",
        "n_stages": 3,
    },
]
