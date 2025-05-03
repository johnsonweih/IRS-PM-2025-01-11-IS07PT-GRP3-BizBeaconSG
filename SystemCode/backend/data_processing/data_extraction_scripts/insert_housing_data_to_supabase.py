import datetime
import json
import os
import uuid
from supabase import ClientOptions, create_client, Client
from dotenv import load_dotenv

with open("filtered_hdb_listings.json", "r") as f:
    data = json.load(f)

dotenv_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(dotenv_path)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
print(f"SUPABASE_URL: {SUPABASE_URL}")
print(f"SUPABASE_KEY: {SUPABASE_KEY}")

opts = ClientOptions().replace(schema="public")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY,options=opts)

print("connected to DB")

def extract_lease_years(lease_str):
    try:
        return int(lease_str.split()[0]) if lease_str else None
    except:
        return -1

response = supabase.table('properties').select('*').execute()
print("test: ",response)

for house in data:
    property_id = str(uuid.uuid4())
    latitude = house["latitude"]
    longitude = house["longitude"]
    geo_location = f"SRID=4326;POINT({longitude} {latitude})"
    #print(house)
    try:
        response = supabase.table("properties").insert({
            #"property_id": property_id,
            "property_type": house["category"],
            "address": house["location"],
            "postal_code": house.get("postal_code", None),
            "district": house.get("district", None),
            "town": house.get("town", None),
            "flat_type": house["hdb_type"],
            "floor_area": house.get("floor_area", None),
            "number_of_rooms": house.get("number_of_rooms", None),
            "floor": house.get("floor", None),
            "built_year": int(house.get("built_in_year", "0")),
            "lease_remaining": house.get("lease_remaining", None),
            "location": geo_location,
            "listing_price": house["price"],
            "status": house.get("status", "available"),
            #"created_at": datetime.utcnow().isoformat(),
            #"updated_at": datetime.utcnow().isoformat(),
            "lease_type": extract_lease_years(house["lease_type"])
        }).execute()

        print(f"Inserted property: {house["location"]}")
    except Exception as e:
        print(f"Error inserting property: {house["location"]}", e)

print("All properties successfully inserted into Supabase!")