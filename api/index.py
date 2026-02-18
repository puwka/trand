"""Vercel FastAPI entrypoint.

Vercel's FastAPI detection expects an `app` variable in this module.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT / "backend"

# Ensure both `backend` package and `app` package (backend/app) are importable.
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Important: expose `app` at module top-level
from backend.main import app  # noqa: E402

