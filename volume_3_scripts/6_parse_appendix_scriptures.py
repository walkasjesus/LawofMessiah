import json
import re
import yaml
from pathlib import Path

# Map short book names to full names (adjust as needed)
BOOKS = {
    # Old Testament
    "Gen": "Genesis",
    "Exo": "Exodus",
    "Lev": "Leviticus",
    "Num": "Numbers",
    "Deu": "Deuteronomy",
    "Jos": "Joshua",
    "Jdg": "Judges",
    "Rut": "Ruth",
    "1Sa": "1 Samuel",
    "2Sa": "2 Samuel",
    "1Ki": "1 Kings",
    "2Ki": "2 Kings",
    "1Ch": "1 Chronicles",
    "2Ch": "2 Chronicles",
    "Ezr": "Ezra",
    "Neh": "Nehemiah",
    "Est": "Esther",
    "Job": "Job",
    "Psa": "Psalms",
    "Pro": "Proverbs",
    "Ecc": "Ecclesiastes",
    "Son": "Song of Solomon",
    "Isa": "Isaiah",
    "Jer": "Jeremiah",
    "Lam": "Lamentations",
    "Eze": "Ezekiel",
    "Dan": "Daniel",
    "Hos": "Hosea",
    "Joe": "Joel",
    "Amo": "Amos",
    "Oba": "Obadiah",
    "Jon": "Jonah",
    "Mic": "Micah",
    "Nah": "Nahum",
    "Hab": "Habakkuk",
    "Zep": "Zephaniah",
    "Hag": "Haggai",
    "Zec": "Zechariah",
    "Mal": "Malachi",

    # New Testament
    "Mat": "Matthew",
    "Mar": "Mark",
    "Luk": "Luke",
    "Joh": "John",
    "Act": "Acts",
    "Rom": "Romans",
    "1Co": "1 Corinthians",
    "2Co": "2 Corinthians",
    "Gal": "Galatians",
    "Eph": "Ephesians",
    "Php": "Philippians",
    "Col": "Colossians",
    "1Th": "1 Thessalonians",
    "2Th": "2 Thessalonians",
    "1Ti": "1 Timothy",
    "2Ti": "2 Timothy",
    "Tit": "Titus",
    "Phm": "Philemon",
    "Heb": "Hebrews",
    "Jam": "James",
    "1Pe": "1 Peter",
    "2Pe": "2 Peter",
    "1Jn": "1 John",
    "2Jn": "2 John",
    "3Jn": "3 John",
    "Jud": "Jude",
    "Rev": "Revelation",
}

# Regex to detect Bible references, e.g. "Acts 10:15", "Romans 6:19, 12:1, 13:14"
bible_ref_pattern = re.compile(
    r"(?P<book>[1-3]?[A-Z][a-z]{1,4})\s*(?P<chapter>\d+):(?P<verse>[\d,-]+)"
)

# Regex to detect commandment IDs like 'AA1', 'BA47', etc.
cmd_id_pattern = re.compile(r"\b[A-Z]{2,}\d+\b")
normalized_cmd_id_pattern = re.compile(r"^([A-Z]{2,})(\d+)$")

def normalize_bible_ref(text):
    """Convert short book names to full names in a single Bible ref."""
    m = bible_ref_pattern.match(text)
    if not m:
        return text
    book = m.group("book")
    chapter = m.group("chapter")
    verse = m.group("verse")
    full_book = BOOKS.get(book, book)
    return f"{full_book} {chapter}:{verse}"

def extract_bible_references(text):
    matches = bible_ref_pattern.findall(text)
    refs = []
    for match in matches:
        book, chapter, verse = match
        short_ref = f"{book} {chapter}:{verse}"
        full_ref = normalize_bible_ref(short_ref)
        refs.append(full_ref)
    return refs

def extract_commandment_ids(text):
    return cmd_id_pattern.findall(text)


def normalize_commandment_id(raw_id):
    """Normalize appendix commandment IDs like AA01 -> AA1."""
    match = normalized_cmd_id_pattern.match(raw_id)
    if not match:
        return raw_id
    prefix, number = match.groups()
    return f"{prefix}{int(number)}"

