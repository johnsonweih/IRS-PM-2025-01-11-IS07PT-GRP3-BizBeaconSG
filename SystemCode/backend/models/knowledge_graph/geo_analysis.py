from neo4j import GraphDatabase
import pandas as pd
import os
from dotenv import load_dotenv
import folium
from supabase import create_client, Client  # NEW: supabase import

# Load credentials
load_dotenv()
driver = GraphDatabase.driver(
    os.getenv("NEO4J_URI"),
    auth=(os.getenv("NEO4J_USERNAME"), os.getenv("NEO4J_PASSWORD"))
)
print("✅ Connected to Neo4j")

# ─── NEW: Initialize Supabase client ──────────────────────────────────────────
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Step 1: Fetch all competitor venues with lat/lon and type
def fetch_venues():
    with driver.session() as session:
        result = session.run("""
            MATCH (c:Competitor)-[:LOCATED_IN]->(pa:PlanningArea)
            RETURN c.venue_name AS name, c.venue_type AS type,
                   c.latitude AS lat, c.longitude AS lon,
                   pa.subzone AS subzone
        """)
        return pd.DataFrame([dict(r) for r in result])

df = fetch_venues()
print("📊 Sample Venues:")
print(df.head())
print("-----------------------------------------------")

# Count venue types per subzone
venue_counts = df.groupby(['subzone', 'type']).size().reset_index(name='venue_count')
print("🏙️ Top Subzones by Venue Count:")
print(venue_counts.sort_values(by='venue_count', ascending=False).head(10))
print("-----------------------------------------------")

# Step 2: Base map with all venues
m = folium.Map(location=[1.3521, 103.8198], zoom_start=12)

for _, row in df.iterrows():
    if row['lat'] and row['lon'] and row['type']:
        folium.CircleMarker(
            location=[float(row['lat']), float(row['lon'])],
            radius=3,
            popup=f"{row['name']} ({row['type']}) in {row['subzone']}",
            color='blue',
            fill=True
        ).add_to(m)

# Step 3: Fetch population stats
def fetch_population_stats():
    with driver.session() as session:
        result = session.run("""
            MATCH (pop:PopulationStats)
            RETURN pop.subzone AS subzone,
                   toFloat(pop.population_density) AS density,
                   toFloat(pop.subzone_size) AS size
        """)
        return pd.DataFrame([dict(r) for r in result])

# Step 4: Fetch competitor stats
def fetch_competitor_stats():
    with driver.session() as session:
        result = session.run("""
            MATCH (cs:CompetitorStats)
            RETURN cs.subzone AS subzone,
                   cs.venue_type AS type,
                   toInteger(cs.competitor_count) AS count
        """)
        return pd.DataFrame([dict(r) for r in result])

# Step 5: Update Neo4j with underserved_score
def update_underserved_scores(data):
    updated = 0
    with driver.session() as session:
        for _, row in data.iterrows():
            subzone = row['subzone']
            venue_type = row['type']
            underserved_score = round(row['underserved_score'], 2)

            session.run("""
                MATCH (cs:CompetitorStats)
                WHERE cs.subzone = $subzone AND cs.venue_type = $venue_type
                      AND (cs.underserved_score IS NULL OR cs.underserved_score = 0)
                SET cs.underserved_score = $underserved_score
            """, {
                "subzone": subzone,
                "venue_type": venue_type,
                "underserved_score": underserved_score
            })

            updated += 1

    print(f"✅ Updated underserved_score for {updated} CompetitorStats nodes")

# ---------------- MAIN FLOW ----------------
pop_df = fetch_population_stats()
comp_stats_df = fetch_competitor_stats()

print("📊 Sample Population Stats:")
print(pop_df.head())
print("-----------------------------------------------")
print("📊 Sample Competitor Stats:")
print(comp_stats_df.head())
print("-----------------------------------------------")

# Step 6: Merge and compute underserved score
merged = comp_stats_df.merge(pop_df, on='subzone', how='left')
merged['competitor_count'] = merged['count'].fillna(0)
merged['underserved_score'] = merged['density'] / (merged['competitor_count'] + 1)

# Step 7: Normalize underserved_score to 0–100 ────────────────────────────────
min_score = merged['underserved_score'].min()
max_score = merged['underserved_score'].max()
merged['underserved_score'] = (
    (merged['underserved_score'] - min_score)
    / (max_score - min_score)
    * 100
)

# Step 8: Show top underserved subzone/type combos
underserved = merged.sort_values(by='underserved_score', ascending=False)
print("🔍 Top Underserved Venue Types by Subzone:")
print(underserved[['subzone', 'type', 'density', 'competitor_count', 'underserved_score']].head(10))

# Step 9: Update Supabase competitor_stats table ──────────────────────────────
def update_supabase_scores(data):
    updated = 0

    for idx, row in data.iterrows():
        subzone = row['subzone']
        venue_type = row['type']
        underserved_score = row.get('underserved_score', None)

        # Skip rows with missing bits
        if pd.isna(subzone) or pd.isna(venue_type) or underserved_score is None:
            print(f"⏭️ Skipping row {idx}: subzone={subzone}, type={venue_type}, underserved_score={underserved_score}")
            continue

        # Build a strictly Python-native dict
        payload = { "underserved_score": float(round(underserved_score, 2)) }
        match_filter = {
            "subzone": str(subzone),
            "venue_type": str(venue_type)
        }

        # Debug print
        # print(f"🔄 Row {idx} → match={match_filter}, payload={payload}")

        try:
            res = (
                supabase
                .table("competitor_stats")
                .update(payload)
                .match(match_filter)
                .execute()
            )
        except Exception as e:
            print(f"❌ Exception for row {idx}: {e}")
            continue

        # Supabase-py returns a `.error` field if something went wrong
        if hasattr(res, 'error') and res.error:
            print(f"❌ Supabase error for row {idx}: {res.error}")
        else:
            updated += 1

    print(f"✅ Updated {updated} rows in Supabase")

update_supabase_scores(merged)

# Update Neo4j with new underserved scores
update_underserved_scores(merged)

# Save results
underserved.to_csv("outputs/underserved_by_density.csv", index=False)
print("📁 Saved CSV: outputs/underserved_by_density.csv")

# Highlight top underserved venues on map
top_underserved = underserved.head(10)
for _, row in top_underserved.iterrows():
    venues_in_zone = df[(df['subzone'] == row['subzone']) & (df['type'] == row['type'])]
    for _, venue in venues_in_zone.iterrows():
        if venue['lat'] and venue['lon']:
            folium.CircleMarker(
                location=[float(venue['lat']), float(venue['lon'])],
                radius=6,
                popup=f"UNDERSERVED: {venue['name']} ({venue['type']}) in {venue['subzone']}",
                color='red',
                fill=True,
                fill_opacity=0.9
            ).add_to(m)



# Final map output
m.save("outputs/sg_venue_map.html")
print("🗺️ Map saved: outputs/sg_venue_map.html")