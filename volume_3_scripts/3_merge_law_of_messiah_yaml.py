import yaml
import logging
import re
import os
from collections import Counter, defaultdict
from pathlib import Path
from collections import OrderedDict

# Configure logging
logging.basicConfig(
    filename="logs/merge_law_of_messiah_yaml.log",
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

def ordered_dict_representer(dumper, data):
    """
    Represent OrderedDict as a normal YAML dictionary.
    """
    return dumper.represent_dict(data.items())

# Register the OrderedDict representer with SafeDumper
yaml.add_representer(OrderedDict, ordered_dict_representer, Dumper=yaml.SafeDumper)


def normalize_reference_id(reference_id):
    """Normalize commandment IDs to reduce formatting variants (e.g., AA02 -> AA2, I-5 -> I5)."""
    if not isinstance(reference_id, str):
        return reference_id

    cleaned = reference_id.strip()
    cleaned = re.sub(r"[‐‑–—]", "-", cleaned)
    cleaned = cleaned.replace(" ", "")

    match = re.match(r"^([A-Za-z]+)-?0*([0-9]+)([A-Za-z]?)$", cleaned)
    if not match:
        return cleaned

    prefix, number, suffix = match.groups()
    return f"{prefix.upper()}{int(number)}{suffix.upper()}"


def normalize_title_key(title):
    """Normalize a title so equivalent text can be matched safely."""
    if not isinstance(title, str):
        return ""

    cleaned = title.strip().lower()
    cleaned = cleaned.replace("’", "'")
    cleaned = re.sub(r"[^a-z0-9]+", " ", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()


def build_title_index(rows):
    """Build title -> IDs index for unique title-based ID fallback remapping."""
    index = defaultdict(set)
    for row in rows:
        if not isinstance(row, dict):
            continue
        norm_id = normalize_reference_id(row.get("id"))
        title_key = normalize_title_key(row.get("title", ""))
        if norm_id and title_key:
            index[title_key].add(norm_id)
    return index


def load_ot_reference_metadata(path):
    """Load normalized OT IDs and title index for cross-reference auditing."""
    ot_path = Path(path)
    if not ot_path.exists():
        logging.warning(f"OT file not found for audit: {path}")
        return set(), defaultdict(set)

    try:
        with open(ot_path, "r", encoding="utf-8") as file:
            ot_data = yaml.safe_load(file) or []
        valid_ids = {
            normalize_reference_id(item.get("id"))
            for item in ot_data
            if isinstance(item, dict) and item.get("id")
        }
        title_index = build_title_index(ot_data)
        return valid_ids, title_index
    except Exception as exc:
        logging.warning(f"Could not load OT IDs for audit: {exc}")
        return set(), defaultdict(set)


def grouped_reference_summary(unresolved_rows):
    """Create condensed summaries by unresolved prefix and by parent commandment ID."""
    prefix_counter = Counter()
    parent_counter = Counter()
    sample_by_prefix = defaultdict(list)

    for parent_id, _, raw_id, norm_id, title in unresolved_rows:
        prefix = ""
        match = re.match(r"^([A-Z]+)", norm_id or "")
        if match:
            prefix = match.group(1)
        else:
            prefix = "<UNKNOWN>"

        prefix_counter[prefix] += 1
        parent_counter[parent_id] += 1
        if len(sample_by_prefix[prefix]) < 5:
            sample_by_prefix[prefix].append((raw_id, norm_id, title))

    return prefix_counter, parent_counter, sample_by_prefix


def normalize_and_audit_related_ids(commandments_data, mode="lenient", ot_file_path="Law_of_Messiah_ot.yaml"):
    """Normalize related IDs and capture unresolved references in an audit report.

    mode='lenient': always writes output and logs unresolved references.
    mode='strict': raises an exception when unresolved references remain.
    """
    valid_nt_ids = {
        normalize_reference_id(commandment.get("id"))
        for commandment in commandments_data
        if isinstance(commandment, dict) and commandment.get("id")
    }
    nt_title_index = build_title_index(commandments_data)
    valid_ot_ids, ot_title_index = load_ot_reference_metadata(ot_file_path)

    unresolved_nt = []
    unresolved_ot = []
    remapped_nt = []
    remapped_ot = []

    for commandment in commandments_data:
        parent_id = commandment.get("id", "")

        for key, valid_set, title_index, unresolved_bucket, remap_bucket in [
            ("commandments_related_nt", valid_nt_ids, nt_title_index, unresolved_nt, remapped_nt),
            ("commandments_related_ot", valid_ot_ids, ot_title_index, unresolved_ot, remapped_ot),
        ]:
            related_items = commandment.get(key, []) or []
            for rel in related_items:
                if not isinstance(rel, dict):
                    continue
                raw_id = rel.get("id")
                norm_id = normalize_reference_id(raw_id)
                if norm_id:
                    rel["id"] = norm_id
                if norm_id and valid_set and norm_id not in valid_set:
                    title_key = normalize_title_key(rel.get("title", ""))
                    title_candidates = title_index.get(title_key, set()) if title_key else set()
                    if len(title_candidates) == 1:
                        remapped_id = next(iter(title_candidates))
                        if remapped_id != norm_id:
                            rel["id"] = remapped_id
                            remap_bucket.append((parent_id, key, raw_id, norm_id, remapped_id, rel.get("title", "")))
                            norm_id = remapped_id
                if norm_id and valid_set and norm_id not in valid_set:
                    unresolved_bucket.append((parent_id, key, raw_id, norm_id, rel.get("title", "")))

    ot_prefix_counts, ot_parent_counts, ot_samples = grouped_reference_summary(unresolved_ot)
    nt_prefix_counts, nt_parent_counts, nt_samples = grouped_reference_summary(unresolved_nt)

    audit_lines = []
    audit_lines.append(f"Mode: {mode}")
    audit_lines.append("")

    audit_lines.append(f"Title-based OT remaps: {len(remapped_ot)}")
    for row in remapped_ot[:100]:
        audit_lines.append(
            f"{row[0]} remap {row[3]} -> {row[4]} ({row[5]}) [raw={row[2]}]"
        )
    audit_lines.append(f"Title-based NT remaps: {len(remapped_nt)}")
    for row in remapped_nt[:100]:
        audit_lines.append(
            f"{row[0]} remap {row[3]} -> {row[4]} ({row[5]}) [raw={row[2]}]"
        )
    audit_lines.append("")

    audit_lines.append(f"Unresolved OT references: {len(unresolved_ot)}")
    audit_lines.append("OT unresolved by prefix: " + ", ".join(
        f"{prefix}:{count}" for prefix, count in ot_prefix_counts.most_common(20)
    ))
    audit_lines.append("OT top parent IDs: " + ", ".join(
        f"{parent}:{count}" for parent, count in ot_parent_counts.most_common(20)
    ))
    for prefix, samples in ot_samples.items():
        audit_lines.append(f"OT sample [{prefix}]: " + "; ".join(
            f"raw={raw} norm={norm} title={title}" for raw, norm, title in samples
        ))
    audit_lines.append("")

    for row in unresolved_ot[:200]:
        audit_lines.append(f"{row[0]} -> {row[3]} ({row[4]}) [raw={row[2]}]")

    audit_lines.append("")
    audit_lines.append(f"Unresolved NT references: {len(unresolved_nt)}")
    audit_lines.append("NT unresolved by prefix: " + ", ".join(
        f"{prefix}:{count}" for prefix, count in nt_prefix_counts.most_common(20)
    ))
    audit_lines.append("NT top parent IDs: " + ", ".join(
        f"{parent}:{count}" for parent, count in nt_parent_counts.most_common(20)
    ))
    for prefix, samples in nt_samples.items():
        audit_lines.append(f"NT sample [{prefix}]: " + "; ".join(
            f"raw={raw} norm={norm} title={title}" for raw, norm, title in samples
        ))
    audit_lines.append("")

    for row in unresolved_nt[:400]:
        audit_lines.append(f"{row[0]} -> {row[3]} ({row[4]}) [raw={row[2]}]")

    audit_path = Path("logs/3_reference_audit.log")
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text("\n".join(audit_lines), encoding="utf-8")

    logging.info(f"Reference audit written to {audit_path}")
    logging.info(f"Title-based OT remaps: {len(remapped_ot)}")
    logging.info(f"Title-based NT remaps: {len(remapped_nt)}")
    logging.info(f"Unresolved OT references: {len(unresolved_ot)}")
    logging.info(f"Unresolved NT references: {len(unresolved_nt)}")

    if mode == "strict" and (unresolved_ot or unresolved_nt):
        raise ValueError(
            f"Strict reference audit failed: unresolved_ot={len(unresolved_ot)}, unresolved_nt={len(unresolved_nt)}"
        )

def merge_commentary(commentary_section):
    """
    Merge all list items in a commentary section into a single string.
    """
    if isinstance(commentary_section, list):
        # Extract all 'title' attributes and concatenate them into a single string
        merged_commentary = " ".join(
            item.get("title", "") if isinstance(item, dict) else str(item)
            for item in commentary_section
        ).strip()
        return merged_commentary
    elif isinstance(commentary_section, str):
        # If it's already a string, return it as is
        return commentary_section
    return ""

# Function to determine if a commandment is positive or negative
def determine_commandment_type(commandment_text):
    """
    Determine if a commandment is positive or negative based on keywords.
    """
    negative_keywords = ["not", "do not", "shall not", "must not", "cannot"]
    commandment_text = commandment_text.lower()  # Convert to lowercase for case-insensitive matching
    for keyword in negative_keywords:
        if keyword in commandment_text:
            return "Negative"
    return "Positive"

def add_commandment_type_and_source(commandments_data):
    """
    Add 'commandment_type', 'source', and other attributes to each commandment.
    """
    for commandment in commandments_data:
        # Add 'ncla' attribute
        commandment["ncla"] = "JMm JFm KMm KFm GMm GFm"

        # Add 'commandment_type' attribute
        commandment_text = commandment.get("commandment", "")
        commandment["commandment_type"] = determine_commandment_type(commandment_text)

        # Add 'copyright'
        commandment["copyright"] = "Copyright © Michael Rudolph and Daniel C. Juster, The Law of Messiah - Torah from a New Covenant Perspective - Volume 3"

        # Ensure related commandments and commandment_form are populated
        commandment["commandments_related_ot"] = commandment.get("commandments_related_ot", [])
        commandment["commandments_related_nt"] = commandment.get("commandments_related_nt", [])
        commandment["commandment_form"] = commandment.get("commandment_form", "")

        logging.debug(f"Processed commandment ID {commandment.get('id')}: type={commandment['commandment_type']}")

def restructure_commandments(commandments_data):
    """
    Restructure commandments to ensure the correct order of keys.
    """
    restructured_data = []
    for commandment in commandments_data:
        restructured_commandment = OrderedDict()
        restructured_commandment["id"] = commandment.get("id", "")
        restructured_commandment["title"] = commandment.get("title", "")
        restructured_commandment["commandment"] = commandment.get("commandment", "")
        restructured_commandment["commentary_rudolph"] = commandment.get("commentary_rudolph", "")
        restructured_commandment["commentary_juster"] = commandment.get("commentary_juster", "")
        restructured_commandment["commandments_related_ot"] = commandment.get("commandments_related_ot", [])
        restructured_commandment["commandments_related_nt"] = commandment.get("commandments_related_nt", [])
        restructured_commandment["commandment_form"] = commandment.get("commandment_form", "")
        restructured_commandment["bible_references"] = {
            "key_nt_scriptures": commandment.get("bible_references", {}).get("key_nt_scriptures", []),
            "supportive_nt_scriptures": commandment.get("bible_references", {}).get("supportive_nt_scriptures", []),
            "supportive_ot_scriptures": commandment.get("bible_references", {}).get("supportive_ot_scriptures", []),
        }
        restructured_commandment["ncla"] = commandment.get("ncla", "")
        restructured_commandment["category"] = commandment.get("category", "")
        restructured_commandment["commandment_type"] = commandment.get("commandment_type", "")
        restructured_commandment["copyright"] = commandment.get("copyright", "")
        restructured_data.append(restructured_commandment)
    return restructured_data

def merge_yaml_files(commandments_file, extras_file, output_file):
    """
    Merge two YAML files, process commentary sections, and restructure the output.
    """
    try:
        # Load the YAML files
        with open(commandments_file, "r", encoding="utf-8") as file1:
            commandments_data = yaml.safe_load(file1)
            logging.info(f"Loaded commandments file: {commandments_file}")

        with open(extras_file, "r", encoding="utf-8") as file2:
            extras_data = yaml.safe_load(file2)
            logging.info(f"Loaded extras file: {extras_file}")

        # Merge the two datasets
        for commandment, extra in zip(commandments_data, extras_data):
            # Ensure 'sections' exists in both commandment and extra
            if "sections" not in commandment:
                commandment["sections"] = {}
            if "sections" not in extra:
                extra["sections"] = {}

            # Merge commentary_rudolph
            if "commentary_rudolph" in extra["sections"]:
                extra_commentary = merge_commentary(extra["sections"]["commentary_rudolph"]).replace("  ", " ")
                commandment["commentary_rudolph"] = extra_commentary

            # Merge commentary_juster
            if "commentary_juster" in extra["sections"]:
                extra_commentary = merge_commentary(extra["sections"]["commentary_juster"]).replace("  ", " ")
                commandment["commentary_juster"] = extra_commentary

            # Merge commandments_related_ot
            if "commandments_related_ot" in extra["sections"]:
                commandment["commandments_related_ot"] = extra["sections"]["commandments_related_ot"]

            # Merge commandments_related_nt
            if "commandments_related_nt" in extra["sections"]:
                commandment["commandments_related_nt"] = extra["sections"]["commandments_related_nt"]

            # Merge commandment_form
            if "commandment_form" in extra:
                commandment["commandment_form"] = extra["commandment_form"]

            # Move all content from 'sections' to the upper level
            if "sections" in commandment:
                for key, value in commandment["sections"].items():
                    commandment[key] = value
                commandment.pop("sections", None)
                
        # Add commandment type, ncla, and other attributes
        add_commandment_type_and_source(commandments_data)

        # Normalize related IDs and audit unresolved cross-references.
        audit_mode = os.getenv("LAW_MESSIAH_REF_AUDIT_MODE", "lenient").strip().lower() or "lenient"
        if audit_mode not in {"lenient", "strict"}:
            logging.warning(f"Unknown LAW_MESSIAH_REF_AUDIT_MODE='{audit_mode}', defaulting to lenient")
            audit_mode = "lenient"
        normalize_and_audit_related_ids(commandments_data, mode=audit_mode)

        # Restructure commandments to ensure the correct order of keys
        restructured_data = restructure_commandments(commandments_data)

        # Save the merged data to a new YAML file
        with open(output_file, "w", encoding="utf-8") as outfile:
            yaml.dump(restructured_data, outfile, allow_unicode=True, default_flow_style=False, sort_keys=False, width=3000, Dumper=yaml.SafeDumper)
            logging.info(f"Merged data saved to: {output_file}")

    except Exception as e:
        logging.error(f"An error occurred: {e}")
        print(f"An error occurred: {e}")
        raise

if __name__ == "__main__":
    # Input and output file paths
    commandments_file = "volume_3_output/law_of_Messiah_commandments.yaml"  # Replace with your commandments YAML file path
    extras_file = "volume_3_output/law_of_Messiah_sections.yaml"  # Replace with your extras YAML file path
    output_file = "Law_of_Messiah_nt.yaml"  # Replace with your desired output YAML file path

    # Run the merge
    merge_yaml_files(commandments_file, extras_file, output_file)
    