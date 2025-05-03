def get_queries_dict():
    # Define queries for different user intent
    # Note: Before running the queries below, need to create index consisting of planning areas and venue types separately
    # CREATE FULLTEXT INDEX planning_area_index IF NOT EXISTS
    # FOR (n:PlanningArea)
    # ON EACH [n.subzone]
    # CREATE FULLTEXT INDEX venue_type_index IF NOT EXISTS
    # FOR (n:VenueType)
    # ON EACH [n.type_name]

    # Get competitor information (statistics, count, and example competitors) for all 11 venue types in given planning area
    comp_info_for_planning_area_query = """
    CALL db.index.fulltext.queryNodes("planning_area_index", $query, {limit:1})
    YIELD node
    WITH node
    OPTIONAL MATCH (node)-[has_cs_rel:HAS_COMPETITOR_STATS]->(cs:CompetitorStats)-[for_type_rel:FOR_TYPE]->(vt:VenueType {type_name: cs.venue_type})
    OPTIONAL MATCH (node)<-[:LOCATED_IN]-(comp:Competitor)-[:OF_TYPE]->(vt)
    WITH 
        node, cs, vt, has_cs_rel, for_type_rel,
        node.subzone AS planning_area,
        collect(DISTINCT comp.venue_name) AS all_comps,
        count(DISTINCT comp) AS comp_count
    WITH 
        node, cs, vt, has_cs_rel, for_type_rel, planning_area,
        (CASE
            WHEN size(all_comps) = 0
            THEN []
            ELSE apoc.coll.randomItems(all_comps, 3, false)
            END
        ) AS eg_comps
    WHERE cs.overall_score IS NOT NULL
    ORDER BY cs.overall_score DESC
    OPTIONAL MATCH (eg_comp:Competitor)
    WHERE eg_comp.venue_name IN eg_comps
    OPTIONAL MATCH (eg_comp)-[loc_in_rel:LOCATED_IN]->(node)
    OPTIONAL MATCH (eg_comp)-[of_type_rel:OF_TYPE]->(vt)
    WITH 
        node, cs, vt, has_cs_rel, for_type_rel, planning_area,
        collect(DISTINCT
            (CASE
                WHEN eg_comp IS NOT NULL
                THEN eg_comp.venue_name + " [" + head(labels(eg_comp)) + "] " + apoc.convert.toJson(properties(eg_comp)) + " - " + type(loc_in_rel) + " -> " + planning_area + " [" + head(labels(node)) + "] " + apoc.convert.toJson(properties(node)) + "\n" +
                eg_comp.venue_name + " [" + head(labels(eg_comp)) + "] " + apoc.convert.toJson(properties(eg_comp)) + " - " + type(of_type_rel) + " -> " + vt.type_name + " [" + head(labels(vt)) + "] " + apoc.convert.toJson(properties(vt))
                ELSE ""
                END
            )
        ) AS comp_graph_lines
    WITH collect(
        (CASE
            WHEN cs IS NULL OR size(keys(properties(cs))) = 0
            THEN ""
            ELSE
                planning_area + " [" + head(labels(node)) + "] " + apoc.convert.toJson(properties(node)) + " - " + type(has_cs_rel) + " -> " + cs.name + " [" + head(labels(cs)) + "] " + apoc.convert.toJson(properties(cs)) + "\n" +
                cs.name + " [" + head(labels(cs)) + "] " + apoc.convert.toJson(properties(cs)) + " - " + type(for_type_rel) + " -> " + vt.type_name + " [" + head(labels(vt)) + "] " + apoc.convert.toJson(properties(vt)) + "\n" +
                reduce(acc = "", line IN comp_graph_lines | acc + line + "\n")
            END
        )
    ) AS graph_like_outputs, planning_area
    RETURN
        "Subgraph of competitor information in " + planning_area + ":\n" +
        reduce(acc = "", o IN graph_like_outputs | acc + o) AS finalOutput
    """

    # Get competitor information (statistics, count, and example competitors) for top 5 planning areas, ranked by competitor score, given business type
    comp_info_for_biz_type_query = """
    CALL db.index.fulltext.queryNodes("venue_type_index", $query, {limit:1})
    YIELD node
    WITH node
    MATCH (pa:PlanningArea)<-[:LOCATED_IN]-(comp:Competitor)-[:OF_TYPE]->(node)
    OPTIONAL MATCH (pa)-[has_cs_rel:HAS_COMPETITOR_STATS]->(cs:CompetitorStats)-[for_type_rel:FOR_TYPE]->(node)
    WITH
        node, pa, cs, has_cs_rel, for_type_rel,
        node.type_name AS biz_type,
        pa.subzone AS planning_area,
        cs.overall_score AS score,
        collect(DISTINCT comp.venue_name) AS all_comps
    WITH node, pa, cs, has_cs_rel, for_type_rel, biz_type, planning_area, score,
        (CASE
            WHEN size(all_comps) = 0
            THEN []
            ELSE apoc.coll.randomItems(all_comps, 3, false)
            END
        ) AS eg_comps
    WHERE score IS NOT NULL
    ORDER BY score DESC
    LIMIT 5
    OPTIONAL MATCH (eg_comp:Competitor)
    WHERE eg_comp.venue_name IN eg_comps
    OPTIONAL MATCH (eg_comp)-[loc_in_rel:LOCATED_IN]->(pa)
    OPTIONAL MATCH (eg_comp)-[of_type_rel:OF_TYPE]->(node)
    WITH node, pa, cs, has_cs_rel, for_type_rel, biz_type, planning_area,
        collect(DISTINCT
            (CASE
                WHEN eg_comp IS NOT NULL
                THEN eg_comp.venue_name + " [" + head(labels(eg_comp)) + "] " + apoc.convert.toJson(properties(eg_comp)) + " - " + type(loc_in_rel) + " -> " + planning_area + " [" + head(labels(pa)) + "] " + apoc.convert.toJson(properties(node)) + "\n" +
                eg_comp.venue_name + " [" + head(labels(eg_comp)) + "] " + apoc.convert.toJson(properties(eg_comp)) + " - " + type(of_type_rel) + " -> " + node.type_name + " [" + head(labels(node)) + "] " + apoc.convert.toJson(properties(node))
                ELSE ""
                END
            )
        ) AS comp_graph_lines
    WITH collect(
        (CASE
            WHEN cs IS NULL OR size(keys(properties(cs))) = 0
            THEN ""
            ELSE
                planning_area + " [" + head(labels(pa)) + "] " + apoc.convert.toJson(properties(pa)) + " - " + type(has_cs_rel) + " -> " + cs.name + " [" + head(labels(cs)) + "] " + apoc.convert.toJson(properties(cs)) + "\n" +
                cs.name + " [" + head(labels(cs)) + "] " + apoc.convert.toJson(properties(cs)) + " - " + type(for_type_rel) + " -> " + node.type_name + " [" + head(labels(node)) + "] " + apoc.convert.toJson(properties(node)) + "\n" +
                reduce(acc = "", line IN comp_graph_lines | acc + line + "\n")
            END
        )
    ) AS graph_like_outputs, biz_type 
    RETURN 
        "Subgraph of competitor information for venue type " + biz_type + " in planning areas with top 5 overall score:\n" +
        reduce(acc = "", o IN graph_like_outputs | acc + o) AS finalOutput
    """

    # Get competitor information (statistics, count, and example competitors) given planning area and business type
    specific_comp_info_query = """
    // Find venue type node
    CALL db.index.fulltext.queryNodes("venue_type_index", $venue_type_query, {limit: 1})
    YIELD node AS venue_type

    // And find planning area node
    CALL db.index.fulltext.queryNodes("planning_area_index", $planning_area_query, {limit: 1})
    YIELD node AS planning_area

    // Get venue type's competitor stats and example competitors
    OPTIONAL MATCH (planning_area)-[has_cs_rel:HAS_COMPETITOR_STATS]->(cs:CompetitorStats)-[for_type_rel:FOR_TYPE]->(venue_type)
    OPTIONAL MATCH (planning_area)<-[:LOCATED_IN]-(comp:Competitor)-[:OF_TYPE]->(venue_type)

    WITH
        planning_area, cs, has_cs_rel, for_type_rel, venue_type,
        planning_area.subzone AS pa_subzone,
        venue_type.type_name AS biz_type,
        collect(DISTINCT comp.venue_name) AS all_comps
    WITH planning_area, cs, has_cs_rel, for_type_rel, venue_type, pa_subzone, biz_type,
        (CASE
            WHEN size(all_comps) = 0
            THEN []
            ELSE apoc.coll.randomItems(all_comps, 3, false)
            END
        ) AS eg_comps
    OPTIONAL MATCH (eg_comp:Competitor)
    WHERE eg_comp.venue_name IN eg_comps
    OPTIONAL MATCH (eg_comp)-[loc_in_rel:LOCATED_IN]->(planning_area)
    OPTIONAL MATCH (eg_comp)-[of_type_rel:OF_TYPE]->(venue_type)
    WITH planning_area, cs, has_cs_rel, for_type_rel, venue_type, pa_subzone, biz_type,
        collect(DISTINCT
            (CASE
                WHEN eg_comp IS NOT NULL
                THEN eg_comp.venue_name + " [" + head(labels(eg_comp)) + "] " + apoc.convert.toJson(properties(eg_comp)) + " - " + type(loc_in_rel) + " -> " + pa_subzone + " [" + head(labels(planning_area)) + "] " + apoc.convert.toJson(properties(planning_area)) + "\n" +
                eg_comp.venue_name + " [" + head(labels(eg_comp)) + "] " + apoc.convert.toJson(properties(eg_comp)) + " - " + type(of_type_rel) + " -> " + biz_type + " [" + head(labels(venue_type)) + "] " + apoc.convert.toJson(properties(venue_type))
                ELSE ""
                END
            )
        ) AS comp_graph_lines
    WITH collect(
        (CASE
            WHEN cs IS NULL OR size(keys(properties(cs))) = 0
            THEN ""
            ELSE
                pa_subzone + " [" + head(labels(planning_area)) + "] " + apoc.convert.toJson(properties(planning_area)) + " - " + type(has_cs_rel) + " -> " + cs.name + " [" + head(labels(cs)) + "] " + apoc.convert.toJson(properties(cs)) + "\n" +
                cs.name + " [" + head(labels(cs)) + "] " + apoc.convert.toJson(properties(cs)) + " - " + type(for_type_rel) + " -> " + venue_type.type_name + " [" + head(labels(venue_type)) + "] " + apoc.convert.toJson(properties(venue_type)) + "\n" +
                reduce(acc = "", line IN comp_graph_lines | acc + line + "\n")
            END
        )
    ) AS graph_like_outputs, pa_subzone, biz_type
    RETURN
        "Subgraph of competitor information for " + biz_type + " in " + pa_subzone + ":\n" +
        reduce(acc = "", o IN graph_like_outputs | acc + o) AS output
    """

    # Get population statistics given planning area
    pop_stats_query = """
    CALL db.index.fulltext.queryNodes("planning_area_index", $query, {limit:1})
    YIELD node
    WITH node
    OPTIONAL MATCH (node)-[has_ps_rel:HAS_POPULATION_STATS]->(pop_stats:PopulationStats)
    WITH node, pop_stats, has_ps_rel
    RETURN
        "Subgraph of population statistics of " + node.subzone +
        (CASE
            WHEN pop_stats IS NULL OR size(keys(properties(pop_stats))) = 0
            THEN ""
            ELSE ", " + pop_stats.planning_area
            END
        ) + ":\n" +
        (CASE
            WHEN pop_stats IS NULL OR size(keys(properties(pop_stats))) = 0
            THEN "No data available"
            ELSE
                node.subzone + " [" + head(labels(node)) + "] " + apoc.convert.toJson(properties(node)) +
                " - " + type(has_ps_rel) + " -> " +
                pop_stats.name + " [" + head(labels(pop_stats)) + "] " + apoc.convert.toJson(properties(pop_stats))
            END
        ) AS output
    """

    # Get age distribution, formatted in ascending order of age group given planning area
    age_distr_query = """
    CALL db.index.fulltext.queryNodes("planning_area_index", $query, {limit:1})
    YIELD node
    WITH node
    OPTIONAL MATCH (node)-[has_ad_rel:HAS_AGE_DISTRIBUTION]->(age_distr:AgeDistribution)
    RETURN
        "Subgraph of age distribution of " + node.subzone +
        (CASE
            WHEN age_distr IS NULL OR size(keys(age_distr)) = 0
            THEN ""
            ELSE ", " + age_distr.planning_area
            END
        ) + ":\n" +
        (CASE
            WHEN age_distr IS NULL OR size(keys(properties(age_distr))) = 0
            THEN "No data available"
            ELSE
                node.subzone + " [" + head(labels(node)) + "] " + apoc.convert.toJson(properties(node)) +
                " - " + type(has_ad_rel) + " -> " +
                age_distr.name + " [" + head(labels(age_distr)) + "] " + apoc.convert.toJson(properties(age_distr))
            END
        ) AS output
    """

    # Get housing profile given planning area
    house_prof_query = """
    CALL db.index.fulltext.queryNodes("planning_area_index", $query, {limit:1})
    YIELD node
    WITH node
    OPTIONAL MATCH (node)-[has_hp_rel:HAS_HOUSING_PROFILE]->(house_prof:HousingProfile)
    WITH node, house_prof, has_hp_rel
    RETURN
        "Subgraph of housing profile of " + node.subzone +
        (CASE
            WHEN house_prof IS NULL OR size(keys(house_prof)) = 0
            THEN ""
            ELSE ", " + house_prof.planning_area
            END
        ) + ":\n" +
        (CASE
            WHEN house_prof IS NULL OR size(keys(properties(house_prof))) = 0
            THEN "No data available"
            ELSE
                node.subzone + " [" + head(labels(node)) + "] " + apoc.convert.toJson(properties(node)) +
                " - " + type(has_hp_rel) + " -> " +
                house_prof.name + " [" + head(labels(house_prof)) + "] " + apoc.convert.toJson(properties(house_prof))
            END
        ) AS output
    """

    # Get average property prices given planning area
    prop_price_query = """
    CALL db.index.fulltext.queryNodes("planning_area_index", $query, {limit:1})
    YIELD node
    WITH node
    OPTIONAL MATCH (node)-[offers_prop_rel:OFFERS_PROPERTIES]->(prop_available:PropertiesAvailable)
    WITH node, prop_available, offers_prop_rel
    RETURN
        "Subgraph of average property prices in " + node.subzone + ":\n" +
        (CASE
            WHEN prop_available IS NULL
            THEN "No data available"
            ELSE
                node.subzone + " [" + head(labels(node)) + "] " + apoc.convert.toJson(properties(node)) +
                " - " + type(offers_prop_rel) + " -> " +
                "Average property prices in " + node.subzone + " [" + head(labels(prop_available)) + "] " + apoc.convert.toJson(properties(prop_available))
            END
        ) AS output
    """

    # Get available properties given planning area
    avail_prop_query = """
    CALL db.index.fulltext.queryNodes("planning_area_index", $query, {limit:1})
    YIELD node
    WITH node
    OPTIONAL MATCH (node)-[offers_prop_rel:OFFERS_PROPERTIES]->(avail_prop:PropertiesAvailable)-[has_prop_rel:HAS_PROPERTY]->(prop:IndustrialProperty)
    WITH
        node, avail_prop, offers_prop_rel,
        node.subzone AS subzone,
        collect(properties(prop)) AS all_props,
        collect(DISTINCT
            CASE
                WHEN prop IS NOT NULL
                THEN "Properties in " + avail_prop.subzone + " [" + head(labels(avail_prop)) + "] " + apoc.convert.toJson(properties(avail_prop)) +
                    " - " + type(has_prop_rel) + " -> " +
                    prop.listing_id + " [" + head(labels(prop)) + "] " + apoc.convert.toJson(properties(prop))
                ELSE "No data available"
            END
        ) AS prop_lines
    WITH node, avail_prop, offers_prop_rel, subzone, all_props, apoc.text.join(prop_lines, "\n") AS all_prop_lines
    RETURN
        "Subgraph of properties available in " + subzone + ":\n" +
        (CASE
            WHEN size(all_props) = 0
            THEN "No data available"
            ELSE subzone + " [" + head(labels(node)) + "] " + apoc.convert.toJson(properties(node)) +
                " - " + type(offers_prop_rel) + " -> " +
                "Properties in " + avail_prop.subzone + " [" + head(labels(avail_prop)) + "] " + apoc.convert.toJson(properties(avail_prop)) + "\n" +
        all_prop_lines
            END
        ) AS output
    """

    # Get info needed for location recommendation, given a business type
    loc_rec_query = """
    CALL db.index.fulltext.queryNodes("venue_type_index", $query, {limit:1})
    YIELD node
    CALL {
        WITH node
        MATCH (pa:PlanningArea)
        OPTIONAL MATCH (pa)-[has_ad_rel:HAS_AGE_DISTRIBUTION]->(ad:AgeDistribution)
        OPTIONAL MATCH (pa)-[has_hp_rel:HAS_HOUSING_PROFILE]->(hp:HousingProfile)
        OPTIONAL MATCH (pa)-[has_ps_rel:HAS_POPULATION_STATS]->(pop:PopulationStats)
        OPTIONAL MATCH (pa)-[offers_prop_rel:OFFERS_PROPERTIES]->(prop:PropertiesAvailable)
        OPTIONAL MATCH (pa)-[has_cs_rel:HAS_COMPETITOR_STATS]->(cs:CompetitorStats)-[for_type_rel:FOR_TYPE]->(node)
        OPTIONAL MATCH (pa)<-[:LOCATED_IN]-(comp:Competitor)-[:OF_TYPE]->(node)

        WITH 
            node, pa, ad, hp, pop, prop, cs,
            has_ad_rel, has_hp_rel, has_ps_rel, offers_prop_rel, has_cs_rel, for_type_rel,
            pa.subzone AS planning_area,
            cs.overall_score AS comp_score,
            collect(DISTINCT comp.venue_name) AS all_comps,
            toLower(node.type_name) AS biz_type

        WITH
            node, pa, ad, hp, pop, prop, cs,
            has_ad_rel, has_hp_rel, has_ps_rel, offers_prop_rel, has_cs_rel, for_type_rel,
            planning_area, comp_score, biz_type,
            (CASE
                WHEN size(all_comps) = 0
                THEN []
                ELSE apoc.coll.randomItems(all_comps, 3, false)
                END
            ) AS eg_comps

        WHERE comp_score IS NOT NULL
        ORDER BY comp_score DESC
        LIMIT 3
            
        RETURN
            pa, ad, hp, pop, prop, cs,
            has_ad_rel, has_hp_rel, has_ps_rel, offers_prop_rel, has_cs_rel, for_type_rel,
            planning_area, eg_comps, biz_type
    }
    OPTIONAL MATCH (eg_comp:Competitor)
    WHERE eg_comp.venue_name IN eg_comps
    OPTIONAL MATCH (eg_comp)-[loc_in_rel:LOCATED_IN]->(pa)
    OPTIONAL MATCH (eg_comp)-[of_type_rel:OF_TYPE]->(node)
    WITH 
        collect(DISTINCT
            (CASE
                WHEN eg_comp IS NOT NULL
                THEN eg_comp.venue_name + " [" + head(labels(eg_comp)) + "] " + apoc.convert.toJson(properties(eg_comp)) + " - " + type(loc_in_rel) + " -> " + planning_area + " [" + head(labels(pa)) + "] " + apoc.convert.toJson(properties(pa)) + "\n" +
                eg_comp.venue_name + " [" + head(labels(eg_comp)) + "] " + apoc.convert.toJson(properties(eg_comp)) + " - " + type(of_type_rel) + " -> " + node.type_name + " [" + head(labels(node)) + "] " + apoc.convert.toJson(properties(node))
                ELSE ""
                END
            )
        ) AS comp_graph_lines,
        node, pa, ad, hp, pop, prop, cs,
        has_ad_rel, has_hp_rel, has_ps_rel, offers_prop_rel, has_cs_rel, for_type_rel,
        planning_area, biz_type
    WITH collect(
        (CASE
            WHEN ad IS NULL OR size(keys(properties(ad))) = 0
            THEN ""
            ELSE
                planning_area + " [" + head(labels(pa)) + "] " + apoc.convert.toJson(properties(pa)) +
                " - " + type(has_ad_rel) + " -> " +
                ad.name + " [" + head(labels(ad)) + "] " + apoc.convert.toJson(properties(ad))
            END
        ) + "\n" +
        (CASE
            WHEN hp IS NULL OR size(keys(properties(hp))) = 0
            THEN ""
            ELSE
                planning_area + " [" + head(labels(pa)) + "] " + apoc.convert.toJson(properties(pa)) +
                " - " + type(has_hp_rel) + " -> " +
                hp.name + " [" + head(labels(hp)) + "] " + apoc.convert.toJson(properties(hp))
            END
        ) + "\n" +
        (CASE
            WHEN pop IS NULL OR size(keys(properties(pop))) = 0
            THEN ""
            ELSE
                planning_area + " [" + head(labels(pa)) + "] " + apoc.convert.toJson(properties(pa)) +
                " - " + type(has_ps_rel) + " -> " +
                pop.name + " [" + head(labels(pop)) + "] " + apoc.convert.toJson(properties(pop))
            END
        ) + "\n" +
        (CASE
            WHEN prop IS NULL OR size(keys(properties(prop))) = 0
            THEN ""
            ELSE
                planning_area + " [" + head(labels(pa)) + "] " + apoc.convert.toJson(properties(pa)) +
                " - " + type(offers_prop_rel) + " -> " +
                "Average property prices in " + planning_area + " [" + head(labels(prop)) + "] " + apoc.convert.toJson(properties(prop))
            END
        ) + "\n" +
        (CASE
            WHEN cs IS NULL OR size(keys(properties(cs))) = 0
            THEN ""
            ELSE
                planning_area + " [" + head(labels(pa)) + "] " + apoc.convert.toJson(properties(pa)) + " - " + type(has_cs_rel) + " -> " + cs.name + " [" + head(labels(cs)) + "] " + apoc.convert.toJson(properties(cs)) + "\n" +
                cs.name + " [" + head(labels(cs)) + "] " + apoc.convert.toJson(properties(cs)) + " - " + type(for_type_rel) + " -> " + node.type_name + " [" + head(labels(node)) + "] " + apoc.convert.toJson(properties(node)) + "\n" +
                reduce(acc = "", line IN comp_graph_lines | acc + line + "\n")
            END
        )
    ) AS graph_like_outputs, biz_type

    RETURN
        "Subgraph of top 3 planning area subzones to open a/an " + biz_type + " in:\n" +
        reduce(acc = "", o IN graph_like_outputs | acc + o) AS finalOutput
    """

    # Get info needed for business type recommendation, given a location / planning area
    biz_rec_query = """
    CALL db.index.fulltext.queryNodes("planning_area_index", $query, {limit:1})
    YIELD node

    // Get planning area information excluding competitor stats
    OPTIONAL MATCH (node)-[has_ad_rel:HAS_AGE_DISTRIBUTION]->(ad:AgeDistribution)
    OPTIONAL MATCH (node)-[has_hp_rel:HAS_HOUSING_PROFILE]->(hp:HousingProfile)
    OPTIONAL MATCH (node)-[has_ps_rel:HAS_POPULATION_STATS]->(pop:PopulationStats)
    OPTIONAL MATCH (node)-[offers_prop_rel:OFFERS_PROPERTIES]->(prop:PropertiesAvailable)

    // Get top 3 business types based on competitor score
    OPTIONAL MATCH (node)-[has_cs_rel:HAS_COMPETITOR_STATS]->(cs:CompetitorStats)-[for_type_rel:FOR_TYPE]->(vt:VenueType)
    WITH node, ad, hp, pop, prop, vt, cs,
        has_ad_rel, has_hp_rel, has_ps_rel, offers_prop_rel, has_cs_rel, for_type_rel
    WHERE vt IS NOT NULL AND cs IS NOT NULL
    ORDER BY cs.overall_score DESC
    WITH node, ad, hp, pop, prop, 
        has_ad_rel, has_hp_rel, has_ps_rel, offers_prop_rel,
        collect({
            comp_stats_node: cs,
            has_cs_rel: has_cs_rel,
            for_type_rel: for_type_rel,
            venue_type_node: vt,
            biz_type: toLower(vt.type_name)
        })[0..3] AS top_biz_types_info

    // Get planning area info
    WITH node, ad, hp, pop, prop, has_ad_rel, has_hp_rel, has_ps_rel, offers_prop_rel, top_biz_types_info,
        node.subzone AS planning_area

    //Format planning area info
    WITH node, ad, hp, pop, prop, top_biz_types_info, planning_area,
        (CASE
            WHEN ad IS NULL OR size(keys(properties(ad))) = 0
            THEN ""
            ELSE
                planning_area + " [" + head(labels(node)) + "] " + apoc.convert.toJson(properties(node)) +
                " - " + type(has_ad_rel) + " -> " +
                ad.name + " [" + head(labels(ad)) + "] " + apoc.convert.toJson(properties(ad))
            END
        ) + "\n" +
        (CASE
            WHEN hp IS NULL OR size(keys(properties(hp))) = 0
            THEN ""
            ELSE
                planning_area + " [" + head(labels(node)) + "] " + apoc.convert.toJson(properties(node)) +
                " - " + type(has_hp_rel) + " -> " +
                hp.name + " [" + head(labels(hp)) + "] " + apoc.convert.toJson(properties(hp))
            END
        ) + "\n" +
        (CASE
            WHEN pop IS NULL OR size(keys(properties(pop))) = 0
            THEN ""
            ELSE
                planning_area + " [" + head(labels(node)) + "] " + apoc.convert.toJson(properties(node)) +
                " - " + type(has_ps_rel) + " -> " +
                pop.name + " [" + head(labels(pop)) + "] " + apoc.convert.toJson(properties(pop))
            END
        ) + "\n" +
        (CASE
            WHEN prop IS NULL OR size(keys(properties(prop))) = 0
            THEN ""
            ELSE
                planning_area + " [" + head(labels(node)) + "] " + apoc.convert.toJson(properties(node)) +
                " - " + type(offers_prop_rel) + " -> " +
                "Average property prices in " + planning_area + " [" + head(labels(prop)) + "] " + apoc.convert.toJson(properties(prop))
            END
        ) + "\n" AS pa_info_graph
        
    // Get 3 examples of competitors of each venue type
    UNWIND top_biz_types_info AS biz_type_info
    WITH node, pa_info_graph, planning_area,
        biz_type_info.comp_stats_node AS comp_stats_node,
        biz_type_info.venue_type_node AS venue_type_node,
        biz_type_info.has_cs_rel AS has_cs_rel,
        biz_type_info.for_type_rel AS for_type_rel,
        biz_type_info.biz_type AS biz_type

    OPTIONAL MATCH (node)<-[:LOCATED_IN]-(comp:Competitor)-[:OF_TYPE]->(venue_type_node)
    WITH 
        node, pa_info_graph, planning_area,
        comp_stats_node, venue_type_node, has_cs_rel, for_type_rel, biz_type,
        collect(DISTINCT comp.venue_name) AS all_comps
    WITH
        node, pa_info_graph, planning_area,
        comp_stats_node, venue_type_node, has_cs_rel, for_type_rel, biz_type,
        (CASE
            WHEN size(all_comps) = 0
            THEN []
            ELSE apoc.coll.randomItems(all_comps, 3, false)
            END
        ) AS eg_comps

    OPTIONAL MATCH (eg_comp:Competitor)
    WHERE eg_comp.venue_name IN eg_comps
    OPTIONAL MATCH (eg_comp)-[loc_in_rel:LOCATED_IN]->(node)
    OPTIONAL MATCH (eg_comp)-[of_type_rel:OF_TYPE]->(venue_type_node)
    WITH 
        collect(DISTINCT
            (CASE
                WHEN eg_comp IS NOT NULL
                THEN eg_comp.venue_name + " [" + head(labels(eg_comp)) + "] " + apoc.convert.toJson(properties(eg_comp)) + " - " + type(loc_in_rel) + " -> " + planning_area + " [" + head(labels(node)) + "] " + apoc.convert.toJson(properties(node)) + "\n" +
                eg_comp.venue_name + " [" + head(labels(eg_comp)) + "] " + apoc.convert.toJson(properties(eg_comp)) + " - " + type(of_type_rel) + " -> " + venue_type_node.type_name + " [" + head(labels(venue_type_node)) + "] " + apoc.convert.toJson(properties(venue_type_node))
                ELSE ""
                END
            )
        ) AS comp_graph_lines,
        node, pa_info_graph, planning_area,
        comp_stats_node, venue_type_node, has_cs_rel, for_type_rel, biz_type

    // Format top 3 business types to consider
    WITH
        pa_info_graph, planning_area,
        (CASE
            WHEN comp_stats_node IS NULL OR size(keys(properties(comp_stats_node))) = 0
            THEN ""
            ELSE
                planning_area + " [" + head(labels(node)) + "] " + apoc.convert.toJson(properties(node)) + " - " + type(has_cs_rel) + " -> " + comp_stats_node.name + " [" + head(labels(comp_stats_node)) + "] " + apoc.convert.toJson(properties(comp_stats_node)) + "\n" +
                comp_stats_node.name + " [" + head(labels(comp_stats_node)) + "] " + apoc.convert.toJson(properties(comp_stats_node)) +
                " - " + type(for_type_rel) + " -> " + venue_type_node.type_name + " [" + head(labels(venue_type_node)) + "] " + apoc.convert.toJson(properties(venue_type_node)) + "\n" +
                reduce(acc = "", line IN comp_graph_lines | acc + line + "\n")
            END
        ) AS biz_type_rec_graph

    WITH pa_info_graph, planning_area, collect(biz_type_rec_graph) AS biz_type_recs_graph
    RETURN "Subgraph of top 3 business types to consider opening in " + planning_area + ":\n" + pa_info_graph + reduce(acc="", rec in biz_type_recs_graph | acc + rec) + "\n" AS final_output
    """

    # Get info of specific business type in specific location
    # Note: For this query, need to add some logic (probably in rag.py) to get the $venue_type_query and $planning_area_query
    # Different from other queries, which only have one variable as user input ($query)
    biz_advice_query = """
    // Find venue type node
    CALL db.index.fulltext.queryNodes("venue_type_index", $venue_type_query, {limit: 1})
    YIELD node AS venue_type

    // And find planning area node
    CALL db.index.fulltext.queryNodes("planning_area_index", $planning_area_query, {limit: 1})
    YIELD node AS planning_area

    CALL {
        WITH planning_area, venue_type
        // Get planning area info
        OPTIONAL MATCH (planning_area)-[has_ad_rel:HAS_AGE_DISTRIBUTION]->(ad:AgeDistribution)
        OPTIONAL MATCH (planning_area)-[has_hp_rel:HAS_HOUSING_PROFILE]->(hp:HousingProfile)
        OPTIONAL MATCH (planning_area)-[has_ps_rel:HAS_POPULATION_STATS]->(pop:PopulationStats)
        OPTIONAL MATCH (planning_area)-[offers_prop_rel:OFFERS_PROPERTIES]->(prop:PropertiesAvailable)
        // Get venue type's competitor stats and example competitors
        OPTIONAL MATCH (planning_area)-[has_cs_rel:HAS_COMPETITOR_STATS]->(cs:CompetitorStats)-[for_type_rel:FOR_TYPE]->(venue_type)
        OPTIONAL MATCH (planning_area)<-[:LOCATED_IN]-(comp:Competitor)-[:OF_TYPE]->(venue_type)

        WITH
            ad, hp, pop, prop, cs,
            has_ad_rel, has_hp_rel, has_ps_rel, offers_prop_rel, has_cs_rel, for_type_rel,
            planning_area.subzone AS pa_subzone,
            toLower(venue_type.type_name) AS biz_type,
            collect(DISTINCT comp.venue_name) AS all_comps
        
        WITH
            ad, hp, pop, prop, cs,
            has_ad_rel, has_hp_rel, has_ps_rel, offers_prop_rel, has_cs_rel, for_type_rel,
            pa_subzone, biz_type,
            (CASE
                WHEN size(all_comps) = 0
                THEN []
                ELSE apoc.coll.randomItems(all_comps, 3, false)
                END
            ) AS eg_comps

        RETURN ad, hp, pop, prop, cs,
            has_ad_rel, has_hp_rel, has_ps_rel, offers_prop_rel, has_cs_rel, for_type_rel,
            pa_subzone, biz_type, eg_comps
    }

    OPTIONAL MATCH (eg_comp:Competitor)
    WHERE eg_comp.venue_name IN eg_comps
    OPTIONAL MATCH (eg_comp)-[loc_in_rel:LOCATED_IN]->(planning_area)
    OPTIONAL MATCH (eg_comp)-[of_type_rel:OF_TYPE]->(venue_type)
    WITH 
        collect(DISTINCT
            (CASE
                WHEN eg_comp IS NOT NULL
                THEN eg_comp.venue_name + " [" + head(labels(eg_comp)) + "] " + apoc.convert.toJson(properties(eg_comp)) + " - " + type(loc_in_rel) + " -> " + pa_subzone + " [" + head(labels(planning_area)) + "] " + apoc.convert.toJson(properties(planning_area)) + "\n" +
                eg_comp.venue_name + " [" + head(labels(eg_comp)) + "] " + apoc.convert.toJson(properties(eg_comp)) + " - " + type(of_type_rel) + " -> " + venue_type.type_name + " [" + head(labels(venue_type)) + "] " + apoc.convert.toJson(properties(venue_type))
                ELSE ""
                END
            )
        ) AS comp_graph_lines,
        venue_type, planning_area,
        ad, hp, pop, prop, cs,
        has_ad_rel, has_hp_rel, has_ps_rel, offers_prop_rel, has_cs_rel, for_type_rel,
        pa_subzone, biz_type

    RETURN
        "Subgraph of information regarding opening a/an " + biz_type + " in " + pa_subzone + ":\n" +
        (CASE
            WHEN ad IS NULL OR size(keys(properties(ad))) = 0
            THEN ""
            ELSE
                pa_subzone + " [" + head(labels(planning_area)) + "] " + apoc.convert.toJson(properties(planning_area)) +
                " - " + type(has_ad_rel) + " -> " +
                ad.name + " [" + head(labels(ad)) + "] " + apoc.convert.toJson(properties(ad))
            END
        ) + "\n" +
        (CASE
            WHEN hp IS NULL OR size(keys(properties(hp))) = 0
            THEN ""
            ELSE
                pa_subzone + " [" + head(labels(planning_area)) + "] " + apoc.convert.toJson(properties(planning_area)) +
                " - " + type(has_hp_rel) + " -> " +
                hp.name + " [" + head(labels(hp)) + "] " + apoc.convert.toJson(properties(hp))
            END
        ) + "\n" +
        (CASE
            WHEN pop IS NULL OR size(keys(properties(pop))) = 0
            THEN ""
            ELSE
                pa_subzone + " [" + head(labels(planning_area)) + "] " + apoc.convert.toJson(properties(planning_area)) +
                " - " + type(has_ps_rel) + " -> " +
                pop.name + " [" + head(labels(pop)) + "] " + apoc.convert.toJson(properties(pop))
            END
        ) + "\n" +
        (CASE
            WHEN prop IS NULL OR size(keys(properties(prop))) = 0
            THEN ""
            ELSE
                pa_subzone + " [" + head(labels(planning_area)) + "] " + apoc.convert.toJson(properties(planning_area)) +
                " - " + type(offers_prop_rel) + " -> " +
                "Average property prices in " + pa_subzone + " [" + head(labels(prop)) + "] " + apoc.convert.toJson(properties(prop))
            END
        ) + "\n" +
        (CASE
            WHEN cs IS NULL OR size(keys(properties(cs))) = 0
            THEN ""
            ELSE
                pa_subzone + " [" + head(labels(planning_area)) + "] " + apoc.convert.toJson(properties(planning_area)) + " - " + type(has_cs_rel) + " -> " + cs.name + " [" + head(labels(cs)) + "] " + apoc.convert.toJson(properties(cs)) + "\n" +
                cs.name + " [" + head(labels(cs)) + "] " + apoc.convert.toJson(properties(cs)) + " - " + type(for_type_rel) + " -> " + venue_type.type_name + " [" + head(labels(venue_type)) + "] " + apoc.convert.toJson(properties(venue_type)) + "\n" +
                reduce(acc = "", line IN comp_graph_lines | acc + line + "\n")
            END
        ) AS output
    """

    # Define dictionary of predefined Cypher queries mapped to user intent
    queries_dict = {
        "competitor information in given planning area": comp_info_for_planning_area_query,
        "competitor information of given business type in 5 planning areas with highest competitor scores": comp_info_for_biz_type_query,
        "competitor information of given business type in given planning area": specific_comp_info_query,
        "population statistics in given planning area": pop_stats_query,
        "age distribution in given planning area": age_distr_query,
        "housing profile in given planning area": house_prof_query,
        "average property pricing by property type in given planning area": prop_price_query,
        "available properties in given planning area": avail_prop_query,
        "location suggestion given a business type": loc_rec_query,
        "business type suggestion given a planning area": biz_rec_query,
        "business advice for given venue type at given planning area": biz_advice_query
    }

    return queries_dict