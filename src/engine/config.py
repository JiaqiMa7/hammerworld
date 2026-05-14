"""Unified configuration for the HammerWorld project.

Priority chain (highest → lowest):
  1. Environment variables
  2. ~/.hammerworld/config file (key=value format)
  3. Built-in defaults

Config file location: ~/.hammerworld/config

Example config file::

    api_key=sk-xxx
    api_base=https://api.deepseek.com
    model=gpt-4o                # default model for all tasks
    agent_model=gpt-4o          # for agent assistant
    mining_model=deepseek-v4-pro  # for mine/math-mine
    triz_model=gpt-4o           # for TRIZ analysis
    HAMMERWORLD_ADDRESS=0x...
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional


_DEFAULT_API_BASE = "https://api.openai.com/v1"
_DEFAULT_MODEL = "gpt-4o"

_TASK_MODEL_KEYS = {
    "default": "model",
    "agent": "agent_model",
    "mining": "mining_model",
    "triz": "triz_model",
}


def _load_file() -> dict[str, str]:
    """Load key=value pairs from ~/.hammerworld/config."""
    config: dict[str, str] = {}
    config_path = Path.home() / ".hammerworld" / "config"
    if config_path.exists():
        for line in config_path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            config[k.strip()] = v.strip().strip('"').strip("'")
    return config


class HammerConfig:
    """Global configuration, loaded once. All modules read from here."""

    _instance: Optional["HammerConfig"] = None

    def __init__(self):
        file_cfg = _load_file()

        # API key: env > config file > None
        self.api_key: Optional[str] = (
            os.environ.get("HAMMERWORLD_API_KEY")
            or file_cfg.get("api_key")
        )

        # API base: env > config file > default
        self.api_base: str = (
            os.environ.get("HAMMERWORLD_API_BASE")
            or file_cfg.get("api_base")
            or _DEFAULT_API_BASE
        ).rstrip("/")

        # Per-task models (no env overrides — too many)
        self._models: dict[str, str] = {}
        for task, cfg_key in _TASK_MODEL_KEYS.items():
            self._models[task] = (
                file_cfg.get(cfg_key)
                or file_cfg.get("model")
                or os.environ.get("HAMMERWORLD_MODEL")
                or _DEFAULT_MODEL
            )

        # Address
        self.address: Optional[str] = (
            os.environ.get("HAMMERWORLD_ADDRESS")
            or file_cfg.get("HAMMERWORLD_ADDRESS")
        )

    def get_model(self, task: str = "default") -> str:
        """Return the model name for *task* (default|agent|mining|triz)."""
        return self._models.get(task, self._models["default"])

    @classmethod
    def load(cls) -> "HammerConfig":
        """Return the singleton config instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reload(cls) -> "HammerConfig":
        """Force re-read config from disk/env. Useful for tests."""
        cls._instance = cls()
        return cls._instance
