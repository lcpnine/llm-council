"""Configuration for the Medical QA Benchmark."""

import os
from dotenv import load_dotenv

load_dotenv()

# OpenRouter API key
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# OpenRouter API endpoint
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

# Default model for benchmarks
DEFAULT_MODEL = "meta-llama/llama-3.1-70b-instruct"

# Available models for benchmark runs
AVAILABLE_MODELS = [
    "meta-llama/llama-3.1-70b-instruct",
    "openai/gpt-5.1",
    "google/gemini-3-pro-preview",
    "anthropic/claude-sonnet-4.5",
    "x-ai/grok-4",
]

# Data directory
DATA_DIR = "data"
