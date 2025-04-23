import os
import yaml
from bs4 import BeautifulSoup

# Directory containing the scraped HTML files
scraped_dir = "volume_1_2_scraped_commandments"

# Function to determine if a commandment is positive or negative
def determine_commandment_type(commandment):
    negative_keywords = ["not", "do not", "shall not", "must not", "cannot"]
    for keyword in negative_keywords:
        if keyword in commandment.lower():
            return "Negative"
    return "Positive"

# Function to extract commandment from an HTML file
def extract_commandment_from_html(filepath):
    with open(filepath, "r", encoding="ISO-8859-1") as file:
        soup = BeautifulSoup(file, "html.parser")
        
        # Extract the commandment
        commandment_tag = soup.find("font", size="4", face="Times New Roman, Times, serif")
        if commandment_tag and commandment_tag.find("b") and commandment_tag.find("b").find("i"):
            commandment_text = commandment_tag.find("b").find("i").get_text(separator=" ", strip=True)
        else:
            commandment_text = "No commandment"
        
        # Ensure the commandment text is on one line
        commandment_text = " ".join(commandment_text.split())
        
        # Determine the commandment type
        commandment_type = determine_commandment_type(commandment_text)
        
        return {
            "id": os.path.splitext(os.path.basename(filepath))[0],  # Remove .php extension
            "commandment": commandment_text,
            "commandment_type": commandment_type
        }

# List to hold all the extracted information
data = []

# Process each HTML file in the directory
for filename in os.listdir(scraped_dir):
    if filename.endswith(".php"):
        filepath = os.path.join(scraped_dir, filename)
        info = extract_commandment_from_html(filepath)
        data.append(info)

# Convert the list to a structured YAML format
yaml_data = yaml.dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False, width=1000)

# Save the YAML data to a file
output_dir = "volume_1_2_output"
os.makedirs(output_dir, exist_ok=True)
with open(os.path.join(output_dir, "output_2b_commandments.yaml"), "w") as yaml_file:
    yaml_file.write(yaml_data)

print("YAML data has been written to volume_1_2_output/output_2b_commandments.yaml")