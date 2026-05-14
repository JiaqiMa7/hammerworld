"""AI provider implementations for evaluation and TRIZ analysis."""
from __future__ import annotations

import json
import urllib.request
from typing import Optional

from src.engine.config import HammerConfig


def get_api_key() -> Optional[str]:
    """Return the configured API key, or None if not set."""
    return HammerConfig.load().api_key


def get_api_base() -> str:
    """Return the API base URL. Defaults to OpenAI."""
    return HammerConfig.load().api_base


def get_model() -> str:
    """Return the default model name. Defaults to gpt-4o."""
    return HammerConfig.load().get_model("default")


def get_model_for_task(task: str) -> str:
    """Return the model for a specific task (mining, triz, agent, default)."""
    return HammerConfig.load().get_model(task)


class OpenAIProvider:
    """OpenAI-compatible API provider using stdlib only. No pip install needed."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.api_key = api_key or get_api_key()
        self.api_base = (api_base or get_api_base()).rstrip("/")
        self.model = model or get_model()

        if not self.api_key:
            raise ValueError(
                "No API key configured. Set one of:\n"
                "  export HAMMERWORLD_API_KEY=sk-...\n"
                "  or add 'api_key=sk-...' to ~/.hammerworld/config"
            )

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Send a chat completion request to the API."""
        url = f"{self.api_base}/chat/completions"
        body = json.dumps({
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.7,
            "max_tokens": 4096,
        }).encode()

        req = urllib.request.Request(url, data=body, method="POST")
        req.add_header("Content-Type", "application/json")
        req.add_header("Authorization", f"Bearer {self.api_key}")

        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read())
            return data["choices"][0]["message"]["content"]
        except urllib.error.HTTPError as exc:
            body = exc.read().decode(errors="replace")
            raise RuntimeError(f"API request failed ({exc.code}): {body}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"API connection failed: {exc.reason}") from exc
        except (KeyError, IndexError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"Unexpected API response format: {exc}") from exc
