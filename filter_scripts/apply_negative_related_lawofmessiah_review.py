from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
COLLECTED_PATH = ROOT / "filter_output" / "collected_ids_titles.yaml"
REVIEW_PATH = ROOT / "filter_output" / "negative_related_lawofmessiah_review.yaml"


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


def build_row_lookup(rows):
    lookup = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        rid = row.get("id")
        if isinstance(rid, str) and rid.strip():
            lookup[rid.strip()] = row
    return lookup


def normalize_approved_ids(approved_related):
    ids = []
    if not isinstance(approved_related, list):
        return ids

    for entry in approved_related:
        if isinstance(entry, str):
            rid = entry.strip()
            if rid:
                ids.append(rid)
        elif isinstance(entry, dict):
            rid = entry.get("id")
            if isinstance(rid, str) and rid.strip():
                ids.append(rid.strip())
    return ids


def main():
    rows = to_items(load_yaml(COLLECTED_PATH))
    review_data = load_yaml(REVIEW_PATH)
    review_items = to_items(review_data)

    rows_by_id = build_row_lookup(rows)

    applied = 0
    skipped_missing_target = 0
    skipped_unapproved = 0

    for item in review_items:
        if not isinstance(item, dict):
            continue

        review = item.get("review", {})
        if not isinstance(review, dict) or review.get("approved") is not True:
            skipped_unapproved += 1
            continue

        target_id = item.get("id")
        if not isinstance(target_id, str) or target_id.strip() not in rows_by_id:
            skipped_missing_target += 1
            continue
        target_id = target_id.strip()

        approved_ids = normalize_approved_ids(review.get("approved_related_lawofmessiah", []))
        related_out = []
        seen = set()

        for rel_id in approved_ids:
            if rel_id in seen:
                continue
            seen.add(rel_id)

            rel_row = rows_by_id.get(rel_id)
            if not rel_row:
                continue

            related_out.append({"id": rel_id, "title": rel_row.get("title", "")})

        rows_by_id[target_id]["related_lawofmessiah"] = related_out
        applied += 1

    COLLECTED_PATH.write_text(
        yaml.dump(rows, default_flow_style=False, allow_unicode=True, sort_keys=False, width=1000),
        encoding="utf-8",
    )

    print(f"Updated {COLLECTED_PATH}")
    print(
        {
            "applied_items": applied,
            "skipped_unapproved": skipped_unapproved,
            "skipped_missing_target": skipped_missing_target,
        }
    )


if __name__ == "__main__":
    main()
