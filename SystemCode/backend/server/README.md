# Python OpenAI Server

This is a simple Flask server that provides an API endpoint to interact with OpenAI's GPT-4o model.

## Setup

1. Create a virtual environment (recommended):

   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:

   ```
   pip install -r requirements.txt
   ```

3. Create a `.env` file with your OpenAI API key and Neo4j and Supabase credentials:

   ```bash
   OPENAI_API_KEY=your_openai_api_key_here

   # Neo4j credentials
   NEO4J_URI=neo4j+s:your_neo4j_uri_here
   NEO4J_USERNAME=neo4j
   NEO4J_PASSWORD=your_neo4j_pwd_here

   # Supabase credentials
   SUPABASE_URL=your_supabase_url_here
   SUPABASE_KEY=your_supabase_key_here
   ```

## Running the Server

Start the server with:

```
python app.py
```

The server will run on port 4000 by default.

## API Endpoints

### POST /respond

Send a message to the OpenAI API and get a response.

**Request Body:**

```json
{
  "message": "Your message here"
}
```

**Response:**

```json
{
  "botResponse": "OpenAI's response here"
}
```

## Error Handling

If there's an error with the OpenAI API, the server will return a 500 status code with an error message.
