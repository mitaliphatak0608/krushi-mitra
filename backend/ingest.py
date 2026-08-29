import json
from pathlib import Path
from typing import Any

import faiss
from sentence_transformers import SentenceTransformer


ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT_DIR / "data" / "schemes_content.json"
VECTOR_STORE = Path(__file__).resolve().parent / "vector_store"
INDEX_FILE = VECTOR_STORE / "schemes.faiss"
METADATA_FILE = VECTOR_STORE / "metadata.json"
EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

# ---------------------------------------------------------------------------
# Short-form aliases for schemes whose colloquial names differ from the
# official text stored in schemes_content.json.
#
# These are embedded as extra lightweight "alias" vectors so that brief
# Marathi/Hindi queries (e.g. "पीक विमा", "ठिबक") return the right scheme
# even when the model struggles to link a 2-word query to a long document.
#
# Format: { scheme_id: { lang: [alias_phrase, ...] } }
# ---------------------------------------------------------------------------
SCHEME_ALIASES: dict[str, dict[str, list[str]]] = {
    "PMFBY": {
        "en": ["crop insurance", "fasal bima", "kharif insurance", "rabi insurance"],
        "hi": ["फसल बीमा", "पीएम फसल बीमा योजना", "पीएमएफबीवाई"],
        "mr": ["पीक विमा", "पीएम पीक विमा योजना", "खरीप पीक विमा", "रब्बी पीक विमा"],
    },
    "MICRO_IRRIGATION": {
        "en": ["drip irrigation", "sprinkler irrigation", "micro irrigation subsidy"],
        "hi": ["ड्रिप सिंचाई", "स्प्रिंकलर सिंचाई", "सूक्ष्म सिंचाई अनुदान", "टपक सिंचाई"],
        "mr": ["ठिबक सिंचन", "तुषार सिंचन", "ठिबक अनुदान", "ठिबक सिंचन अनुदान", "सूक्ष्म सिंचन"],
    },
    "SOLAR_PUMP": {
        "en": ["solar pump", "solar agricultural pump", "mukhyamantri solar pump"],
        "hi": ["सौर पंप", "सौर कृषि पंप", "सोलर पंप योजना"],
        "mr": ["सौर पंप", "सौर कृषी पंप", "मुख्यमंत्री सौर कृषी पंप योजना"],
    },
    "PMKISAN": {
        "en": ["PM KISAN", "kisan samman nidhi", "direct income support farmer"],
        "hi": ["पीएम किसान", "किसान सम्मान निधि", "प्रत्यक्ष आय सहायता"],
        "mr": ["पीएम किसान", "किसान सन्मान निधी", "शेतकरी उत्पन्न सहाय्य"],
    },
    "KARJMAFI": {
        "en": ["loan waiver", "crop loan waiver", "debt relief farmer"],
        "hi": ["कर्जमाफी", "फसल ऋण माफी", "किसान ऋण मुक्ति"],
        "mr": ["कर्जमाफी", "पीक कर्जमाफी", "शेतकरी कर्जमुक्ती"],
    },
    "WELL_SUBSIDY": {
        "en": ["well subsidy", "new well construction", "borewell subsidy"],
        "hi": ["कुआं अनुदान", "नई कुआं निर्माण", "बोरवेल अनुदान"],
        "mr": ["विहीर अनुदान", "नवीन विहीर बांधणी", "विहीर दुरुस्ती अनुदान"],
    },
    "KCC": {
        "en": ["kisan credit card", "crop credit card", "KCC loan"],
        "hi": ["किसान क्रेडिट कार्ड", "केसीसी", "फसल ऋण कार्ड"],
        "mr": ["किसान क्रेडिट कार्ड", "के.सी.सी.", "पीक कर्ज कार्ड"],
    },
    "PKVY": {
        "en": ["organic farming", "organic grant", "paramparagat krishi vikas"],
        "hi": ["जैविक खेती", "परंपरागत कृषि विकास योजना", "पीकेवीवाई"],
        "mr": ["सेंद्रिय शेती", "परंपरागत कृषी विकास योजना", "सेंद्रिय अनुदान"],
    },
    "SMAM": {
        "en": ["farm mechanization", "tractor subsidy", "power tiller subsidy", "SMAM"],
        "hi": ["कृषि यंत्रीकरण", "ट्रैक्टर अनुदान", "पावर टिलर", "एसएमएएम"],
        "mr": ["शेती यंत्रीकरण", "ट्रॅक्टर अनुदान", "पॉवर टिलर अनुदान"],
    },
    "NAMO_SHETKARI": {
        "en": ["namo shetkari", "Maharashtra income support", "state top-up grant"],
        "hi": ["नमो शेतकारी", "महाराष्ट्र आय सहायता", "राज्य अनुदान"],
        "mr": ["नमो शेतकरी", "नमो शेतकरी महासन्मान निधी", "राज्य उत्पन्न अनुदान"],
    },
    "FARM_POND": {
        "en": ["farm pond", "water storage pond", "shetatale"],
        "hi": ["खेत तालाब", "सिंचाई तालाब", "फार्म पॉन्ड"],
        "mr": ["शेततळे", "फार्म पॉन्ड", "शेत तलाव अनुदान"],
    },
}


