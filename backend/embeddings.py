"""
backend/embeddings.py
=====================
OpenAI embeddings wrapper for Krushi Mitra.

Uses ``text-embedding-3-small`` by default (configurable via
``OPENAI_EMBEDDING_MODEL`` env var).

PHASE 1 NOTE
─────────────
This module provides embedding primitives for *future* use (Phase 2:
agricultural knowledge base).  During Phase 1 the existing FAISS scheme
index continues to use the local ``sentence-transformers`` model.
Do NOT mix vectors from different embedding models in the same FAISS index.
"""

import os
import logging
from typing import Optional

from openai import OpenAI

logger = logging.getLogger(__name__)


def _get_client() -> OpenAI:
    """Return an OpenAI client, raising clearly if the key is missing."""
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key or api_key.startswith("your-"):
        raise RuntimeError(
            "OPENAI_API_KEY is not configured. "
            "Set it in backend/.env (see .env.example)."
        )
    return OpenAI(api_key=api_key)


def _get_model() -> str:
    return os.environ.get("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")


# ── Public API ────────────────────────────────────────────────────────────

def embed_text(text: str, model: Optional[str] = None) -> list[float]:
    """
    Embed a single text string.

    Returns the embedding vector as a list of floats.
    """
    client = _get_client()
    mdl = model or _get_model()

    response = client.embeddings.create(model=mdl, input=text)
    return response.data[0].embedding


def embed_batch(texts: list[str], model: Optional[str] = None) -> list[list[float]]:
    """
    Embed multiple texts in one API call.

    Returns a list of embedding vectors, one per input text, in the same
    order as the input.
    """
    if not texts:
        return []

    client = _get_client()
    mdl = model or _get_model()

    response = client.embeddings.create(model=mdl, input=texts)
    # The API may return embeddings out of order; sort by index.
    sorted_data = sorted(response.data, key=lambda d: d.index)
    return [item.embedding for item in sorted_data]
