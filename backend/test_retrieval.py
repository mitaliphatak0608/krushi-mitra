"""
backend/test_retrieval.py
=========================
RAG retrieval smoke-test — run this after every re-ingest to confirm that
semantic search returns the expected scheme *before* wiring anything to an LLM.

Usage:
    python backend/test_retrieval.py

Exit code 0  → all test cases passed
Exit code 1  → one or more test cases failed
"""

import json
import sys
from pathlib import Path

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

# Force UTF-8 output so Devanagari query strings print correctly on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ---------------------------------------------------------------------------
# Paths (same as ingest.py / main.py)
# ---------------------------------------------------------------------------
VECTOR_STORE = Path(__file__).resolve().parent / "vector_store"
INDEX_FILE   = VECTOR_STORE / "schemes.faiss"
METADATA_FILE = VECTOR_STORE / "metadata.json"
EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
NO_MATCH_THRESHOLD = 0.30   # scores below this → "no good match"

# ---------------------------------------------------------------------------
# Test cases: (query, expected_scheme_id_or_None, lang_hint)
# None  → we expect NO match above threshold
# lang_hint is used for labelling only; search is cross-lingual
# ---------------------------------------------------------------------------
TEST_CASES: list[tuple[str, str | None, str]] = [
    # English
    ("crop insurance for kharif season",        "PMFBY",             "en"),
    ("drip irrigation subsidy Maharashtra",      "MICRO_IRRIGATION",  "en"),
    ("solar pump yojana",                        "SOLAR_PUMP",        "en"),
    ("organic farming grant",                    "PKVY",              "en"),
    ("kisan credit card interest subvention",    "KCC",               "en"),
    ("farm mechanization tractor subsidy",       "SMAM",              "en"),
    # Marathi — cross-lingual: Marathi query matches best English/Marathi vector
    ("पीक विमा",                                "PMFBY",             "mr"),  # crop insurance
    ("कर्जमाफी",                               "KARJMAFI",          "mr"),  # loan waiver
    ("ठिबक सिंचन अनुदान",                       "MICRO_IRRIGATION",  "mr"),  # drip irrigation subsidy
    # Hindi
    ("सौर कृषी पंप योजना",                      "SOLAR_PUMP",        "hi"),  # solar agri pump
    # No-match case
    ("weather forecast today",                   None,               "en"),
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_store() -> tuple[faiss.Index, list[dict]]:
    if not INDEX_FILE.exists() or not METADATA_FILE.exists():
        print("[ERROR] Vector store not found. Run `python backend/ingest.py` first.")
        sys.exit(1)
    index = faiss.read_index(str(INDEX_FILE))
    metadata = json.loads(METADATA_FILE.read_text(encoding="utf-8"))
    return index, metadata


def top_match(
    query: str,
    index: faiss.Index,
    metadata: list[dict],
    model: SentenceTransformer,
) -> tuple[str | None, float]:
    """
    Cross-lingual search — return (scheme_id, score) for the best match
    regardless of which language vector it came from.

    Using cross-lingual retrieval means a Marathi query like 'ठिबक सिंचन अनुदान'
    will correctly match the MICRO_IRRIGATION English vector (score ~0.71) instead
    of being restricted to potentially weaker Marathi-only vectors.
    """
    vec: np.ndarray = model.encode([query], normalize_embeddings=True)
    scores, indices = index.search(vec, 1)
    if indices[0][0] < 0:
        return None, 0.0
    best = metadata[indices[0][0]]
    return best["scheme_id"], float(scores[0][0])


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print("=" * 62)
    print("  Krushi Mitra — RAG Retrieval Smoke Test")
    print("=" * 62)

    index, metadata = load_store()
    print(f"  Index loaded: {index.ntotal} vectors, dim={index.d}")

    print(f"\n  Loading model: {EMBEDDING_MODEL} ...")
    model = SentenceTransformer(EMBEDDING_MODEL)
    print("  Model ready.\n")

    col_q  = 42   # query column width
    col_s  = 20   # scheme_id column width

    header = f"  {'Query':<{col_q}}  {'Top match':<{col_s}}  {'Score':>6}  Result"
    print(header)
    print("  " + "-" * (len(header) - 2))

    passed = 0
    failed = 0

    for query, expected_id, lang in TEST_CASES:
        scheme_id, score = top_match(query, index, metadata, model)

        # Determine pass / fail
        if expected_id is None:
            # Expect no match above threshold
            ok = score < NO_MATCH_THRESHOLD
            actual_label = f"NO MATCH (score={score:.2f})"
        else:
            ok = (scheme_id == expected_id) and (score >= NO_MATCH_THRESHOLD)
            actual_label = scheme_id or "NO MATCH"

        status = "[PASS]" if ok else "[FAIL]"
        if ok:
            passed += 1
        else:
            failed += 1

        # Truncate long queries for display
        q_display = query if len(query) <= col_q else query[: col_q - 1] + "…"
        print(f"  {q_display:<{col_q}}  {actual_label:<{col_s}}  {score:>6.3f}  {status}")

        if not ok:
            print(f"         Expected: {expected_id!r}")

    print("\n" + "=" * 62)
    print(f"  Result: {passed}/{len(TEST_CASES)} passed", end="")
    if failed:
        print(f"  ({failed} FAILED)")
    else:
        print("  -- all good!")
    print("=" * 62)

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
