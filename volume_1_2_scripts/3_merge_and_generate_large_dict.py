import os
import yaml
from collections import defaultdict

# Directory containing the output YAML files
output_dir = "volume_1_2_output"
output_file_path = os.path.join(output_dir, "output_3_dict.yaml")

# Function to merge YAML files
def merge_yaml_files(output_dir):
    merged_data = defaultdict(lambda: defaultdict(list))

    # Process each YAML file in the directory
    for filename in os.listdir(output_dir):
        if filename.endswith(".yaml") and filename != "merged_output.yaml":
            filepath = os.path.join(output_dir, filename)
            with open(filepath, "r") as file:
                try:
                    data = yaml.safe_load(file)
                    if not isinstance(data, list):
                        raise ValueError(f"Expected a list in file {filepath}, but got {type(data)}")
                    for entry in data:
                        if not isinstance(entry, dict):
                            raise ValueError(f"Expected a dict in file {filepath}, but got {type(entry)}")
                        id = entry["id"]
                        for key, value in entry.items():
                            if key != "id":
                                merged_data[id][key].append(value)
                except Exception as e:
                    print(f"Error processing file {filepath}: {e}")

    # Convert defaultdict to regular dict and handle single items
    merged_data = {id: {key: (value[0] if len(value) == 1 else value) for key, value in fields.items()} for id, fields in merged_data.items()}

    # Rename id_short to id
    for id, fields in merged_data.items():
        if "id_short" in fields:
            fields["id"] = fields.pop("id_short")

    # Convert the list to a structured YAML format
    yaml_data = yaml.dump(merged_data, default_flow_style=False, allow_unicode=True, sort_keys=False, width=1000)

    # Save the merged YAML data to a file
    with open(output_file_path, "w") as yaml_file:
        yaml_file.write(yaml_data)

    print(f"Merged YAML data has been written to {output_file_path}")

# Run the merge function
merge_yaml_files(output_dir)