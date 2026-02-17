"""Vercel serverless entry point. Handles all /api/* routes."""
import sys
from pathlib import Path

# Add project root so backend can be imported
root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))

from backend.main import app
