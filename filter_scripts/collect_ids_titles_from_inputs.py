from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]

INPUTS = [
    (
        ROOT / "Law_of_Messiah_nt.yaml",
        "The Law of Messiah - Torah from a New Covenant Perspective - Volume 3",
    ),
    (
        ROOT / "Law_of_Messiah_ot.yaml",
        "The Law of Messiah - Torah from a New Covenant Perspective - Volume 1 & 2",
    ),
    (
        ROOT / "volume_3_output" / "appendix_output" / "Appendix_Full.yaml",
        "The Law of Messiah - Torah from a New Covenant Perspective - Volume 3 - Appendix",
    ),
]

OUTPUT_PATH = ROOT / "filter_output" / "collected_ids_titles.yaml"
MANUAL_REVIEW_PATH = (
    ROOT / "filter_output" / "manually_reviewed_unique_positive_ids_titles.yaml"
)
MANUAL_NCLA_ADDITIONS_PATH = (
    ROOT / "filter_output" / "manually_added_ncla_collected_ids_titles.yaml"
)
CATEGORY_REVIEW_PATH = ROOT / "filter_output" / "category_normalization_review.yaml"


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


def build_manual_review_lookup(path: Path):
    if not path.exists():
        return {}

    review_data = load_yaml(path)
    lookup = {}
    for row in to_items(review_data):
        if not isinstance(row, dict):
            continue

        row_id = row.get("id")
        if not row_id:
            continue

        lookup[row_id] = {
            "unique": row.get("unique"),
            "double_ids": row.get("double_ids", []),
        }

    return lookup


def build_manual_ncla_lookup(path: Path):
    if not path.exists():
        return {}

    manual_data = load_yaml(path)
    lookup = {}
    for row in to_items(manual_data):
        if not isinstance(row, dict):
            continue

        row_id = row.get("id")
        if not row_id:
            continue

        lookup[row_id] = dict(row)

    return lookup


def build_existing_related_lookup(path: Path):
    if not path.exists():
        return {}

    existing_data = load_yaml(path)
    lookup = {}
    for row in to_items(existing_data):
        if not isinstance(row, dict):
            continue

        row_id = row.get("id")
        if not isinstance(row_id, str) or not row_id.strip():
            continue

        related = row.get("related_lawofmessiah", [])
        if not isinstance(related, list):
            continue

        lookup[row_id.strip()] = list(related)

    return lookup


def build_category_normalization_lookup(path: Path):
    if not path.exists():
        return {}

    review_data = load_yaml(path)
    if not isinstance(review_data, dict):
        return {}

    proposals = review_data.get("proposals", [])
    if not isinstance(proposals, list):
        return {}

    lookup = {}
    for proposal in proposals:
        if not isinstance(proposal, dict):
            continue
        if proposal.get("approved") is not True:
            continue

        final_category = proposal.get("proposed_final_category")
        if not isinstance(final_category, str):
            continue
        final_category = final_category.strip()
        if not final_category:
            continue

        aliases = proposal.get("aliases", [])
        if not isinstance(aliases, list):
            continue

        for alias in aliases:
            if not isinstance(alias, str):
                continue
            alias = alias.strip()
            if not alias:
                continue
            lookup[alias] = final_category

    return lookup


def normalize_category(row, category_lookup):
    if not category_lookup:
        return

    category = row.get("category")
    if not isinstance(category, str):
        return

    category = category.strip()
    if not category:
        return

    row["category"] = category_lookup.get(category, category)


def merge_related_lawofmessiah(row):
    merged = []
    seen = set()

    for field in [
        "related_lawofmessiah",
        "commandments_related_ot",
        "commandments_related_nt",
        "double_ids",
    ]:
        values = row.get(field, [])
        if not isinstance(values, list):
            continue

        for entry in values:
            if not isinstance(entry, dict):
                continue

            entry_id = entry.get("id")
            entry_title = entry.get("title")
            dedupe_key = (entry_id, entry_title)
            if dedupe_key in seen:
                continue

            seen.add(dedupe_key)
            merged.append(dict(entry))

    return merged


def normalize_related_lawofmessiah(entries):
    if not isinstance(entries, list):
        return []

    out = []
    seen = set()
    for entry in entries:
        if not isinstance(entry, dict):
            continue

        rel_id = entry.get("id")
        if not isinstance(rel_id, str) or not rel_id.strip():
            continue
        rel_id = rel_id.strip()

        rel_title = entry.get("title")
        if not isinstance(rel_title, str):
            rel_title = ""

        key = (rel_id, rel_title)
        if key in seen:
            continue

        seen.add(key)
        out.append({"id": rel_id, "title": rel_title})

    return out


def merge_related_lists(*lists):
    merged = []
    seen = set()

    for values in lists:
        if not isinstance(values, list):
            continue
        for entry in normalize_related_lawofmessiah(values):
            rel_id = entry.get("id", "")
            rel_title = entry.get("title", "")
            key = (rel_id, rel_title)
            if key in seen:
                continue
            seen.add(key)
            merged.append(entry)

    return merged


