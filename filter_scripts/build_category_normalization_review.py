from collections import Counter, defaultdict
from pathlib import Path
import re

import yaml

ROOT = Path(__file__).resolve().parents[1]

INPUTS = [
    ROOT / "Law_of_Messiah_nt.yaml",
    ROOT / "Law_of_Messiah_ot.yaml",
    ROOT / "volume_3_output" / "appendix_output" / "Appendix_Full.yaml",
]

OUTPUT_REVIEW_PATH = ROOT / "filter_output" / "category_normalization_review.yaml"

# Heuristic suggestions. All generated proposals are unapproved by default.
MANUAL_PROPOSED_FINAL_BY_RAW = {
    "Godliness & Godly Living": "Godliness, Holiness & Righteousness",
    "Neighbours & Brothers": "Relating to Brothers & Neighbors",
    "Relating to God": "Relating to God & Yeshua",
    "End-Times": "End Times",
    "Ru'ach HaKodesh": "Holy Spirit",
    "Idolatry & the Occult": "Idolatry, Heathens & the Occult",
    "Family": "Marriage & Family",
}


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


def normalize_key(category: str) -> str:
    text = category.strip().lower()
    text = text.replace("’", "'")
    text = text.replace("neighbours", "neighbors")
    text = text.replace("ru'ach", "ruach")
    text = text.replace("ha-kodesh", "hakodesh")
    text = text.replace("ha kodesh", "hakodesh")
    text = text.replace("-", " ")
    text = text.replace("&", " and ")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def build_category_counts():
    counts = Counter()
    counts_by_source = defaultdict(Counter)
    for path in INPUTS:
        source_name = str(path.relative_to(ROOT))
        data = load_yaml(path)
        for row in to_items(data):
            if not isinstance(row, dict):
                continue

            category = row.get("category")
            if not isinstance(category, str):
                continue

            category = category.strip()
            if not category:
                continue

            counts[category] += 1
            counts_by_source[category][source_name] += 1

    return counts, counts_by_source


def choose_proposed_final(aliases, counts):
    for alias in aliases:
        if alias in MANUAL_PROPOSED_FINAL_BY_RAW:
            return MANUAL_PROPOSED_FINAL_BY_RAW[alias]

    return aliases[0]


def main():
    counts, counts_by_source = build_category_counts()
    groups = defaultdict(list)

    for category in counts:
        groups[normalize_key(category)].append(category)

    proposals = []
    proposal_index = 1
    for _, aliases in sorted(
        groups.items(),
        key=lambda item: (
            -max(counts[c] for c in item[1]),
            sorted(item[1])[0].lower(),
        ),
    ):
        sorted_aliases = sorted(aliases, key=lambda c: (-counts[c], c.lower()))
        proposed_final = choose_proposed_final(sorted_aliases, counts)

        proposals.append(
            {
                "proposal_id": f"CAT{proposal_index:03d}",
                "proposed_final_category": proposed_final,
                "approved": False,
                "aliases": sorted_aliases,
                "counts": [
                    {
                        "category": alias,
                        "count": counts[alias],
                        "source_counts": [
                            {"source": source, "count": count}
                            for source, count in sorted(counts_by_source[alias].items())
                        ],
                    }
                    for alias in sorted_aliases
                ],
            }
        )
        proposal_index += 1

    out = {
        "schema_version": 1,
        "description": "Review and approve category normalization proposals.",
        "sources": [str(path.relative_to(ROOT)) for path in INPUTS],
        "how_to_review": [
            "Set approved: true for each proposal you accept.",
            "You may edit proposed_final_category to your preferred final category name.",
            "You may add aliases under an existing proposal when needed.",
            "You may add a new proposal object to introduce a brand new final category.",
            "Only approved proposals are applied by collect_ids_titles_from_inputs.py.",
        ],
        "proposals": proposals,
    }

    OUTPUT_REVIEW_PATH.write_text(
        yaml.dump(out, default_flow_style=False, allow_unicode=True, sort_keys=False, width=1000),
        encoding="utf-8",
    )

    print(f"Wrote {OUTPUT_REVIEW_PATH}")
    print({"unique_categories": len(counts), "proposal_groups": len(proposals)})


if __name__ == "__main__":
    main()
