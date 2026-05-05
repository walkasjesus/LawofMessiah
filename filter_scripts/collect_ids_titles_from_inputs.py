from pathlib import Path
import re

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
MANUAL_REVIEW_PATH = (
    ROOT / "filter_output" / "manually_reviewed_unique_positive_ids_titles.yaml"
)
MANUAL_NCLA_ADDITIONS_PATH = (
    ROOT / "filter_output" / "manually_added_ncla_collected_ids_titles.yaml"
)
CATEGORY_REVIEW_PATH = ROOT / "filter_output" / "category_normalization_review.yaml"


REFERENCE_RE = re.compile(
    r"^\s*(?P<book>.+?)\s+(?P<chapter>\d+)\s*:\s*(?P<start>\d+)(?P<start_suffix>[a-z]?)"
    r"(?:\s*-\s*(?:(?P<end_chapter>\d+)\s*:\s*)?(?P<end>\d+)(?P<end_suffix>[a-z]?))?\s*$",
    re.IGNORECASE,
)


def ref_dedupe_key(reference):
    return re.sub(r"\s+", " ", str(reference or "")).strip().lower()


def suffix_to_bounds(verse, suffix):
    # Unsuffixed verse means the whole verse; suffixed means a sub-verse marker (e.g. 16a).
    if not suffix:
        return verse * 100, verse * 100 + 99
    index = ord(suffix.lower()) - ord("a") + 1
    index = max(1, min(index, 99))
    point = verse * 100 + index
    return point, point


def parse_reference(reference):
    text = re.sub(r"\s+", " ", str(reference or "")).strip()
    match = REFERENCE_RE.match(text)
    if not match:
        return None

    book = match.group("book").strip()
    chapter = int(match.group("chapter"))
    start_verse = int(match.group("start"))
    start_suffix = (match.group("start_suffix") or "").lower()
    end_chapter_raw = match.group("end_chapter")
    end_chapter = int(end_chapter_raw) if end_chapter_raw else chapter
    end_verse = int(match.group("end") or start_verse)
    end_suffix = (match.group("end_suffix") or "").lower()

    if end_chapter != chapter:
        # Keep cross-chapter references as-is to avoid accidental semantic changes.
        return {
            "text": text,
            "book": book,
            "book_key": book.lower(),
            "chapter": chapter,
            "cross_chapter": True,
        }

    start_low, start_high = suffix_to_bounds(start_verse, start_suffix)
    end_low, end_high = suffix_to_bounds(end_verse, end_suffix)

    low = min(start_low, end_low)
    high = max(start_high, end_high)
    return {
        "text": text,
        "book": book,
        "book_key": book.lower(),
        "chapter": chapter,
        "cross_chapter": False,
        "low": low,
        "high": high,
    }


def bound_to_token(bound, is_start):
    verse = bound // 100
    part = bound % 100
    if (is_start and part == 0) or ((not is_start) and part == 99):
        return str(verse)
    if 1 <= part <= 26:
        return f"{verse}{chr(ord('a') + part - 1)}"
    return str(verse)


def format_interval(book, chapter, low, high):
    start = bound_to_token(low, is_start=True)
    end = bound_to_token(high, is_start=False)
    if low == high:
        return f"{book} {chapter}:{start}"

    start_verse = low // 100
    end_verse = high // 100
    if start_verse == end_verse and start == end:
        return f"{book} {chapter}:{start}"
    return f"{book} {chapter}:{start}-{end}"


