from neo4j import GraphDatabase
from config import load_config

class Neo4jConnector:
    """Class to handle Neo4j database interactions"""
    
    def __init__(self):
        config = load_config()
        neo4j_config = config.get('neo4j', {})
        
        self.uri = neo4j_config.get('uri')
        self.username = neo4j_config.get('username')
        self.password = neo4j_config.get('password')
        self.database = neo4j_config.get('database')
        
        self.driver = GraphDatabase.driver(
            self.uri, 
            auth=(self.username, self.password)
        )
    
    def close(self):
        """Close the Neo4j connection"""
        if self.driver:
            self.driver.close()
    
    def create_location_node(self, location_data):
        """Create a location node in the knowledge graph
        
        Args:
            location_data (dict): Location data to create node from
            
        Returns:
            dict: Created node data
        """
        with self.driver.session(database=self.database) as session:
            result = session.execute_write(self._create_location_node_tx, location_data)
            return result
    
    def _create_location_node_tx(self, tx, location_data):
        """Transaction function to create a location node"""
        query = """
        MERGE (l:Location {id: $id})
        SET l.name = $name,
            l.address = $address,
            l.latitude = $latitude,
            l.longitude = $longitude,
            l.location_type = $location_type,
            l.rating = $rating
        RETURN l
        """
        result = tx.run(query, **location_data)
        record = result.single()
        return record['l'] if record else None
    
    def create_relationship(self, source_id, target_id, relationship_type, properties=None):
        """Create a relationship between two nodes
        
        Args:
            source_id (str): ID of the source node
            target_id (str): ID of the target node
            relationship_type (str): Type of relationship
            properties (dict, optional): Properties of the relationship
            
        Returns:
            bool: True if successful, False otherwise
        """
        properties = properties or {}
        
        with self.driver.session(database=self.database) as session:
            result = session.execute_write(
                self._create_relationship_tx, 
                source_id, 
                target_id, 
                relationship_type, 
                properties
            )
            return result
    
    def _create_relationship_tx(self, tx, source_id, target_id, relationship_type, properties):
        """Transaction function to create a relationship"""
        query = f"""
        MATCH (a:Location {{id: $source_id}})
        MATCH (b:Location {{id: $target_id}})
        MERGE (a)-[r:{relationship_type}]->(b)
        """
        
        # Add properties if any
        if properties:
            props_string = ", ".join(f"r.{key} = ${key}" for key in properties.keys())
            query += f" SET {props_string}"
        
        query += " RETURN r"
        
        params = {
            "source_id": source_id,
            "target_id": target_id,
            **properties
        }
        
        result = tx.run(query, **params)
        return result.single() is not None
    
    def create_proximity_relationships(self, distance_threshold=2.0):
        """Create NEAR relationships between locations within a certain distance
        
        Args:
            distance_threshold (float): Maximum distance in kilometers to create NEAR relationship
            
        Returns:
            int: Number of relationships created
        """
        with self.driver.session(database=self.database) as session:
            result = session.execute_write(self._create_proximity_relationships_tx, distance_threshold)
            return result
    
    def _create_proximity_relationships_tx(self, tx, distance_threshold):
        """Transaction function to create proximity relationships"""
        # Haversine formula in Cypher to calculate distance between coordinates
        query = """
        MATCH (a:Location), (b:Location)
        WHERE a.id <> b.id
        AND NOT EXISTS((a)-[:NEAR]-(b))
        WITH a, b, 
             6371 * acos(cos(radians(a.latitude)) * cos(radians(b.latitude)) * 
             cos(radians(b.longitude) - radians(a.longitude)) + 
             sin(radians(a.latitude)) * sin(radians(b.latitude))) AS distance
        WHERE distance < $distance_threshold
        MERGE (a)-[r:NEAR]->(b)
        SET r.distance = distance
        RETURN count(r) as count
        """
        
        result = tx.run(query, distance_threshold=distance_threshold)
        record = result.single()
        return record['count'] if record else 0
    
    def get_location_by_id(self, location_id):
        """Get a location by its ID
        
        Args:
            location_id (str): ID of the location to fetch
            
        Returns:
            dict: Location data
        """
        with self.driver.session(database=self.database) as session:
            result = session.execute_read(self._get_location_by_id_tx, location_id)
            return result
    
    def _get_location_by_id_tx(self, tx, location_id):
        """Transaction function to get a location by ID"""
        query = """
        MATCH (l:Location {id: $id})
        RETURN l
        """
        result = tx.run(query, id=location_id)
        record = result.single()
        return record['l'] if record else None 