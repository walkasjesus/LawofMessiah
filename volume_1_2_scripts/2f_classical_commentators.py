import os
import yaml
from bs4 import BeautifulSoup

# Directory containing the scraped HTML files
scraped_dir = "volume_1_2_scraped_commandments"

# Function to extract classical commentators from an HTML file
def extract_classical_commentators_from_html(filepath):
    with open(filepath, "r", encoding="ISO-8859-1") as file:
        soup = BeautifulSoup(file, "html.parser")
        
        # Extract classical commentators
        classical_commentators = []
        classical_commentators_start = soup.find("b", text="Classical Commentators")
        if classical_commentators_start:
            for tag in classical_commentators_start.find_all_next("p"):
                if tag.find(text="NCLA"):
                    break
                classical_commentators.append(tag.get_text(separator=" ", strip=True))
        
        # Concatenate all text into one single string and remove empty lines
        classical_commentators_html = " ".join(line for line in classical_commentators if line.strip())
        
        return {
            "id": os.path.splitext(os.path.basename(filepath))[0],  # Remove .php extension
            "classical_commentators": classical_commentators_html
        }

# List to hold all the extracted information
data = []

# Process each HTML file in the directory
for filename in os.listdir(scraped_dir):
    if filename.endswith(".php"):
        filepath = os.path.join(scraped_dir, filename)
        info = extract_classical_commentators_from_html(filepath)
        data.append(info)

# Convert the list to a structured YAML format
yaml_data = yaml.dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False, width=3000)

# Save the YAML data to a file
output_dir = "volume_1_2_output"
os.makedirs(output_dir, exist_ok=True)
with open(os.path.join(output_dir, "output_2f_classical_commentators.yaml"), "w") as yaml_file:
    yaml_file.write(yaml_data)

print("YAML data has been written to volume_1_2_output/output_2f_classical_commentators.yaml")