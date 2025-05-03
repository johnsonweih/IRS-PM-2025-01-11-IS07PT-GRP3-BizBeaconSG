# Knowledge Graph for Business Location Advisor

This module provides the core infrastructure for building and querying a knowledge graph for the Business Location Advisor system. It connects to Supabase for data storage and Neo4j for graph database functionalities.

## Setup

1. Install required dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Create a `.env` file in the `backend/models/knowledge-graph` directory using the provided template:
   ```
   cp .env.template .env
   ```
   
3. Edit the `.env` file with your actual database credentials:
   ```
   # Supabase configuration
   SUPABASE_URL=https://your-project-id.supabase.co
   SUPABASE_KEY=your-supabase-api-key
   
   # Neo4j configuration
   NEO4J_URI=bolt://localhost:7687 
   NEO4J_USERNAME=neo4j
   NEO4J_PASSWORD=your-password
   ```
4. Run the code in this flow to recreate the graph and its contents, it includes the KG Construction, geospatial density analysis and Fuzzy Logic + GNN
	1. aggregate_prices.py
	2. graph_builder.py
	3. node_update.py
	4. populate_competitor_stats.py
	5. update_competitor_count.py
	6. geo_analysis.py
	7. neuro_symbolic.py