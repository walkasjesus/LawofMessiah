import os
import yaml
from bs4 import BeautifulSoup
import re

# Directory containing the scraped HTML files
scraped_dir = "volume_1_2_scraped_commandments"
log_dir = "logs"
log_file = os.path.join(log_dir, "extraction_log.txt")

# Ensure the logs directory exists
os.makedirs(log_dir, exist_ok=True)

# Separate lists for Old Testament and New Testament books
ot_books = [
    "Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy",
    "Joshua", "Judges", "Ruth", "1 Samuel", "2 Samuel", "1 Kings", "2 Kings",
    "1 Chronicles", "2 Chronicles", "Ezra", "Nehemiah", "Esther", "Job",
    "Psalms", "Psalm", "Proverbs", "Ecclesiastes", "Song of Solomon", "Isaiah",
    "Jeremiah", "Lamentations", "Ezekiel", "Daniel", "Hosea", "Joel", "Amos",
    "Obadiah", "Jonah", "Micah", "Nahum", "Habakkuk", "Zephaniah", "Haggai",
    "Zechariah", "Malachi"
]

nt_books = [
    "Matthew", "Mark", "Luke", "John", "Acts", "Romans", "1 Corinthians",
    "2 Corinthians", "Galatians", "Ephesians", "Philippians", "Colossians",
    "1 Thessalonians", "2 Thessalonians", "1 Timothy", "2 Timothy", "Titus",
    "Philemon", "Hebrews", "James", "1 Peter", "2 Peter", "1 John", "2 John",
    "3 John", "Jude", "Revelation"
]

# Function to extract key scriptures from an HTML file
def extract_key_scriptures_from_html(filepath):
    with open(filepath, "r", encoding="ISO-8859-1") as file:
        soup = BeautifulSoup(file, "html.parser")
        
        # Extract scriptures
        key_nt_scriptures = []
        key_ot_scriptures = []
        supportive_nt_scriptures = []
        supportive_ot_scriptures = []
        
        key_scriptures_start = soup.find("b", string=re.compile("Key Scripture(s)?"))
        if key_scriptures_start:
            with open(log_file, "a") as log:
                log.write(f"Found 'Key Scripture(s)' section in file {filepath}\n")
            
            for tag in key_scriptures_start.find_all_next("font", size="4", face="Times New Roman, Times, serif"):
                reference = tag.find("u").get_text(strip=True) if tag.find("u") else tag.get_text(strip=True)
                # Check if the reference contains a valid Bible book
                if any(book in reference for book in ot_books):
                    key_ot_scriptures.append(reference)
                elif any(book in reference for book in nt_books):
                    key_nt_scriptures.append(reference)
                else:
                    with open(log_file, "a") as log:
                        log.write(f"Skipped non-matching reference: {reference} in file {filepath}\n")
                if tag.find("b", string=re.compile("Supportive Scriptures|Commentary|Classical Commentators|NCLA")):
                    break
        
        # Extract supportive scriptures
        supportive_scriptures_start = soup.find("b", string=re.compile("Supportive Scriptures"))
        if supportive_scriptures_start:
            for tag in supportive_scriptures_start.find_all_next("font", size="4", face="Times New Roman, Times, serif"):
                reference = tag.find("u").get_text(strip=True) if tag.find("u") else tag.get_text(strip=True)
                # Check if the reference contains a valid Bible book
                if any(book in reference for book in ot_books):
                    supportive_ot_scriptures.append(reference)
                elif any(book in reference for book in nt_books):
                    supportive_nt_scriptures.append(reference)
                else:
                    with open(log_file, "a") as log:
                        log.write(f"Skipped non-matching supportive reference: {reference} in file {filepath}\n")
                if tag.find("b", string=re.compile("Commentary|Classical Commentators|NCLA")):
                    break
        
        return {
            "id": os.path.basename(filepath).split('.')[0],
            "bible_references": {
                "key_nt_scriptures": key_nt_scriptures,
                "key_ot_scriptures": key_ot_scriptures,
                "supportive_nt_scriptures": supportive_nt_scriptures,
                "supportive_ot_scriptures": supportive_ot_scriptures,
            }
        }

# List to hold all the extracted information
data = []

# Clear the log file
with open(log_file, "w") as log:
    log.write("Extraction Log\n")
    log.write("="*50 + "\n")

# Process each HTML file in the directory
for filename in os.listdir(scraped_dir):
    if filename.endswith(".php"):
        filepath = os.path.join(scraped_dir, filename)
        info = extract_key_scriptures_from_html(filepath)
        if info:
            if not info["bible_references"]["key_nt_scriptures"] and not info["bible_references"]["key_ot_scriptures"] and not info["bible_references"]["supportive_nt_scriptures"] and not info["bible_references"]["supportive_ot_scriptures"]:
                with open(log_file, "a") as log:
                    log.write(f"Warning: No scriptures found in {filename}\n")
            data.append(info)
        else:
            with open(log_file, "a") as log:
                log.write(f"No information extracted from file {filename}\n")

# Convert the list to a structured YAML format
yaml_data = yaml.dump(data, default_flow_style=False, allow_unicode=True)

# Save the YAML data to a file
output_dir = "volume_1_2_output"
os.makedirs(output_dir, exist_ok=True)
with open(os.path.join(output_dir, "output_2c_scriptures.yaml"), "w") as yaml_file:
    yaml_file.write(yaml_data)

print("YAML data has been written to volume_1_2_output/output_2c_scriptures.yaml")
print(f"Log data has been written to {log_file}")