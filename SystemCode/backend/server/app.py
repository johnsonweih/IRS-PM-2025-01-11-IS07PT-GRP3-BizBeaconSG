import os
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from flask_cors import CORS
import openai
from langchain_openai import ChatOpenAI
from rag import invoke_rag_chain
from supabase import create_client, Client
import requests
from bs4 import BeautifulSoup

print("🔵 [APP] Initializing Flask application...")

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Initialize Supabase client
supabase: Client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

# Set OpenAI API key
openai.api_key = os.getenv("OPENAI_API_KEY")

# System message defining the AI's role
SYSTEM_MESSAGE = """You are an intelligent Business Location Advisor. Your role is to help clients determine:
1. The best type of business to start based on their interests, skills, and market conditions
2. The ideal location for their business considering factors like:
   - Demographics and target market
   - Competition and market saturation
   - Cost of operations and real estate
   - Local regulations and zoning laws
   - Infrastructure and accessibility
   - Growth potential and economic indicators

IMPORTANT: Always format your responses using markdown syntax:
- Use headings (##, ###) for main sections
- Use bullet points (-) for lists
- Use bold (**text**) for emphasis
- Use code blocks (```) for data/statistics
- Use tables when presenting structured data
- Use blockquotes (>) for important notes

Provide detailed, well-reasoned advice while considering the client's specific situation, budget, and goals, and in the context of the information retrieved from the knowledge graph.
Always explain your reasoning and provide multiple options when possible."""

print("🔵 [APP] Flask application initialized successfully")

# Route to handle POST requests
@app.route("/respond", methods=["POST"])
def respond():
    try:
        print("\n🔵 [APP] Received new request")
        data = request.json
        message = data.get("message")
        chat_history = data.get("chat_history", [])
        print(f"🔵 [APP] User message: {message}")
        print(f"🔵 [APP] Chat history length: {len(chat_history)}")

        print("🔵 [APP] Initializing LLM...")
        llm = ChatOpenAI(
            temperature=0.2,  # Slightly increase temperature for more creative responses
            model_name="gpt-4o",  # Use GPT-4 for better reasoning and analysis
            streaming=True  # Enable streaming for faster initial responses
        )
        print("🔵 [APP] LLM initialized, invoking RAG chain...")
        
        bot_response = invoke_rag_chain(llm, message, chat_history)
        print(f"🔵 [APP] RAG Response received: {bot_response[:100]}...")
        
        print("🔵 [APP] Sending response back to client")
        return jsonify({"botResponse": bot_response})
    except Exception as error:
        print(f"🔵 [APP] Error: {str(error)}")
        return jsonify({"error": "Failed to generate response from OpenAI"}), 500

@app.route('/api/metadata', methods=['POST'])
def get_metadata():
    try:
        data = request.get_json()
        url = data.get('url')
        
        if not url:
            print("❌ [METADATA] Error: URL is required")
            return jsonify({'error': 'URL is required'}), 400
            
        # Clean the URL by removing any trailing punctuation and whitespace
        url = url.strip().rstrip(').,;')
        print(f"🔵 [METADATA] Received and cleaned URL: {url}")
        
        # Query Supabase for the property using listing_url
        print(f"🔵 [METADATA] Constructing Supabase query:")
        print(f"🔵 [METADATA] Table: industrial_properties")
        print(f"🔵 [METADATA] Filter: listing_url = {url}")
        
        query = supabase.table('industrial_properties').select('*').eq('listing_url', url)
        print(f"🔵 [METADATA] Executing query: {query}")
        
        response = query.execute()
        print(f"🔵 [METADATA] Raw Supabase response: {response}")
        print(f"🔵 [METADATA] Response data: {response.data}")
        print(f"🔵 [METADATA] Response count: {len(response.data) if response.data else 0}")
        
        if not response.data:
            print(f"❌ [METADATA] No property found for listing_url: {url}")
            return jsonify({'error': 'Property not found'}), 404
            
        property_data = response.data[0]
        print(f"✅ [METADATA] Found property: {property_data.get('address_name', 'Unknown Address')}")
        
        # Handle image URL
        photo_url = property_data.get('photo_url', '')
        if photo_url:
            # If the URL is relative, make it absolute
            if not photo_url.startswith(('http://', 'https://')):
                # Assuming the base URL is from the listing_url
                base_url = '/'.join(url.split('/')[:3])  # Get the domain
                photo_url = f"{base_url}{photo_url}"
            print(f"🔵 [METADATA] Processed image URL: {photo_url}")
        
        # Format the response
        metadata = {
            'title': f"{property_data.get('property_segment', '')} - {property_data.get('address_name', '')}",
            'description': property_data.get('description', ''),
            'image': photo_url,
            'price': property_data.get('price', 0),
            'area_size': property_data.get('area_size', 0),
            'area_ppsf': property_data.get('area_ppsf', 0),
            'address': property_data.get('address_name', ''),
            'district': property_data.get('district_number', ''),
            'postal_code': property_data.get('postal_code', ''),
            'closest_mrt': property_data.get('closest_mrt', ''),
            'planning_area': property_data.get('planning_area', ''),
            'subzone': property_data.get('subzone', ''),
            'listing_url': property_data.get('listing_url', '')
        }
        
        print(f"✅ [METADATA] Returning metadata for property: {metadata['title']}")
        return jsonify(metadata)
        
    except Exception as e:
        print(f"❌ [METADATA] Error: {str(e)}")
        print(f"❌ [METADATA] Error type: {type(e)}")
        return jsonify({'error': str(e)}), 500
    
# Start the server
if __name__ == "__main__":
    port = 4000
    print(f"🔵 [APP] Starting server on port {port}")
    app.run(host="0.0.0.0", port=port, debug=True)
    print(f"🔵 [APP] Server listening on port {port}") 