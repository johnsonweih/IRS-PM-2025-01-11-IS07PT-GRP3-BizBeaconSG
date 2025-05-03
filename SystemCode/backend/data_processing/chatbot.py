import os
import json
import openai
import numpy as np
from supabase import ClientOptions, create_client, Client
from dotenv import load_dotenv

dotenv_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(dotenv_path)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
OPENAI_ORG = os.getenv("OPENAI_ORG")
OPENAI_PROJECT = os.getenv("OPENAI_PROJECT")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

opts = ClientOptions().replace(schema="public")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY,options=opts)

openai.api_key = OPENAI_API_KEY

model = "text-embedding-3-small" #1536 dimensions
def convert_prompt_to_embeddings(text):
    response = openai.embeddings.create(input=text, model=model)
    return response.data[0].embedding

def find_best_locations(user_query, top_k=5):
    #query_embedding = convert_prompt_to_embeddings(user_query)
    query_embedding = np.array(convert_prompt_to_embeddings(user_query), dtype=np.float32)
    # query = f"""
    # SELECT ip.property_id, ip.address_name, ip.closest_mrt, ip.price, ip.area_size,
    #        1 - (embedding <=> '{json.dumps(query_embedding)}') AS similarity
    # FROM industrial_property_embeddings ipe
    # JOIN industrial_properties ip ON ipe.property_id = ip.property_id
    # ORDER BY similarity DESC
    # LIMIT {top_k};
    # """
    # response = supabase.rpc("execute_sql", {"query": query}).execute()

    # if response.data:
    #     return response.data
    # else:
    #     return "No relevant properties found."

    response = (
            supabase.table("industrial_property_embeddings")
            .select("property_id, embeddings")
            .execute()
        )

    if not response.data:
        return "No properties found in embeddings table."

    # Compute similarity manually (since we can't run SQL in Supabase directly)
    properties = response.data
    for prop in properties:
        embedding = np.array(json.loads(prop["embeddings"]), dtype=np.float32)
        similarity = 1 - np.dot(embedding, query_embedding) / (np.linalg.norm(embedding) * np.linalg.norm(query_embedding))
        prop["similarity"] = similarity

    # Sort results by similarity
    sorted_properties = sorted(properties, key=lambda x: x["similarity"], reverse=True)[:top_k]

    # Fetch matching property details
    property_ids = [p["property_id"] for p in sorted_properties]
    property_details = supabase.table("industrial_properties").select("*").in_("property_id", property_ids).execute()

    results_with_reasoning = []
    for prop in property_details.data:
        prop_id = prop["property_id"]
        similarity = next((p["similarity"] for p in sorted_properties if p["property_id"] == prop_id), None)
        reason = f"This property is ranked high because it has a similarity score of {similarity:.4f}. "
        reason += f"It is located near {prop['closest_mrt']}, making it accessible. "
        reason += f"It has an area size of {prop['area_size']} sqft and is priced at ${prop['price']}."

        results_with_reasoning.append({
            "property_id": prop["property_id"],
            "address": prop["address_name"],
            "similarity": similarity,
            "reason": reason
        })

    return results_with_reasoning

query = "Where is the best place to set up a new childcare centre?"
results = find_best_locations(query)

for res in results:
    print("====================================================")
    print(res)