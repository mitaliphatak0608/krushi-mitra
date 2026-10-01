"""
backend/knowledge_base.py
=========================
Retrieval module for the Agricultural Knowledge Base.

Queries the `agri_knowledge.faiss` index built by `agri_ingest.py`.
Enforces strict L2 normalization of query vectors and configurable cosine
similarity thresholding.
"""

import json
import logging
import os
from pathlib import Path
from typing import Any

import faiss
import numpy as np

from backend.embeddings import embed_text

logger = logging.getLogger(__name__)

VECTOR_STORE_DIR = Path(__file__).resolve().parent / "vector_store"
PROD_INDEX = VECTOR_STORE_DIR / "agri_knowledge.faiss"
PROD_META = VECTOR_STORE_DIR / "agri_metadata.json"

TEST_INDEX = VECTOR_STORE_DIR / "agri_knowledge_test.faiss"
TEST_META = VECTOR_STORE_DIR / "agri_metadata_test.json"

# Cached instances
_index: faiss.Index | None = None
_metadata: list[dict[str, Any]] | None = None
_mode_is_test: bool = False


def _load_agri_store(use_test: bool = False) -> tuple[faiss.Index, list[dict[str, Any]]]:
    global _index, _metadata, _mode_is_test
    
    if _index is not None and _metadata is not None and _mode_is_test == use_test:
        return _index, _metadata

    idx_path = TEST_INDEX if use_test else PROD_INDEX
    meta_path = TEST_META if use_test else PROD_META

    if not idx_path.exists() or not meta_path.exists():
        raise FileNotFoundError(f"Agri knowledge index/meta not found for use_test={use_test}")

    _index = faiss.read_index(str(idx_path))
    with open(meta_path, "r", encoding="utf-8") as f:
        _metadata = json.load(f)
    _mode_is_test = use_test

    return _index, _metadata


def search_agri_knowledge(
    query: str,
    language: str | None = None,
    crop: str | None = None,
    state: str | None = None,
    topic: str | None = None,
    top_k: int = 3,
    use_test: bool = False
) -> list[dict[str, Any]]:
    """
    Semantically search the agricultural knowledge base.
    
    Returns a list of dicts with:
    {
       "score": float,
       "chunk_content": str,
       ...source metadata...
    }
    """
    try:
        index, meta = _load_agri_store(use_test)
    except FileNotFoundError:
        logger.warning(f"Agri knowledge base not found (test_mode={use_test}). Returning empty.")
        return []

    # Get threshold from env (default 0.70)
    try:
        threshold = float(os.environ.get("AGRI_RETRIEVAL_THRESHOLD", "0.70"))
    except ValueError:
        threshold = 0.70

    # 1. Embed query
    try:
        query_vec = embed_text(query)
    except Exception as e:
        logger.error(f"Failed to embed query: {e}")
        return []

    # 2. L2 Normalize query for cosine similarity against IndexFlatIP
    q_np = np.array([query_vec], dtype=np.float32)
    faiss.normalize_L2(q_np)

    # 3. Search FAISS
    scores, indices = index.search(q_np, top_k * 2)  # Retrieve extra to allow metadata filtering

    results = []
    seen_docs = set()

    for score, idx in zip(scores[0], indices[0]):
        if idx < 0:
            continue
        
        sim_score = float(score)
        
        # Enforce Threshold
        if sim_score < threshold:
            continue

        chunk_meta = meta[idx]
        
        # Security/Validity Check
        if not use_test and chunk_meta.get("verification_status") != "verified":
            continue

        # Simple metadata filtering (if provided)
        if crop and chunk_meta.get("crop") and crop.lower() not in chunk_meta.get("crop", "").lower():
            continue
        if topic and chunk_meta.get("topic") and topic.lower() != chunk_meta.get("topic", "").lower():
            continue
        
        doc_id = chunk_meta.get("document_id")
        
        # Deduplicate slightly if we got multiple chunks from the exact same doc_id
        # (For better variety. If needed, we could allow multiple chunks from the same doc).
        # We'll allow them but limit to prevent one doc dominating.
        
        result_item = {
            "score": sim_score,
            **chunk_meta
        }
        
        results.append(result_item)
        seen_docs.add(doc_id)

        if len(results) >= top_k:
            break

    return results
