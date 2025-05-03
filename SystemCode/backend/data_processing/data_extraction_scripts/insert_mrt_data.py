import json
import os
from dotenv import load_dotenv
import requests
from bs4 import BeautifulSoup
from supabase import ClientOptions, create_client, Client

dotenv_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(dotenv_path)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

opts = ClientOptions().replace(schema="public")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY,options=opts)

# Load GeoJSON file
with open("LTAMRTStationExitGEOJSON.geojson", "r", encoding="utf-8") as file:
    data = json.load(file)
print(f"data loaded {len(data)} records")
amenities_data = []
for feature in data["features"]:
    properties = feature["properties"]
    geometry = feature["geometry"]

    # Extract station name and exit code from the HTML table in "Description"
    description_html = properties.get("Description", "")
    soup = BeautifulSoup(description_html, "html.parser")

    station_name = None
    exit_code = None

    for row in soup.find_all("tr"):
        cols = row.find_all("th"), row.find_all("td")
        if len(cols[0]) > 0 and len(cols[1]) > 0:
            header, value = cols[0][0].text.strip(), cols[1][0].text.strip()
            if header == "STATION_NA":
                station_name = value
            elif header == "EXIT_CODE":
                exit_code = value

    if not station_name or not exit_code:
        continue  # Skip if we couldn't extract necessary fields

    name = f"{station_name} {exit_code}"

    # Extract longitude and latitude
    longitude, latitude = geometry["coordinates"][:2]
    location = f"SRID=4326;POINT({longitude} {latitude})"  # PostGIS format

    # Prepare data for insertion
    amenity_entry = {
        "name": name,
        "amenity_type": "MRT",
        "location": location,
        "address": None,
        "postal_code": None,
        "additional_info": None,
    }
    amenities_data.append(amenity_entry)

# Save extracted data to a temporary JSON file for review
tmp_file = "tmp_amenities.json"
with open(tmp_file, "w", encoding="utf-8") as tmp:
    json.dump(amenities_data, tmp, indent=4)

print(f"Data saved to {tmp_file}. Please review before inserting into Supabase.")

# Ask for user confirmation before inserting
confirm = input("Do you want to insert the data into Supabase? (yes/no): ").strip().lower()
if confirm == "yes":
    response = supabase.table("amenities").insert(amenities_data).execute()
    print(response)
else:
    print("Insertion canceled. You can modify and re-run the script.")
