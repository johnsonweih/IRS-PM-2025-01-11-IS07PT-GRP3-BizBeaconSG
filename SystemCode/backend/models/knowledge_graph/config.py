import os
import yaml
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def load_config():
    """Load configuration from config.yaml and environment variables"""
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                             'config', 'config.yaml')
    
    with open(config_path, 'r') as file:
        config = yaml.safe_load(file)
    
    # Replace environment variable placeholders
    for db_type in ['supabase', 'neo4j']:
        if db_type in config:
            for key, value in config[db_type].items():
                if isinstance(value, str) and value.startswith('${') and value.endswith('}'):
                    env_var = value[2:-1]
                    config[db_type][key] = os.getenv(env_var, '')
    
    return config 