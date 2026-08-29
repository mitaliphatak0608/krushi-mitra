"""Search router - semantic search over schemes using embeddings."""
import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_FILE = ROOT_DIR / "data" / "schemes_content.json"
VECTOR_STORE = Path(__file__).resolve().parent.parent / "vector_store"
INDEX_FILE = VECTOR_STORE / "schemes.faiss"
METADATA_FILE = VECTOR_STORE / "metadata.json"
EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

router = APIRouter(prefix="/api/search", tags=["search"])

# Load model and index at module import (once, not per-request)
_model = None
_index = None
_metadata = None


def _load_resources():
    """Lazy-load embedding model and FAISS index (only when search is actually used)."""
    global _model, _index, _metadata
    
    # Import faiss/transformers only when needed
    import faiss
    from sentence_transformers import SentenceTransformer
    
    if _model is None:
        _model = SentenceTransformer(EMBEDDING_MODEL)
    
    if _index is None or _metadata is None:
        if not INDEX_FILE.exists() or not METADATA_FILE.exists():
            raise RuntimeError("Vector store not found. Run `python -m app.ingest` first.")
        
        _index = faiss.read_index(str(INDEX_FILE))
        _metadata = json.loads(METADATA_FILE.read_text(encoding="utf-8"))
    
    return _model, _index, _metadata


class SchemeSearchResult(BaseModel):
    scheme_id: str
    scheme_name_en: str
    category: str
    score: float


@router.get("/schemes", response_model=list[SchemeSearchResult])
def search_schemes(q: str, limit: int = 5) -> list[SchemeSearchResult]:
    """
    Semantic search over schemes in all supported languages.
    
    Query in any language (English, Hindi, Marathi) and get results
    ranked by semantic similarity.
    """
    model, index, metadata = _load_resources()
    
    # Encode query using the multilingual model
    query_embedding = model.encode([q], normalize_embeddings=True)
    
    # Search FAISS index
    scores, indexes = index.search(query_embedding, min(limit, len(metadata)))
    
    # Deduplicate by scheme_id and format results
    seen_schemes = {}  # Maps scheme_id -> (best_score, result)
    
    for score, idx in zip(scores[0], indexes[0]):
        if idx < 0:
            continue
        
        doc_entry = metadata[idx]
        scheme_id = doc_entry.get("scheme_id")
        original_scheme = doc_entry.get("original_scheme", {})
        
        # Keep only the highest score for each scheme (from any language)
        if scheme_id not in seen_schemes or score > seen_schemes[scheme_id][0]:
            result = SchemeSearchResult(
                scheme_id=scheme_id,
                scheme_name_en=original_scheme.get("scheme_name", {}).get("en", "Unknown"),
                category=original_scheme.get("category", "Unknown"),
                score=float(score)
            )
            seen_schemes[scheme_id] = (score, result)
    
    # Sort by score and return top limit results
    results = sorted(
        [result for _, result in seen_schemes.values()],
        key=lambda r: r.score,
        reverse=True
    )[:limit]
    
    return results
