import os
from dotenv import load_dotenv
from supabase import create_client, Client

def fetch_industrial_properties(supabase: Client):
    """
    Retrieve all records from the industrial_properties table.
    """
    response = supabase.table("industrial_properties").select("*").execute()
    # Convert the Pydantic model to a dict
    response_dict = response.dict()
    if response_dict.get("error"):
        raise Exception(f"Error fetching data: {response_dict.get('error')}")
    return response_dict.get("data")

def calculate_average_prices(records):
    """
    Calculate the average price for each combination of subzone, sub_category, and listing_type.
    Returns a list of dictionaries ready for insertion into the new table.
    """
    groups = {}
    
    for rec in records:
        # Retrieve relevant fields
        subzone = rec.get("subzone")
        sub_category = rec.get("sub_category")
        listing_type = rec.get("listing_type")
        price_str = rec.get("price")
        
        # Skip record if any key fields are missing
        if not subzone or not sub_category or not listing_type or not price_str:
            continue

        try:
            price = float(price_str)
        except ValueError:
            continue  # Skip rows with invalid price
        
        key = (subzone.strip().upper(), sub_category.strip().lower(), listing_type.strip().lower())
        groups.setdefault(key, []).append(price)
    
    # Calculate average for each group
    aggregated_data = []
    for key, prices in groups.items():
        avg_price = sum(prices) / len(prices)
        aggregated_data.append({
            "subzone": key[0],
            "sub_category": key[1],
            "listing_type": key[2],
            "average_price": round(avg_price, 2)
        })
    return aggregated_data

def insert_aggregated_data(supabase: Client, data):
    """
    Inserts the aggregated average pricing data into a new table (avg_industrial_prices).
    """
    response = supabase.table("avg_industrial_prices").insert(data).execute()
    # Convert the response to a dict for safe access
    response_dict = response.dict()
    if response_dict.get("error"):
        raise Exception(f"Error inserting aggregated data: {response_dict.get('error')}")
    print("Aggregated data successfully inserted into avg_industrial_prices.")

def main():
    # Load environment variables from .env file
    load_dotenv()
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")
    
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

    # Fetch records from industrial_properties
    print("Fetching industrial_properties records...")
    records = fetch_industrial_properties(supabase)

    # Calculate averages by grouping records (by subzone, sub_category, listing_type)
    print("Calculating average prices...")
    aggregated = calculate_average_prices(records)
    
    # Display aggregated data for verification
    print("Aggregated Data:")
    for row in aggregated:
        print(row)
    
    # Insert aggregated data into the new table
    print("Inserting aggregated data into the new table...")
    insert_aggregated_data(supabase, aggregated)
    print("Process complete.")

if __name__ == "__main__":
    main()