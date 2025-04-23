import os
import yaml
import re
from bs4 import BeautifulSoup

# Directory containing the scraped HTML files
scraped_dir = "volume_1_2_scraped_commandments"
output_dir = "volume_1_2_output"
output_file_path = os.path.join(output_dir, "output_2h_maimonides.yaml")

# Function to extract references from an HTML file
def extract_references_from_html(filepath):
    with open(filepath, "r", encoding="ISO-8859-1") as file:
        soup = BeautifulSoup(file, "html.parser")
        text = soup.get_text()
        
        references = {
            "id": os.path.splitext(os.path.basename(filepath))[0],  # Remove .php extension
            "maimonides": [],
            "meir": [],
            "chinuch": []
        }
        
        maimonides_matches = re.findall(r"Maimonides\s+([A-Z]{2}[0-9]+(?:-[0-9]+)?)", text)
        meir_matches = re.findall(r"Meir\s+([A-Z]{2}[0-9]+(?:-[0-9]+)?)", text)
        chinuch_matches = re.findall(r"Chinuch\s+([A-Z]{2}[0-9]+(?:-[0-9]+)?)", text)
        
        for match in maimonides_matches:
            if '-' in match:
                start, end = match.split('-')
                references["maimonides"].extend([f"RP{num}" for num in range(int(start[2:]), int(end) + 1)])
            else:
                references["maimonides"].append(match)
        
        for match in meir_matches:
            if '-' in match:
                start, end = match.split('-')
                references["meir"].extend([f"MP{num}" for num in range(int(start[2:]), int(end) + 1)])
            else:
                references["meir"].append(match)
        
        for match in chinuch_matches:
            if '-' in match:
                start, end = match.split('-')
                references["chinuch"].extend([f"C{num}" for num in range(int(start[1:]), int(end) + 1)])
            else:
                references["chinuch"].append(match)
        
        return references

# List to hold all the extracted information
data = []

# Process each HTML file in the directory
for filename in os.listdir(scraped_dir):
    if filename.endswith(".php"):
        filepath = os.path.join(scraped_dir, filename)
        info = extract_references_from_html(filepath)
        data.append(info)

# Filter out entries with no references
filtered_data = [entry for entry in data if any(entry[key] for key in ["maimonides", "meir", "chinuch"])]

# Ensure the output directory exists
os.makedirs(output_dir, exist_ok=True)

# Convert the list to a structured YAML format
yaml_data = yaml.dump(filtered_data, default_flow_style=False, allow_unicode=True, sort_keys=False, width=3000)

# Save the YAML data to a file
with open(output_file_path, "w") as yaml_file:
    yaml_file.write(yaml_data)

print(f"YAML data has been written to {output_file_path}")