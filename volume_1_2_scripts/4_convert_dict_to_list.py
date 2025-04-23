import yaml

# Load the dictionary from the YAML file
with open("volume_1_2_output/output_3_dict.yaml", "r") as yaml_file:
    data_dict = yaml.safe_load(yaml_file)

# Convert the dictionary to a list and ensure 'id' is the first item
data_list = []
for id, fields in data_dict.items():
    fields['id_ot'] = id
    # Ensure 'id' is the first item in the dictionary
    fields = {'id': fields.pop('id_ot'), **fields}
    data_list.append(fields)

# Sort the list by 'id' if needed
data_list.sort(key=lambda x: x['id'])

# Convert the list to a structured YAML format
yaml_data = yaml.dump(data_list, default_flow_style=False, allow_unicode=True, sort_keys=False, width=1000)

# Save the converted YAML data to a new file
with open("Law_of_Messiah_ot.yaml", "w") as yaml_file:
    yaml_file.write(yaml_data)

print("Converted YAML data has been written to Law_of_Messiah_ot.yaml")