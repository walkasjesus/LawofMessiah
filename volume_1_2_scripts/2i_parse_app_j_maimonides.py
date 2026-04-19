import os
import re
import yaml
from bs4 import BeautifulSoup, NavigableString, Tag

APP_J_PATH = "volume_1_2_scraped_files/App-J.php"
OUTPUT_PATH = "volume_1_2_output/output_maimonides.yaml"


def normalize_ws(value):
    return " ".join(str(value or "").split()).strip()


def lines_from_font(font_tag):
    """Split content on <br> while preserving inline text within each line."""
    lines = []
    buffer = []

    for child in font_tag.children:
        if isinstance(child, Tag) and child.name == "br":
            line = normalize_ws(" ".join(buffer))
            if line:
                lines.append(line)
            buffer = []
        elif isinstance(child, NavigableString):
            text = str(child)
            if text.strip():
                buffer.append(text)
        elif isinstance(child, Tag):
            text = child.get_text(" ", strip=False)
            if text.strip():
                buffer.append(text)

    trailing = normalize_ws(" ".join(buffer))
    if trailing:
        lines.append(trailing)

    return lines


def find_section_font(soup, title_pattern):
    title = soup.find("b", string=re.compile(title_pattern))
    if not title:
        raise ValueError(f"Could not find section title matching: {title_pattern}")

    # The lines are in the next <p> tag containing a size=4 font block.
    p = title.find_parent("p")
    if not p:
        raise ValueError(f"Could not find parent paragraph for: {title_pattern}")

    target_p = p.find_next("p")
    if not target_p:
        raise ValueError(f"Could not find section content paragraph for: {title_pattern}")

    font = target_p.find("font", attrs={"size": "4"})
    if not font:
        raise ValueError(f"Could not find section font for: {title_pattern}")

    return font


def extract_commandments(lines, expected_prefix):
    results = []
    pattern = re.compile(r"^(R[PN]\d+)\s*:\s*(.+)$")

    for line in lines:
        match = pattern.match(line)
        if not match:
            continue

        code, commandment = match.groups()
        if not code.startswith(expected_prefix):
            continue

        commandment = re.sub(r"\s*Return to main index\s*$", "", normalize_ws(commandment), flags=re.IGNORECASE)

        results.append({
            "id": code,
            "commandment_type": "Positive" if code.startswith("RP") else "Negative",
            "commandment": commandment,
        })

    return results


def main():
    with open(APP_J_PATH, "r", encoding="ISO-8859-1") as f:
        soup = BeautifulSoup(f, "html.parser")

    positive_font = find_section_font(soup, r"248 Positive Mitzvot")
    negative_font = find_section_font(soup, r"365 Negative Mitzvot")

    positive = extract_commandments(lines_from_font(positive_font), "RP")
    negative = extract_commandments(lines_from_font(negative_font), "RN")

    data = {
        "source_file": APP_J_PATH,
        "totals": {
            "positive": len(positive),
            "negative": len(negative),
            "all": len(positive) + len(negative),
        },
        "commandments": positive + negative,
    }

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False, width=1000)

    print(f"Wrote {OUTPUT_PATH}")
    print(f"Positive: {len(positive)} | Negative: {len(negative)} | Total: {len(positive) + len(negative)}")


if __name__ == "__main__":
    main()
