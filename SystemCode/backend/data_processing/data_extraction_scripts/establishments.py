import json
import os
import requests
from dotenv import load_dotenv
from supabase import ClientOptions, create_client, Client
from shapely import MultiPolygon
from shapely.geometry import Point, Polygon

# Load environment variables
dotenv_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(dotenv_path)
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
GEOAPIFY_API_KEY = os.getenv("GEOAPIFY_API_KEY")
ONEMAP_TOKEN = os.getenv("ONEMAP_TOKEN")

is_data_extracted = True
is_area_details_populated = False

opts = ClientOptions().replace(schema="public")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY, options=opts)
print("Connected to Supabase.")

area_polygons = []

place_ids = {"NW":"place:51f0969c9714f259405947f8286dbb4af63ff00101f901a2773a0000000000c00206",
            "NE":"place:51648d49af5bfb5940590c1f11532209f63ff00101f901a1773a0000000000c00206",
            "SW":"place:51be2bc776e4ec59405936464662ddb3f43ff00101f901a4773a0000000000c00206", 
            "SE":"place:519ef1776492005a40592d4d00b49c5af53ff00101f901a3773a0000000000c00206"}

categories = [
    "activity.community_center", "activity.sport_club", "commercial.supermarket", "commercial.marketplace",
    "commercial.shopping_mall", "commercial.department_store", "commercial.elektronics", "commercial.outdoor_and_sport",
    "commercial.vehicle", "commercial.hobby", "commercial.books", "commercial.gift_and_souvenir",
    "commercial.clothing", "commercial.clothing.shoes", "commercial.clothing.clothes", "commercial.clothing.sport",
    "commercial.bag", "commercial.health_and_beauty", "commercial.health_and_beauty.pharmacy",
    "commercial.health_and_beauty.optician", "commercial.health_and_beauty.medical_supply",
    "commercial.health_and_beauty.hearing_aids", "commercial.health_and_beauty.cosmetics", "commercial.toy_and_game",
    "commercial.pet", "commercial.food_and_drink", "commercial.food_and_drink.bakery", "commercial.second_hand",
    "catering.restaurant", "catering.fast_food", "catering.cafe", "education.school", "education.driving_school",
    "education.music_school", "education.language_school", "education.library", "education.college",
    "education.university", "childcare", "entertainment.culture.theatre", "entertainment.culture.arts_centre",
    "entertainment.culture.gallery", "healthcare.clinic_or_praxis", "healthcare.dentist.orthodontics",
    "healthcare.hospital", "healthcare.pharmacy", "heritage.unesco", "leisure.spa", "service.vehicle.fuel",
    "service.vehicle.car_wash", "service.vehicle.charging_station", "service.vehicle.repair", "service.beauty"
]

PROGRESS_FILE = "progress.json"

def load_progress():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, "r") as f:
            return json.load(f)
    return {}

def save_progress(progress):
    with open(PROGRESS_FILE, "w") as f:
        json.dump(progress, f, indent=2)

def fetch_data(category, place_id):
    url = (
    f"https://api.geoapify.com/v2/places?categories={category}&filter={place_id}&limit=500&apiKey={GEOAPIFY_API_KEY}"
    )
    print(url)
    response = requests.get(url)
    data = response.json()
    return data

def insert_data(data, category, region):
    if "features" not in data:
        raise ValueError("No features found in Geoapify response")
    
    features = data["features"]
    print(f"Extracted {len(features)} records for {category} for {region}")

    for feature in data["features"]:
        try:
            prop = feature.get("properties", {})

            entry = {
                "subzone": None,
                "planning_area": prop.get("suburb", "").upper() if prop.get("suburb") else None,
                "region": None,
                "latitude": prop.get("lat"),
                "longitude": prop.get("lon"),
                "venue_type": category,
                "rank": None,
                "venue_name": prop.get("name"),
                "venue_address": prop.get("formatted"),
                "venue_id": None,
                "avg_weekday_footfall": None,
                "avg_weekend_footfall": None
            }

            res = supabase.table("establishments").insert(entry).execute()
            print(f"✅ Inserted: {entry['venue_name']}")
        except Exception as e:
            print(f"Error inserting for {category} in {region}: ",e)