def merge_reference_list(values):
    ordered_unique = []
    seen = set()
    for value in values or []:
        text = re.sub(r"\s+", " ", str(value or "")).strip()
        if not text:
            continue
        key = ref_dedupe_key(text)
        if key in seen:
            continue
        seen.add(key)
        ordered_unique.append(text)

    passthrough_by_index = {}
    groups = {}

    for idx, text in enumerate(ordered_unique):
        ref = parse_reference(text)
        if not ref or ref.get("cross_chapter"):
            passthrough_by_index[idx] = text
            continue

        group_key = (ref["book_key"], ref["chapter"])
        if group_key not in groups:
            groups[group_key] = {
                "first_index": idx,
                "book": ref["book"],
                "chapter": ref["chapter"],
                "intervals": [],
            }
        groups[group_key]["intervals"].append((ref["low"], ref["high"]))

    merged_by_first_index = {}
    for group in groups.values():
        intervals = sorted(group["intervals"], key=lambda pair: (pair[0], pair[1]))
        merged = []
        low, high = intervals[0]
        for next_low, next_high in intervals[1:]:
            current_end_verse = high // 100
            next_start_verse = next_low // 100
            if next_start_verse <= current_end_verse + 1:
                high = max(high, next_high)
            else:
                merged.append((low, high))
                low, high = next_low, next_high
        merged.append((low, high))

        merged_text = [
            format_interval(group["book"], group["chapter"], m_low, m_high)
            for m_low, m_high in merged
        ]
        merged_by_first_index[group["first_index"]] = merged_text

    out = []
    for idx in range(len(ordered_unique)):
        if idx in passthrough_by_index:
            out.append(passthrough_by_index[idx])
        if idx in merged_by_first_index:
            out.extend(merged_by_first_index[idx])

    return out


def normalize_bible_references_sectioned(bible_references):
    if not isinstance(bible_references, dict):
        return {
            "key_nt_scriptures": [],
            "key_ot_scriptures": [],
            "supportive_nt_scriptures": [],
            "supportive_ot_scriptures": [],
        }

    sections = {
        "key_nt_scriptures": merge_reference_list(
            bible_references.get("key_nt_scriptures", [])
        ),
        "key_ot_scriptures": merge_reference_list(
            bible_references.get("key_ot_scriptures", [])
        ),
        "supportive_nt_scriptures": merge_reference_list(
            bible_references.get("supportive_nt_scriptures", [])
        ),
        "supportive_ot_scriptures": merge_reference_list(
            bible_references.get("supportive_ot_scriptures", [])
        ),
    }

    # Keep only one copy across all sections, with key scriptures taking precedence.
    precedence = [
        "key_nt_scriptures",
        "key_ot_scriptures",
        "supportive_nt_scriptures",
        "supportive_ot_scriptures",
    ]
    seen = set()
    for section in precedence:
        deduped = []
        for ref in sections.get(section, []):
            key = ref_dedupe_key(ref)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(ref)
        sections[section] = deduped

    return sections


def normalize_row_bible_references(row):
    if not isinstance(row, dict):
        return
    row["bible_references"] = normalize_bible_references_sectioned(
        row.get("bible_references", {})
    )


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


def build_manual_review_lookup(path: Path):
    if not path.exists():
        return {}

    review_data = load_yaml(path)
    lookup = {}
    for row in to_items(review_data):
        if not isinstance(row, dict):
            continue

        row_id = row.get("id")
        if not row_id:
            continue

        lookup[row_id] = {
            "unique": row.get("unique"),
            "double_ids": row.get("double_ids", []),
        }

    return lookup


def build_manual_ncla_lookup(path: Path):
    if not path.exists():
        return {}

    manual_data = load_yaml(path)
    lookup = {}
    for row in to_items(manual_data):
        if not isinstance(row, dict):
            continue

        row_id = row.get("id")
        if not row_id:
            continue

        lookup[row_id] = dict(row)

    return lookup


def build_existing_related_lookup(path: Path):
    if not path.exists():
        return {}

    existing_data = load_yaml(path)
    lookup = {}
    for row in to_items(existing_data):
        if not isinstance(row, dict):
            continue

        row_id = row.get("id")
        if not isinstance(row_id, str) or not row_id.strip():
            continue

        related = row.get("related_lawofmessiah", [])
        if not isinstance(related, list):
            continue

        lookup[row_id.strip()] = list(related)

    return lookup


