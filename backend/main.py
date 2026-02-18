"""
Local dev entrypoint. Re-exports app from server.
For Vercel: api/index.py imports from backend.app.server
For uvicorn: uvicorn backend.main:app
"""

import sys
from pathlib import Path

_backend = Path(__file__).resolve().parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

from app.server import app
