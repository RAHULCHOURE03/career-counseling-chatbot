"""Build the local page-aware PDF corpus before starting the Flask app."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from webapp.services.knowledge_base import build_corpus


if __name__ == "__main__":
    chunks = build_corpus()
    print(f"Knowledge corpus built successfully: {len(chunks)} chunks saved.")
