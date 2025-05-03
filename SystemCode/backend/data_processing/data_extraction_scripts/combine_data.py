import json

# List of input files
# input_files = ["results1.json", "results2.json", "results3.json"]
# output_file = "all_results.json"

# input_files = []
# output_file = "all_results_non_hdb.json"
# for i in range(1,14):
#     input_files.append("tmp_data/non-hdb" + str(i) + ".json")

input_files = ["all_results.json", "all_results_non_hdb.json"]
output_file = "all_property_types.json"

all_results = []

# Read and merge data from each file
for file in input_files:
    with open(file, "r", encoding="utf-8") as f:
        data = json.load(f)
        print(f"{file}: {len(data)} records")
        all_results.extend(data)  # Assuming each file contains a list of JSON objects

# Write merged data to output file
with open(output_file, "w", encoding="utf-8") as f:
    json.dump(all_results, f, indent=4)

print(f"Merged {len(all_results)} records into {output_file}")
