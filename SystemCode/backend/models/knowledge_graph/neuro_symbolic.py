#!/usr/bin/env python3
"""
Pipeline: Dynamic Venue Types + optional Graph Transformer + Enhanced Fuzzy Logic → upsert composite competitor scores
into Supabase’s `competitor_stats` table, per venue type and subzone.
Now supports venue-type-specific rule importance adjustments and includes an underserved_score component.
"""

import os
from dotenv import load_dotenv
from typing import Dict, List
from tqdm import tqdm
import math

# Toggle graph transformer on/off via env var
USE_GNN = os.getenv("USE_GNN", "true").lower() in ("1", "true", "yes")

import torch
import torch.nn.functional as F
from torch_geometric.data import HeteroData
from torch_geometric.nn import HGTConv
from neo4j import GraphDatabase
from supabase import create_client, Client
from postgrest.exceptions import APIError  # to catch upsert failures

# Fuzzy thresholds (tune to domain)
# FEW_COMP_THRESH    = 3.0
# MANY_COMP_THRESH   = 10.0
# POP_LOW_THRESH     = 500.0
# POP_HIGH_THRESH    = 1200.0
# SPEND_LOW_THRESH   = 100000.0
# SPEND_HIGH_THRESH  = 500000.0

torch.manual_seed(0)

# Blend factor: how much weight to give GNN vs. rule‑based
ALPHA             = 0.6

# How much of the final overall_score should come from the existing underserved_score
UNDERSERVED_RATIO = 0.35

# ——— SOFT RULES ———
# Increased weights give any non‑zero membership more “oomph”
OTHER_WEIGHTS = {
    "few_comp_high_pop":      1.0,
    "many_competitors":       2.0,
    "high_population":        1.5,
    "high_spending":          1.5,
    "underserved_high_spend": 2.5,
}

sum_other = sum(OTHER_WEIGHTS.values())  # = 8.5

SOFT_RULES = [
    {"name": "few_comp_high_pop",      "weight": OTHER_WEIGHTS["few_comp_high_pop"]},
    {"name": "many_competitors",       "weight": OTHER_WEIGHTS["many_competitors"]},
    {"name": "medium_default",         "weight": 4},          # now 50% baseline
    {"name": "high_population",        "weight": OTHER_WEIGHTS["high_population"]},
    {"name": "high_spending",          "weight": OTHER_WEIGHTS["high_spending"]},
    {"name": "underserved_high_spend", "weight": OTHER_WEIGHTS["underserved_high_spend"]},
]

# ——— VENUE‑TYPE MULTIPLIERS ———
# Bump the multipliers for the rules you care most about per venue type:
RULE_IMPORTANCE: Dict[str, Dict[str, float]] = {
    "CAFE": {
        "few_comp_high_pop":      2.0,   # small boost
        "many_competitors":       1.5,   # ↑ from 1.2
        "high_spending":          1.2,   # ↑ from 0.8
        "underserved_high_spend": 1.8,   # new boost
    },
    "RESTAURANT": {
        "many_competitors":       3.5,   # ↑ from 1.5
        "high_population":        2.0,   # ↑ from 1.3
        "high_spending":          1.2,   # new
    },
    "SCHOOL": {
        "few_comp_high_pop":      1.8,   # ↑ from 1.1
        "high_population":        3.0,   # ↑ from 1.5
        "medium_default":         0.8,   # slight de‑emphasis
    },
    # …and so on for other types
}

# Housing weights
HOUSING_WEIGHTS = {
    "hdb_2_room": 1.0,
    "hdb_3_room": 1.5,
    "hdb_4_room": 2.0,
    "hdb_5_room_ea": 2.5,
    "condominiums_and_apartments": 3.0,
    "landed_properties": 3.0,
    "other_types_properties": 1.0,
}

# Age map
# Which age brackets drive demand per venue type
VENUE_AGE_MAP = {
    "SCHOOL":        ["5-9","10-14","15-19"],
    "CAFE":          ["20-24","25-29","30-34"],
    "RESTAURANT":    ["25-29","30-34","35-39","40-44"],
    "DOCTOR":        ["60-64","65-69","70-74"],
    "APPAREL":       ["25-29","30-34","35-39"],
    "ARTS":          ["20-24","25-29","30-34"],
    "CLUBS":         ["20-24","25-29","30-34"],
    "SHOPPING":      ["25-29","30-34","35-39","40-44"],
    "PERSONAL_CARE": ["35-39","40-44","45-49"],
    "VEHICLE":       ["25-29","30-34","35-39","40-44"],
    "SPORTS_COMPLEX":["20-24","25-29","30-34"]
}

