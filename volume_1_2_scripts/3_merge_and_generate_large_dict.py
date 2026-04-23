import os
import yaml
from collections import defaultdict
import re

# Directory containing the output YAML files
output_dir = "volume_1_2_output"
output_file_path = os.path.join(output_dir, "output_3_dict.yaml")


def id_sort_key(id_value):
    match = re.match(r"^([A-Z]+)(\d+)$", str(id_value or ""))
    if not match:
        return (str(id_value or ""), 0)
    return (match.group(1), int(match.group(2)))

# Function to merge YAML files
def merge_yaml_files(output_dir):
    merged_data = defaultdict(lambda: defaultdict(list))
    # output_2g_ncla.yaml is the raw extraction; output_2g_ncla_revised.yaml supersedes it.
    skip_files = {"output_3_dict.yaml", "merged_output.yaml", "output_2g_ncla.yaml"}

    try:
        with open(output_file_path, "r", encoding="utf-8") as existing_file:
            existing_output = yaml.safe_load(existing_file) or {}
    except FileNotFoundError:
        existing_output = {}
    if not isinstance(existing_output, dict):
        existing_output = {}

    # Process each YAML file in the directory
    for filename in sorted(os.listdir(output_dir)):
        if filename.endswith(".yaml") and filename not in skip_files:
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

    # Preserve existing id order and per-id field order to minimize diff churn.
    ordered_merged = {}
    for id in existing_output.keys():
        if id not in merged_data:
            continue
        existing_fields = existing_output.get(id) or {}
        new_fields = merged_data[id]
        if not isinstance(existing_fields, dict):
            existing_fields = {}

        ordered_fields = {}
        for key in existing_fields.keys():
            if key in new_fields:
                ordered_fields[key] = new_fields[key]
        for key, value in new_fields.items():
            if key not in ordered_fields:
                ordered_fields[key] = value
        ordered_merged[id] = ordered_fields

    for id in sorted((set(merged_data.keys()) - set(ordered_merged.keys())), key=id_sort_key):
        ordered_merged[id] = dict(merged_data[id])

    merged_data = ordered_merged

    # Convert the list to a structured YAML format
    yaml_data = yaml.dump(merged_data, default_flow_style=False, allow_unicode=True, sort_keys=False, width=1000)

    # Save the merged YAML data to a file
    with open(output_file_path, "w") as yaml_file:
        yaml_file.write(yaml_data)

    print(f"Merged YAML data has been written to {output_file_path}")

# Run the merge function
merge_yaml_files(output_dir)