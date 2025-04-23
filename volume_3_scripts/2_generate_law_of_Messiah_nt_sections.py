import json
import yaml
import logging
import re

# Configure logging
logging.basicConfig(
    filename="logs/2_generate_law_of_Messiah_nt_sections.log",
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

def extract_sections(data):
    """
    Extract sections and fields from the JSON data based on the specified rules.
    """
    sections = []
    current_commandment = None
    current_section = None  # Initialize current_section to None

    # Section mapping based on title
    section_mapping = {
        "Comment by Dr. Daniel C. Juster": "commentary_juster",
        "Comment": "commentary_rudolph",
        "Related Mitzvot in Volumes 1 & 2": "commandments_related_ot",
        "Related New Testament Mitzvot": "commandments_related_nt",
        "Command Form": "commandment_form",
        "Key New Testament Scriptures": "key_nt_scriptures",
        "Additional New Testament Scriptures": "supportive_nt_scriptures",
        "Supportive Tanakh Scriptures": "supportive_ot_scriptures"
    }

    # Regex for splitting title into ID and title
    title_split_regex = re.compile(r"^([A-Z0-9\-]+)\s{2,}(.*)")

    for page in data:
        content = page.get("content", [])
        # Skip pages that only contain a category
        if len(content) == 1:
            entry = content[0]
            text = entry.get("text", "").strip()
            font = entry.get("font", "")
            size = entry.get("size", 0)
            if font == "TimesNewRomanPS-BoldMT" and size > 25 and text and not entry.get("title", ""):
                logging.info(f"Skipping page with only category: {text}")
                continue

        for i, entry in enumerate(content):
            text = entry.get("text", "").strip()
            title = entry.get("title", "").strip()
            font = entry.get("font", "")
            size = entry.get("size", 0)

            # Detect ID at the start of a new page
            if i == 0 and font == "TimesNewRomanPS-BoldMT" and size > 25 and text:
                if current_commandment:
                    sections.append(current_commandment)
                    logging.info(f"Finalized commandment: {current_commandment}")
                # Strip the dot at the end of the ID, if present
                commandment_id = text.rstrip(".")
                current_commandment = {
                    "id": commandment_id,
                    # "commandment": "",
                    "sections": {}
                }
                logging.info(f"Detected ID: {commandment_id}")
                current_section = None  # Reset current_section for the new commandment
                continue

            # Detect sections
            if title in section_mapping:
                current_section = section_mapping[title]
                if current_section == "commandment_form":
                    # Handle commandment_form as a single value
                    if i + 1 < len(content):
                        next_entry = content[i + 1]
                        current_commandment["commandment_form"] = next_entry.get("title", "").strip()
                        logging.info(f"Set commandment_form: {current_commandment['commandment_form']}")
                    current_section = None  # Reset section since commandment_form is not a list
                else:
                    if current_commandment:
                        current_commandment["sections"].setdefault(current_section, [])
                    logging.info(f"Detected section: {current_section}")
                continue

            # Add content to the current section
            if current_section and current_commandment:
                if current_section in ["commandments_related_ot", "commandments_related_nt"]:
                    # Split title into ID and title
                    match = title_split_regex.match(title)
                    if match:
                        entry_data = {
                            "id": match.group(1),
                            "title": match.group(2)
                        }
                        current_commandment["sections"][current_section].append(entry_data)
                        logging.debug(f"Added entry to section {current_section}: {entry_data}")

                    # Merge all titles into a single commentary string
                    if current_section in ["commentary_rudolph", "commentary_juster"]:
                        if current_section not in current_commandment["sections"]:
                            current_commandment["sections"][current_section] = ""  # Initialize as a string
                        # Ensure title is treated as a string and concatenate properly
                        current_commandment["sections"][current_section] += f" {title}".strip()
                        logging.debug(f"Appended to commentary in section {current_section}: {title}")

                else:
                    # Remove font and size from the entry
                    entry.pop("font", None)
                    entry.pop("size", None)
                    current_commandment["sections"][current_section].append(entry)
                    logging.debug(f"Added entry to section {current_section}: {entry}")
                    
    # Finalize the last commandment
    if current_commandment:
        sections.append(current_commandment)
        logging.info(f"Finalized last commandment: {current_commandment}")

    # Remove unwanted sections from the final output
    for commandment in sections:
        for scripture_section in ["key_nt_scriptures", "supportive_nt_scriptures", "supportive_ot_scriptures"]:
            commandment["sections"].pop(scripture_section, None)  # Remove scripture lists

    return sections

def convert_json_to_yaml(input_json_path, output_yaml_path):
    """
    Convert a JSON file to a YAML file.
    """
    try:
        # Load the JSON data
        with open(input_json_path, "r", encoding="utf-8") as json_file:
            data = json.load(json_file)
            logging.info(f"Successfully loaded JSON file: {input_json_path}")

        # Extract sections
        structured_data = extract_sections(data)

        # Save the structured data to a YAML file
        with open(output_yaml_path, "w", encoding="utf-8") as yaml_file:
            yaml.dump(
                structured_data,
                yaml_file,
                allow_unicode=True,
                default_flow_style=False,
                Dumper=yaml.SafeDumper  # Prevent YAML anchors and aliases
            )
            logging.info(f"Successfully converted JSON to YAML: {output_yaml_path}")

    except Exception as e:
        logging.error(f"An error occurred: {e}")
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    # Input and output file paths
    input_json_path = "volume_3_output/law_of_Messiah_volume_3_structured.json"  # Replace with your JSON file path
    output_yaml_path = "volume_3_output/law_of_Messiah_sections.yaml"  # Replace with your desired YAML output path

    # Run the converter
    convert_json_to_yaml(input_json_path, output_yaml_path)