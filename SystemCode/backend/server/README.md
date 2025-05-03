# Python OpenAI Server

This is a simple Flask server that provides an API endpoint to interact with OpenAI's GPT-3.5 Turbo model.

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

3. Create a `.env` file in the server directory with your OpenAI API key:
   ```
   OPENAI_API_KEY=your_openai_api_key_here
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