def scheme_to_texts(scheme: dict[str, Any]) -> dict[str, str]:
    """
    Convert a scheme dict to multilingual text documents.

    Returns a dict with keys 'en', 'hi', 'mr' — one searchable text blob per
    language, combining scheme_id, category, type, and all translatable fields.
    """
    text_fields = ("scheme_name", "benefit_text", "eligibility_summary", "status_notes")

    result = {}
    for lang in ("en", "hi", "mr"):
        parts = [scheme["scheme_id"], scheme["category"], scheme["type"]]
        for field in text_fields:
            field_data = scheme.get(field, {})
            if isinstance(field_data, dict):
                parts.extend(field_data.get(lang, "").splitlines())

        docs_data = scheme.get("documents_required", {})
        if isinstance(docs_data, dict):
            parts.extend(docs_data.get(lang, []))

        result[lang] = "\n".join(part for part in parts if part)

    return result


def ingest() -> None:
    schemes: list[dict[str, Any]] = json.loads(DATA_FILE.read_text(encoding="utf-8"))

    documents: list[str] = []
    document_metadata: list[dict[str, Any]] = []

    # Pass 1 — one full-content document per scheme per language
    for scheme in schemes:
        multilang_texts = scheme_to_texts(scheme)
        for lang in ("en", "hi", "mr"):
            documents.append(multilang_texts[lang])
            document_metadata.append({
                "scheme_id": scheme["scheme_id"],
                "language": lang,
                "original_scheme": scheme,
            })

    # Pass 2 — short alias vectors for colloquial/abbreviated queries
    # Each alias phrase gets its own vector pointing to the same scheme,
    # so "पीक विमा" (2 words) embeds and retrieves PMFBY correctly.
    alias_count = 0
    scheme_map = {s["scheme_id"]: s for s in schemes}
    for scheme_id, lang_aliases in SCHEME_ALIASES.items():
        scheme = scheme_map.get(scheme_id)
        if scheme is None:
            continue
        for lang, phrases in lang_aliases.items():
            for phrase in phrases:
                documents.append(phrase)
                document_metadata.append({
                    "scheme_id": scheme_id,
                    "language": lang,
                    "original_scheme": scheme,
                })
                alias_count += 1

    total_docs = len(documents)
    n_schemes  = len(schemes)
    print(
        f"Embedding {total_docs} documents "
        f"({n_schemes} schemes x 3 langs = {n_schemes * 3} content vectors, "
        f"{alias_count} alias vectors)..."
    )

    model = SentenceTransformer(EMBEDDING_MODEL)
    embeddings = model.encode(documents, normalize_embeddings=True, show_progress_bar=True)

    # Inner-product index (cosine similarity after L2-normalisation)
    index = faiss.IndexFlatIP(embeddings.shape[1])
    index.add(embeddings)

    VECTOR_STORE.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(INDEX_FILE))
    METADATA_FILE.write_text(
        json.dumps(document_metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(
        f"[OK] Ingested {n_schemes} schemes "
        f"({total_docs} total vectors: {n_schemes * 3} content + {alias_count} aliases) "
        f"into {VECTOR_STORE}"
    )


if __name__ == "__main__":
    ingest()