"""
2g_ncla.py — Extract NCLA values from scraped PHP commandment files.

Produces volume_1_2_output/output_2g_ncla.yaml where each item's ncla field
is a list of {code, group} dicts.  Single-group items get group='All'.
Multi-group items (separated by <br> tags in the HTML) each get a named group.
"""
import os
import re
import yaml
from bs4 import BeautifulSoup, NavigableString, Tag

scraped_dir = "volume_1_2_scraped_commandments"
log_dir = "logs"
log_file = os.path.join(log_dir, "ncla_extraction_log.txt")
output_dir = "volume_1_2_output"
output_path = os.path.join(output_dir, "output_2g_ncla.yaml")
os.makedirs(log_dir, exist_ok=True)
os.makedirs(output_dir, exist_ok=True)

COPYRIGHT = (
    "Copyright \u00a9 Michael Rudolph and Daniel C. Juster, "
    "The Law of Messiah, Torah from a New Covenant Perspective, Volume 1 & 2"
)

NCLA_TOKEN_RE = re.compile(r"\b(JM|JF|KM|KF|GM|GF)([mronupi])\b")
ALL_GROUPS = ("JM", "JF", "KM", "KF", "GM", "GF")


def extract_tokens(text):
    seen = {}
    for grp, val in NCLA_TOKEN_RE.findall(text):
        if grp not in seen:
            seen[grp] = val
    if not seen:
        return None
    return " ".join(f"{g}{seen[g]}" for g in ALL_GROUPS if g in seen)


def _split_b_by_br(tag):
    """Split a <b> tag on <br> children; return list of text strings (one per segment)."""
    segments = []
    current_parts = []
    for child in tag.children:
        if isinstance(child, Tag) and child.name == "br":
            segments.append(" ".join(current_parts).strip())
            current_parts = []
        elif isinstance(child, Tag):
            current_parts.append(child.get_text(separator=" ", strip=True))
        elif isinstance(child, NavigableString):
            current_parts.append(str(child))
    segments.append(" ".join(current_parts).strip())
    return segments


def _segment_to_entry(segment):
    seg = re.sub(r"Return to main index", "", segment, flags=re.IGNORECASE).strip()
    if not NCLA_TOKEN_RE.search(seg):
        return None
    code = extract_tokens(seg)
    if not code:
        return None
    name_part = NCLA_TOKEN_RE.sub("", seg)
    name_part = re.sub(r"[();,]", " ", name_part)
    name_part = re.sub(r"\s+", " ", name_part).strip().strip(":").strip()
    group = name_part if re.search(r"[A-Za-z]", name_part) else "All"
    return {"code": code, "group": group}


def parse_ncla_segments(segments):
    entries = [_segment_to_entry(s) for s in segments]
    entries = [e for e in entries if e is not None]
    if not entries:
        return []
    if len(entries) == 1:
        return [{"code": entries[0]["code"], "group": "All"}]
    return entries


def extract_ncla_from_html(filepath, log):
    file_id = os.path.splitext(os.path.basename(filepath))[0]
    with open(filepath, "r", encoding="ISO-8859-1") as f:
        soup = BeautifulSoup(f, "html.parser")
    ncla_tag = soup.find(string=re.compile(r"NCLA"))
    if not ncla_tag:
        log.write(f"NO NCLA TAG: {filepath}\n")
        return {"id": file_id, "ncla": None, "copyright": COPYRIGHT}
    parent_b = ncla_tag.find_parent("b")
    if not parent_b:
        log.write(f"NO <b> PARENT: {filepath}\n")
        return {"id": file_id, "ncla": None, "copyright": COPYRIGHT}
    segments = _split_b_by_br(parent_b)
    segments[0] = re.sub(r"^NCLA\s*:?\s*", "", segments[0], flags=re.IGNORECASE).strip()
    segments = [s.strip() for s in segments if s.strip()]
    groups = parse_ncla_segments(segments)
    log.write(f"OK  {file_id}: {groups}\n")
    return {"id": file_id, "ncla": groups if groups else None, "copyright": COPYRIGHT}


with open(log_file, "w", encoding="utf-8") as log:
    log.write("NCLA Extraction Log\n" + "=" * 50 + "\n")
    data = []
    for filename in sorted(os.listdir(scraped_dir)):
        if not filename.endswith(".php"):
            continue
        entry = extract_ncla_from_html(os.path.join(scraped_dir, filename), log)
        data.append(entry)

with open(output_path, "w", encoding="utf-8") as f:
    f.write(yaml.dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False, width=1000))

total = len(data)
no_ncla = sum(1 for d in data if d["ncla"] is None)
multi_ids = [d["id"] for d in data if isinstance(d["ncla"], list) and len(d["ncla"]) > 1]
single = sum(1 for d in data if isinstance(d["ncla"], list) and len(d["ncla"]) == 1)
print(f"Wrote {output_path}")
print(f"  Total files : {total}  |  No NCLA: {no_ncla}  |  Single-group: {single}  |  Multi-group: {len(multi_ids)}")
print(f"  Multi-group IDs: {multi_ids}")
print(f"Log: {log_file}")
