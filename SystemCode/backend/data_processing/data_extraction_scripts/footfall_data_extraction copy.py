from supabase import ClientOptions, create_client, Client
from dotenv import load_dotenv
import requests
import statistics
import os
import time

dotenv_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(dotenv_path)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
BESTTIME_API_KEY = os.getenv("BESTTIME_PRIVATE_API_KEY")
opts = ClientOptions().replace(schema="public")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY,options=opts)

print("connected to DB")


subcategory_map = {
    'cafes': ['CAFE', 'COFFEE', 'BAKERY'],
    'restaurants': ['RESTAURANT'],
    'fast food': ['FAST_FOOD'],
    'nightlife': ['CLUBS'],

    'fashion': ['APPAREL'],
    'electronics': ['ELECTRONICS_STORE'],
    'specialty stores': ['SHOPPING'],

    'salon and spas': ['SPA', 'PERSONAL_CARE'],
    'personal care': ['PERSONAL_CARE'],
    'fitness': ['SPORTS_COMPLEX'],

    'tuition and schools': ['SCHOOL'],
    'coworking spaces': ['COWORKING_SPACE'],

    'consulting': ['OFFICE'],
    'logistics': ['LOGISTICS_SERVICE'],
    'pet services': ['PET_STORE']
}

def get_footfall_data(location, venue_types):
    url = 'https://besttime.app/api/v1/venues/filter'
    headers = {'X-API-KEY': BESTTIME_API_KEY}

    payload = {
        "usermsg": f"Popular venues in {location} of Singapore",
        "area": location,
        "types": venue_types,
        "limit": 10,
        "rating_min": 3.5,
        "reviews_min": 30
    }

    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()
    return response.json()["venues"]

def analyze_weekday_weekend(venues):
    weekday_hours = [0] * 24
    weekend_hours = [0] * 24
    dwell_times = []

    for v in venues:
        day_raw = v['day_raw']  # 7x24 = 168 hours, starts Monday 6AM
        dwell_times.append(v.get('venue_dwell_time_min', 0))

        for h in range(24):
            # Mon-Fri = day_raw[0:5*24], Sat-Sun = day_raw[5*24:]
            weekday_hours[h] += sum(day_raw[h + 24*d] for d in range(5)) / 5
            weekend_hours[h] += sum(day_raw[h + 24*d] for d in range(5, 7)) / 2

    def summarize(hour_data):
        avg = round(statistics.mean(hour_data), 2)
        peak = hour_data.index(max(hour_data))
        quiet = hour_data.index(min(hour_data))
        intensity = "🔥🔥🔥" if avg > 80 else "🔥🔥" if avg > 60 else "🔥"
        return avg, peak, quiet, intensity

    weekday_summary = summarize(weekday_hours)
    weekend_summary = summarize(weekend_hours)
    avg_dwell = int(statistics.mean(dwell_times)) if dwell_times else None

    return weekday_summary, weekend_summary, avg_dwell

def store_to_supabase(district, sector_list, location, subcategory, footfall_type, summary, dwell, venue_types):
    data = {
        "postal_district": district,
        "postal_sector": sector_list,
        "general_location": location,
        "subcategory": subcategory,
        "footfall_type": footfall_type,
        "avg_footfall_pct": summary[0],
        "peak_hour": summary[1],
        "quiet_hour": summary[2],
        "peak_intensity": summary[3],
        "avg_dwell_time_min": dwell,
        "venue_types": venue_types
    }
    supabase.table("footfall_insights").insert(data).execute()

district = "09"
sector = ["21", "22", "23"]
location = "Orchard, Cairnhill, River Valley"

for subcat, venue_types in subcategory_map.items():
    try:
        print(f"Processing {subcat} in {location}...")
        venues = get_footfall_data(location, venue_types)
        if not venues:
            print("No venues found. Skipping.")
            continue

        weekday, weekend, dwell = analyze_weekday_weekend(venues)

        store_to_supabase(district, sector, location, subcat, 'weekday', weekday, dwell, venue_types)
        store_to_supabase(district, sector, location, subcat, 'weekend', weekend, dwell, venue_types)

        time.sleep(1)  # Avoid hitting rate limits

    except Exception as e:
        print(f"Error processing {subcat} in {location}: {e}")