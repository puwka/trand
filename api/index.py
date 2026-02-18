"""
Vercel serverless entrypoint. Exposes FastAPI app only.
No code execution, no side effects, no heavy imports.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

# Deferred import: backend.app builds app with router; no execution on import
from backend.app.server import app
