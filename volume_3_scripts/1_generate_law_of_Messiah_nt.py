import json
import re
import yaml
import logging
import os

# Configure logging to write only to a file in the "logs" directory
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/1_generate_law_of_Messiah_nt.log", mode="w", encoding="utf-8")
    ]
)

# Define input and output paths
input_json_path = "volume_3_output/law_of_Messiah_volume_3_structured.json"
output_yaml_path = "volume_3_output/law_of_Messiah_commandments.yaml"

# List of pages to ignore
pages_to_ignore = [350, 351]  # We skip these pages because they are not relevant to get out commandments.

# Regex to detect Bible references
bible_reference_regex = re.compile(
    r"^[1-3]?\s?[A-Za-z]+\s[0-9]+:[0-9]+(-[0-9]+)?(,\s?[0-9]+:[0-9]+(-[0-9]+)?|,\s?[0-9]+)*$"
)
partial_reference_regex = re.compile(r"^[1-3]?\s?[A-Za-z]+\s?[0-9]*$")  # Matches "Acts 26", "Romans", etc.

# Custom Dumper to prevent anchors and aliases
class NoAliasDumper(yaml.Dumper):
    def ignore_aliases(self, data):
        return True

# List of Bible books
bible_books = [
    "Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy",
    "Joshua", "Judges", "Ruth", "1 Samuel", "2 Samuel", "1 Kings", "2 Kings",
    "1 Chronicles", "2 Chronicles", "Ezra", "Nehemiah", "Esther", "Job",
    "Psalms", "Psalm", "Proverbs", "Ecclesiastes", "Song of Solomon", "Isaiah",
    "Jeremiah", "Lamentations", "Ezekiel", "Daniel", "Hosea", "Joel", "Amos",
    "Obadiah", "Jonah", "Micah", "Nahum", "Habakkuk", "Zephaniah", "Haggai",
    "Zechariah", "Malachi", "Matthew", "Mark", "Luke", "John", "Acts",
    "Romans", "1 Corinthians", "2 Corinthians", "Galatians", "Ephesians",
    "Philippians", "Colossians", "1 Thessalonians", "2 Thessalonians",
    "1 Timothy", "2 Timothy", "Titus", "Philemon", "Hebrews", "James",
    "1 Peter", "2 Peter", "1 John", "2 John", "3 John", "Jude", "Revelation"
]

def extract_bible_references(references_text):
    """
    Extract Bible references from a given text by capturing everything after the first valid reference.
    """
    # Regex to match the first valid Bible reference and capture everything after it
    bible_reference_pattern = rf"\b(?:{'|'.join(bible_books)})\s+\d+[:.]\d+.*"
    match = re.search(bible_reference_pattern, references_text)
    if match:
        # Return the matched text as a single reference string
        return [match.group(0).strip()]
    return []

