import json
import requests
import time
import uuid

#HOUSING_API_TEMPLATE = "https://www.99.co/api/v11/web/search/listings?query_type=city&query_limit=radius&sort_field=relevance&sort_order=desc&property_segments=residential&page_size=36&path=%2Fsingapore%2Fsale%3Fmain_category%3Dhdb&show_cluster_preview=true&show_internal_linking=true&show_meta_description=true&show_description=true&show_nearby=true&page_num={page}&listing_type=sale&main_category=hdb&rooms=any&bathrooms=any&has_floor_plan=false&composite_floor_level=any&period_of_availability=any&composite_furnishing=any&composite_views=any&features_and_amenities=any"
ONEMAP_API_URL = "https://www.onemap.gov.sg/api/common/elastic/search?searchVal={location}&returnGeom=Y&getAddrDetails=Y&pageNum=1"
headers = {"Authorization": "Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJmM2NmMjQwNjg4YTdiZDdhYzFhM2M4MWJkZjM5ZWU0OCIsImlzcyI6Imh0dHA6Ly9pbnRlcm5hbC1hbGItb20tcHJkZXppdC1pdC1uZXctMTYzMzc5OTU0Mi5hcC1zb3V0aGVhc3QtMS5lbGIuYW1hem9uYXdzLmNvbS9hcGkvdjIvdXNlci9wYXNzd29yZCIsImlhdCI6MTczODgzODk0MSwiZXhwIjoxNzM5MDk4MTQxLCJuYmYiOjE3Mzg4Mzg5NDEsImp0aSI6InEyQmhHWkN2dTE2Mks3REEiLCJ1c2VyX2lkIjo1ODcxLCJmb3JldmVyIjpmYWxzZX0.x_KuGYFNjKBZGnIQUdcPct5MqmoW5B8n-_o-yszoRho"}

TOTAL_PAGES = 164

#input_file = "all_results_non_hdb.json"
#output_file = "filtered_non_hdb_listings.json"

input_file = "all_property_types.json"
output_file = "filtered_property_listings.json"


def fetch_housing_data():
    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)  # Read the entire JSON file
    print(len(data))
    all_listings = []

    for page in data:
        listings = page.get("data", "").get("main_results",{}).get("listing_cards", [{}])
        if (listings):
            for listing in listings:
                # title_array = listing.get("listing_title", "").split(" HDB for Sale in ")
                # if len(title_array) == 1:
                #     title_array = listing.get("listing_title", "").split(" (HDB) for Sale in ")
                title_array = listing.get("listing_title", "").split(" for Sale in ")
                try:
                    property_id = str(uuid.uuid4())
                    hdb_type = title_array[0]
                    location = title_array[1]
                    price = listing.get("attributes", {"price":{}}).get("price", {}).get("value", None)
                    lease_type = listing.get("attributes", {"lease_type":"Unknown"}).get("lease_type", "Unknown")
                    built_in_year = listing.get("attributes", {"top":"Unknown"}).get("top", "Unknown")
                    nearest_mrt_station_name = (listing.get("commute_nearest_mrt") or {}).get("name","")
                    nearest_mrt_station_code = (listing.get("commute_nearest_mrt") or {"mrt_tags":[{}]}).get("mrt_tags",[{}])[0].get("text","")
                    duration_to_mrt = (listing.get("commute_nearest_mrt") or {"distance":{}}).get("duration",{}).get("formatted_string","")
                    distance_to_mrt = (listing.get("commute_nearest_mrt") or {"distance":{}}).get("distance",{}).get("formatted_string","")
                    commute_type_to_mrt = (listing.get("commute_nearest_mrt") or {}).get("commute_type","")
                    category = listing.get("attributes", {"main_category":"Unknown"}).get("main_category", "Unknown")
                    floor_area = listing.get("attributes", {"floorarea_sqft":{}}).get("floorarea_sqft", {}).get("value", None)
                    number_of_rooms = listing.get("attributes", {"beds":{}}).get("beds", {}).get("value", None)
                    if hdb_type and location and price is not None:
                        all_listings.append({
                            "property_id": property_id,
                            "category": category.upper(),
                            "num_rooms": number_of_rooms,
                            "hdb_type": hdb_type,
                            "location": location,
                            "price": price,
                            "lease_type": lease_type,
                            "built_in_year": built_in_year,
                            "floor_area": floor_area,
                            "mrt_info": {
                                "nearest_mrt_station_name": nearest_mrt_station_name,
                                "nearest_mrt_station_code": nearest_mrt_station_code,
                                "duration_to_mrt": duration_to_mrt,
                                "distance_to_mrt": distance_to_mrt,
                                "commute_type_to_mrt": commute_type_to_mrt
                            }
                        })
                except Exception as e:
                    #print(listing)
                    print(f"unable to process record with mrt for location {title_array}: {e}")
                
                
            
    print(f"Processed successfully. Total listings: {len(all_listings)}")
    return all_listings

def get_coordinates(location):
    response = requests.get(ONEMAP_API_URL.format(location=location),headers=headers)
    if response.status_code == 200:
        results = response.json().get("results", [])
        if results:
            return {"latitude": results[0]["LATITUDE"], "longitude": results[0]["LONGITUDE"]}
    return {"latitude": None, "longitude": None}

if __name__ == "__main__":
    listings = fetch_housing_data()
    idx = 1
    for listing in listings:
        coords = get_coordinates(listing["location"])
        listing.update(coords)
        print(f"{idx}: Updated {listing['location']} with coordinates: {coords}")
        idx += 1
        time.sleep(0.4)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(listings, f, indent=4)

    print(f"\nData scraping complete! Saved to {output_file}")