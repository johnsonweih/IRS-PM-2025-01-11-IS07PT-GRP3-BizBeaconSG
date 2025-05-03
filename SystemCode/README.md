# Intelligent Business Location Advisor System

A full-stack application that provides intelligent business location recommendations using OpenAI's GPT model.

## Project Structure

- `frontend/` - React-based web application
- `backend/` - Python Flask server with OpenAI integration

## Frontend Setup

The frontend is built with Create React App. To get started:

1. Navigate to the frontend directory:

   ```bash
   cd frontend
   ```

2. Install dependencies:

   ```bash
   npm install
   ```

3. Start the development server:
   ```bash
   npm start
   ```
   The app will be available at [http://localhost:3000](http://localhost:3000)

### Available Frontend Scripts

- `npm start` - Runs the app in development mode
- `npm test` - Launches the test runner
- `npm run build` - Builds the app for production
- `npm run eject` - Ejects from Create React App (one-way operation)

## Backend Setup

The backend is a Python Flask server that interfaces with OpenAI's API.

1. Navigate to the backend server directory:

   ```bash
   cd backend/server
   ```

2. Create and activate a virtual environment:

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file with your OpenAI API key:

   ```
   OPENAI_API_KEY=your_openai_api_key_here
   ```

5. Start the server:
   ```bash
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

- Frontend errors will be displayed in the browser console
- Backend API errors will return a 500 status code with an error message

## Learn More

- [Create React App Documentation](https://facebook.github.io/create-react-app/docs/getting-started)
- [React Documentation](https://reactjs.org/)
- [Flask Documentation](https://flask.palletsprojects.com/)
- [OpenAI API Documentation](https://platform.openai.com/docs/api-reference)
