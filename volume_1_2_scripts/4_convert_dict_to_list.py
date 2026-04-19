import yaml
import re

# Load the dictionary from the YAML file
with open("volume_1_2_output/output_3_dict.yaml", "r") as yaml_file:
    data_dict = yaml.safe_load(yaml_file)

try:
    with open("Law_of_Messiah_ot.yaml", "r") as yaml_file:
        existing_list = yaml.safe_load(yaml_file) or []
except FileNotFoundError:
    existing_list = []

if not isinstance(existing_list, list):
    existing_list = []

# Build id -> new fields from fresh merge output.
new_by_id = {}


def normalize_id(id_value):
    text = str(id_value or "")
    match = re.match(r"^([A-Z]+)0*([0-9]+)$", text)
    if match:
        return f"{match.group(1)}{int(match.group(2))}"
    return text


for id_value, fields in (data_dict or {}).items():
    entry = dict(fields or {})
    normalized_id = normalize_id(id_value)
    entry["id"] = normalized_id
    new_by_id[normalized_id] = entry


def merge_preserving_order(old_entry, new_entry):
    merged = {}
    # Keep id first, then existing key order, then any newly-added keys.
    ordered_keys = ["id"]
    ordered_keys.extend(k for k in old_entry.keys() if k != "id")
    ordered_keys.extend(k for k in new_entry.keys() if k not in old_entry and k != "id")

    for key in ordered_keys:
        if key in new_entry:
            merged[key] = new_entry[key]
        elif key in old_entry:
            merged[key] = old_entry[key]
    return merged


# Rebuild list in the current OT file order to avoid large reorder diffs.
data_list = []
for existing in existing_list:
    if not isinstance(existing, dict):
        continue
    existing_id = existing.get("id")
    if existing_id in new_by_id:
        data_list.append(merge_preserving_order(existing, new_by_id.pop(existing_id)))
    else:
        data_list.append(existing)

# Append any ids that are new and not present in existing file.
for id_value in sorted(new_by_id.keys()):
    new_entry = dict(new_by_id[id_value])
    data_list.append({"id": id_value, **{k: v for k, v in new_entry.items() if k != "id"}})

# Convert the list to a structured YAML format
yaml_data = yaml.dump(data_list, default_flow_style=False, allow_unicode=True, sort_keys=False, width=1000)

# Save the converted YAML data to a new file
with open("Law_of_Messiah_ot.yaml", "w") as yaml_file:
    yaml_file.write(yaml_data)

print("Converted YAML data has been written to Law_of_Messiah_ot.yaml")