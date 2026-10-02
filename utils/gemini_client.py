"""Google Gemini API client integration."""

import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


class GeminiError(Exception):
    """Custom exception for Gemini API related errors."""
    pass


_cached_client = None
_cached_api_key = None


def get_api_key() -> Optional[str]:
    """Retrieve Gemini API key from environment."""
    return os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")


def is_gemini_configured() -> bool:
    """Check if a Gemini API key is configured."""
    key = get_api_key()
    return bool(key and key.strip() and key.strip() != "your_gemini_api_key_here")


def set_api_key(api_key: str) -> None:
    """Set the Gemini API key dynamically."""
    global _cached_client, _cached_api_key
    clean_key = api_key.strip()
    os.environ["GEMINI_API_KEY"] = clean_key
    _cached_api_key = clean_key
    _cached_client = None


def get_gemini_client():
    """Get or create Google GenAI Client instance."""
    global _cached_client, _cached_api_key
    current_key = get_api_key()

    if not is_gemini_configured():
        raise GeminiError(
            "GEMINI_API_KEY is not configured. Please set GEMINI_API_KEY in your .env file or UI sidebar."
        )

    if _cached_client is not None and _cached_api_key == current_key:
        return _cached_client

    try:
        from google import genai
        _cached_client = genai.Client(api_key=current_key)
        _cached_api_key = current_key
        return _cached_client
    except Exception as exc:
        raise GeminiError(f"Failed to initialize Google GenAI Client: {exc}") from exc


import time


def generate_gemini_content(
    prompt: str,
    model: Optional[str] = None,
    system_instruction: Optional[str] = None,
    max_retries_per_model: int = 2,
) -> str:
    """Generate text using Google Gemini API with automatic model fallback and retries.

    Args:
        prompt: User prompt content.
        model: Model name (defaults to GEMINI_MODEL env var or 'gemini-3.8-flash').
        system_instruction: Optional system instruction.
        max_retries_per_model: Attempts per candidate model on transient errors.

    Returns:
        Generated text string.
    """
    primary_model = model or os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
    client = get_gemini_client()

    candidate_models = [primary_model]
    for fallback in ["gemini-3.8-flash", "gemini-3.5-flash", "gemini-3.5-flash-lite"]:
        if fallback not in candidate_models:
            candidate_models.append(fallback)

    last_error = None
    from google.genai import types

    config = types.GenerateContentConfig(
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        system_instruction=system_instruction,
    )

    for candidate in candidate_models:
        for attempt in range(max_retries_per_model):
            try:
                response = client.models.generate_content(
                    model=candidate,
                    contents=prompt,
                    config=config,
                )
                if response and response.text:
                    return response.text.strip()
                return ""
            except Exception as exc:
                last_error = exc
                err_msg = str(exc)
                if "API_KEY_INVALID" in err_msg or ("400" in err_msg and "key" in err_msg.lower()):
                    raise GeminiError(f"Invalid Google Gemini API key: {err_msg}") from exc
                # If model is unavailable (503), rate limited (429), or deprecated (404), try next attempt or model
                if any(code in err_msg for code in ("503", "UNAVAILABLE", "429", "RESOURCE_EXHAUSTED", "404", "NOT_FOUND")):
                    time.sleep(0.5 * (attempt + 1))
                    continue
                raise GeminiError(f"Gemini API error: {err_msg}") from exc

    raise GeminiError(f"Gemini API error: {last_error}") from last_error