def is_nt_ref(ref):
    NT_BOOKS = {
        "Matthew", "Mark", "Luke", "John", "Acts", "Romans", "1 Corinthians", "2 Corinthians",
        "Galatians", "Ephesians", "Philippians", "Colossians", "1 Thessalonians", "2 Thessalonians",
        "1 Timothy", "2 Timothy", "Titus", "Philemon", "Hebrews", "James", "1 Peter", "2 Peter",
        "1 John", "2 John", "3 John", "Jude", "Revelation"
    }
    for book in NT_BOOKS:
        if ref.startswith(book):
            return True
    return False

def merge_ranges(refs):
    """
    Merge overlapping and consecutive verse ranges within the same chapter.
    Input: list of refs like 'Book Chapter:Verse', 'Book Chapter:Start-End'
    Output: merged list with ranges like 'Book Chapter:Start-End'
    """
    import re
    # Parse refs into (book, chapter, start, end)
    parsed = []
    for ref in refs:
        m = re.match(r"(.+?) (\d+):(\d+)(?:-(\d+))?$", ref)
        if not m:
            continue
        book = m.group(1)
        chapter = int(m.group(2))
        start = int(m.group(3))
        end = int(m.group(4)) if m.group(4) else start
        parsed.append((book, chapter, start, end))

    # Group by book and chapter
    from collections import defaultdict
    grouped = defaultdict(list)
    for book, chapter, start, end in parsed:
        grouped[(book, chapter)].append((start, end))

    # Merge ranges within each group
    merged_refs = []
    for (book, chapter), ranges in grouped.items():
        # Sort by start
        ranges.sort()
        merged = []
        for start, end in ranges:
            if not merged:
                merged.append([start, end])
            else:
                prev_start, prev_end = merged[-1]
                if start <= prev_end + 1:  # Overlapping or consecutive
                    merged[-1][1] = max(prev_end, end)
                else:
                    merged.append([start, end])
        # Format merged ranges
        for start, end in merged:
            if start == end:
                merged_refs.append(f"{book} {chapter}:{start}")
            else:
                merged_refs.append(f"{book} {chapter}:{start}-{end}")
    return merged_refs

def main():
    repo_root = Path(__file__).resolve().parent.parent
    appendix_output_dir = repo_root / "volume_3_output" / "appendix_output"
    appendix_output_dir.mkdir(parents=True, exist_ok=True)

    input_file_nt = appendix_output_dir / "NT_Scripture_Index.json"
    input_file_ot = appendix_output_dir / "OT_Scripture_Index.json"

    # Load data
    with open(input_file_nt, "r", encoding="utf-8") as f:
        nt_data = json.load(f)

    with open(input_file_ot, "r", encoding="utf-8") as f:
        ot_data = json.load(f)

    # Combine pages from both
    all_pages = nt_data + ot_data

    commandment_to_refs = {}
    last_bible_refs = []

    for page in all_pages:
        for block in page.get("blocks", []):
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    text = span.get("text", "").strip()

                    if not text:
                        continue

                    bible_refs = extract_bible_references(text)
                    if bible_refs:
                        # Store Bible refs for next commandment IDs found
                        last_bible_refs = bible_refs
                        continue

                    cmd_ids = extract_commandment_ids(text)
                    if cmd_ids and last_bible_refs:
                        for cmd_id in cmd_ids:
                            cmd_id = normalize_commandment_id(cmd_id)
                            if cmd_id not in commandment_to_refs:
                                commandment_to_refs[cmd_id] = set()
                            commandment_to_refs[cmd_id].update(last_bible_refs)
                        # Clear to avoid duplicates
                        last_bible_refs = []

    # Prepare YAML format with merged verse ranges and neutral scripture keys
    output_data = []
    for cmd_id, refs_set in sorted(commandment_to_refs.items()):
        refs_list = sorted(refs_set)
        merged_refs = merge_ranges(refs_list)
        nt_refs = merge_ranges([r for r in merged_refs if is_nt_ref(r)])
        ot_refs = merge_ranges([r for r in merged_refs if not is_nt_ref(r)])
        bible_references = {}
        if nt_refs:
            bible_references["nt_scriptures"] = nt_refs
        if ot_refs:
            bible_references["ot_scriptures"] = ot_refs
        output_data.append({
            "id": cmd_id,
            "bible_references": bible_references
        })

    output_file = appendix_output_dir / "Scripture_Index.yaml"
    with open(output_file, "w", encoding="utf-8") as f:
        yaml.dump(output_data, f, sort_keys=False, allow_unicode=True)

    print(f"✅ YAML merged and written to {output_file}")
    print(f"Total commandments processed: {len(commandment_to_refs)}")

if __name__ == "__main__":
    main()