def fetch_venue_types(supa: Client) -> List[str]:
    resp = supa.table("venue_types").select("type_name").execute()
    return [r["type_name"] for r in resp.data]

def parse_int(val: str) -> int:
    try:
        return int(val.replace(",", ""))
    except:
        return 0

def fuzzy_membership(x, low, high):
    if x <= low:  return 1.0
    if x >= high: return 0.0
    return (high - x)/(high - low)

def inverse_fuzzy(x, low, high):
    if x <= low:  return 0.0
    if x >= high: return 1.0
    return (x - low)/(high - low)

# Modified to handle missing vs. zero counts
# Enhanced compute to include spending_power and population
def compute_rule_scores(comp_count, pop_relevant, has_count, spending_power):
    # If count is missing, fall back entirely to the "medium_default" rule
    if not has_count:
        # fallback fully to medium_default when no competitor data
        return {r["name"]: (1.0 if r["name"] == "medium_default" else 0.0) for r in SOFT_RULES}

    few = fuzzy_membership(comp_count, FEW_COMP_THRESH, MANY_COMP_THRESH)
    many = inverse_fuzzy(comp_count, FEW_COMP_THRESH, MANY_COMP_THRESH)
    pop_high = fuzzy_membership(pop_relevant, POP_LOW_THRESH, POP_HIGH_THRESH)
    r1 = few * pop_high
    r2 = many
    r3 = 1.0 - abs(r1 - r2)

    high_pop = inverse_fuzzy(pop_relevant, POP_LOW_THRESH, POP_HIGH_THRESH)
    high_spend = inverse_fuzzy(spending_power, SPEND_LOW_THRESH, SPEND_HIGH_THRESH)
    underserved_spend = few * high_spend

    return {
        "few_comp_high_pop":      r1,
        "many_competitors":       r2,
        "medium_default":         r3,
        "high_population":        high_pop,
        "high_spending":          high_spend,
        "underserved_high_spend": underserved_spend,
    }

# Aggregate with venue-type-specific adjustments
def aggregate_rules(scores: Dict[str, float], venue_type: str) -> float:
    # apply base weights
    weighted = []
    for rule in SOFT_RULES:
        name = rule["name"]
        base_w = rule["weight"]
        # lookup multiplier, default to 1.0
        mult = RULE_IMPORTANCE.get(venue_type, {}).get(name, 1.0)
        weighted.append(scores[name] * base_w * mult)
    total_w = sum(r["weight"] * RULE_IMPORTANCE.get(venue_type, {}).get(r["name"], 1.0)
                  for r in SOFT_RULES)
    return sum(weighted) / total_w if total_w else 0.0

class CompetitionHGT(torch.nn.Module):
    def __init__(self, in_dim, hid_dim, out_dim, metadata, heads=4):
        super().__init__()
        self.conv1 = HGTConv(in_dim, hid_dim, metadata=metadata, heads=heads)
        self.conv2 = HGTConv(hid_dim, out_dim, metadata=metadata, heads=1)
    def forward(self, x_dict, edge_index_dict):
        x = self.conv1(x_dict, edge_index_dict)
        x = {k: F.relu(v) for k,v in x.items()}
        return self.conv2(x, edge_index_dict)

