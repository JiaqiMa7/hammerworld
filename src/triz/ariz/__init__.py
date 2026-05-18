"""ARIZ-85C: Algorithm for Inventive Problem Solving."""
from src.triz.ariz.full import run_full
from src.triz.ariz.simplified import run_simplified
from src.triz.ariz.base import ARIZState, ARIZPhase, ARIZResult

__all__ = ["run_full", "run_simplified", "ARIZState", "ARIZPhase", "ARIZResult"]
