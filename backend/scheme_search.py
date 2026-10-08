import json
import faiss
import numpy as np
from pathlib import Path
from functools import lru_cache
from sentence_transformers import SentenceTransformer

VECTOR_STORE = Path(__file__).resolve().parent / "vector_store"
INDEX_FILE = VECTOR_STORE / "schemes.faiss"
METADATA_FILE = VECTOR_STORE / "metadata.json"
EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

_index = None
_metadata = None

@lru_cache(maxsize=1)
def get_search_model() -> SentenceTransformer:
    return SentenceTransformer(EMBEDDING_MODEL)

def load_vector_store():
    global _index, _metadata
    if _index is None:
        _index = faiss.read_index(str(INDEX_FILE))
        _metadata = json.loads(METADATA_FILE.read_text(encoding="utf-8"))
    return _index, _metadata

def search_schemes_semantic(query: str, threshold: float = 0.20):
    try:
        index, metadata = load_vector_store()
    except Exception as exc:
        return None, 0.0
    
    model = get_search_model()
    query_vec = model.encode([query], normalize_embeddings=True)
    scores, indices = index.search(query_vec, 1)
    
    best_idx = int(indices[0][0])
    best_score = float(scores[0][0])
    
    if best_idx < 0 or best_score < threshold:
        return None, best_score
        
    return metadata[best_idx], best_score