def build_category_normalization_lookup(path: Path):
    if not path.exists():
        return {}

    review_data = load_yaml(path)
    if not isinstance(review_data, dict):
        return {}

    proposals = review_data.get("proposals", [])
    if not isinstance(proposals, list):
        return {}

    lookup = {}
    for proposal in proposals:
        if not isinstance(proposal, dict):
            continue
        if proposal.get("approved") is not True:
            continue

        final_category = proposal.get("proposed_final_category")
        if not isinstance(final_category, str):
            continue
        final_category = final_category.strip()
        if not final_category:
            continue

        aliases = proposal.get("aliases", [])
        if not isinstance(aliases, list):
            continue

        for alias in aliases:
            if not isinstance(alias, str):
                continue
            alias = alias.strip()
            if not alias:
                continue
            lookup[alias] = final_category

    return lookup


def normalize_category(row, category_lookup):
    if not category_lookup:
        return

    category = row.get("category")
    if not isinstance(category, str):
        return

    category = category.strip()
    if not category:
        return

    row["category"] = category_lookup.get(category, category)


def merge_related_lawofmessiah(row):
    merged = []
    seen = set()

    for field in [
        "related_lawofmessiah",
        "commandments_related_ot",
        "commandments_related_nt",
        "double_ids",
    ]:
        values = row.get(field, [])
        if not isinstance(values, list):
            continue

        for entry in values:
            if not isinstance(entry, dict):
                continue

            entry_id = entry.get("id")
            entry_title = entry.get("title")
            dedupe_key = (entry_id, entry_title)
            if dedupe_key in seen:
                continue

            seen.add(dedupe_key)
            merged.append(dict(entry))

    return merged


def normalize_related_lawofmessiah(entries):
    if not isinstance(entries, list):
        return []

    out = []
    seen = set()
    for entry in entries:
        if not isinstance(entry, dict):
            continue

        rel_id = entry.get("id")
        if not isinstance(rel_id, str) or not rel_id.strip():
            continue
        rel_id = rel_id.strip()

        rel_title = entry.get("title")
        if not isinstance(rel_title, str):
            rel_title = ""

        key = (rel_id, rel_title)
        if key in seen:
            continue

        seen.add(key)
        out.append({"id": rel_id, "title": rel_title})

    return out


def merge_related_lists(*lists):
    merged = []
    seen = set()

    for values in lists:
        if not isinstance(values, list):
            continue
        for entry in normalize_related_lawofmessiah(values):
            rel_id = entry.get("id", "")
            rel_title = entry.get("title", "")
            key = (rel_id, rel_title)
            if key in seen:
                continue
            seen.add(key)
            merged.append(entry)

    return merged


def expand_bidirectional_related(rows):
    rows_by_id = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        row_id = row.get("id")
        if not isinstance(row_id, str) or not row_id.strip():
            continue
        rows_by_id[row_id.strip()] = row

    for row in rows:
        if not isinstance(row, dict):
            continue

        row_id = row.get("id")
        if not isinstance(row_id, str) or not row_id.strip():
            continue
        row_id = row_id.strip()
        row_title = row.get("title") if isinstance(row.get("title"), str) else ""

        related = normalize_related_lawofmessiah(row.get("related_lawofmessiah", []))
        row["related_lawofmessiah"] = related

        for rel in list(related):
            rel_id = rel.get("id")
            if not isinstance(rel_id, str) or not rel_id.strip():
                continue
            rel_id = rel_id.strip()

            if rel_id == row_id:
                continue

            target = rows_by_id.get(rel_id)
            if not isinstance(target, dict):
                continue

            target_related = normalize_related_lawofmessiah(
                target.get("related_lawofmessiah", [])
            )

            has_backref = any(
                isinstance(entry, dict)
                and isinstance(entry.get("id"), str)
                and entry.get("id").strip() == row_id
                for entry in target_related
            )

            if not has_backref:
                target_related.append({"id": row_id, "title": row_title})

            target["related_lawofmessiah"] = normalize_related_lawofmessiah(target_related)