def get_planning_area(lat, lon):
    url = f"https://www.onemap.gov.sg/api/public/popapi/getPlanningarea?latitude={lat}&longitude={lon}&year=2019"
    headers = {
        "Authorization": f"Bearer {ONEMAP_TOKEN}"
    }
    try:
        response = requests.request("GET", url, headers=headers)
        print(response)
        if response.status_code == 200:
            data = response.json()
            if data and isinstance(data, list):
                return data[0].get("pln_area_n")
    except Exception as e:
        print(f"Error calling OneMap API for lat={lat}, lon={lon}: {e}")
    return None

def update_planning_area(id, planning_area):
    response = (
        supabase.table("establishments")
        .update({"planning_area": planning_area})
        .eq("id", id)
        .execute()
    )
    return response

progress = load_progress()

def main():
    #Step 1: Extract data
    if not is_data_extracted:
        for category in categories:
            if category not in progress:
                progress[category] = []

            for region in place_ids:
                if region in progress[category]:
                    print(f"✅ Skipping already processed: {category} - {region}")
                    continue

                try:
                    print(f"Processing: {category} - {region}")
                    data = fetch_data(category, place_ids[region])
                    insert_data(data, category, region)

                    # Mark this (category, region) as done
                    progress[category].append(region)
                    save_progress(progress)

                except Exception as e:
                    print(f"❌ Error processing {category} - {region}: {e}")

        print("completed extraction and insertion")
    
    #Step 2: Populate missing planning areas and all subzones and regions
    if not is_area_details_populated:
        records = supabase.table("establishments").select("id, latitude, longitude").is_("planning_area","null").execute()

        if not records.data:
            print("No records found with null planning areas.")
        else:
            for record in records.data:
                prop_id = record["id"]
                lat = record.get("latitude")
                lon = record.get("longitude")

                planning_area = get_planning_area(lat, lon)

                if planning_area:
                    print(f"Updating id {prop_id} with planning area: {planning_area}")
                    update_planning_area(prop_id, planning_area)
                else:
                    print(f"No planning area found for id {prop_id} (lat: {lat}, lon: {lon})")
        
        planning_areas_resp = (
        supabase.table("planning_areas")
        .select("subzone, planning_area, region, geometry_type, coordinates")
        .execute()
        )
        planning_areas = planning_areas_resp.data
        print("Retrieved planning areas")

        for area in planning_areas:
            try:
                coords_raw = json.loads(area["coordinates"])
                if not coords_raw or not coords_raw[0]:
                    continue
                if (area["geometry_type"] == "Polygon"):
                    polygon = Polygon([(lng, lat) for lng, lat, *_ in coords_raw[0]])
                    area_polygons.append((polygon, area["subzone"]))
                else: #Multi polygon
                    polygons = []
                    for part in coords_raw:
                        if not part:
                            continue
                        # part[0] is usually the outer ring; ignore holes for now
                        poly = Polygon([(lng, lat) for lng, lat, *_ in part[0]])
                        polygons.append(poly)
                    multi = MultiPolygon(polygons)
                    area_polygons.append((multi, area["subzone"]))
            except Exception as e:
                print(f"Error parsing polygon for {area['subzone']}: {e}")

        print("Formed polygons for all areas")

        establishments_resp = supabase.table("establishments").select("id, latitude, longitude, planning_area").is_("subzone","null").execute()
        establishments = establishments_resp.data
        updates = []
        if not establishments:
            print("No records found with null subzones.")
            return

        for establishment in establishments:
            point = Point(establishment["longitude"], establishment["latitude"])
            matched_subzone = None

            for shape, subzone in area_polygons:
                if shape.contains(point):
                    matched_subzone = subzone
                    break
            
            id = establishment["id"]
            if matched_subzone:
                updates.append({
                    "id": id,
                    "subzone": matched_subzone
                })
            else:
                print(f"No subzone found for id {id}")
        
        for update in updates:
            id = update["id"]
            sz = update["subzone"]
            supabase.table("establishments") \
                .update({"subzone": update["subzone"]}) \
                .eq("id", update["id"]) \
                .execute()
            print(f"Updated id {id} with subzone {sz}")

    #Step 3: Use OpenAI to re-classify each business types to constrained venue types


if __name__ == "__main__":
    main()