import yaml
import difflib
import os
import torch
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from transformers import BertTokenizer, BertModel

# Define the directory paths
input_dir = ""
output_dir = "filter_output"

# Define the commandment type to filter on. Choose 'Positive' or 'Negative'.
commandment_type = 'Positive'

# Each mitzvah in this compilation includes a New Covenant Literal Application Code (abbreviated NCLA) that consists of three parts.  The first part specifies Jew, K'rov Yisrael, or Gentile. The second part specifies Male, or Female. The third part specifies one of seven possible levels of literal compliance that applies to each. 
# Define a list of ncla values to filter on.
ncla_filter = ['GMm', 'GFm']  # Example: ['GMm', 'GFm']

# Explanation of possible NCLA codes:
# Person Categories:
# JM: Jewish male
# JF: Jewish female
# KM: K'rov Yisrael male (those who are closely related to Israel like family)
# KF: K'rovat Yisrael female (those who are closely related to Israel like family)
# GM: Gentile male
# GF: Gentile female
# Literal Application Categories:
# m: Literal compliance mandated
# r: Literal compliance recommended
# o: Literal compliance optional
# n: Literal compliance not generally recommended
# u: Literal compliance unauthorized
# p: Literal compliance prohibited
# i: Literal compliance impossible

# Whether to filter on unique commandments. Set to True to filter unique commandments, False otherwise.
# Please be aware that this filter will never be perfect. It can be used as a starting point for further manual review.
filter_unique = True
# Configuration variables for similarity checks
similarity_logic = 'or'  # Logic to combine similarity checks ('and' or 'or')
# We use 3 differtent similarity checks:
# 1) difflib: Compare sequences (such as strings) to find similarities between commandment texts based on a specified threshold.
# 2) cosine_similarity: Measure the cosine similarity between TF-IDF vectors of commandment texts to determine how similar they are based on their content.
# 3) bert: Compare the similarity of commandment texts based on their content using BERT embeddings.
use_difflib = True  # Whether to use difflib for similarity checks
difflib_threshold = 0.7  # Threshold for difflib similarity (0 to 1)
use_cosine = True  # Whether to use cosine similarity (True or False)
cosine_threshold = 0.6  # Threshold for cosine similarity (0 to 1)
use_bert = True  # Whether to use BERT for similarity checks
bert_threshold = 0.95  # Threshold for BERT similarity (0 to 1)

# Function to determine if two commandments are similar using difflib
def are_similar_difflib(cmd1, cmd2, threshold=difflib_threshold):
    if cmd1 is None or cmd2 is None:
        return False
    similarity = difflib.SequenceMatcher(None, cmd1, cmd2).ratio()
    return similarity >= threshold

# Function to determine if two commandments are similar using BERT
def are_similar_bert(tokenizer, model, cmd1, cmd2, threshold=bert_threshold):
    if cmd1 is None or cmd2 is None:
        return False
    inputs1 = tokenizer(cmd1, return_tensors='pt')
    inputs2 = tokenizer(cmd2, return_tensors='pt')
    outputs1 = model(**inputs1)
    outputs2 = model(**inputs2)
    cmd1_vec = outputs1.last_hidden_state.mean(dim=1).detach().numpy()
    cmd2_vec = outputs2.last_hidden_state.mean(dim=1).detach().numpy()
    similarity = cosine_similarity(cmd1_vec, cmd2_vec)[0][0]
    return similarity >= threshold

# Load the commandments from the New Testament YAML file
with open(os.path.join(input_dir, "Law_of_Messiah_nt.yaml"), "r") as nt_file:
    nt_commandments = yaml.safe_load(nt_file)

# Load the commandments from the Old Testament YAML file
with open(os.path.join(input_dir, "Law_of_Messiah_ot.yaml"), "r") as ot_file:
    ot_commandments = yaml.safe_load(ot_file)

# Extract the relevant fields and combine them
filtered_commandments = []
for commandment in nt_commandments + ot_commandments:
    if commandment.get('commandment_type') == commandment_type:
        if not ncla_filter or any(ncla in commandment.get('ncla', '') for ncla in ncla_filter):
            filtered_commandments.append({
                'id': commandment.get('id'),
                'commandment': commandment.get('commandment'),
                'title': commandment.get('title')
            })

# If filtering on unique commandments, apply similarity checks
if filter_unique:
    # Extract the commandment texts
    commandment_texts = [cmd['commandment'] for cmd in filtered_commandments]

    # Compute the TF-IDF vectors for the commandment texts
    vectorizer = TfidfVectorizer().fit_transform(commandment_texts)
    vectors = vectorizer.toarray()

    # Compute the cosine similarity between the commandment texts
    cosine_sim = cosine_similarity(vectors)

    # Load BERT model and tokenizer
    if use_bert:
        bert_tokenizer = BertTokenizer.from_pretrained('bert-base-uncased')
        bert_model = BertModel.from_pretrained('bert-base-uncased')

    # Use a list to store unique commandments and a dictionary to store duplicate IDs
    unique_commandments = []
    duplicate_ids = {}

    # Iterate over the filtered commandments and add unique ones to the list
    for i, commandment in enumerate(filtered_commandments):
        cmd_text = commandment.get('commandment')
        cmd_id = commandment.get('id')
        found_duplicate = False
        for j, unique_cmd in enumerate(unique_commandments):
            difflib_similar = are_similar_difflib(cmd_text, unique_cmd['commandment']) if use_difflib else False
            cosine_similar = cosine_sim[i, j] > cosine_threshold if use_cosine else False
            bert_similar = are_similar_bert(bert_tokenizer, bert_model, cmd_text, unique_cmd['commandment']) if use_bert else False

            if (similarity_logic == 'and' and difflib_similar and cosine_similar and bert_similar) or \
               (similarity_logic == 'or' and (difflib_similar or cosine_similar or bert_similar)):
                found_duplicate = True
                if 'double_ids' in unique_cmd:
                    unique_cmd['double_ids'].append({'id': cmd_id, 'commandment': cmd_text})
                else:
                    unique_cmd['double_ids'] = [{'id': cmd_id, 'commandment': cmd_text}]
                break
        if not found_duplicate:
            unique_commandments.append({
                'id': cmd_id,
                'commandment': cmd_text
            })

    # Print the duplicate IDs
    for unique_cmd in unique_commandments:
        if 'double_ids' in unique_cmd:
            print(f"Commandment ID {unique_cmd['id']} is similar to: {unique_cmd['double_ids']}")

    # Use the unique commandments as the final filtered commandments
    filtered_commandments = unique_commandments

# Convert the list of filtered commandments to a structured YAML format
yaml_data = yaml.dump(filtered_commandments, default_flow_style=False, allow_unicode=True, sort_keys=False, width=1000)

# Ensure the output directory exists
os.makedirs(output_dir, exist_ok=True)

# Save the filtered commandments to a new YAML file
with open(os.path.join(output_dir, "filtered_commandments.yaml"), "w") as yaml_file:
    yaml_file.write(yaml_data)

print(f"Filtered commandments have been written to {os.path.join(output_dir, 'filtered_commandments.yaml')}")