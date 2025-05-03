import os
from dotenv import load_dotenv
from supabase import create_client, Client
from neo4j import GraphDatabase
from tqdm import tqdm  # progress bars

print("🔍 Starting graph_builder_updated.py")

# ─── Helper: fetch all records with pagination ─────────────────────────────────
def fetch_all_records(supabase: Client, table_name: str, page_size: int = 1000):
    print(f"   ↳ Fetching all from {table_name}…")
    records = []
    offset = 0
    while True:
        batch = supabase.table(table_name) \
                        .select("*") \
                        .range(offset, offset + page_size - 1) \
                        .execute().data
        if not batch:
            break
        records.extend(batch)
        offset += page_size
    print(f"     • Retrieved {len(records)} rows from {table_name}")
    return records

# ─── Step 1: Fetch data from Supabase ─────────────────────────────────────────
def fetch_supabase_data():
    print("➡️  Enter fetch_supabase_data()")
    load_dotenv()
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    print(f"   • SUPABASE_URL loaded: {'YES' if supabase_url else 'NO'}")
    supabase: Client = create_client(supabase_url, supabase_key)

    # ─── One‐shot fetches with logging ───────────────────────────────
    planning_areas = supabase.table("planning_areas") \
                             .select("*") \
                             .execute().data
    print(f"   ↳ Retrieved {len(planning_areas)} rows from planning_areas")

    venue_types = supabase.table("venue_types") \
                          .select("*") \
                          .execute().data
    print(f"   ↳ Retrieved {len(venue_types)} rows from venue_types")

    demographics_age = supabase.table("demographics_age_group") \
                               .select("*") \
                               .execute().data
    print(f"   ↳ Retrieved {len(demographics_age)} rows from demographics_age_group")

    demographics_housing = supabase.table("demographics_housing_types") \
                                   .select("*") \
                                   .execute().data
    print(f"   ↳ Retrieved {len(demographics_housing)} rows from demographics_housing_types")

    demographics_pop = supabase.table("demographics_population") \
                               .select("*") \
                               .execute().data
    print(f"   ↳ Retrieved {len(demographics_pop)} rows from demographics_population")

    avg_industrial_prices = supabase.table("avg_industrial_prices") \
                                     .select("*") \
                                     .execute().data
    print(f"   ↳ Retrieved {len(avg_industrial_prices)} rows from avg_industrial_prices")

    # ─── Paginated fetches (already logged inside helper) ───────────
    competitor_data  = fetch_all_records(supabase, "establishments")
    competitor_stats = fetch_all_records(supabase, "competitor_stats")
    industrial_props = fetch_all_records(supabase, "industrial_properties")

    # ─── Complete summary ────────────────────────────────────────────
    print(
        "   • Fetched summary:\n"
        f"     {len(planning_areas)} planning areas\n"
        f"     {len(venue_types)} venue types\n"
        f"     {len(competitor_data)} competitor records\n"
        f"     {len(competitor_stats)} competitor stats records\n"
        f"     {len(demographics_age)} age demographics records\n"
        f"     {len(demographics_housing)} housing demographics records\n"
        f"     {len(demographics_pop)} population demographics records\n"
        f"     {len(industrial_props)} industrial properties\n"
        f"     {len(avg_industrial_prices)} avg industrial price records"
    )

    return (
        planning_areas, venue_types, competitor_data, competitor_stats,
        demographics_age, demographics_housing, demographics_pop,
        industrial_props, avg_industrial_prices
    )
# ─── Step 2: Clear existing graph ───────────────────────────────────────────────
def clear_graph():
    print("➡️  Enter clear_graph()")
    uri      = os.getenv("NEO4J_URI")
    user     = os.getenv("NEO4J_USERNAME")
    password = os.getenv("NEO4J_PASSWORD")
    driver = GraphDatabase.driver(uri, auth=(user, password))
    with driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n")
    driver.close()
    print("   • All nodes and relationships deleted")

