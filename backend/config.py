"""Configuration for the Medical QA Benchmark."""

import os
from dotenv import load_dotenv

load_dotenv()

# Groq API key
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Groq API endpoint (OpenAI-compatible)
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

# Default model for benchmarks
DEFAULT_MODEL = "llama-3.3-70b-versatile"

# Available models for benchmark runs (Groq-hosted)
AVAILABLE_MODELS = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "qwen/qwen3-32b",
    "meta-llama/llama-4-scout-17b-16e-instruct",
]

# Data directory
DATA_DIR = "data"
