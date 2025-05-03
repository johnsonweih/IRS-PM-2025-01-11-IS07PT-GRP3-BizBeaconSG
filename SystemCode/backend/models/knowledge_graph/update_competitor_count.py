import os
from dotenv import load_dotenv
from supabase import create_client
from neo4j import GraphDatabase

# --- Load environment
load_dotenv()

# --- Connect to Supabase
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
print("✅ Connected to Supabase")

# --- Connect to Neo4j
neo4j_driver = GraphDatabase.driver(
    os.getenv("NEO4J_URI"),
    auth=(os.getenv("NEO4J_USERNAME"), os.getenv("NEO4J_PASSWORD"))
)
print("✅ Connected to Neo4j")

# --- Step 1: Fetch competitor stats from Supabase
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

# --- Step 2: Update Neo4j nodes
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
# --- Run the pipeline
if __name__ == "__main__":
    stats = fetch_competitor_counts()
    update_neo4j_competitor_stats(stats)