"""Backward-compatible shim for hanviet.source_preparation.text_ops."""
from hanviet.source_preparation.text_ops import join_parts, read_text, select_characters, select_lines

__all__ = ["join_parts", "read_text", "select_characters", "select_lines"]
