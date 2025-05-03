import datetime
import json
import os
import uuid
from supabase import ClientOptions, create_client, Client
from dotenv import load_dotenv

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

files = ["industrial_raw1.json","industrial_raw2.json","industrial_raw3.json"]
total = 0
for file in files:
    with open(file, "r", encoding="utf-8") as file:
        data = json.load(file)
    for listing_data in data:
        listings = listing_data.get("data", {}).get("sections", [{}])[0].get("listings", [])
        print(f"Number of listings: {len(listings)}")
        total += len(listings)
        for listing in listings:
            try:
                address_name = listing.get("address_name")
                listing_id = listing.get("id")
                try:
                    lat = listing["location"]["coordinates"].get("lat")
                    lng = listing["location"]["coordinates"].get("lng")
                    geo_point = f"SRID=4326;POINT({lng} {lat})" if lat and lng else None
                    response = supabase.table("industrial_properties").insert({
                        "listing_id": listing.get("id"),
                        "property_segment": listing.get("property_segment"),
                        "listing_type": listing.get("listing_type"),
                        "main_category": listing.get("main_category"),
                        "sub_category": listing.get("sub_category"),
                        "status": listing.get("status"),
                        "description": listing.get("description"),
                        "price": listing["attributes"].get("price"),
                        "area_size": listing["attributes"].get("area_size"),
                        "area_ppsf": listing["attributes"].get("area_ppsf"),
                        "district_number": listing.get("district_number"),
                        "postal_code": listing.get("postal_code"),
                        "latitude": lat,
                        "longitude": lng,
                        "address_name": listing.get("address_name"),
                        "closest_mrt": listing["within_distance_from_query"]["closest_mrt"].get("title") if listing.get("within_distance_from_query") else None,
                        "photo_url": listing.get("photo_url"),
                        "listing_url": "https://www.99.co" + listing.get("listing_url") if listing.get("listing_url") else None,
                        "location": geo_point
                    }).execute()
                    print(f"Inserted property: {address_name} listing_id: {listing_id}")
                except Exception as e:
                    print(f"Error inserting property: {address_name} listing_id: {listing_id}", e)
            except Exception as e:
                    print(f"General Error inserting property: ", e)

print("All properties successfully inserted into Supabase!")