def expand_bidirectional_related(rows):
    rows_by_id = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        row_id = row.get("id")
        if not isinstance(row_id, str) or not row_id.strip():
            continue
        rows_by_id[row_id.strip()] = row

    for row in rows:
        if not isinstance(row, dict):
            continue

        row_id = row.get("id")
        if not isinstance(row_id, str) or not row_id.strip():
            continue
        row_id = row_id.strip()
        row_title = row.get("title") if isinstance(row.get("title"), str) else ""

        related = normalize_related_lawofmessiah(row.get("related_lawofmessiah", []))
        row["related_lawofmessiah"] = related

        for rel in list(related):
            rel_id = rel.get("id")
            if not isinstance(rel_id, str) or not rel_id.strip():
                continue
            rel_id = rel_id.strip()

            if rel_id == row_id:
                continue

            target = rows_by_id.get(rel_id)
            if not isinstance(target, dict):
                continue

            target_related = normalize_related_lawofmessiah(
                target.get("related_lawofmessiah", [])
            )

            has_backref = any(
                isinstance(entry, dict)
                and isinstance(entry.get("id"), str)
                and entry.get("id").strip() == row_id
                for entry in target_related
            )

            if not has_backref:
                target_related.append({"id": row_id, "title": row_title})

            target["related_lawofmessiah"] = normalize_related_lawofmessiah(target_related)


def normalize_commandment_subtitles(subtitles):
    if not isinstance(subtitles, list):
        return []

    out = []
    for subtitle in subtitles:
        if isinstance(subtitle, dict):
            subtitle_id = subtitle.get("id")
            subtitle_title = subtitle.get("commandment") or subtitle.get("title")
            if not subtitle_id or not subtitle_title:
                continue
            out.append(
                {
                    "id": str(subtitle_id).strip().upper(),
                    "commandment": str(subtitle_title).strip().rstrip("."),
                }
            )
            continue

        if isinstance(subtitle, str):
            raw = subtitle.strip().strip("'\"")
            if not raw:
                continue

            if ":" not in raw:
                continue

            subtitle_id, subtitle_title = raw.split(":", 1)
            subtitle_id = subtitle_id.strip().upper()
            subtitle_title = subtitle_title.strip().rstrip(".")
            if not subtitle_id or not subtitle_title:
                continue

            out.append({"id": subtitle_id, "commandment": subtitle_title})

    return out


def main():
    seen_ids = set()
    out = []
    manual_review_by_id = build_manual_review_lookup(MANUAL_REVIEW_PATH)
    manual_ncla_by_id = build_manual_ncla_lookup(MANUAL_NCLA_ADDITIONS_PATH)
    existing_related_by_id = build_existing_related_lookup(OUTPUT_PATH)
    category_lookup = build_category_normalization_lookup(CATEGORY_REVIEW_PATH)

    for path, source_name in INPUTS:
        data = load_yaml(path)
        for row in to_items(data):
            if not isinstance(row, dict):
                continue

            row_id = row.get("id")
            if not row_id or row_id in seen_ids:
                continue

            seen_ids.add(row_id)
            row_out = dict(row)
            row_out["source"] = source_name

            manual_review = manual_review_by_id.get(row_id)
            if manual_review:
                row_out.update(manual_review)

            manual_ncla_row = manual_ncla_by_id.get(row_id)
            if manual_ncla_row and isinstance(manual_ncla_row.get("ncla"), list):
                # Manual file is the source of truth for reviewed NCLA values.
                row_out["ncla"] = manual_ncla_row["ncla"]

            normalize_category(row_out, category_lookup)

            row_out["related_lawofmessiah"] = merge_related_lists(
                merge_related_lawofmessiah(row_out),
                existing_related_by_id.get(row_id, []),
            )
            normalized_subtitles = normalize_commandment_subtitles(
                row_out.get("commandment_subtitles", [])
            )
            if "commandment_subtitles" in row_out or normalized_subtitles:
                row_out["commandment_subtitles"] = normalized_subtitles
            row_out.pop("commandments_related_ot", None)
            row_out.pop("commandments_related_nt", None)
            row_out.pop("double_ids", None)

            out.append(row_out)

    # Keep manual-only entries so reviewed NCLA rows are never dropped.
    for row_id, manual_row in manual_ncla_by_id.items():
        if row_id in seen_ids:
            continue
        manual_row_out = dict(manual_row)
        normalize_category(manual_row_out, category_lookup)
        manual_row_out["related_lawofmessiah"] = merge_related_lists(
            manual_row_out.get("related_lawofmessiah", []),
            existing_related_by_id.get(row_id, []),
        )
        normalized_subtitles = normalize_commandment_subtitles(
            manual_row_out.get("commandment_subtitles", [])
        )
        if "commandment_subtitles" in manual_row_out or normalized_subtitles:
            manual_row_out["commandment_subtitles"] = normalized_subtitles
        out.append(manual_row_out)
        seen_ids.add(row_id)

    expand_bidirectional_related(out)

    OUTPUT_PATH.write_text(
        yaml.dump(out, default_flow_style=False, allow_unicode=True, sort_keys=False, width=1000),
        encoding="utf-8",
    )

    print(f"Wrote {OUTPUT_PATH}")
    print({"rows": len(out)})


if __name__ == "__main__":
    main()
