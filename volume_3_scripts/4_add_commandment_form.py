import yaml
import openai
import re
import time
from bible_lib import BibleFactory, BibleBooks

DRY_RUN_BIBLE = True   # If True, do not fetch verses, just log what would be fetched
DRY_RUN_OPENAI = True  # If True, do not call OpenAI, just log what would be sent
MAX_VERSES_PER_REF = 50  # Set your threshold here to limit the number of verses per reference.
file_path = "Law_of_Messiah_ot.yaml"
debug_file = "logs/debug_commandment_form.log"

BIBLE_BOOKS = [
    "Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy", "Joshua", "Judges", "Ruth",
    "1 Samuel", "2 Samuel", "1 Kings", "2 Kings", "1 Chronicles", "2 Chronicles", "Ezra", "Nehemiah", "Esther", "Job",
    "Psalms", "Proverbs", "Ecclesiastes", "Song of Solomon", "Isaiah", "Jeremiah", "Lamentations", "Ezekiel", "Daniel",
    "Hosea", "Joel", "Amos", "Obadiah", "Jonah", "Micah", "Nahum", "Habakkuk", "Zephaniah", "Haggai", "Zechariah", "Malachi",
    "Matthew", "Mark", "Luke", "John", "Acts", "Romans", "1 Corinthians", "2 Corinthians", "Galatians", "Ephesians",
    "Philippians", "Colossians", "1 Thessalonians", "2 Thessalonians", "1 Timothy", "2 Timothy", "Titus", "Philemon",
    "Hebrews", "James", "1 Peter", "2 Peter", "1 John", "2 John", "3 John", "Jude", "Revelation",
]

# Load OpenAI API key
with open(".openai_api_key", "r") as keyfile:
    openai.api_key = keyfile.read().strip()

# Load settings.py
api_key = None
default_bible_id = None
with open("bible_lib/settings.py") as f:
    for line in f:
        if "API_KEY" in line:
            api_key = line.split("=")[1].strip().strip('"').strip("'")
        if "DEFAULT_BIBLE_ID" in line:
            default_bible_id = line.split("=")[1].strip().strip('"').strip("'")

bible = BibleFactory(api_key).create(default_bible_id)

def extract_book_and_rest(part):
    for book in sorted(BIBLE_BOOKS, key=len, reverse=True):
        if part.startswith(book + " "):
            return book, part[len(book)+1:]
    return None, part

def get_scripture_text(refs):
    texts = []
    for ref in refs:
        verses = parse_scripture_reference(ref)
        if not verses:
            texts.append(f"{ref}: [Skipped or malformed]")
            continue
        for verse_ref in verses:
            book, rest = extract_book_and_rest(verse_ref)
            if not book or ":" not in rest:
                texts.append(f"{verse_ref}: [Malformed]")
                continue
            chapter, verse = rest.split(":", 1)
            if DRY_RUN_BIBLE:
                texts.append(f"[DRY_RUN_BIBLE] Would fetch: {book} {chapter}:{verse}")
            else:
                try:
                    book_enum = getattr(BibleBooks, book)
                    text = bible.verse(book_enum, int(chapter), int(verse))
                    texts.append(f"{book} {chapter}:{verse}: {text}")
                except Exception as e:
                    texts.append(f"{book} {chapter}:{verse}: [Error: {e}]")
    return "\n".join(texts)

