import yaml
import logging
import re
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


def load_valid_ot_ids(path):
    """Load normalized OT IDs for cross-reference auditing."""
    ot_path = Path(path)
    if not ot_path.exists():
        logging.warning(f"OT file not found for audit: {path}")
        return set()

    try:
        with open(ot_path, "r", encoding="utf-8") as file:
            ot_data = yaml.safe_load(file) or []
        return {
            normalize_reference_id(item.get("id"))
            for item in ot_data
            if isinstance(item, dict) and item.get("id")
        }
    except Exception as exc:
        logging.warning(f"Could not load OT IDs for audit: {exc}")
        return set()


def normalize_and_audit_related_ids(commandments_data, ot_file_path="Law_of_Messiah_ot.yaml"):
    """Normalize related IDs and capture unresolved references in an audit report."""
    valid_nt_ids = {
        normalize_reference_id(commandment.get("id"))
        for commandment in commandments_data
        if isinstance(commandment, dict) and commandment.get("id")
    }
    valid_ot_ids = load_valid_ot_ids(ot_file_path)

    unresolved_nt = []
    unresolved_ot = []

    for commandment in commandments_data:
        parent_id = commandment.get("id", "")

        for key, valid_set, unresolved_bucket in [
            ("commandments_related_nt", valid_nt_ids, unresolved_nt),
            ("commandments_related_ot", valid_ot_ids, unresolved_ot),
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
                    unresolved_bucket.append((parent_id, key, raw_id, norm_id, rel.get("title", "")))

    audit_lines = []
    audit_lines.append(f"Unresolved OT references: {len(unresolved_ot)}")
    for row in unresolved_ot[:200]:
        audit_lines.append(f"{row[0]} -> {row[3]} ({row[4]}) [raw={row[2]}]")

    audit_lines.append("")
    audit_lines.append(f"Unresolved NT references: {len(unresolved_nt)}")
    for row in unresolved_nt[:400]:
        audit_lines.append(f"{row[0]} -> {row[3]} ({row[4]}) [raw={row[2]}]")

    audit_path = Path("logs/3_reference_audit.log")
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text("\n".join(audit_lines), encoding="utf-8")

    logging.info(f"Reference audit written to {audit_path}")
    logging.info(f"Unresolved OT references: {len(unresolved_ot)}")
    logging.info(f"Unresolved NT references: {len(unresolved_nt)}")

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

        # Normalize related IDs and log unresolved cross-references for review.
        normalize_and_audit_related_ids(commandments_data)

        # Restructure commandments to ensure the correct order of keys
        restructured_data = restructure_commandments(commandments_data)

        # Save the merged data to a new YAML file
        with open(output_file, "w", encoding="utf-8") as outfile:
            yaml.dump(restructured_data, outfile, allow_unicode=True, default_flow_style=False, sort_keys=False, width=3000, Dumper=yaml.SafeDumper)
            logging.info(f"Merged data saved to: {output_file}")

    except Exception as e:
        logging.error(f"An error occurred: {e}")
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    # Input and output file paths
    commandments_file = "volume_3_output/law_of_Messiah_commandments.yaml"  # Replace with your commandments YAML file path
    extras_file = "volume_3_output/law_of_Messiah_sections.yaml"  # Replace with your extras YAML file path
    output_file = "Law_of_Messiah_nt.yaml"  # Replace with your desired output YAML file path

    # Run the merge
    merge_yaml_files(commandments_file, extras_file, output_file)
    