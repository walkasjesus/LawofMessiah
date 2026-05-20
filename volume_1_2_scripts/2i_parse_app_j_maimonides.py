import os
import re
import yaml
from bs4 import BeautifulSoup, NavigableString, Tag

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def script_path(*parts):
    return os.path.normpath(os.path.join(SCRIPT_DIR, *parts))


APP_E_PATH = "volume_1_2_scraped_files/App-E.php"
APP_F_PATH = "volume_1_2_scraped_files/App-F.php"
APP_G_PATH = "volume_1_2_scraped_files/App-G.php"
APP_J_PATH = "volume_1_2_scraped_files/App-J.php"
OUTPUT_PATH = "volume_1_2_output/output_maimonides.yaml"


def normalize_ws(value):
    return " ".join(str(value or "").split()).strip()


def normalize_code(value):
    return normalize_ws(value).replace(" ", "").rstrip("*")


def split_codes(value):
    normalized = normalize_ws(value)
    if not normalized or normalized == "--":
        return []

    parts = re.split(r"\s*(?:,|\+)\s*", normalized)
    return [normalize_code(part) for part in parts if normalize_code(part)]


def split_scriptures(value):
    normalized = normalize_ws(value)
    if not normalized or normalized == "--":
        return []

    return [part.strip() for part in normalized.split(";") if part.strip()]


def extend_unique(target, values):
    seen = set(target)
    for value in values:
        if value and value not in seen:
            target.append(value)
            seen.add(value)


def add_scripture_detail(target, item_id, scriptures):
    normalized_id = normalize_code(item_id)
    normalized_scriptures = split_scriptures("; ".join(scriptures)) if isinstance(scriptures, str) else list(scriptures or [])
    if not normalized_id or not normalized_scriptures:
        return

    for detail in target:
        if detail.get("id") == normalized_id:
            extend_unique(detail.setdefault("scriptures", []), normalized_scriptures)
            return

    target.append({
        "id": normalized_id,
        "scriptures": normalized_scriptures,
    })


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
            "meir": [],
            "chinuch": [],
            "rudolph": [],
            "scriptures": [],
            "meir_scriptures": [],
            "chinuch_scriptures": [],
        })

    return results


def iter_appendix_table_rows(path):
    with open(script_path("..", path), "r", encoding="ISO-8859-1") as f:
        html = f.read()

    for chunk in html.split("<tr>")[1:]:
        row_soup = BeautifulSoup("<tr>" + chunk, "html.parser")
        cells = []

        for td in row_soup.find_all("td"):
            if td.get("width"):
                continue
            text = normalize_ws(td.get_text(" ", strip=True))
            if text:
                cells.append(text)

        if len(cells) < 5:
            continue

        first_cell = cells[0].lower()
        if "maimonides" in first_cell or "meir" in first_cell or "chinuch" in first_cell:
            continue

        yield cells[:5]


def merge_cross_reference_data(commandments):
    commandments_by_id = {item["id"]: item for item in commandments}

    for maimonides_id, meir_text, chinuch_text, rudolph_text, scripture_text in iter_appendix_table_rows(APP_E_PATH):
        normalized_maimonides_id = normalize_code(maimonides_id)
        commandment = commandments_by_id.get(normalized_maimonides_id)
        if not commandment:
            continue

        extend_unique(commandment["meir"], split_codes(meir_text))
        extend_unique(commandment["chinuch"], split_codes(chinuch_text))
        extend_unique(commandment["rudolph"], split_codes(rudolph_text))
        extend_unique(commandment["scriptures"], split_scriptures(scripture_text))

    for meir_id, maimonides_id, chinuch_text, rudolph_text, scripture_text in iter_appendix_table_rows(APP_F_PATH):
        normalized_maimonides_id = normalize_code(maimonides_id)
        commandment = commandments_by_id.get(normalized_maimonides_id)
        if not commandment:
            continue

        normalized_meir_id = normalize_code(meir_id)
        extend_unique(commandment["meir"], [normalized_meir_id])
        extend_unique(commandment["chinuch"], split_codes(chinuch_text))
        extend_unique(commandment["rudolph"], split_codes(rudolph_text))
        add_scripture_detail(commandment["meir_scriptures"], normalized_meir_id, split_scriptures(scripture_text))

    for chinuch_id, maimonides_id, meir_text, rudolph_text, scripture_text in iter_appendix_table_rows(APP_G_PATH):
        normalized_maimonides_id = normalize_code(maimonides_id)
        commandment = commandments_by_id.get(normalized_maimonides_id)
        if not commandment:
            continue

        normalized_chinuch_id = normalize_code(chinuch_id)
        extend_unique(commandment["chinuch"], [normalized_chinuch_id])
        extend_unique(commandment["meir"], split_codes(meir_text))
        extend_unique(commandment["rudolph"], split_codes(rudolph_text))
        add_scripture_detail(commandment["chinuch_scriptures"], normalized_chinuch_id, split_scriptures(scripture_text))


def main():
    with open(script_path("..", APP_J_PATH), "r", encoding="ISO-8859-1") as f:
        soup = BeautifulSoup(f, "html.parser")

    positive_font = find_section_font(soup, r"248 Positive Mitzvot")
    negative_font = find_section_font(soup, r"365 Negative Mitzvot")

    positive = extract_commandments(lines_from_font(positive_font), "RP")
    negative = extract_commandments(lines_from_font(negative_font), "RN")
    commandments = positive + negative
    merge_cross_reference_data(commandments)

    data = {
        "source_files": [APP_J_PATH, APP_E_PATH, APP_F_PATH, APP_G_PATH],
        "totals": {
            "positive": len(positive),
            "negative": len(negative),
            "all": len(positive) + len(negative),
        },
        "commandments": commandments,
    }

    output_path = script_path("..", OUTPUT_PATH)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False, width=1000)

    print(f"Wrote {output_path}")
    print(f"Positive: {len(positive)} | Negative: {len(negative)} | Total: {len(positive) + len(negative)}")


if __name__ == "__main__":
    main()
