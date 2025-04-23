import os
import yaml
from bs4 import BeautifulSoup

# Directory containing the scraped HTML files
scraped_dir = "volume_1_2_scraped_commandments"

# Function to extract commentary from an HTML file
def extract_commentary_from_html(filepath):
    with open(filepath, "r", encoding="ISO-8859-1") as file:
        soup = BeautifulSoup(file, "html.parser")
        
        # Extract commentary
        commentary = []
        commentary_start = soup.find("b", text="Commentary")
        if commentary_start:
            for tag in commentary_start.find_all_next("p"):
                if any(tag.find("b", text=txt) for txt in ["Classical Commentators", "NCLA", "Commentary by Daniel C. Juster", "Commentary of Daniel C. Juster", "Daniel C. Juster", "Commentary by Dr. Daniel C. Juster", "Daniel Juster"]) or tag.find("i", text="NOTE BY DANIEL C. JUSTER"):
                    break
                commentary.append(tag.get_text(separator=" ", strip=True))
        
        # Concatenate all text into one single string and remove empty lines
        commentary_html = " ".join(line for line in commentary if line.strip())
        
        return {
            "id": os.path.splitext(os.path.basename(filepath))[0],  # Remove .php extension
            "commentary_rudolph": commentary_html
        }

# List to hold all the extracted information
data = []

# Process each HTML file in the directory
for filename in os.listdir(scraped_dir):
    if filename.endswith(".php"):
        filepath = os.path.join(scraped_dir, filename)
        info = extract_commentary_from_html(filepath)
        data.append(info)

# Convert the list to a structured YAML format
yaml_data = yaml.dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False, width=3000)

# Save the YAML data to a file
output_dir = "volume_1_2_output"
os.makedirs(output_dir, exist_ok=True)
with open(os.path.join(output_dir, "output_2d_commentary.yaml"), "w") as yaml_file:
    yaml_file.write(yaml_data)

print("YAML data has been written to volume_1_2_output/output_2d_commentary.yaml")