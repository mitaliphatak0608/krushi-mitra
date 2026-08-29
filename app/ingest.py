"""Backend ingest module - run with: python -m app.ingest"""
import sys
from pathlib import Path

# Add parent directory to path so we can import from backend
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.ingest import ingest

if __name__ == "__main__":
    ingest()