def normalize_commandment_subtitles(subtitles):
    if not isinstance(subtitles, list):
        return []

    out = []
    for subtitle in subtitles:
        if isinstance(subtitle, dict):
            subtitle_id = subtitle.get("id")
            subtitle_title = subtitle.get("commandment") or subtitle.get("title")
            if not subtitle_id or not subtitle_title:
                continue
            out.append(
                {
                    "id": str(subtitle_id).strip().upper(),
                    "commandment": str(subtitle_title).strip().rstrip("."),
                }
            )
            continue

        if isinstance(subtitle, str):
            raw = subtitle.strip().strip("'\"")
            if not raw:
                continue

            if ":" not in raw:
                continue

            subtitle_id, subtitle_title = raw.split(":", 1)
            subtitle_id = subtitle_id.strip().upper()
            subtitle_title = subtitle_title.strip().rstrip(".")
            if not subtitle_id or not subtitle_title:
                continue

            out.append({"id": subtitle_id, "commandment": subtitle_title})

    return out


def main():
    seen_ids = set()
    out = []
    manual_review_by_id = build_manual_review_lookup(MANUAL_REVIEW_PATH)
    manual_ncla_by_id = build_manual_ncla_lookup(MANUAL_NCLA_ADDITIONS_PATH)
    existing_related_by_id = build_existing_related_lookup(OUTPUT_PATH)
    category_lookup = build_category_normalization_lookup(CATEGORY_REVIEW_PATH)

    for path, source_name in INPUTS:
        data = load_yaml(path)
        for row in to_items(data):
            if not isinstance(row, dict):
                continue

            row_id = row.get("id")
            if not row_id or row_id in seen_ids:
                continue

            seen_ids.add(row_id)
            row_out = dict(row)
            row_out["source"] = source_name

            manual_review = manual_review_by_id.get(row_id)
            if manual_review:
                row_out.update(manual_review)

            manual_ncla_row = manual_ncla_by_id.get(row_id)
            if manual_ncla_row and isinstance(manual_ncla_row.get("ncla"), list):
                # Manual file is the source of truth for reviewed NCLA values.
                row_out["ncla"] = manual_ncla_row["ncla"]

            normalize_category(row_out, category_lookup)
            normalize_row_bible_references(row_out)

            row_out["related_lawofmessiah"] = merge_related_lists(
                merge_related_lawofmessiah(row_out),
                existing_related_by_id.get(row_id, []),
            )
            normalized_subtitles = normalize_commandment_subtitles(
                row_out.get("commandment_subtitles", [])
            )
            if "commandment_subtitles" in row_out or normalized_subtitles:
                row_out["commandment_subtitles"] = normalized_subtitles
            row_out.pop("commandments_related_ot", None)
            row_out.pop("commandments_related_nt", None)
            row_out.pop("double_ids", None)

            out.append(row_out)

    # Keep manual-only entries so reviewed NCLA rows are never dropped.
    for row_id, manual_row in manual_ncla_by_id.items():
        if row_id in seen_ids:
            continue
        manual_row_out = dict(manual_row)
        normalize_category(manual_row_out, category_lookup)
        normalize_row_bible_references(manual_row_out)
        manual_row_out["related_lawofmessiah"] = merge_related_lists(
            manual_row_out.get("related_lawofmessiah", []),
            existing_related_by_id.get(row_id, []),
        )
        normalized_subtitles = normalize_commandment_subtitles(
            manual_row_out.get("commandment_subtitles", [])
        )
        if "commandment_subtitles" in manual_row_out or normalized_subtitles:
            manual_row_out["commandment_subtitles"] = normalized_subtitles
        out.append(manual_row_out)
        seen_ids.add(row_id)

    expand_bidirectional_related(out)

    OUTPUT_PATH.write_text(
        yaml.dump(out, default_flow_style=False, allow_unicode=True, sort_keys=False, width=1000),
        encoding="utf-8",
    )

    print(f"Wrote {OUTPUT_PATH}")
    print({"rows": len(out)})


if __name__ == "__main__":
    main()
