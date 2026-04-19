import os
import json
import yaml
import re
from pathlib import Path

# === CONFIGURATION ===
REPO_ROOT = Path(__file__).resolve().parent.parent
yaml_output_dir = REPO_ROOT / "volume_3_output" / "appendix_output"
yaml_output_dir.mkdir(parents=True, exist_ok=True)
input_json_file = yaml_output_dir / "Mitzvah_Title_List.json"

category_pattern = re.compile(r"^([A-Z]{2})\.\s*(.*)")  # e.g., AA. Godliness, Holiness...
commandment_pattern = re.compile(r"^(\d{1,3})\s+(.*)")  # e.g., 01 Aspiring to Godliness...
trailing_page_pattern = re.compile(r"\s+\d{1,4}\s*[-‐‑–—]\s*\d{1,4}\s*$")
commandment_id_pattern = re.compile(r"^([A-Z]{2,})(\d+)$")


def clean_title(text):
    """Remove trailing appendix page markers from parsed commandment titles."""
    cleaned = trailing_page_pattern.sub("", text).strip()
    return re.sub(r"\s{2,}", " ", cleaned)


def normalize_commandment_id(raw_id):
    """Normalize appendix commandment IDs like AA01 -> AA1."""
    match = commandment_id_pattern.match(raw_id)
    if not match:
        return raw_id
    prefix, number = match.groups()
    return f"{prefix}{int(number)}"

def parse_commandments_flat(json_file):
    """
    Parse JSON and output a flat list of commandments with category reference.
    Each item: {id: 'AA1', title: 'Aspiring to Godliness', category: 'Godliness, Holiness...'}
    """
    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    results = []
    current_category = None
    current_cat_id = None

    for page in data:
        for block in page.get("blocks", []):
            for line in block.get("lines", []):
                line_text = "".join(span.get("text", "") for span in line.get("spans", []))
                text = line_text.strip()
                if not text:
                    continue

                # Detect category
                match_cat = category_pattern.match(text)
                if match_cat:
                    current_cat_id, cat_name = match_cat.groups()
                    current_category = cat_name.strip()
                    continue

                # Detect commandment
                match_cmd = commandment_pattern.match(text)
                if match_cmd and current_category and current_cat_id:
                    cmd_num, cmd_text = match_cmd.groups()
                    cmd_id = normalize_commandment_id(f"{current_cat_id}{cmd_num}")
                    results.append({
                        "id": cmd_id,
                        "title": clean_title(cmd_text),
                        "category": current_category
                    })

    return results


if __name__ == "__main__":
    if not input_json_file.exists():
        raise FileNotFoundError(f"Input file not found: {input_json_file}")

    commandments = parse_commandments_flat(input_json_file)

    yaml_filename = input_json_file.stem + ".yaml"
    yaml_output_path = yaml_output_dir / yaml_filename

    with open(yaml_output_path, "w", encoding="utf-8") as yf:
        yaml.dump(commandments, yf, allow_unicode=True, sort_keys=False)

    print(f"✅ Parsed {len(commandments)} commandments -> {yaml_output_path}")