# ─── Step 3: Create nodes & relationships ─────────────────────────────────────
def create_graph_nodes_and_relationships(
    planning_areas, venue_types,
    competitor_data, competitor_stats,
    demographics_age, demographics_housing, demographics_pop,
    industrial_props, avg_industrial_prices
):
    print("➡️  Enter create_graph_nodes_and_relationships()")
    uri      = os.getenv("NEO4J_URI")
    user     = os.getenv("NEO4J_USERNAME")
    password = os.getenv("NEO4J_PASSWORD")
    driver = GraphDatabase.driver(uri, auth=(user, password))

    with driver.session() as session:
        # -- PlanningArea nodes --
        for pa in tqdm(planning_areas, desc="Creating PlanningArea nodes"):
            subzone = pa.get("subzone")
            if subzone:
                norm = subzone.strip().upper()
                session.run("MERGE (pa:PlanningArea {subzone:$norm})", norm=norm)

        # -- VenueType nodes --
        for vt in tqdm(venue_types, desc="Creating VenueType nodes"):
            t = vt.get("type_name")
            if t:
                session.run("MERGE (vt:VenueType {type_name:$t})", t=t)

        # -- Competitor nodes & relationships --
        for cd in tqdm(competitor_data, desc="Creating Competitor nodes"):
            name        = cd.get("venue_name")
            subzone     = cd.get("subzone")
            venue_type  = cd.get("venue_type")
            if not name or name == "No venues found":
                continue
            norm_zone = subzone.strip().upper() if subzone else None

            # Merge competitor
            session.run(
                "MERGE (c:Competitor {venue_name:$name, subzone:$norm_zone})",
                name=name, norm_zone=norm_zone
            )
            # Competitor -> PlanningArea
            if norm_zone:
                session.run(
                    """
                    MATCH (c:Competitor {venue_name:$name, subzone:$norm_zone})
                    MATCH (pa:PlanningArea {subzone:$norm_zone})
                    MERGE (c)-[:LOCATED_IN]->(pa)
                    """,
                    name=name, norm_zone=norm_zone
                )
            # Competitor -> VenueType
            if venue_type:
                session.run(
                    """
                    MATCH (c:Competitor {venue_name:$name, subzone:$norm_zone})
                    MATCH (vt:VenueType {type_name:$vt})
                    MERGE (c)-[:OF_TYPE]->(vt)
                    """,
                    name=name, norm_zone=norm_zone, vt=venue_type
                )

        # -- CompetitorStats: one node per (subzone, venue_type) --
        for rec in tqdm(competitor_stats, desc="Creating CompetitorStats nodes"):
            subzone    = rec.get("subzone")
            venue_type = rec.get("venue_type")
            overall_score      = rec.get("overall_score")
            density    = rec.get("competitor_density")
            competitor_count      = rec.get("competitor_count")
            if not (subzone and venue_type):
                continue

            sz = subzone.strip().upper()
            # Merge stats node
            session.run(
                """
                MERGE (cs:CompetitorStats {subzone:$sz, venue_type:$vt})
                SET cs.overall_score = $overall_score,
                    cs.density  = $density,
                    cs.competitor_count  = $competitor_count,
                    cs.name  = 'Stats for ' + $sz + ' ' + $vt
                """,
                sz=sz, vt=venue_type, overall_score=overall_score, density=density, competitor_count=competitor_count
            )
            # Link to PlanningArea
            session.run(
                """
                MATCH (pa:PlanningArea {subzone:$sz})
                MATCH (cs:CompetitorStats {subzone:$sz, venue_type:$vt})
                MERGE (pa)-[:HAS_COMPETITOR_STATS]->(cs)
                """,
                sz=sz, vt=venue_type
            )
            # Link to VenueType
            session.run(
                """
                MATCH (cs:CompetitorStats {subzone:$sz, venue_type:$vt})
                MATCH (vt:VenueType {type_name:$vt})
                MERGE (cs)-[:FOR_TYPE]->(vt)
                """,
                sz=sz, vt=venue_type
            )

        # -- AgeDistribution nodes --
        for rec in tqdm(demographics_age, desc="Creating AgeDistribution nodes"):
            props = {k: ("No data available" if v == "-" else v) for k, v in rec.items()}
            subzone = props.get("subzone")
            if not subzone:
                continue
            sz = subzone.strip().upper()
            session.run(
                "MERGE (ad:AgeDistribution {subzone:$sz}) SET ad += $props, ad.name = 'Age Dist for '+$sz",
                sz=sz, props=props
            )
            session.run(
                """
                MATCH (pa:PlanningArea {subzone:$sz})
                MATCH (ad:AgeDistribution {subzone:$sz})
                MERGE (pa)-[:HAS_AGE_DISTRIBUTION]->(ad)
                """,
                sz=sz
            )

        # -- HousingProfile nodes --
        for rec in tqdm(demographics_housing, desc="Creating HousingProfile nodes"):
            props = {k: ("No data available" if v == "-" else v) for k, v in rec.items()}
            subzone = props.get("subzone")
            if not subzone:
                continue
            sz = subzone.strip().upper()
            session.run(
                "MERGE (hp:HousingProfile {subzone:$sz}) SET hp += $props, hp.name = 'Housing Prof for '+$sz",
                sz=sz, props=props
            )
            session.run(
                """
                MATCH (pa:PlanningArea {subzone:$sz})
                MATCH (hp:HousingProfile {subzone:$sz})
                MERGE (pa)-[:HAS_HOUSING_PROFILE]->(hp)
                """,
                sz=sz
            )

        # -- PopulationStats nodes --
        for rec in tqdm(demographics_pop, desc="Creating PopulationStats nodes"):
            props = {k: ("No data available" if v == "-" else v) for k, v in rec.items()}
            subzone = props.get("subzone")
            if not subzone:
                continue
            sz = subzone.strip().upper()
            session.run(
                "MERGE (ps:PopulationStats {subzone:$sz}) SET ps += $props, ps.name = 'Pop Stats for '+$sz",
                sz=sz, props=props
            )
            session.run(
                """
                MATCH (pa:PlanningArea {subzone:$sz})
                MATCH (ps:PopulationStats {subzone:$sz})
                MERGE (pa)-[:HAS_POPULATION_STATS]->(ps)
                """,
                sz=sz
            )

        # -- IndustrialProperty & PropertiesAvailable nodes --
        FILTERED = ["dormitory", "showroom", "office_grade_a", "generic_office", "factory", "warehouse"]
        for rec in tqdm(industrial_props, desc="Creating IndustrialProperty nodes"):
            subcat = rec.get("sub_category")
            if subcat in FILTERED:
                continue
            subzone = rec.get("subzone")
            if not subzone:
                continue
            sz = subzone.strip().upper()
            # Merge PropertiesAvailable
            session.run("MERGE (pa:PropertiesAvailable {subzone:$sz})", sz=sz)
            session.run(
                """
                MATCH (pl:PlanningArea {subzone:$sz})
                MATCH (pa:PropertiesAvailable {subzone:$sz})
                MERGE (pl)-[:OFFERS_PROPERTIES]->(pa)
                """,
                sz=sz
            )
            # Create IndustrialProperty
            props = {
                "property_id": rec.get("property_id"),
                "listing_id":  rec.get("listing_id"),
                "listing_url": rec.get("listing_url"),
                "price":       rec.get("price"),
                "description": rec.get("description"),
                "sub_category": subcat,
                "status":      rec.get("status"),
                "area_size":   rec.get("area_size"),
                "listing_type": rec.get("listing_type")
            }
            session.run("CREATE (ip:IndustrialProperty $props)", props=props)
            session.run(
                """
                MATCH (pa:PropertiesAvailable {subzone:$sz})
                MATCH (ip:IndustrialProperty {property_id:$pid})
                MERGE (pa)-[:HAS_PROPERTY]->(ip)
                """,
                sz=sz, pid=rec.get("property_id")
            )

        # -- Update PropertiesAvailable with average prices --
        EXCL = FILTERED
        avg_group = {}
        for rec in avg_industrial_prices:
            subcat = rec.get("sub_category")
            if subcat in EXCL:
                continue
            subzone = rec.get("subzone")
            lt = rec.get("listing_type")
            avg  = rec.get("average_price")
            if not subzone or not lt:
                continue
            sz = subzone.strip().upper()
            key = f"averagePrice_{subcat.lower().replace(' ', '_')}_{lt.lower()}"
            avg_group.setdefault(sz, {})[key] = avg

        for sz, attrs in tqdm(avg_group.items(), desc="Updating avg prices"):
            session.run(
                "MATCH (pa:PropertiesAvailable {subzone:$sz}) SET pa += $attrs",
                sz=sz, attrs=attrs
            )

    driver.close()
    print("   • Finished create_graph_nodes_and_relationships()")

