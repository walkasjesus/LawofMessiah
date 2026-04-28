from collections import defaultdict
from difflib import SequenceMatcher
from pathlib import Path
import re

import yaml

ROOT = Path(__file__).resolve().parents[1]
INPUT_PATH = ROOT / "filter_output" / "collected_ids_titles.yaml"
OUTPUT_PATH = ROOT / "filter_output" / "negative_related_lawofmessiah_review.yaml"
MAX_SUGGESTIONS = 8

STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "in",
    "into",
    "is",
    "it",
    "its",
    "not",
    "of",
    "on",
    "or",
    "our",
    "that",
    "the",
    "their",
    "them",
    "they",
    "this",
    "to",
    "we",
    "with",
    "you",
    "your",
    "was",
    "were",
    "will",
    "all",
    "do",
    "does",
}


def load_yaml(path: Path):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def to_items(data):
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        items = data.get("items", [])
        return items if isinstance(items, list) else []
    return []


def normalize_text(text):
    if not isinstance(text, str):
        return ""
    text = text.lower().replace("’", "'")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def tokenize(text):
    return {t for t in normalize_text(text).split() if t and t not in STOPWORDS}


def extract_related_ids(row):
    related = row.get("related_lawofmessiah", [])
    if not isinstance(related, list):
        return set()

    out = set()
    for entry in related:
        if not isinstance(entry, dict):
            continue
        rid = entry.get("id")
        if isinstance(rid, str) and rid.strip():
            out.add(rid.strip())
    return out


def is_negative(row):
    ctype = row.get("commandment_type")
    return isinstance(ctype, str) and ctype.strip().lower() == "negative"


def has_related_ids(row):
    return len(extract_related_ids(row)) > 0


def similarity_ratio(a, b):
    a = normalize_text(a)
    b = normalize_text(b)
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def overlap_score(a_tokens, b_tokens):
    if not a_tokens or not b_tokens:
        return 0.0
    inter = len(a_tokens.intersection(b_tokens))
    union = len(a_tokens.union(b_tokens))
    if union == 0:
        return 0.0
    return inter / union


def score_candidate(target, candidate, inbound_count):
    reasons = []
    score = 0.0

    if target.get("category") and target.get("category") == candidate.get("category"):
        score += 0.35
        reasons.append("same_category")

    title_sim = similarity_ratio(target.get("title", ""), candidate.get("title", ""))
    score += 0.25 * title_sim
    if title_sim >= 0.45:
        reasons.append("similar_title")

    target_title_tokens = tokenize(target.get("title", ""))
    cand_title_tokens = tokenize(candidate.get("title", ""))
    title_overlap = overlap_score(target_title_tokens, cand_title_tokens)
    score += 0.20 * title_overlap
    if title_overlap >= 0.20:
        reasons.append("title_keyword_overlap")

    target_cmd_tokens = tokenize(target.get("commandment", ""))
    cand_cmd_tokens = tokenize(candidate.get("commandment", ""))
    cmd_overlap = overlap_score(target_cmd_tokens, cand_cmd_tokens)
    score += 0.20 * cmd_overlap
    if cmd_overlap >= 0.15:
        reasons.append("commandment_keyword_overlap")

    if target.get("commandment_type") == candidate.get("commandment_type"):
        score += 0.05
        reasons.append("same_commandment_type")

    if inbound_count > 0:
        score += min(inbound_count, 25) * 0.005
        reasons.append("frequently_linked")

    return score, sorted(set(reasons))


def main():
    rows = to_items(load_yaml(INPUT_PATH))

    rows_by_id = {}
    for row in rows:
        rid = row.get("id")
        if isinstance(rid, str) and rid.strip():
            rows_by_id[rid.strip()] = row

    inbound = defaultdict(int)
    for row in rows:
        for rel_id in extract_related_ids(row):
            inbound[rel_id] += 1

    targets = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        rid = row.get("id")
        if not isinstance(rid, str) or not rid.strip():
            continue
        if is_negative(row) and not has_related_ids(row):
            targets.append(row)

    review_items = []
    for target in targets:
        target_id = target["id"]
        existing_related = extract_related_ids(target)

        suggestions = []
        for cand_id, cand in rows_by_id.items():
            if cand_id == target_id or cand_id in existing_related:
                continue
            if str(cand.get("commandment_type", "")).strip().lower() != "positive":
                continue

            score, reasons = score_candidate(target, cand, inbound.get(cand_id, 0))
            if score <= 0.12:
                continue

            suggestions.append(
                {
                    "id": cand_id,
                    "title": cand.get("title", ""),
                    "score": round(score, 4),
                    "reasons": reasons,
                }
            )

        suggestions.sort(key=lambda x: (-x["score"], x["id"]))
        suggestions = suggestions[:MAX_SUGGESTIONS]

        approved_ids = [entry["id"] for entry in suggestions if entry.get("score", 0) > 0.5]
        if not approved_ids:
            approved_ids = [""]

        review_items.append(
            {
                "id": target.get("id"),
                "title": target.get("title", ""),
                "existing_related_lawofmessiah": [],
                "suggested_related_lawofmessiah": suggestions,
                "review": {
                    "approved": False,
                    "approved_related_lawofmessiah": approved_ids,
                    "notes": "",
                },
            }
        )

    out = {
        "schema_version": 1,
        "description": "Manual review for NEGATIVE items missing related_lawofmessiah links.",
        "source_file": "filter_output/collected_ids_titles.yaml",
        "how_to_review": [
            "Review each item under items.",
            "Use suggested_related_lawofmessiah as candidates.",
            "Set review.approved to true when done.",
            "Fill review.approved_related_lawofmessiah with selected IDs.",
            "Optional: add context in review.notes.",
        ],
        "stats": {
            "total_rows": len(rows),
            "negative_rows_missing_related_ids": len(review_items),
        },
        "items": review_items,
    }

    OUTPUT_PATH.write_text(
        yaml.dump(out, default_flow_style=False, allow_unicode=True, sort_keys=False, width=1000),
        encoding="utf-8",
    )

    print(f"Wrote {OUTPUT_PATH}")
    print(out["stats"])


if __name__ == "__main__":
    main()
