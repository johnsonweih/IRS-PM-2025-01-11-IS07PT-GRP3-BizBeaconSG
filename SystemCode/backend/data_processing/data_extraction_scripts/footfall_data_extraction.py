from supabase import ClientOptions, create_client, Client
from dotenv import load_dotenv
import csv
import requests
import time
import statistics
import os

# --- Configuration ---
#BESTTIME_PRIVATE_API_KEY = os.getenv("BESTTIME_PRIVATE_API_KEY")
#BESTTIME_PUBLIC_API_KEY = os.getenv("BESTTIME_PUBLIC_API_KEY")
BESTTIME_PRIVATE_API_KEY = "pri_046ab094408c427198c1a17edacbd14e"
BESTTIME_PUBLIC_API_KEY = "pub_9549cd2c7eeb430ca283b5c65ca4a512"
CSV_FILE_PATH = "test_areas.csv" # Replace with your CSV file path
OUTPUT_FILE_PATH = "footfall_analysis_output.csv" # Output file name


# SUPABASE_URL = os.getenv("SUPABASE_URL")
# SUPABASE_KEY = os.getenv("SUPABASE_KEY")
# opts = ClientOptions().replace(schema="public")
# supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY,options=opts)

# print("connected to DB")

VENUE_TYPES = [
    "ARTS",
    "APPAREL",
    "CAFE",
    "CLUBS",
    "DOCTOR",
    "RESTAURANT",
    "SHOPPING",
    "PERSONAL_CARE",
    "SCHOOL",
    "VEHICLE"
]


VENUE_FILTER_URL = "https://besttime.app/api/v1/venues/filter"
QUERY_WEEK_RAW_URL = "https://besttime.app/api/v1/forecasts/week/raw2" # Use raw2 for data split by day

REQUEST_DELAY_SECONDS = 0.5 # Delay between API calls to avoid rate limits

def get_top_venues(lat_min, lng_min, lat_max, lng_max, venue_type):
    """Calls Venue Filter API to get top 3 venues for a type in a bounding box."""
    params = {
        'api_key_private': BESTTIME_PRIVATE_API_KEY,
        'lat_min': lat_min,
        'lng_min': lng_min,
        'lat_max': lat_max,
        'lng_max': lng_max,
        'types': venue_type,
        'limit': 3,
        'order_by': 'day_mean', # or 'day_max'
        'order': 'desc',
        'own_venues_only': False # Search the entire BestTime database
    }
    try:
        time.sleep(REQUEST_DELAY_SECONDS) # Rate limiting delay
        response = requests.get(VENUE_FILTER_URL, params=params, timeout=30)
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
        data = response.json()
        if data.get("status") == "OK" and data.get("venues"):
            # Return venue_id, name, and address for context
            return [{"id": v.get("venue_id"), "name": v.get("venue_name"), "address": v.get("venue_address")}
                    for v in data["venues"]]
        elif data.get("status") != "OK":
             print(f"  WARN: Venue Filter API Error for {venue_type}: {data.get('message', 'Unknown API error')}")
             return []
        else:
            # print(f"  INFO: No venues found for type {venue_type} in this area.")
            return []
    except requests.exceptions.Timeout:
        print(f"  ERROR: Timeout calling Venue Filter API for {venue_type}")
        return []
    except requests.exceptions.RequestException as e:
        print(f"  ERROR: Venue Filter API request failed for {venue_type}: {e}")
        return []
    except Exception as e:
        print(f"  ERROR: Unexpected error in get_top_venues for {venue_type}: {e}")
        return []


