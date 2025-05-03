import os
from dotenv import load_dotenv
from supabase import create_client, Client
from neo4j import GraphDatabase
from tqdm import tqdm
import numpy as np

# Load environment variables
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Neo4j config
NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

# Initialize clients
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
neo4j_driver = GraphDatabase.driver(
    NEO4J_URI,
    auth=(NEO4J_USERNAME, NEO4J_PASSWORD)
)

# Pagination constants
_PAGE_SIZE = 1000

def fetch_table_all(table_name: str, columns: str = "*"):
    """Fetch all rows from a Supabase table using range-based pagination."""
    all_data = []
    start = 0
    while True:
        # Use an exclusive upper bound so we get exactly _PAGE_SIZE rows
        upper = start + _PAGE_SIZE
        resp = (supabase
                .table(table_name)
                .select(columns)
                .range(start, upper)
                .execute())
        if getattr(resp, 'error', None):
            print(f"Error fetching {table_name} [{start}:{upper}]: {resp.error}")
            break
        batch = resp.data or []
        all_data.extend(batch)
        # Stop when fewer than a full page is returned
        if len(batch) < _PAGE_SIZE:
            break
        start += _PAGE_SIZE
    return all_data

# Neo4j update function
def update_neo4j_density(tx, subzone: str, venue_type: str, density: str):
    """Set the density property on a CompetitorStats node."""
    tx.run(
        "MATCH (n:CompetitorStats {subzone: $subzone, venue_type: $venue_type})"
        " SET n.density = $density",
        subzone=subzone,
        venue_type=venue_type,
        density=density
    )


def main():
    # 1) Fetch demographics
    demographics = fetch_table_all(
        "demographics_population", "subzone, subzone_size"
    )
    print(f"Fetched {len(demographics)} demographics records.")
    size_map = {d["subzone"]: float(d.get("subzone_size", 0)) for d in demographics}

    # 2) Fetch all competitor_stats
    comp_stats = fetch_table_all(
        "competitor_stats",
        "subzone, planning_area, venue_type, competitor_count"
    )
    print(f"Fetched {len(comp_stats)} competitor_stats records.")

    # 3) Compute valid ratios
    ratios = []
    for r in comp_stats:
        cnt = r.get("competitor_count")
        size = size_map.get(r.get("subzone"), 0)
        if isinstance(cnt, (int, float)) and size > 0:
            ratios.append(cnt / size)
    print(f"Computed {len(ratios)} valid ratios.")
    if not ratios:
        print("No valid ratios to process. Ensure competitor_count and subzone_size are populated.")
        return

    # 4) Calculate thresholds via percentiles
    # compute 20th, 40th, 60th, 80th percentiles
    thresholds = list(np.percentile(ratios, [20, 40, 60, 80]))
    levels = ["extremely low", "low", "medium", "high", "extremely high"]
    print("Density percentiles:")
    for i, perc in enumerate([20, 40, 60, 80]):
        print(f"  {perc}th percentile = {thresholds[i]:.6f}: {levels[i]}")
    print(f"  > 80th percentile: {levels[4]}")

    # 5) Update each record in Supabase and then Neo4j each record in Supabase and then Neo4j
    sup_errors = 0
    neo_errors = 0
    for r in tqdm(comp_stats, desc="Updating records", total=len(comp_stats)):
        sub = r.get("subzone")
        cnt = r.get("competitor_count")
        size = size_map.get(sub, 0)

        if isinstance(cnt, (int, float)) and size > 0:
            ratio = cnt / size
            if ratio <= thresholds[0]: density = levels[0]
            elif ratio <= thresholds[1]: density = levels[1]
            elif ratio <= thresholds[2]: density = levels[2]
            elif ratio <= thresholds[3]: density = levels[3]
            else: density = levels[4]
        else:
            density = "unknown"

        # 5a) Update Supabase
        upd = (supabase
               .table("competitor_stats")
               .update({"competitor_density": density})
               .eq("subzone", sub)
               .eq("planning_area", r.get("planning_area"))
               .eq("venue_type", r.get("venue_type"))
               .execute())
        if getattr(upd, 'error', None):
            sup_errors += 1
            continue

        # 5b) Update Neo4j only after Supabase success
        try:
            with neo4j_driver.session() as session:
                session.execute_write(
                    update_neo4j_density,
                    sub,
                    r.get("venue_type"),
                    density
                )
        except Exception as e:
            neo_errors += 1
            print(f"Neo4j error for {sub}-{r.get('venue_type')}: {e}")

    print(f"Finished updates. Supabase errors: {sup_errors}, Neo4j errors: {neo_errors}")


if __name__ == "__main__":
    try:
        main()
    finally:
        neo4j_driver.close()
