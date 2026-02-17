"""Vercel serverless entry point. Handles all /api/* routes."""
import sys
import os
from pathlib import Path

# Add project root so backend can be imported
root = Path(__file__).resolve().parent.parent
if str(root) not in sys.path:
    sys.path.insert(0, str(root))
# Vercel: ensure backend is findable
backend_path = root / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

# .env not deployed — rely on Vercel env vars only
os.chdir(str(root))

try:
    from backend.main import app
except Exception as e:
    import traceback
    traceback.print_exc()
    raise
