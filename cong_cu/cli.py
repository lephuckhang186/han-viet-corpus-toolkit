"""Backward-compatible shim for hanviet.source_preparation.cli."""
from hanviet.source_preparation.cli import parser_for, run, run_plan

__all__ = ["parser_for", "run", "run_plan"]
