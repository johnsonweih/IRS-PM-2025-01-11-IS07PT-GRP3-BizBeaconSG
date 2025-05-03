import datetime
import json
import os
import uuid
import requests
from shapely import MultiPolygon
from supabase import ClientOptions, create_client, Client
from dotenv import load_dotenv
from shapely.geometry import Point, Polygon

# --- Replace these with your actual credentials ---
dotenv_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(dotenv_path)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

opts = ClientOptions().replace(schema="public")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY,options=opts)

print("connected to DB")
ONEMAP_TOKEN = os.getenv("ONEMAP_TOKEN")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
area_polygons = []

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

def update_planning_area(property_id, planning_area):
    response = (
        supabase.table("industrial_properties")
        .update({"planning_area": planning_area})
        .eq("property_id", property_id)
        .execute()
    )
    return response

def main():
    # Step 1: Get all records from industrial_properties
    records = supabase.table("industrial_properties").select("property_id, latitude, longitude").is_("planning_area","null").execute()

    if not records.data:
        print("No records found with null planning areas.")

    for record in records.data:
        prop_id = record["property_id"]
        lat = record.get("latitude")
        lon = record.get("longitude")

        if lat is None or lon is None:
            print(f"Skipping property_id {prop_id} due to missing coordinates.")
            continue

        # Step 2: Get planning area from OneMap
        planning_area = get_planning_area(lat, lon)

        if planning_area:
            print(f"Updating property_id {prop_id} with planning area: {planning_area}")
            update_planning_area(prop_id, planning_area)
        else:
            print(f"No planning area found for property_id {prop_id} (lat: {lat}, lon: {lon})")

    # Step 3 populate subzones

    planning_areas_resp = (
        supabase.table("planning_areas")
        .select("subzone, planning_area, geometry_type, coordinates")
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

    properties_resp = supabase.table("industrial_properties").select("property_id, latitude, longitude, planning_area").is_("subzone","null").execute()
    properties = properties_resp.data
    updates = []
    if not properties:
        print("No records found with null subzones.")
        return
   
    for prop in properties:
        point = Point(prop["longitude"], prop["latitude"])
        matched_subzone = None

        for shape, subzone in area_polygons:
            if shape.contains(point):
                matched_subzone = subzone
                break

        if matched_subzone:
            updates.append({
                "property_id": prop["property_id"],
                "subzone": matched_subzone
            })
    for update in updates:
        id = update["property_id"]
        sz = update["subzone"]
        supabase.table("industrial_properties") \
            .update({"subzone": update["subzone"]}) \
            .eq("property_id", update["property_id"]) \
            .execute()
        print(f"Updated id {id} with subzone {sz}")

if __name__ == "__main__":
    main()
