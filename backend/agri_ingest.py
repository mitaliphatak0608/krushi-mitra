"""
backend/agri_ingest.py
======================
Ingestion pipeline for Agricultural Knowledge Base (Phase 2).

Reads verified JSON documents, validates structure and authority,
generates L2-normalized embeddings using OpenAI text-embedding-3-small,
and builds an IndexFlatIP (cosine similarity) FAISS index.
"""

import json
import logging
import os
import sys
from pathlib import Path

# pyrefly: ignore [missing-import]
import faiss
# pyrefly: ignore [missing-import]
import numpy as np


# Add project root to sys.path so we can run this directly
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.embeddings import embed_batch

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

VECTOR_STORE_DIR = Path(__file__).resolve().parent / "vector_store"
INDEX_FILE = VECTOR_STORE_DIR / "agri_knowledge.faiss"
METADATA_FILE = VECTOR_STORE_DIR / "agri_metadata.json"

REQUIRED_FIELDS = {"source", "authority", "official_url", "verification_status"}


def validate_doc(doc: dict, allow_test: bool = False) -> bool:
    """
    Strict validation of a knowledge base document.
    """
    for field in REQUIRED_FIELDS:
        if not doc.get(field):
            logger.warning(f"Document {doc.get('id', 'unknown')} missing required field: {field}")
            return False

    status = doc["verification_status"]
    if status == "verified":
        return True
    
    if status == "synthetic_test" and allow_test:
        return True

    logger.warning(f"Document {doc.get('id', 'unknown')} rejected. Invalid status: {status}")
    return False


def chunk_text(text: str, max_chars: int = 1500) -> list[str]:
    """Basic chunking by paragraph/newline to stay within context windows."""
    paragraphs = text.split("\n\n")
    chunks = []
    current_chunk = ""

    for p in paragraphs:
        if len(current_chunk) + len(p) < max_chars:
            current_chunk += p + "\n\n"
        else:
            if current_chunk.strip():
                chunks.append(current_chunk.strip())
            current_chunk = p + "\n\n"
    
    if current_chunk.strip():
        chunks.append(current_chunk.strip())
        
    return chunks


def build_index(data_dir: Path, output_index: Path, output_meta: Path, allow_test: bool = False):
    """
    Reads JSON files, builds FAISS index, and saves metadata.
    """
    if not data_dir.exists() or not data_dir.is_dir():
        logger.error(f"Directory not found: {data_dir}")
        return

    documents = []
    for filepath in data_dir.glob("*.json"):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                doc = json.load(f)
                if validate_doc(doc, allow_test):
                    documents.append(doc)
        except Exception as e:
            logger.error(f"Failed to read {filepath}: {e}")

    if not documents:
        logger.info(f"No valid documents found in {data_dir}. Index not built.")
        return

    chunks_data = []
    texts_to_embed = []

    for doc in documents:
        title = doc.get("title", "")
        content = doc.get("content", "")
        # Combine title and content for better semantics
        full_text = f"Title: {title}\n\nContent: {content}"
        
        chunks = chunk_text(full_text)
        for chunk in chunks:
            chunks_data.append({
                "document_id": doc.get("id"),
                "title": doc.get("title"),
                "authority": doc.get("authority"),
                "source": doc.get("source"),
                "official_url": doc.get("official_url"),
                "language": doc.get("language"),
                "topic": doc.get("topic"),
                "crop": doc.get("crop"),
                "state": doc.get("state"),
                "publication_date": doc.get("publication_date"),
                "last_verified": doc.get("last_verified"),
                "verification_status": doc.get("verification_status"),
                "chunk_content": chunk
            })
            texts_to_embed.append(chunk)

    logger.info(f"Generating embeddings for {len(texts_to_embed)} chunks...")
    # Generate embeddings via OpenAI
    try:
        raw_embeddings = embed_batch(texts_to_embed)
    except Exception as e:
        logger.error(f"Failed to generate embeddings: {e}")
        return

    # L2 Normalization for Cosine Similarity
    embeddings_np = np.array(raw_embeddings, dtype=np.float32)
    faiss.normalize_L2(embeddings_np)

    # Initialize IndexFlatIP (Inner Product). Since vectors are L2 normalized, IP == Cosine Similarity
    dimension = embeddings_np.shape[1]
    index = faiss.IndexFlatIP(dimension)
    index.add(embeddings_np)

    # Ensure output dir exists
    output_index.parent.mkdir(parents=True, exist_ok=True)

    faiss.write_index(index, str(output_index))
    with open(output_meta, "w", encoding="utf-8") as f:
        json.dump(chunks_data, f, ensure_ascii=False, indent=2)

    logger.info(f"Successfully built FAISS index with {len(chunks_data)} chunks.")
    logger.info(f"Index saved to {output_index}")
    logger.info(f"Metadata saved to {output_meta}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Ingest Agricultural Knowledge Base")
    parser.add_argument("--test", action="store_true", help="Allow synthetic_test documents and read from test dir")
    args = parser.parse_args()

    if args.test:
        data_dir = Path(__file__).resolve().parents[1] / "data" / "agri_knowledge_test"
        idx_file = VECTOR_STORE_DIR / "agri_knowledge_test.faiss"
        meta_file = VECTOR_STORE_DIR / "agri_metadata_test.json"
        logger.info("Running in TEST mode. Accepting synthetic_test documents.")
        build_index(data_dir, idx_file, meta_file, allow_test=True)
    else:
        data_dir = Path(__file__).resolve().parents[1] / "data" / "agri_knowledge"
        logger.info("Running in PROD mode. Strictly enforcing verified documents.")
        build_index(data_dir, INDEX_FILE, METADATA_FILE, allow_test=False)
