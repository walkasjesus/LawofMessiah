from pathlib import Path
import yaml


REPO_ROOT = Path(__file__).resolve().parent.parent
APPENDIX_OUTPUT_DIR = REPO_ROOT / "volume_3_output" / "appendix_output"
TITLES_FILE = APPENDIX_OUTPUT_DIR / "Mitzvah_Title_List.yaml"
SCRIPTURES_FILE = APPENDIX_OUTPUT_DIR / "Scripture_Index.yaml"
OUTPUT_FILE = APPENDIX_OUTPUT_DIR / "Appendix_Full.yaml"


def load_yaml_list(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Missing input file: {path}")
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or []
    if not isinstance(data, list):
        raise ValueError(f"Expected a list in {path}, got {type(data).__name__}")
    return data


def normalize_id(raw_id):
    if not isinstance(raw_id, str):
        return raw_id
    import re

    match = re.match(r"^([A-Z]{2,})(\d+)$", raw_id.strip())
    if not match:
        return raw_id.strip()
    prefix, number = match.groups()
    return f"{prefix}{int(number)}"


def merge_appendix():
    APPENDIX_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    titles = load_yaml_list(TITLES_FILE)
    scriptures = load_yaml_list(SCRIPTURES_FILE)

    titles_by_id = {}
    for row in titles:
        if not isinstance(row, dict):
            continue
        row_id = normalize_id(row.get("id"))
        if row_id:
            item = dict(row)
            item["id"] = row_id
            titles_by_id[row_id] = item

    scriptures_by_id = {}
    for row in scriptures:
        if not isinstance(row, dict):
            continue
        row_id = normalize_id(row.get("id"))
        if row_id:
            item = dict(row)
            item["id"] = row_id
            scriptures_by_id[row_id] = item

    all_ids = sorted(set(titles_by_id.keys()) | set(scriptures_by_id.keys()))
    merged = []

    for row_id in all_ids:
        title_row = titles_by_id.get(row_id, {})
        scripture_row = scriptures_by_id.get(row_id, {})

        merged_row = {
            "id": row_id,
            "title": title_row.get("title", ""),
            "category": title_row.get("category", ""),
            "commandment_type": title_row.get("commandment_type", ""),
            "copyright": title_row.get("copyright", ""),
            "bible_references": scripture_row.get("bible_references", {}),
        }
        merged.append(merged_row)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        yaml.dump(
            merged,
            f,
            allow_unicode=True,
            sort_keys=False,
            default_flow_style=False,
            width=2000,
        )

    print(f"Merged appendix YAML written to {OUTPUT_FILE}")
    print(f"Total merged entries: {len(merged)}")


if __name__ == "__main__":
    merge_appendix()
