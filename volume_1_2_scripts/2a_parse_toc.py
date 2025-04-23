import os
import yaml
from bs4 import BeautifulSoup
import re

# Filepath for the toc.php
toc_filepath = "volume_1_2_scraped_files/toc.php"

# Function to parse toc.html and generate the YAML structure
def parse_toc_html(toc_filepath):
    with open(toc_filepath, "r", encoding="ISO-8859-1") as file:
        soup = BeautifulSoup(file, "html.parser")

    data = []
    current_category = None

    # Find all rows in the table of contents
    for row in soup.find_all("tr"):
        # Check if the row is a category row
        category_cell = row.find("td", colspan="2")
        if category_cell and category_cell.find("b"):
            current_category = category_cell.find("b").get_text(strip=True)
            continue

        # Check if the row contains an id and title
        link_cell = row.find("a", href=True)
        if link_cell:
            href = link_cell["href"]
            match = re.match(r"([A-Z][0-9]{3})\.php", href)
            if match:
                id = match.group(1)
                title_text = link_cell.get_text(strip=True)
                # An asterisk (*) following a Mitzvah title below indicates that its assigned NCLA Code is other than JMm JFm KMm KFm GMm GFm
                ncla_deviation = "*" in title_text
                title_text = title_text.replace("*", "").strip()

                # Find the id_short
                id_short_cell = row.find("td", align="right")
                id_short = id_short_cell.get_text(strip=True) if id_short_cell else ""
                classical_commandment = id_short.startswith("*")
                if classical_commandment:
                    id_short = id_short.lstrip("*")

                # Construct the link
                link = f"https://tikkunamerica.org/halachah/{id}.php"

                entry = {
                    "id": id,
                    "id_short": id_short,
                    "category": current_category,
                    "title": title_text,
                    "ncla_deviation": ncla_deviation,
                    "classical_commandment": classical_commandment,
                    "source": link
                }
                data.append(entry)

    # Convert the list to a structured YAML format
    yaml_data = yaml.dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False, width=1000)

    # Save the YAML data to a file
    output_dir = "volume_1_2_output"
    os.makedirs(output_dir, exist_ok=True)
    with open(os.path.join(output_dir, "output_2a_toc.yaml"), "w") as yaml_file:
        yaml_file.write(yaml_data)

    print("YAML data has been written to volume_1_2_output/output_2a_toc.yaml")

# Run the parse function
parse_toc_html(toc_filepath)