# ─── Step 4: Validate graph ─────────────────────────────────────────────────────
def validate_graph(planning_areas, venue_types, competitor_data, competitor_stats,
                   demographics_age_group, demographics_housing_types, demographics_population,
                   industrial_properties, avg_industrial_prices):
    """
    Validate that every node and relationship in the Neo4j graph corresponds
    to the data fetched from Supabase.

    Validations performed:
      1. PlanningArea nodes exist.
      2. VenueType nodes exist.
      3. Competitor nodes exist and are linked to their PlanningArea and VenueType.
      4. AgeDistribution, HousingProfile, and PopulationStats nodes exist and are linked.
      5. CompetitorStats nodes exist and are linked to PlanningArea.
      6. IndustrialProperty nodes exist and are linked through PropertiesAvailable.
      7. PropertiesAvailable nodes are linked to PlanningArea.
      8. PropertiesAvailable nodes have the correct averagePrice_* attributes.
    """
    uri      = os.getenv("NEO4J_URI")
    user     = os.getenv("NEO4J_USERNAME")
    password = os.getenv("NEO4J_PASSWORD")
    driver = GraphDatabase.driver(uri, auth=(user, password))
    with driver.session() as session:
        # 1. Validate PlanningArea nodes
        for pa in tqdm(planning_areas, desc="Validating PlanningArea"):
            subzone = pa.get("subzone")
            if not subzone:
                continue
            norm = subzone.strip().upper()
            result = session.run(
                "MATCH (p:PlanningArea {subzone: $subzone}) RETURN p",
                subzone=norm
            )
            if not result.single():
                tqdm.write(f"[ERROR] Missing PlanningArea node for '{norm}'")

        # 2. Validate VenueType nodes
        for vt in tqdm(venue_types, desc="Validating VenueType"):
            tname = vt.get("type_name")
            if not tname:
                continue
            result = session.run(
                "MATCH (v:VenueType {type_name: $name}) RETURN v",
                name=tname
            )
            if not result.single():
                tqdm.write(f"[ERROR] Missing VenueType node for '{tname}'")

        # 3. Validate Competitor nodes and relationships
        for cd in tqdm(competitor_data, desc="Validating Competitor"):
            vname = cd.get("venue_name")
            subzone = cd.get("subzone")
            vtype = cd.get("venue_type")
            if not vname or vname == "No venues found":
                continue
            norm = subzone.strip().upper() if subzone else None

            # Competitor itself
            comp = session.run(
                "MATCH (c:Competitor {venue_name: $v, subzone: $sz}) RETURN c",
                v=vname, sz=norm
            )
            if not comp.single():
                tqdm.write(f"[ERROR] Missing Competitor '{vname}' in '{norm}'")
                continue

            # LOCATED_IN relationship
            loc = session.run(
                """
                MATCH (c:Competitor {venue_name: $v, subzone: $sz})-[:LOCATED_IN]->(p:PlanningArea {subzone: $sz})
                RETURN c
                """, v=vname, sz=norm
            )
            if not loc.single():
                tqdm.write(f"[ERROR] Competitor '{vname}' not linked to PlanningArea '{norm}'")

            # OF_TYPE relationship
            if vtype:
                typ = session.run(
                    """
                    MATCH (c:Competitor {venue_name: $v, subzone: $sz})-[:OF_TYPE]->(vt:VenueType {type_name: $t})
                    RETURN c
                    """, v=vname, sz=norm, t=vtype
                )
                if not typ.single():
                    tqdm.write(f"[ERROR] Competitor '{vname}' not linked to VenueType '{vtype}'")

        # 4. Validate demographic nodes and relationships
        # AgeDistribution
        for rec in tqdm(demographics_age_group, desc="Validating AgeDistribution"):
            sz = rec.get("subzone")
            if not sz:
                continue
            norm = sz.strip().upper()
            res = session.run(
                """
                MATCH (p:PlanningArea {subzone: $sz})-[:HAS_AGE_DISTRIBUTION]->(ad:AgeDistribution {subzone: $sz})
                RETURN ad
                """, sz=norm
            )
            if not res.single():
                tqdm.write(f"[ERROR] Missing AgeDistribution for '{norm}'")

        # HousingProfile
        for rec in tqdm(demographics_housing_types, desc="Validating HousingProfile"):
            sz = rec.get("subzone")
            if not sz:
                continue
            norm = sz.strip().upper()
            res = session.run(
                """
                MATCH (p:PlanningArea {subzone: $sz})-[:HAS_HOUSING_PROFILE]->(hp:HousingProfile {subzone: $sz})
                RETURN hp
                """, sz=norm
            )
            if not res.single():
                tqdm.write(f"[ERROR] Missing HousingProfile for '{norm}'")

        # PopulationStats
        for rec in tqdm(demographics_population, desc="Validating PopulationStats"):
            sz = rec.get("subzone")
            if not sz:
                continue
            norm = sz.strip().upper()
            res = session.run(
                """
                MATCH (p:PlanningArea {subzone: $sz})-[:HAS_POPULATION_STATS]->(ps:PopulationStats {subzone: $sz})
                RETURN ps
                """, sz=norm
            )
            if not res.single():
                tqdm.write(f"[ERROR] Missing PopulationStats for '{norm}'")

        # 5. Validate CompetitorStats nodes are linked from PlanningArea
        seen = set()
        for rec in competitor_stats:
            sz = rec.get("subzone")
            vt = rec.get("venue_type")
            if sz and vt:
                seen.add((sz.strip().upper(), vt))
        for sz, vt in tqdm(seen, desc="Validating CompetitorStats links"):
            res = session.run(
                """
                MATCH (pa:PlanningArea {subzone: $sz})
                      -[:HAS_COMPETITOR_STATS]->
                      (cs:CompetitorStats {subzone: $sz, venue_type: $vt})
                RETURN cs
                """,
                sz=sz, vt=vt
            )
            if not res.single():
                tqdm.write(f"[ERROR] Missing HAS_COMPETITOR_STATS for '{sz}' / '{vt}'")

        # 6. Validate IndustrialProperty and PropertiesAvailable
        FILTERED = {"dormitory", "showroom", "office_grade_a", "generic_office", "factory", "warehouse"}
        unique_subzones = set()

        for rec in tqdm(industrial_properties, desc="Validating IndustrialProperty"):
            sub = rec.get("sub_category")
            if sub in FILTERED:
                continue
            sz = rec.get("subzone")
            pid = rec.get("property_id")
            if not sz or not pid:
                continue
            norm = sz.strip().upper()
            unique_subzones.add(norm)

            # IndustrialProperty node
            ip = session.run(
                "MATCH (ip:IndustrialProperty {property_id: $pid}) RETURN ip",
                pid=pid
            )
            if not ip.single():
                tqdm.write(f"[ERROR] Missing IndustrialProperty '{pid}' in '{norm}'")
                continue

            # HAS_PROPERTY relationship
            link = session.run(
                """
                MATCH (pa:PropertiesAvailable {subzone: $sz})-[:HAS_PROPERTY]->(ip:IndustrialProperty {property_id: $pid})
                RETURN ip
                """, sz=norm, pid=pid
            )
            if not link.single():
                tqdm.write(f"[ERROR] IndustrialProperty '{pid}' not linked under PropertiesAvailable '{norm}'")

        # OFFERS_PROPERTIES relationship
        for norm in tqdm(unique_subzones, desc="Validating PropertiesAvailable→PlanningArea"):
            rel = session.run(
                """
                MATCH (pl:PlanningArea {subzone: $sz})-[:OFFERS_PROPERTIES]->(pa:PropertiesAvailable {subzone: $sz})
                RETURN pa
                """, sz=norm
            )
            if not rel.single():
                tqdm.write(f"[ERROR] PropertiesAvailable '{norm}' not offered by PlanningArea")

        # 7. Validate averagePrice_* attributes
        EXCL = {"dormitory", "showroom", "office_grade_a", "generic_office", "factory", "warehouse"}
        price_map = {}
        for rec in avg_industrial_prices:
            sub = rec.get("sub_category")
            if sub in EXCL:
                continue
            sz = rec.get("subzone")
            lt = rec.get("listing_type")
            avg = rec.get("average_price")
            if not sz or not lt:
                continue
            norm = sz.strip().upper()
            key = f"averagePrice_{sub.lower().replace(' ', '_')}_{lt.lower()}"
            price_map.setdefault(norm, {})[key] = avg

        for norm, attrs in tqdm(price_map.items(), desc="Validating averagePrice attributes"):
            node = session.run(
                "MATCH (pa:PropertiesAvailable {subzone: $sz}) RETURN pa",
                sz=norm
            ).single()
            if not node:
                tqdm.write(f"[ERROR] Missing PropertiesAvailable node for '{norm}'")
                continue
            pavail = node["pa"]
            for attr, expected in attrs.items():
                actual = pavail.get(attr)
                if str(actual) != str(expected):
                    tqdm.write(f"[ERROR] '{attr}' for '{norm}': expected {expected}, got {actual}")


        # 8. Validate CompetitorStats → VenueType links
        #    (assumes you have a relationship type—for example :TYPE_STATS—linking stats to their venue type)
        for record in tqdm(competitor_stats, desc="Validating CompetitorStats→VenueType"):
            sz = record.get("subzone")
            vt = record.get("venue_type")
            if not sz or not vt:
                continue
            norm = sz.strip().upper()

            rel = session.run(
                """
                MATCH (cs:CompetitorStats {subzone: $sz})
                    -[:FOR_TYPE]->(vt:VenueType {type_name: $vt})
                RETURN vt
                """,
                sz=norm, vt=vt
            )
            if not rel.single():
                tqdm.write(f"[ERROR] CompetitorStats for '{norm}' → VenueType '{vt}' link missing")

    driver.close()
    print("Graph validation completed successfully.")

# ─── Main entrypoint ───────────────────────────────────────────────────────────
def main():
    print("➡️  Enter main()")
    data = fetch_supabase_data()
    clear_graph()
    create_graph_nodes_and_relationships(*data)
    validate_graph(*data)
    print("✅ All done!")

if __name__ == "__main__":
    main()
