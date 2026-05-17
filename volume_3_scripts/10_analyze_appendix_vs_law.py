from pathlib import Path
import re
import yaml


REPO_ROOT = Path(__file__).resolve().parent.parent
APPENDIX_FILE = REPO_ROOT / "volume_3_output" / "appendix_output" / "Appendix_Full.yaml"
LAW_NT_FILE = REPO_ROOT / "Law_of_Messiah_nt.yaml"
LAW_OT_FILE = REPO_ROOT / "Law_of_Messiah_ot.yaml"
OUTPUT_FILE = REPO_ROOT / "volume_3_output" / "appendix_output" / "Appendix_vs_Law_diff_summary.yaml"

BOOK_PREFIX_RE = re.compile(r"^([1-3]?\s?[A-Za-z][A-Za-z'’\-\s]*?)\s+(\d+:.*)$")


def load_yaml_list(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Missing input file: {path}")
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or []
    if not isinstance(data, list):
        raise ValueError(f"Expected list in {path}, got {type(data).__name__}")
    return data


def relative_repo_path(path: Path):
    return str(path.relative_to(REPO_ROOT))


def normalize_id(raw_id):
    if not isinstance(raw_id, str):
        return raw_id
    m = re.match(r"^([A-Z]{1,3})(\d+)$", raw_id.strip())
    if not m:
        return raw_id.strip()
    return f"{m.group(1)}{int(m.group(2))}"


def normalize_text(value):
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def normalize_title_for_compare(value):
    """Normalize titles for loose comparison of semantically equivalent wording."""
    text = normalize_text(value).lower()
    text = text.replace("&", " and ")
    text = re.sub(r"\bthat are\b", " ", text)
    text = re.sub(r"\bthat is\b", " ", text)
    text = re.sub(r"[,:;.!?()\[\]{}“”\"'`]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def expand_compact_scripture_refs(refs):
    """Expand refs like 'Romans 6:19, 12:1, 13:14' into explicit refs."""
    expanded = []
    for ref in refs:
        if not isinstance(ref, str):
            continue
        chunks = [c.strip() for c in ref.split(",") if c.strip()]
        current_book = None
        for chunk in chunks:
            match = BOOK_PREFIX_RE.match(chunk)
            if match:
                current_book = normalize_text(match.group(1))
                expanded.append(f"{current_book} {normalize_text(match.group(2))}")
            elif current_book:
                expanded.append(f"{current_book} {normalize_text(chunk)}")
            else:
                expanded.append(normalize_text(chunk))
    return expanded


def normalize_bible_refs_from_appendix(row):
    refs = row.get("bible_references", {}) if isinstance(row, dict) else {}
    nt_refs = refs.get("nt_scriptures", []) if isinstance(refs, dict) else []
    ot_refs = refs.get("ot_scriptures", []) if isinstance(refs, dict) else []
    nt_norm = sorted(set(expand_compact_scripture_refs(nt_refs)))
    ot_norm = sorted(set(expand_compact_scripture_refs(ot_refs)))
    return {"nt_scriptures": nt_norm, "ot_scriptures": ot_norm}


def normalize_bible_refs_from_law(row):
    refs = row.get("bible_references", {}) if isinstance(row, dict) else {}
    if not isinstance(refs, dict):
        refs = {}

    nt_refs = refs.get("nt_scriptures", [])
    ot_refs = refs.get("ot_scriptures", [])

    # Law files mostly split these into key/supportive lists.
    nt_refs += refs.get("key_nt_scriptures", [])
    nt_refs += refs.get("supportive_nt_scriptures", [])
    ot_refs += refs.get("key_ot_scriptures", [])
    ot_refs += refs.get("supportive_ot_scriptures", [])

    nt_norm = sorted(set(expand_compact_scripture_refs(nt_refs)))
    ot_norm = sorted(set(expand_compact_scripture_refs(ot_refs)))
    return {"nt_scriptures": nt_norm, "ot_scriptures": ot_norm}


def compare_rows(appendix_row, law_row):
    fields_result = {}

    # Shared scalar fields
    for field in ["title", "category", "commandment_type"]:
        if field == "title":
            a_raw = normalize_text(appendix_row.get(field, ""))
            l_raw = normalize_text(law_row.get(field, ""))
            a_val = normalize_title_for_compare(a_raw)
            l_val = normalize_title_for_compare(l_raw)
        else:
            a_val = normalize_text(appendix_row.get(field, ""))
            l_val = normalize_text(law_row.get(field, ""))
            a_raw = a_val
            l_raw = l_val
        fields_result[field] = {
            "appendix": a_val,
            "law": l_val,
            "appendix_raw": a_raw,
            "law_raw": l_raw,
            "equal": a_val == l_val,
        }

    # Keep bible references available for optional inspection, but do not drive differences.
    a_refs = normalize_bible_refs_from_appendix(appendix_row)
    l_refs = normalize_bible_refs_from_law(law_row)
    fields_result["bible_references"] = {
        "appendix": a_refs,
        "law": l_refs,
        "equal": True,
        "ignored_in_diff": True,
    }

    return fields_result


def build_summary():
    appendix_rows = load_yaml_list(APPENDIX_FILE)
    nt_rows = load_yaml_list(LAW_NT_FILE)
    ot_rows = load_yaml_list(LAW_OT_FILE)

    appendix_by_id = {
        normalize_id(row.get("id")): row
        for row in appendix_rows
        if isinstance(row, dict) and row.get("id")
    }
    nt_by_id = {
        normalize_id(row.get("id")): row
        for row in nt_rows
        if isinstance(row, dict) and row.get("id")
    }
    ot_by_id = {
        normalize_id(row.get("id")): row
        for row in ot_rows
        if isinstance(row, dict) and row.get("id")
    }

    compared_ids = []
    only_in_appendix = []
    only_in_law_nt = sorted([row_id for row_id in nt_by_id if row_id not in appendix_by_id])
    only_in_law_ot = sorted([row_id for row_id in ot_by_id if row_id not in appendix_by_id])

    field_counts = {
        "title": {"equal": 0, "different": 0},
        "category": {"equal": 0, "different": 0},
        "commandment_type": {"equal": 0, "different": 0},
        "bible_references": {"equal": 0, "different": 0, "ignored": True},
    }

    differences = []
    matched_in_nt = 0
    matched_in_ot = 0

    for row_id in sorted(appendix_by_id.keys()):
        appendix_row = appendix_by_id[row_id]

        law_row = None
        law_source = None
        if row_id in nt_by_id:
            law_row = nt_by_id[row_id]
            law_source = "nt"
            matched_in_nt += 1
        elif row_id in ot_by_id:
            law_row = ot_by_id[row_id]
            law_source = "ot"
            matched_in_ot += 1

        if law_row is None:
            only_in_appendix.append(row_id)
            continue

        compared_ids.append(row_id)
        compared = compare_rows(appendix_row, law_row)

        differing_fields = []
        for field, detail in compared.items():
            if detail["equal"]:
                field_counts[field]["equal"] += 1
            else:
                field_counts[field]["different"] += 1
                differing_fields.append(field)

        if differing_fields:
            field_value_differences = {
                field: {
                    "appendix": compared[field].get("appendix_raw", compared[field]["appendix"]),
                    "law": compared[field].get("law_raw", compared[field]["law"]),
                }
                for field in differing_fields
            }
            differences.append(
                {
                    "id": row_id,
                    "law_source": law_source,
                    "title_appendix": normalize_text(appendix_row.get("title", "")),
                    "different_fields": differing_fields,
                    "title_law": normalize_text(law_row.get("title", "")),
                    "field_value_differences": field_value_differences,
                }
            )

    summary = {
        "inputs": {
            "appendix_full": relative_repo_path(APPENDIX_FILE),
            "law_nt": relative_repo_path(LAW_NT_FILE),
            "law_ot": relative_repo_path(LAW_OT_FILE),
        },
        "coverage": {
            "appendix_total": len(appendix_by_id),
            "law_nt_total": len(nt_by_id),
            "law_ot_total": len(ot_by_id),
            "compared_ids": len(compared_ids),
            "matched_in_nt": matched_in_nt,
            "matched_in_ot": matched_in_ot,
            "only_in_appendix": len(only_in_appendix),
            "only_in_law_nt": len(only_in_law_nt),
            "only_in_law_ot": len(only_in_law_ot),
        },
        "shared_fields_analyzed": [
            "id",
            "title",
            "category",
            "commandment_type",
            "bible_references",
        ],
        "field_summary": field_counts,
        "difference_summary": {
            "ids_with_any_difference": len(differences),
            "all_differences": differences,
        },
        "id_samples": {
            "only_in_appendix": only_in_appendix[:60],
            "only_in_law_nt": only_in_law_nt[:60],
            "only_in_law_ot": only_in_law_ot[:60],
        },
    }

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        yaml.dump(summary, f, allow_unicode=True, sort_keys=False, default_flow_style=False, width=2000)

    print(f"Summary written to {relative_repo_path(OUTPUT_FILE)}")
    print(f"Compared IDs: {len(compared_ids)}")
    print(f"IDs with differences: {len(differences)}")


if __name__ == "__main__":
    build_summary()
