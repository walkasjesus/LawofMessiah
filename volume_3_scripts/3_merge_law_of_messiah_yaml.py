import yaml
import logging
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
    