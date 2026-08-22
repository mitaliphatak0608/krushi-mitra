# Krushi Mitra — Scheme Data (Task 5 Output)

This folder contains the structured JSON data generated from the Scheme Reference spreadsheet (Task 3/4). It splits scheme data into **two deliberately separate files**, matching the core design principle of the whole project: the LLM/RAG side should only ever read natural-language content, and the eligibility engine should only ever read structured, machine-checkable fields — never the reverse.

## Files

| File | Used by | Contains |
|---|---|---|
| `schemes_content.json` | RAG retrieval / embeddings / chatbot responses | Human-readable scheme name, benefit description, eligibility summary, documents, official link — in English now, with `hi`/`mr` fields left blank for Task 6 (translation) |
| `eligibility_rules.json` | Deterministic eligibility rule engine | Structured, checkable fields: landholding bands (numeric), region top-ups, category shares, land record requirements, crop season, special conditions |
| `schemes_content.schema.json` | Validation | JSON Schema (draft-07) for `schemes_content.json` — run any future edits through this before committing |
| `eligibility_rules.schema.json` | Validation | JSON Schema (draft-07) for `eligibility_rules.json` |

Both data files are linked by `scheme_id` (e.g. `"MICRO_IRRIGATION"`) — always join on this field, never on the scheme name (names can have spelling/translation variants; the ID never changes).

## How to validate after editing

```bash
pip install jsonschema
python3 -c "
import json, jsonschema
content = json.load(open('schemes_content.json'))
schema = json.load(open('schemes_content.schema.json'))
jsonschema.validate(content, schema)
print('OK')
"
```
Run the same pattern for `eligibility_rules.json` against `eligibility_rules.schema.json`.

## Important: `verify_needed` fields

Several entries in `eligibility_rules.json` have a non-empty `verify_needed` list — these mark exact numbers (mostly category-wise subsidy percentages for SMAM, Well Subsidy, and Karjmafi) that the spreadsheet's free text didn't give as a precise, checkable figure. **Do not treat these as final until confirmed against the live MahaDBT portal.** Once confirmed, fill in the real number and clear the `verify_needed` note for that field. This mirrors the exact numeric-hallucination risk your project is designed to guard against — don't let an unverified guess slip into the rule engine as if it were fact.

## Next steps

- **Task 6 (Translation):** fill in the `hi` and `mr` fields in `schemes_content.json` for every scheme. Keep `scheme_id` and all of `eligibility_rules.json` untouched — translation only ever touches the content file.
- **Task 7 (Rule engine logic):** write the actual Python decision functions that read `eligibility_rules.json` and a farmer's profile, and return a verdict per scheme.
- **Task 9 (Vector DB ingestion):** embed the `en` (and later `hi`/`mr`) fields from `schemes_content.json` — never embed anything from `eligibility_rules.json`, since that file has no natural-language content to search over.