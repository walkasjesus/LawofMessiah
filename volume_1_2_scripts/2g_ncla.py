import os
import yaml
from bs4 import BeautifulSoup
import re

# Directory containing the scraped HTML files
scraped_dir = "volume_1_2_scraped_commandments"
log_dir = "logs"
log_file = os.path.join(log_dir, "ncla_extraction_log.txt")

# Ensure the logs directory exists
os.makedirs(log_dir, exist_ok=True)

# Function to extract NCLA from an HTML file
def extract_ncla_from_html(filepath):
    with open(filepath, "r", encoding="ISO-8859-1") as file:
        soup = BeautifulSoup(file, "html.parser")
        
        # Extract the NCLA
        ncla_tag = soup.find(string=re.compile(r"NCLA"))
        if ncla_tag:
            with open(log_file, "a") as log:
                log.write(f"Found NCLA tag in file {filepath}\n")
                log.write(f"Raw NCLA tag content: {ncla_tag.strip()}\n")
            
            # Traverse up the DOM tree to find the nearest <b> tag
            parent_b_tag = ncla_tag.find_parent("b")
            if parent_b_tag:
                ncla_text = parent_b_tag.get_text(separator=" ", strip=True)
                if "NCLA" in ncla_text:
                    # Extract only the part after "NCLA:"
                    ncla_text = ncla_text.split("NCLA", 1)[1].strip(": ").strip()
                    # Remove "Return to main index" if present
                    ncla_text = ncla_text.replace("Return to main index", "").strip()
                else:
                    ncla_text = "No NCLA content found after NCLA tag"
            else:
                ncla_text = "NCLA tag found but no <b> parent"
        else:
            ncla_text = "No NCLA"
            with open(log_file, "a") as log:
                log.write(f"NCLA tag not found in file {filepath}\n")
                log.write(f"HTML content: {soup.prettify()}\n")
        
        return {
            "id": os.path.splitext(os.path.basename(filepath))[0],  # Remove .php extension
            "ncla": ncla_text,
            "copyright": "Copyright © Michael Rudolph and Daniel C. Juster, The Law of Messiah, Torah from a New Covenant Perspective, Volume 1 & 2"
        }

# Clear the log file
with open(log_file, "w") as log:
    log.write("NCLA Extraction Log\n")
    log.write("="*50 + "\n")

# List to hold all the extracted information
data = []

# Process each HTML file in the directory
for filename in os.listdir(scraped_dir):
    if filename.endswith(".php"):
        filepath = os.path.join(scraped_dir, filename)
        info = extract_ncla_from_html(filepath)
        data.append(info)

# Convert the list to a structured YAML format
yaml_data = yaml.dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False)

# Save the YAML data to a file
output_dir = "volume_1_2_output"
os.makedirs(output_dir, exist_ok=True)
with open(os.path.join(output_dir, "output_2g_ncla.yaml"), "w") as yaml_file:
    yaml_file.write(yaml_data)

print("YAML data has been written to volume_1_2_output/output_2g_ncla.yaml")
print(f"Log data has been written to {log_file}")