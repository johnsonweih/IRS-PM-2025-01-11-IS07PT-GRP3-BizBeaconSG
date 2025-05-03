import os
from dotenv import load_dotenv
from supabase import create_client, Client
from neo4j import GraphDatabase
from tqdm import tqdm  # progress bars

print("🔍 Starting node_update.py")
# update competitor count into neo4j

load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))

def fetch_competitor_counts():
    all_data = []
    page_size = 1000
    for start in range(0, 4000, page_size):
        end = start + page_size - 1
        response = supabase.table("competitor_stats") \
            .select("subzone, venue_type, competitor_count") \
            .range(start, end) \
            .execute()
        all_data.extend(response.data)

    print(f"✅ Total records fetched: {len(all_data)}")
    return all_data

def update_neo4j_competitor_stats(data):
    updated = 0
    skipped = 0

    with neo4j_driver.session() as session:
        for row in data:
            subzone = row.get("subzone", "").strip()
            venue_type = row.get("venue_type", "").strip()
            raw_count = row.get("competitor_count")

            if not subzone or not venue_type:
                print(f"{skipped}: skipping")
                continue

            # Ensure count is a valid integer (default to 0)
            count = int(raw_count) if raw_count is not None else 0

            # Only update if competitor_count is NOT already set
            result = session.run("""
                MATCH (cs:CompetitorStats)
                WHERE cs.subzone = $subzone AND cs.venue_type = $venue_type AND NOT EXISTS(cs.competitor_count)
                SET cs.competitor_count = $count
                RETURN cs
            """, {
                "subzone": subzone,
                "venue_type": venue_type,
                "count": count
            })

            if result.peek():
                updated += 1
                print(f"{updated}: Set {count} for {subzone} / {venue_type}")
            else:
                skipped += 1

    print(f"✅ {updated} nodes updated, {skipped} skipped (already had competitor_count)")

def fetch_venue_coords():
    all_data = []
    page_size = 1000
    for start in range(0, 8000, page_size):
        end = start + page_size - 1
        response = supabase.table("establishments") \
            .select("venue_name, latitude, longitude, venue_type") \
            .range(start, end) \
            .execute()
        all_data.extend(response.data)

    print(f"✅ Total records fetched: {len(all_data)}")

    # Clean and filter
    coords = {}
    for row in all_data:
        name = row.get("venue_name")
        lat = row.get("latitude")
        lon = row.get("longitude")
        venue_type = row.get("venue_type")

        if name and lat is not None and lon is not None:
            coords[name.strip()] = (lat, lon, venue_type)

    print(f"📍 Records with valid lat/lon: {len(coords)}")
    return coords

def update_lat_lon_in_neo4j(venue_coords):
    with driver.session() as session:
        updated = 0
        for name, (lat, lon, venue_type) in venue_coords.items():
            result = session.run("""
                MATCH (c:Competitor {venue_name: $name})
                SET c.latitude = $lat, c.longitude = $lon, c.venue_type = $venue_type
                RETURN c
            """, name=name, lat=lat, lon=lon, venue_type=venue_type)
            if result.peek():
                updated += 1
            print(f"{updated}: {name} with long,lat and vtype")
        print(f"✅ Updated {updated} Competitor nodes in Neo4j.")


# --- Main Execution
if __name__ == "__main__":
    venue_coords = fetch_venue_coords()
    update_lat_lon_in_neo4j(venue_coords)

    stats = fetch_competitor_counts()
    update_neo4j_competitor_stats(stats)