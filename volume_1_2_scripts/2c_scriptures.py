import os
import yaml
from bs4 import BeautifulSoup
import re

# Directory containing the scraped HTML files
scraped_dir = "volume_1_2_scraped_commandments"
log_dir = "logs"
log_file = os.path.join(log_dir, "extraction_log.txt")

# Ensure the logs directory exists
os.makedirs(log_dir, exist_ok=True)

# Separate lists for Old Testament and New Testament books
ot_books = [
    "Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy",
    "Joshua", "Judges", "Ruth", "1 Samuel", "2 Samuel", "1 Kings", "2 Kings",
    "1 Chronicles", "2 Chronicles", "Ezra", "Nehemiah", "Esther", "Job",
    "Psalms", "Psalm", "Proverbs", "Ecclesiastes", "Song of Solomon", "Isaiah",
    "Jeremiah", "Lamentations", "Ezekiel", "Daniel", "Hosea", "Joel", "Amos",
    "Obadiah", "Jonah", "Micah", "Nahum", "Habakkuk", "Zephaniah", "Haggai",
    "Zechariah", "Malachi"
]

nt_books = [
    "Matthew", "Mark", "Luke", "John", "Acts", "Romans", "1 Corinthians",
    "2 Corinthians", "Galatians", "Ephesians", "Philippians", "Colossians",
    "1 Thessalonians", "2 Thessalonians", "1 Timothy", "2 Timothy", "Titus",
    "Philemon", "Hebrews", "James", "1 Peter", "2 Peter", "1 John", "2 John",
    "3 John", "Jude", "Revelation"
]

all_books = sorted(ot_books + nt_books, key=len, reverse=True)
book_prefix_re = re.compile(r"^(?:" + "|".join(re.escape(book) for book in all_books) + r")\b", re.IGNORECASE)
verse_token_re = re.compile(r"\d+\s*:\s*\d+")

# Function to extract key scriptures from an HTML file
def normalize_reference(reference):
    text = str(reference or "")
    # Remove footnote markers like *, ** around references.
    text = text.replace("*", "")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def normalize_reference_minimal(reference):
    text = str(reference or "")
    # Conservative cleanup for existing outputs to avoid broad churn.
    text = text.replace("*", "")
    return text.strip()


def is_likely_scripture_reference(text):
    # Guard against commentary prose such as "Peter explains that ...".
    return bool(book_prefix_re.search(text) and verse_token_re.search(text))


def is_known_false_positive(text):
    lowered = str(text or "").lower()
    return (
        "peter explains" in lowered
        or "thou shalt not take" in lowered
    )


def clean_reference_list(values):
    cleaned = []
    for value in values or []:
        normalized = normalize_reference_minimal(value)
        if not normalized:
            continue
        if is_known_false_positive(normalized):
            continue
        cleaned.append(normalized)
    return cleaned


def clean_entry(entry):
    refs = (entry.get("bible_references") or {}) if isinstance(entry, dict) else {}
    return {
        "id": entry.get("id"),
        "bible_references": {
            "key_nt_scriptures": clean_reference_list(refs.get("key_nt_scriptures") or []),
            "key_ot_scriptures": clean_reference_list(refs.get("key_ot_scriptures") or []),
            "supportive_nt_scriptures": clean_reference_list(refs.get("supportive_nt_scriptures") or []),
            "supportive_ot_scriptures": clean_reference_list(refs.get("supportive_ot_scriptures") or []),
        },
    }


def file_sort_key(filename):
    stem = filename.rsplit(".", 1)[0]
    match = re.match(r"^([A-Z]+)(\d+)$", stem)
    if not match:
        return (stem, 0)
    return (match.group(1), int(match.group(2)))


def id_sort_key(id_value):
    match = re.match(r"^([A-Z]+)(\d+)$", str(id_value or ""))
    if not match:
        return (str(id_value or ""), 0)
    return (match.group(1), int(match.group(2)))


def collect_references(soup, section_title_re, stop_title_re, filepath, log_label):
    collected = []
    section_start = soup.find("b", string=section_title_re)
    if not section_start:
        return collected

    for node in section_start.find_all_next(["b", "font"]):
        if node.name == "b":
            header = node.get_text(" ", strip=True)
            if stop_title_re.search(header):
                break
            continue

        if node.get("size") != "4" or node.get("face") != "Times New Roman, Times, serif":
            continue

        reference = node.find("u").get_text(strip=True) if node.find("u") else node.get_text(strip=True)
        reference = normalize_reference(reference)
        if not reference:
            continue
        if not is_likely_scripture_reference(reference):
            with open(log_file, "a") as log:
                log.write(f"Skipped non-reference {log_label}: {reference} in file {filepath}\n")
            continue
        collected.append(reference)

    return collected