def extract_commandments_from_json(input_json_path, output_yaml_path):
    """
    Process the structured JSON file to extract commandments and save them in YAML format.
    """
    try:
        # Load the JSON data
        with open(input_json_path, "r", encoding="utf-8") as json_file:
            data = json.load(json_file)
        logging.info(f"Loaded JSON data from {input_json_path}")

        # Initialize variables
        commandments = []
        current_category = None
        multi_line_category = ""
        category_page_number = None
        current_commandment = None
        saved_commandment = None
        current_scripture_section = None
        partial_reference = None  # To track split Bible references

        # Iterate through the pages in the JSON
        for page in data:
            page_number = page["page"]
            logging.info(f"Processing page {page_number}")

            # Check if the commandment continues on the new page
            if saved_commandment and not new_commandment_detected:
                current_commandment = saved_commandment  # Restore the commandment state
                logging.info(f"Continuing commandment ID: {current_commandment['id']} on page: {page_number}")
            else:
                current_commandment = None  # Reset if no continuation is detected
                logging.warning(f"No active commandment found on page: {page_number}")
    
            # Finalize the multi-line category if the page number changes
            if multi_line_category and category_page_number != page_number:
                current_category = multi_line_category.strip()
                logging.info(f"Finalized multi-line category at the start of page {page_number}: {current_category}")
                multi_line_category = ""  # Reset the multi-line category tracker
                category_page_number = None  # Reset the category page number
    
            # Skip pages in the ignore list
            if page_number in pages_to_ignore:
                logging.info(f"Skipping page {page_number} as it is in the ignore list.")
                continue

            if not page.get("content"):
                logging.warning(f"Page {page_number} has no content.")
                continue

            for item in page["content"]:
                # Log the entire JSON entry for debugging
                logging.debug(f"Full JSON entry: {item}")

                # Extract text from either the 'text' or 'title' key
                text = item.get("text", "").strip() or item.get("title", "").strip()
                size = item.get("size", 0)
                font = item.get("font", "")

                # Log all text, even if empty
                logging.debug(f"Raw text: '{text}' with size: {size}")

                # Skip empty or whitespace-only text
                if not text:
                    logging.debug(f"Skipping empty text with size: {size}")
                    continue

                logging.debug(f"Processing text: '{text}' with size: {size}")

                # Detect category (e.g., "CA: Prioritization & Acquisition")
                if size > 25 and re.match(r"^[A-Z]{2}[.:]\s*", text):
                    # If a multi-line category is already being tracked, finalize it
                    if multi_line_category:
                        current_category = multi_line_category.strip()
                        logging.info(f"Finalized multi-line category: {current_category}")
                        multi_line_category = ""  # Reset the multi-line category tracker

                    # Start a new category and set the page number
                    multi_line_category += re.sub(r"^[A-Z]{2}[.:]\s*", "", text).strip()
                    category_page_number = page_number  # Track the page number for the category
                    logging.info(f"Detected start of category on page {page_number}: {multi_line_category}")
                    continue

                # Handle continuation of a multi-line category
                if size > 25 and multi_line_category:
                    multi_line_category += f" {text.strip()}"
                    logging.debug(f"Continuing multi-line category: {multi_line_category}")
                    continue
                
                # Detect commandment ID (e.g., "AA1.")
                if size > 25 and re.match(r"^[A-Z]{2,}[0-9]+\.?$", text):
                    if current_commandment:  # Save the previous commandment
                        logging.debug(f"Saving commandment: {current_commandment}")
                        commandments.append(current_commandment)
                    commandment_id = re.sub(r"\.$", "", text).strip()
                    current_commandment = {
                        "id": commandment_id,
                        "title": "",
                        "commandment": "",
                        "commentary_rudolph": "",
                        "commentary_juster": "",
                        "bible_references": {
                            "key_nt_scriptures": [],
                            "supportive_nt_scriptures": [],
                            "supportive_ot_scriptures": [],
                        },
                        "category": current_category
                    }
                    logging.info(f"Detected new commandment ID: {commandment_id}")
                    continue
                else:
                    new_commandment_detected = False
                
                if size > 13 and current_commandment and not current_commandment["title"]:
                    current_commandment["title"] = text
                    logging.info(f"Detected title: {text}")
                    continue

                # Detect commandment text (e.g., "We are to aspire to godliness and holiness.")
                if size == 12 and current_commandment and not current_commandment["commandment"]:
                    current_commandment["commandment"] = text
                    logging.info(f"Detected commandment text: {text}")
                    continue

                # Detect section "Comment"
                if size == 12 and text == 'Comment' and font == 'TimesNewRomanPS-BoldMT' and current_commandment and not current_commandment["commentary_rudolph"]:
                    current_commandment["commentary_rudolph"] = text
                    logging.info(f"Detected Section Commentary from Rabbi Rudolph: {text}")
                    continue

                # Detect section "Commentary Juster"
                if size == 12 and text == 'Comment by Dr. Daniel C. Juster' and font == 'TimesNewRomanPS-BoldMT' and current_commandment and not current_commandment["commentary_juster"]:
                    current_commandment["commentary_juster"] = text
                    logging.info(f"Detected Section Commentary from Rabbi Juster: {text}")
                    continue
                
                # Detect scripture sections
                if current_commandment:
                    # Skip scripture sections if commentary_rudolph is already populated
                    if current_commandment.get("commentary_rudolph"):
                        logging.debug("Skipping scripture sections because commentary_rudolph is already populated.")
                        continue
                    # Skip scripture sections if commentary_juster is already populated
                    if current_commandment.get("commentary_juster"):
                        logging.debug("Skipping scripture sections because commentary_juster is already populated.")
                        continue
                    if "Key New Testament Scriptures" in text:
                        current_scripture_section = "key_nt_scriptures"
                        logging.info(f"Detected Key New Testament Scriptures section")
                        continue
                    elif "Supportive New Testament Scriptures" in text or "Additional New Testament Scriptures" in text:
                        current_scripture_section = "supportive_nt_scriptures"
                        logging.info(f"Detected Supportive New Testament Scriptures section")
                        continue
                    elif "Supportive Tanakh Scriptures" in text:
                        current_scripture_section = "supportive_ot_scriptures"
                        logging.info(f"Detected Supportive Old Testament Scriptures section")
                        continue
        
                # Handle split Bible references
                if size == 12 and current_commandment and current_scripture_section:
                    if partial_reference:
                        # Combine partial reference with the current text, ensuring proper formatting
                        combined_reference = f"{partial_reference} {text}".replace(" :", ":").strip()  # Fix formatting issues
                        logging.debug(f"Attempting to combine partial reference: '{partial_reference}' with text: '{text}'")
                        # Use the new extract_bible_references function to validate the combined reference
                        combined_references = extract_bible_references(combined_reference)
                        if combined_references:
                            for reference in combined_references:
                                current_commandment["bible_references"][current_scripture_section].append(reference)
                                logging.info(f"Added combined reference to {current_scripture_section}: {reference}")
                            partial_reference = None  # Reset partial reference
                        else:
                            logging.debug(f"Ignored invalid combined reference: {combined_reference}")
                            partial_reference = None  # Reset partial reference even if invalid
                    elif partial_reference_regex.match(text):
                        # Store partial reference for the next iteration
                        partial_reference = text
                        logging.debug(f"Stored partial reference: {partial_reference}")
                    else:
                        # Use the new extract_bible_references function to validate standalone references
                        standalone_references = extract_bible_references(text)
                        if standalone_references:
                            for reference in standalone_references:
                                current_commandment["bible_references"][current_scripture_section].append(reference)
                                logging.info(f"Added to {current_scripture_section}: {reference}")
                        else:
                            logging.debug(f"Ignored non-Bible reference: {text} (partial_reference: {partial_reference})")
                    continue
                                                                  
            # Save the last commandment on the page
            if current_commandment:
                logging.info(f"Saving last commandment on page {page_number}: {current_commandment}")
                saved_commandment = current_commandment  # Preserve the commandment state

        # Finalize the last commandment
        if current_commandment:
            logging.info(f"Finalizing last commandment: {current_commandment}")
            commandments.append(current_commandment)

        # Save the commandments to a YAML file
        with open(output_yaml_path, "w", encoding="utf-8") as yaml_file:
            yaml.dump(commandments, yaml_file, Dumper=NoAliasDumper, allow_unicode=True, default_flow_style=False)
        logging.info(f"Commandments successfully saved to {output_yaml_path}")

    except Exception as e:
        logging.error(f"An error occurred: {e}")

if __name__ == "__main__":
    extract_commandments_from_json(input_json_path, output_yaml_path)