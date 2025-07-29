# Jira MCP Server

This project provides a powerful, natural language interface for interacting with Jira. It uses a CrewAI agent powered by Google's Gemini model to understand user prompts and perform actions like creating, searching, validating and updating Jira issues.

The backend is built with FastAPI, and a user-friendly web interface is provided with Streamlit.

## 🚀 Features

The agent can understand natural language requests to perform the following Jira actions:

- **Get Issue Details**: Retrieve full details for a specific issue key (e.g., `SCRUM-123`).
- **Search Issues**: Find issues using complex JQL queries derived from plain English.
- **Create Issues**: Create new tasks, stories, or bugs in any accessible project.
- **Add Comments**: Add comments to existing issues.
- **Transition Issues**: Change the status of an issue (e.g., from 'To Do' to 'In Progress').
- **Validate Projects**: Check if a project key is valid before performing actions.

## 🏛️ Architecture

The application consists of two main components that work together:

1.  **FastAPI Backend (`main.py`)**:

    - Exposes a single endpoint (`/invoke`).
    - Receives a natural language prompt.
    - Initializes a CrewAI agent ("Jira Product Manager").
    - The agent uses the Gemini LLM to decide which Jira tool to use based on the prompt.
    - Executes the tool and returns the result.

2.  **Streamlit Frontend (`streamlit_app.py`)**:
    - Provides a simple web UI to enter a prompt.
    - Sends the prompt to the FastAPI backend.
    - Displays the agent's final response.

```
User -> [Streamlit UI] --(HTTP POST)--> [FastAPI Backend] --(CrewAI)--> [Jira Agent] --(Jira API)--> [Jira Cloud/Server]
                                                                             |
                                                                             +-----> [Gemini LLM]
```

## 🛠️ Setup and Installation

Follow these steps to get the project running locally.

### 1. Prerequisites

- Python 3.9+
- Git

### 2. Clone the Repository

```bash
git clone <your-repository-url>
cd jira-mcp-server
```

### 3. Set Up a Virtual Environment

It's highly recommended to use a virtual environment.

```bash
# For Windows
python -m venv venv
.\venv\Scripts\activate

# For macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 4. Install Dependencies

Install all the required Python packages from `requirements.txt`.

```bash
pip install -r requirements.txt
```

### 5. Configure Environment Variables

Create a `.env` file in the root of the project by copying the example file:

```bash
cp .env.example .env
```

Now, open the `.env` file and fill in your specific credentials:

```dotenv
# .env

# Jira Configuration
JIRA_SERVER=https://your-domain.atlassian.net
JIRA_USERNAME=your-email@example.com
JIRA_API_TOKEN=your_jira_api_token

# Google Gemini API Key
GEMINI_API_KEY=your_gemini_api_key

# Backend URL for Streamlit (optional, defaults to localhost)
FASTAPI_BACKEND_URL=http://127.0.0.1:8000/invoke
```

- **JIRA_API_TOKEN**: You can generate this from your Atlassian account settings.
- **GEMINI_API_KEY**: You can get this from Google AI Studio.

## ▶️ Running the Application

You need to run the backend and frontend in two separate terminals.

### 1. Start the FastAPI Backend

In your first terminal, run:

```bash
uvicorn main:app --reload
```

The server will be available at `http://127.0.0.1:8000`.

### 2. Start the Streamlit Frontend

In your second terminal, run:

```bash
streamlit run streamlit_app.py
```

Your browser should automatically open to the Streamlit interface.

## 💡 How to Use

Once the application is running, navigate to the Streamlit URL and type your request into the text area.

**Examples:**

- `Create a new task in project SCRUM with summary 'Implement login page' and description 'Design and code the user login interface.'`
- `Find all issues in project PROJ that are 'In Progress'.`
- `What are the details of SCRUM-123?`
- `Add a comment to SCRUM-456: 'The backend changes for this task are complete.'`
- `Transition issue SCRUM-789 to 'Done'.`
