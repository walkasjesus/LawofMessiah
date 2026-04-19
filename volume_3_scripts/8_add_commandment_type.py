import yaml
import re
from pathlib import Path

# --- FILE PATHS ---
REPO_ROOT = Path(__file__).resolve().parent.parent
appendix_output_dir = REPO_ROOT / "volume_3_output" / "appendix_output"
appendix_output_dir.mkdir(parents=True, exist_ok=True)
input_yaml_file = appendix_output_dir / "Mitzvah_Title_List.yaml"
output_yaml_file = appendix_output_dir / "Mitzvah_Title_List.yaml"

# --- LOAD YAML ---
with open(input_yaml_file, "r", encoding="utf-8") as f:
    data = yaml.safe_load(f)

def determine_commandment_type(text: str) -> str:
    """
    Determine if a commandment is Positive, Negative, or Positive & Negative
    based on grammatical cues.
    """
    if not text:
        return "Positive"

    text = text.strip().lower()

    # Detect Positive & Negative when phrase contains a positive clause followed by "and not ..."
    if re.search(r"\band not\b", text):
        return "Positive & Negative"

    # Detect Negative if it contains any negative keyword
    negative_keywords = [
        "do not",
        "shall not",
        "must not",
        "cannot",
        "not "
    ]
    for keyword in negative_keywords:
        if keyword in text:
            return "Negative"

    return "Positive"

# --- ADD ATTRIBUTE ---
for cmd in data:
    cmd_text = cmd.get("commandment") or cmd.get("title") or ""
    cmd["commandment_type"] = determine_commandment_type(cmd_text)

# --- SAVE UPDATED YAML ---
with open(output_yaml_file, "w", encoding="utf-8") as f:
    yaml.dump(
        data,
        f,
        allow_unicode=True,
        sort_keys=False,
        width=2000,
        default_flow_style=False
    )

print(f"✅ Added 'commandment_type' to {output_yaml_file}")