def get_weekly_footfall(venue_id):
    """Calls Query Week Raw API to get hourly data for all 7 days."""
    if not venue_id:
        return None
    params = {
        'api_key_public': BESTTIME_PUBLIC_API_KEY,
        'venue_id': venue_id
    }
    try:
        time.sleep(REQUEST_DELAY_SECONDS) # Rate limiting delay
        response = requests.get(QUERY_WEEK_RAW_URL, params=params, timeout=20)
        response.raise_for_status()
        data = response.json()
        if data.get("status") == "OK" and data.get("analysis", {}).get("week_raw"):
            return data["analysis"]["week_raw"] # List of 7 day objects
        elif data.get("status") != "OK":
             print(f"    WARN: Query Week Raw API Error for {venue_id}: {data.get('message', 'Unknown API error')}")
             return None
        else:
            # print(f"    INFO: No weekly data found for venue {venue_id}.")
            return None
    except requests.exceptions.Timeout:
        print(f"    ERROR: Timeout calling Query Week Raw API for {venue_id}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"    ERROR: Query Week Raw API request failed for {venue_id}: {e}")
        return None
    except Exception as e:
        print(f"    ERROR: Unexpected error in get_weekly_footfall for {venue_id}: {e}")
        return None

def calculate_averages(weekly_data):
    """Calculates average weekday and weekend footfall from raw weekly data."""
    if not weekly_data:
        return None, None

    weekday_hours = []
    weekend_hours = []

    for day_data in weekly_data:
        day_int = day_data.get("day_int")
        day_raw = day_data.get("day_raw", [])

        if day_int is None:
            continue

        # day_int: 0=Mon, 1=Tue, 2=Wed, 3=Thu, 4=Fri, 5=Sat, 6=Sun
        if 0 <= day_int <= 4: # Weekday
            weekday_hours.extend(day_raw)
        elif 5 <= day_int <= 6: # Weekend
            weekend_hours.extend(day_raw)

    # Calculate averages, handle cases with no data
    weekday_avg = statistics.mean(weekday_hours) if weekday_hours else 0
    weekend_avg = statistics.mean(weekend_hours) if weekend_hours else 0

    return round(weekday_avg, 2), round(weekend_avg, 2)

# --- Main Processing Logic ---

results = []
print(f"Starting processing for {CSV_FILE_PATH}...")

try:
    with open(CSV_FILE_PATH, mode='r', encoding='utf-8') as infile:
        reader = csv.DictReader(infile)
        rownum = 0
        for row in reader:
            rownum += 1
            subzone = row.get('subzone', f'Row_{rownum}') # Use subzone or row number as identifier
            print(f"\nProcessing Row {rownum} (Subzone: {subzone})...")

            try:
                lat_min = float(row['min_latitude'])
                lng_min = float(row['min_longitude'])
                lat_max = float(row['max_latitude'])
                lng_max = float(row['max_longitude'])
            except (KeyError, ValueError) as e:
                print(f"  ERROR: Invalid coordinate data in row {rownum}: {e}. Skipping row.")
                continue

            for venue_type in VENUE_TYPES:
                print(f"  Querying for type: {venue_type}...")
                top_venues = get_top_venues(lat_min, lng_min, lat_max, lng_max, venue_type)

                if not top_venues:
                    print(f"    No top venues found for {venue_type}.")
                    # Optionally add a row indicating no venues found
                    results.append({
                        'subzone': subzone,
                        'planning_area': row.get('planning_area', ''),
                        'region': row.get('region', ''),
                        'venue_type': venue_type,
                        'rank': '0',
                        'venue_name': 'No venues found',
                        'venue_address': '',
                        'venue_id': '',
                        'avg_weekday_footfall': 0,
                        'avg_weekend_footfall': 0
                    })
                    continue
                #print("Top venues: ", top_venues)
                for rank, venue_info in enumerate(top_venues, 1):
                    venue_id = venue_info.get("id")
                    venue_name = venue_info.get("name", "N/A")
                    venue_address = venue_info.get("address", "N/A")
                    print(f"    Rank {rank}: {venue_name} ({venue_id})")

                    weekly_data = get_weekly_footfall(venue_id)

                    #print("weekly_data: ", weekly_data)

                    weekday_avg, weekend_avg = calculate_averages(weekly_data)

                    if weekday_avg is None:
                         print(f"      Could not calculate averages for {venue_name}")
                         weekday_avg, weekend_avg = 0, 0 # Default to 0 if calculation fails

                    results.append({
                        'subzone': subzone,
                        'planning_area': row.get('planning_area', ''),
                        'region': row.get('region', ''),
                        'venue_type': venue_type,
                        'rank': rank,
                        'venue_name': venue_name,
                        'venue_address': venue_address,
                        'venue_id': venue_id if venue_id else '',
                        'avg_weekday_footfall': weekday_avg,
                        'avg_weekend_footfall': weekend_avg
                    })

                    #print(results)

except FileNotFoundError:
    print(f"ERROR: CSV file not found at {CSV_FILE_PATH}")
    exit()
except Exception as e:
    print(f"An unexpected error occurred during CSV processing: {e}")

# --- Write Results to CSV ---
if results:
    print(f"\nWriting {len(results)} results to {OUTPUT_FILE_PATH}...")
    try:
        with open(OUTPUT_FILE_PATH, mode='w', newline='', encoding='utf-8') as outfile:
            fieldnames = results[0].keys()
            writer = csv.DictWriter(outfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)
        print("Processing complete. Output saved.")
    except Exception as e:
        print(f"Error writing output CSV: {e}")
else:
    print("No results generated to write.")