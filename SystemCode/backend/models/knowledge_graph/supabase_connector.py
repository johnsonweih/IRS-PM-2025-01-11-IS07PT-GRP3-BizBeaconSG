from supabase import create_client
import os
from dotenv import load_dotenv
from config import load_config
from table_config import get_table_name

class SupabaseConnector:
    """Class to handle Supabase data extraction"""
    
    def __init__(self):
        load_dotenv()
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_KEY')
        
        if not supabase_url or not supabase_key:
            raise ValueError("Supabase credentials not found in environment variables")
            
        # Initialize client with the current version's API
        self.client = create_client(supabase_url, supabase_key)
        self.table = 'locations'  # Default table
        
    def set_table(self, data_type=None):
        """Change the table being used for queries
        
        Args:
            data_type (str, optional): Type of data to fetch. Defaults to None.
        """
        self.table = get_table_name(data_type)
        
    def fetch_business_data(self, limit: int = 100) -> list:
        """Fetch business data from Supabase with optional limit"""
        try:
            response = self.client.table('properties').select('*').limit(limit).execute()
            return response.data if response.data else []
        except Exception as e:
            print(f"Error fetching location data: {e}")
            return []
        
    def fetch_by_location_type(self, location_type: str, limit: int = 100) -> list:
        """Fetch locations by type from Supabase"""
        try:
            response = self.client.table('locations').select('*').eq('type', location_type).limit(limit).execute()
            return response.data if response.data else []
        except Exception as e:
            print(f"Error fetching locations by type: {e}")
            return []
    
    def fetch_by_geographic_area(self, area: str, limit: int = 100) -> list:
        """Fetch locations by geographic area from Supabase"""
        try:
            response = self.client.table('locations').select('*').eq('area', area).limit(limit).execute()
            return response.data if response.data else []
        except Exception as e:
            print(f"Error fetching locations by geographic area: {e}")
            return [] 