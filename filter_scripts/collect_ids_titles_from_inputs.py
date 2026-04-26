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
            "related_steps": row.get("related_steps", []),
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


def merge_related_lawofmessiah(row):
    merged = []
    seen = set()

    for field in ["commandments_related_ot", "commandments_related_nt", "double_ids"]:
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

            row_out["related_lawofmessiah"] = merge_related_lawofmessiah(row_out)
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
        normalized_subtitles = normalize_commandment_subtitles(
            manual_row_out.get("commandment_subtitles", [])
        )
        if "commandment_subtitles" in manual_row_out or normalized_subtitles:
            manual_row_out["commandment_subtitles"] = normalized_subtitles
        out.append(manual_row_out)
        seen_ids.add(row_id)

    OUTPUT_PATH.write_text(
        yaml.dump(out, default_flow_style=False, allow_unicode=True, sort_keys=False, width=1000),
        encoding="utf-8",
    )

    print(f"Wrote {OUTPUT_PATH}")
    print({"rows": len(out)})


if __name__ == "__main__":
    main()
