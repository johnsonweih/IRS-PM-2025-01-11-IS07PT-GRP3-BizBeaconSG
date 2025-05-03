import csv
import json
import os
from dotenv import load_dotenv
from openai import OpenAI
import pandas as pd
from supabase import Client, create_client
from transformers import GPT2TokenizerFast 

dotenv_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(dotenv_path)

# OPENAI_ORG = os.getenv("OPENAI_ORG")
# OPENAI_PROJECT = os.getenv("OPENAI_PROJECT")
# OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# openai_client = OpenAI(organization=OPENAI_ORG, project=OPENAI_PROJECT, api_key=OPENAI_API_KEY)
# data = pd.read_csv("industrial_properties.csv")

# def concat_columns(row):
#     return " ".join([f"{col} : {row[col]}" for col in data.columns])
# data["description"] = data["description"].astype(str).str.replace(",", " ")
# data["text"] = data.apply(concat_columns, axis=1)

# data.to_csv("industrial_properties_with_text.csv", index=False, quoting=csv.QUOTE_ALL)

# model = "text-embedding-3-small" #1536 dimensions
# def get_embedding(text, model):
#     text = text.replace("\n", " ")
#     return openai_client.embeddings.create(input=[text], model=model).data[0].embedding

# data["embeddings"] = data.text.apply(lambda x: get_embedding(x, model))
# data.to_csv("industrial_properties_with_embeddings.csv", index=False, quoting=csv.QUOTE_ALL)

data = pd.read_csv("industrial_properties_with_embeddings.csv")

tokenizer = GPT2TokenizerFast.from_pretrained("gpt2")
data['n_tokens'] = data.text.apply(lambda x: len(tokenizer.encode(x)))

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def convert_embedding(embedding_str):
    try:
        return json.loads(embedding_str.replace("'", '"'))
    except Exception as e:
        print(f"Error converting embedding: {embedding_str} - {e}")
        return None

for index, row in data.iterrows():
    try:
        property_id = row["property_id"]
        text = row["text"]
        embeddings = convert_embedding(row["embeddings"])

        if embeddings is None:
            print(f"Skipping row {index} due to invalid embeddings.")
            continue
        
        response = supabase.table("industrial_property_embeddings").insert({
            "property_id": property_id,
            "text": text,
            "embeddings": embeddings
        }).execute()
        print(f"Inserted embeddings for property_id: {property_id}")
    
    except Exception as e:
        print(f"Error inserting embeddings for property_id {property_id}: {e}")
print("All embeddings successfully inserted into Supabase!")