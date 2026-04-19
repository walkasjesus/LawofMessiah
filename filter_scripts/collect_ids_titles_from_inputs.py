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


def main():
    seen_ids = set()
    out = []

    for path, source_name in INPUTS:
        data = load_yaml(path)
        for row in to_items(data):
            if not isinstance(row, dict):
                continue

            row_id = row.get("id")
            if not row_id or row_id in seen_ids:
                continue

            seen_ids.add(row_id)
            out.append(
                {
                    "id": row_id,
                    "title": row.get("title", ""),
                    "commandment_type": row.get("commandment_type"),
                    "source": source_name,
                }
            )

    OUTPUT_PATH.write_text(
        yaml.dump(out, default_flow_style=False, allow_unicode=True, sort_keys=False, width=1000),
        encoding="utf-8",
    )

    print(f"Wrote {OUTPUT_PATH}")
    print({"rows": len(out)})


if __name__ == "__main__":
    main()
