"""Test package init ensuring src/ is importable without requiring pip install -e . offline."""
from pathlib import Path
import sys

_SRC = Path(__file__).resolve().parents[1] / "src"
if _SRC.is_dir() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