def main():
    load_dotenv()
    print(f"🔍 Starting pipeline (USE_GNN={USE_GNN})")

    driver = GraphDatabase.driver(
        os.getenv("NEO4J_URI"),
        auth=(os.getenv("NEO4J_USERNAME"), os.getenv("NEO4J_PASSWORD"))
    )
    supa = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

    # 1) Fetch raw records
    records = []
    for vt in fetch_venue_types(supa):
        print(f"→ Querying venue type: {vt}")
        with driver.session() as sess:
            cypher = f"""
            MATCH (pa:PlanningArea)
            OPTIONAL MATCH (pa)-[:HAS_COMPETITOR_STATS]->
                          (cs:CompetitorStats {{subzone: pa.subzone, venue_type: '{vt}'}})
            OPTIONAL MATCH (pa)-[:HAS_AGE_DISTRIBUTION]->(ad:AgeDistribution)
            OPTIONAL MATCH (pa)-[:HAS_HOUSING_PROFILE]->(hp:HousingProfile)
            WITH
              pa.subzone                 AS subzone,
              cs.competitor_count        AS comp_count,
	          cs.underserved_score       AS underserved_score, 
              (cs.competitor_count IS NOT NULL)     AS has_count,
              [ ageKey IN keys(ad)
                WHERE ageKey IN {list(VENUE_AGE_MAP.get(vt, []))}
                | toInteger(ad[ageKey]) ]  AS age_vals,
              hp.hdb_2_room              AS hdb2,
              hp.hdb_3_room              AS hdb3,
              hp.hdb_4_room              AS hdb4,
              hp.hdb_5_room_ea           AS hdb5,
              hp.condominiums_and_apartments AS condos,
              hp.landed_properties       AS landed,
              hp.other_types_properties  AS other
            RETURN
              subzone,
              comp_count,
              underserved_score,
              has_count,
              reduce(s=0, x IN age_vals | s + x) AS pop_relevant,
              hdb2,
              hdb3,
              hdb4,
              hdb5,
              condos,
              landed,
              other;
            """
            for rec in sess.run(cypher).data():
                # Differentiate missing vs zero
                raw_count = rec.get("comp_count")
                has_count = rec.get("has_count", False)
                comp_count = raw_count if raw_count is not None else 0
                pop_relevant = rec.get("pop_relevant", 0) or 0
                hv = {
                    "hdb_2_room": str(rec.get("hdb2", "0")),
                    "hdb_3_room": str(rec.get("hdb3", "0")),
                    "hdb_4_room": str(rec.get("hdb4", "0")),
                    "hdb_5_room_ea": str(rec.get("hdb5", "0")),
                    "condominiums_and_apartments": str(rec.get("condos", "0")),
                    "landed_properties": str(rec.get("landed", "0")),
                    "other_types_properties": str(rec.get("other", "0")),
                }
                spending_power = sum(parse_int(hv[k]) * w for k, w in HOUSING_WEIGHTS.items())
                
                # **Log each fetched record**
                # print(f"   • subzone={rec.get('subzone')} | comp_count={comp_count} | pop_relevant={pop_relevant} | spending_power={spend}")
                raw_us = rec.get("underserved_score")
                if raw_us is None:
                    us_val = None
                else:
                    # catches true float("nan") as well as any non-numeric
                    try:
                        f = float(raw_us)
                        us_val = None if math.isnan(f) else f
                    except (TypeError, ValueError):
                        us_val = None
                records.append({
                    "subzone":       rec.get("subzone") or "",
                    "venue_type":    vt,
                    "comp_count":    comp_count,
                    "has_count":     has_count,
                    "pop_relevant":  pop_relevant,
                    "spending_power": spending_power,
                    "underserved_score": us_val
                })


    # ── INSERT DYNAMIC THRESHOLDS HERE ──────────────────
    comp_vals  = sorted(r["comp_count"]     for r in records if r["has_count"] and r["comp_count"] > 0)
    pop_vals   = sorted(r["pop_relevant"]   for r in records if r["pop_relevant"] > 0)
    spend_vals = sorted(r["spending_power"] for r in records)

    if comp_vals:
        i1, i2 = len(comp_vals)//3, 2*len(comp_vals)//3
        global FEW_COMP_THRESH, MANY_COMP_THRESH
        FEW_COMP_THRESH  = comp_vals[i1]
        MANY_COMP_THRESH = comp_vals[i2]

    if pop_vals:
        i1, i2 = len(pop_vals)//3, 2*len(pop_vals)//3
        global POP_LOW_THRESH, POP_HIGH_THRESH
        POP_LOW_THRESH  = pop_vals[i1]
        POP_HIGH_THRESH = pop_vals[i2]

    if spend_vals:
        i1, i2 = len(spend_vals)//3, 2*len(spend_vals)//3
        global SPEND_LOW_THRESH, SPEND_HIGH_THRESH
        SPEND_LOW_THRESH  = spend_vals[i1]
        SPEND_HIGH_THRESH = spend_vals[i2]
    # ─────────────────────────────────────────────────────    
        
    print(f"✅ Fetched total records: {len(records)}")

    # Compute rule_scores with venue-type-specific weights
    rule_scores = [
        aggregate_rules(
            compute_rule_scores(r["comp_count"], r["pop_relevant"], r["has_count"], r["spending_power"]),
            r["venue_type"]
        ) for r in records
    ]
    print("✅ Computed rule_scores")

    # 3) Optionally run GNN
    if USE_GNN and records:
        print("✅ Running GNN with subzone/type relations")

        # 1) Prepare node features and identifiers
        het = HeteroData()
        feats, idxs = [], []
        for r in records:
            feats.append([r["comp_count"], r["pop_relevant"], r["spending_power"]])
            idxs.append((r["subzone"], r["venue_type"]))
        het["PA_VT"].x = torch.tensor(feats, dtype=torch.float)

        # 2) Build edges for “same_subzone”
        from collections import defaultdict
        sub2nodes = defaultdict(list)
        for i, (sub, _) in enumerate(idxs):
            sub2nodes[sub].append(i)
        rows, cols = [], []
        for nodes in sub2nodes.values():
            for i in nodes:
                for j in nodes:
                    if i != j:
                        rows.append(i); cols.append(j)
        het["PA_VT", "same_subzone", "PA_VT"].edge_index = torch.tensor([rows, cols], dtype=torch.long)

        # 3) Build edges for “same_type”
        type2nodes = defaultdict(list)
        for i, (_, vt) in enumerate(idxs):
            type2nodes[vt].append(i)
        rows, cols = [], []
        for nodes in type2nodes.values():
            for i in nodes:
                for j in nodes:
                    if i != j:
                        rows.append(i); cols.append(j)
        het["PA_VT", "same_type", "PA_VT"].edge_index = torch.tensor([rows, cols], dtype=torch.long)

        # 4) Run heterogeneous GNN
        metadata = het.metadata()
        model = CompetitionHGT(3, 16, 1, metadata)
        model.eval()
        with torch.no_grad():
            out = model(het.x_dict, het.edge_index_dict)
        raw = out["PA_VT"].squeeze().tolist()
        mn, mx = min(raw), max(raw)
        gnn_scores = [(v - mn)/(mx - mn + 1e-9) for v in raw]
    else:
        print("ℹ️ Skipped GNN, using zeros for gnn_scores")
        gnn_scores = [0.0] * len(records)

    # 4) Blend & upsert, with fallback if no unique constraint
    updates = []
    print("=== Blending Scores ===")
    for r, g, ru in zip(records, gnn_scores, rule_scores):
        # — apply mild contrast around 1.3 (increase from 0.5) to spread scores —
        contrast = 1.3
        ru = 0.5 + (ru - 0.5) * contrast
        ru = max(0.0, min(ru, 1.0))

        alpha = ALPHA if USE_GNN else 0.0
        raw_score = alpha * g + (1 - alpha) * ru
        clamped = max(0.0, min(raw_score, 1.0))
        # scale to 0–100
        base_pct = clamped * 100.0
 
        # attempt to fetch a valid underserved_score
        # blend with underserved_score if present
        us_pct = r.get("underserved_score")
        if us_pct is not None:
            raw_overall = base_pct * (1 - UNDERSERVED_RATIO) + us_pct * UNDERSERVED_RATIO
        else:
            raw_overall = base_pct

        # round to two decimal places
        overall_pct = round(raw_overall, 2)
        	# print(
        	#     f"[{r['subzone']}|{r['venue_type']}] "
        	#     f"rule={ru:.4f}, gnn={g:.4f} → raw={raw_score:.4f}, "
        	#     f"clamped={clamped:.4f} → overall_pct={overall_pct:.1f}"
        	# )
        updates.append({
            "subzone":    r["subzone"],
            "venue_type": r["venue_type"],
            "overall_score": float(overall_pct)
        })

    try:
        supa.table("competitor_stats") \
            .upsert(updates, on_conflict=["subzone","venue_type"]) \
            .execute()
    except APIError:
        print("⚠️ upsert failed. Falling back to per-record update/insert.")
        for u in tqdm(updates, desc="Updating Supabase"):
            # 1) try to update the overall_score on the matching row
    # 1) try to update existing row
            try:
                resp = supa.table("competitor_stats") \
                        .update({"overall_score": u["overall_score"]}) \
                        .eq("subzone", u["subzone"]) \
                        .eq("venue_type", u["venue_type"]) \
                        .execute()
                num_updated = len(resp.data or [])
            except APIError as e:
                err = getattr(e, "args", [{}])[0]
                # If it’s the “empty or invalid json” error, treat as zero updated
                if isinstance(err, dict) and err.get("code") == "PGRST102":
                    num_updated = 0
                else:
                    # some other error—raise or log
                    print("❌ Update failed for %s|%s: %s", u["subzone"], u["venue_type"], err)
                    num_updated = 0

            # 2) if nothing got updated, insert instead
            if num_updated == 0:
                try:
                    supa.table("competitor_stats").insert(u).execute()
                except APIError as e:
                    print("❌ Insert failed for %s|%s: %s", u["subzone"], u["venue_type"], e)

    print(f"✅ competitor_stats updated  (USE_GNN={USE_GNN})")


     # 5) Update Neo4j CompetitorStats nodes with overall_score
    print(f"→ Writing overall_score back to Neo4j…")
    with driver.session() as session:
        for u in tqdm(updates, desc="Updating Neo4j"):
            session.run(
                 """
                 MATCH (cs:CompetitorStats {subzone: $subzone, venue_type: $venue_type})
                 SET cs.overall_score = $overall_score
                 """,
                 {
                     "subzone": u["subzone"],
                     "venue_type": u["venue_type"],
                     "overall_score": u["overall_score"]
                 }
             )
    print("✅ Neo4j updated with overall_score")
    driver.close()

if __name__ == "__main__":
    main()