def extract_key_scriptures_from_html(filepath):
    with open(filepath, "r", encoding="ISO-8859-1") as file:
        soup = BeautifulSoup(file, "html.parser")
        
        # Extract scriptures
        key_nt_scriptures = []
        key_ot_scriptures = []
        supportive_nt_scriptures = []
        supportive_ot_scriptures = []
        
        key_references = collect_references(
            soup,
            re.compile("Key Scripture(s)?"),
            re.compile("Supportive Scriptures|Commentary|Classical Commentators|NCLA"),
            filepath,
            "key reference",
        )
        if key_references:
            with open(log_file, "a") as log:
                log.write(f"Found 'Key Scripture(s)' section in file {filepath}\n")

            for reference in key_references:
                if any(book in reference for book in ot_books):
                    key_ot_scriptures.append(reference)
                elif any(book in reference for book in nt_books):
                    key_nt_scriptures.append(reference)
        
        # Extract supportive scriptures
        supportive_references = collect_references(
            soup,
            re.compile("Supportive Scriptures"),
            re.compile("Commentary|Classical Commentators|NCLA"),
            filepath,
            "supportive reference",
        )
        for reference in supportive_references:
            if any(book in reference for book in ot_books):
                supportive_ot_scriptures.append(reference)
            elif any(book in reference for book in nt_books):
                supportive_nt_scriptures.append(reference)
        
        return {
            "id": os.path.basename(filepath).split('.')[0],
            "bible_references": {
                "key_nt_scriptures": key_nt_scriptures,
                "key_ot_scriptures": key_ot_scriptures,
                "supportive_nt_scriptures": supportive_nt_scriptures,
                "supportive_ot_scriptures": supportive_ot_scriptures,
            }
        }

# List to hold all the extracted information
data = []

# Clear the log file
with open(log_file, "w") as log:
    log.write("Extraction Log\n")
    log.write("="*50 + "\n")

# Process each HTML file in the directory
for filename in sorted(os.listdir(scraped_dir), key=file_sort_key):
    if filename.endswith(".php"):
        filepath = os.path.join(scraped_dir, filename)
        info = extract_key_scriptures_from_html(filepath)
        if info:
            if not info["bible_references"]["key_nt_scriptures"] and not info["bible_references"]["key_ot_scriptures"] and not info["bible_references"]["supportive_nt_scriptures"] and not info["bible_references"]["supportive_ot_scriptures"]:
                with open(log_file, "a") as log:
                    log.write(f"Warning: No scriptures found in {filename}\n")
            data.append(info)
        else:
            with open(log_file, "a") as log:
                log.write(f"No information extracted from file {filename}\n")

# Save the YAML data to a file
output_dir = "volume_1_2_output"
os.makedirs(output_dir, exist_ok=True)
output_path = os.path.join(output_dir, "output_2c_scriptures.yaml")

# Preserve existing output order/values to keep git diffs minimal.
try:
    with open(output_path, "r", encoding="utf-8") as existing_file:
        existing_rows = yaml.safe_load(existing_file) or []
except FileNotFoundError:
    existing_rows = []

existing_order = {
    row.get("id"): idx
    for idx, row in enumerate(existing_rows)
    if isinstance(row, dict) and row.get("id")
}

parsed_by_id = {
    row.get("id"): clean_entry(row)
    for row in data
    if isinstance(row, dict) and row.get("id")
}

merged = []
seen_ids = set()

for row in existing_rows:
    if not isinstance(row, dict) or not row.get("id"):
        continue
    row_id = row.get("id")
    seen_ids.add(row_id)
    if row_id in parsed_by_id:
        # Keep existing payload shape/content as baseline, only apply cleanup bugfixes.
        merged.append(clean_entry(row))
    else:
        merged.append(clean_entry(row))

for row_id in sorted((set(parsed_by_id.keys()) - seen_ids), key=id_sort_key):
    merged.append(parsed_by_id[row_id])

merged.sort(
    key=lambda row: (
        0 if row.get("id") in existing_order else 1,
        existing_order.get(row.get("id"), 0),
        id_sort_key(row.get("id")),
    )
)

# Convert the list to a structured YAML format
yaml_data = yaml.dump(merged, default_flow_style=False, allow_unicode=True, sort_keys=False, width=1000)

with open(output_path, "w", encoding="utf-8") as yaml_file:
    yaml_file.write(yaml_data)

print("YAML data has been written to volume_1_2_output/output_2c_scriptures.yaml")
print(f"Log data has been written to {log_file}")