def parse_scripture_reference(ref, max_verses=MAX_VERSES_PER_REF):
    """Return a list of fully expanded scripture references from a string like 'John 1:1-4, 14'.
       If the expansion would exceed max_verses, return None."""
    results = []
    # Handle '&' for multiple groups
    for part in ref.split('&'):
        part = part.strip()
        if not part:
            continue
        if " " not in part:
            continue  # skip malformed
        book, rest = extract_book_and_rest(part)
        if not book:
            continue  # skip malformed

        if ":" not in rest:
            continue  # skip malformed
        chapter, verses = rest.split(":", 1)
        chapter_clean = re.sub(r"\D", "", chapter)
        # Split on commas for multiple verses/groups
        for verse_group in verses.split(","):
            verse_group = verse_group.strip()
            verse_main = verse_group
            verse_paren = None
            if "(" in verse_group and ")" in verse_group:
                m = re.match(r"([^\(]+)\(([^)]+)\)", verse_group)
                if m:
                    verse_main, verse_paren = m.groups()
            # Handle ranges
            if "-" in verse_main:
                start_verse, end_verse = verse_main.split("-")
                start_verse_clean = re.sub(r"\D", "", start_verse)
                end_verse_clean = re.sub(r"\D", "", end_verse)
                try:
                    rng = range(int(start_verse_clean), int(end_verse_clean) + 1)
                except Exception:
                    continue
                if len(rng) > max_verses:
                    return None
                for v in rng:
                    results.append(f"{book} {chapter_clean}:{v}")
            elif verse_main:
                verse_clean = re.sub(r"\D", "", verse_main)
                results.append(f"{book} {chapter_clean}:{verse_clean}")
            # Optionally add parenthetical verse
            if verse_paren:
                if ":" in verse_paren:
                    ch, v = verse_paren.split(":", 1)
                    ch = re.sub(r"\D", "", ch)
                    v = re.sub(r"\D", "", v)
                else:
                    ch = chapter_clean
                    v = re.sub(r"\D", "", verse_paren)
                results.append(f"{book} {ch}:{v}")
    if len(results) > max_verses:
        return None
    return results

def get_commandment_form(commandment_text, scripture_text):
    prompt = (
        "Given the following commandment and the full text of its key scriptures, "
        "choose ONLY one of these labels for 'commandment_form':\n"
        "- Explicit: if the scripture text gives an explicit commandment\n"
        "- Implied: if the scripture text does not give an explicit commandment, but a command can be implied\n"
        "- (empty string): if you are uncertain or don't know\n\n"
        f"Commandment: \"{commandment_text}\"\n"
        f"Scripture Text: \"{scripture_text}\"\n\n"
        "Answer with only one word: Explicit, Implied, or leave blank if uncertain."
    )
    if DRY_RUN_OPENAI:
        return "[DRY_RUN_OPENAI] Would send prompt to OpenAI"
    else:
        response = openai.chat.completions.create(
            model="gpt-4.1",
            messages=[
                {"role": "system", "content": "You label commandments as Explicit, Implied, or blank based on the scripture text."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=2,
            temperature=0
        )
        # Add a delay to avoid exceeding 25,000 tokens per minute
        time.sleep(1.3)  # ~46 requests/minute, adjust if your average tokens/request is higher or lower
        answer = response.choices[0].message.content.strip()
        if answer not in ["Explicit", "Implied"]:
            return ""
        return answer

# Load the commandments
with open(file_path, "r") as f:
    commandments = yaml.safe_load(f)

with open(debug_file, "w") as debug:
    for idx, cmd in enumerate(commandments):
        cmd_id = cmd.get('id', f'index_{idx}')
        cmd_text = cmd.get('commandment', '')

        bible_refs = cmd.get('bible_references', {})
        key_nt_scriptures = bible_refs.get('key_nt_scriptures', [])
        key_ot_scriptures = bible_refs.get('key_ot_scriptures', [])
        all_refs = key_nt_scriptures + key_ot_scriptures

        debug.write(f"\n--- Commandment {cmd_id} ---\n")
        debug.write(f"Commandment: {cmd_text}\n")
        debug.write(f"Scripture references: {all_refs}\n")

        scripture_text = get_scripture_text(all_refs)
        debug.write(f"Retrieved scripture text:\n{scripture_text}\n")

        cmd_form = get_commandment_form(cmd_text, scripture_text)
        debug.write(f"Determined commandment_form: {cmd_form}\n")

        cmd['commandment_form'] = cmd_form

if not DRY_RUN_BIBLE and not DRY_RUN_OPENAI:
    with open(file_path, "w") as f:
        yaml.dump(commandments, f, allow_unicode=True, default_flow_style=False, sort_keys=False, width=1000, Dumper=yaml.SafeDumper)
    print(f"\nUpdated commandments written to {file_path}")
else:
    print("\nDRY RUN: No changes written to the YAML file.")

print(f"Debug output written to {debug_file}")