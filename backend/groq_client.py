"""Groq API client for making LLM requests."""

import httpx
from typing import List, Dict, Any, Optional
from .config import GROQ_API_KEY, GROQ_API_URL


async def query_model(
    model: str,
    messages: List[Dict[str, str]],
    timeout: float = 120.0
) -> Optional[Dict[str, Any]]:
    """
    Query a single model via Groq API (OpenAI-compatible format).

    Returns:
        Response dict with 'content', optional 'reasoning_details',
        and 'token_usage', or None if failed
    """
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model,
        "messages": messages,
    }

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                GROQ_API_URL,
                headers=headers,
                json=payload
            )
            response.raise_for_status()

            data = response.json()
            message = data['choices'][0]['message']

            # Extract token usage from Groq response
            usage = data.get('usage', {})
            token_usage = {
                'prompt_tokens': usage.get('prompt_tokens', 0),
                'completion_tokens': usage.get('completion_tokens', 0),
                'total_tokens': usage.get('total_tokens', 0),
            }

            return {
                'content': message.get('content'),
                'reasoning_details': message.get('reasoning_details'),
                'token_usage': token_usage,
            }

    except Exception as e:
        print(f"Error querying model {model}: {e}")
        return None
