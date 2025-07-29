import os
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from crewai import Agent, Crew, Process, Task, LLM

# Import our custom tool
from jira_tools import (
    add_comment_to_issue,
    create_issue,
    validate_project_key,
    get_issue_details,
    search_issues,
    transition_issue
)

# Load environment variables
load_dotenv()

# --- Pydantic Model for Request Body ---
class JiraTaskRequest(BaseModel):
    prompt: str  # The main input is now a natural language prompt


# --- FastAPI App Initialization ---
app = FastAPI(
    title="Jira MCP Server",
    description="A Multi-agent Collaboration Platform for interacting with Jira.",
)


# --- LLM Configuration ---
llm = LLM(
    model="gemini/gemini-1.5-flash-latest",
    temperature=0.1,
    api_key=os.getenv("GEMINI_API_KEY")
)

# --- Crew Execution Logic ---
def run_crew(prompt: str) -> str:
    """Initializes and runs the Jira analysis crew for a given prompt."""
    # Define a more capable agent that can use multiple tools
    jira_product_manager = Agent(
        role="Jira Product Manager",
        goal="Understand user requests, use the available tools to find information in Jira or create new issues, and provide clear, helpful answers. You must validate project keys before creating issues.",
        backstory=(
            "You are an expert product manager with years of experience using Jira. "
            "You are an expert in JQL (Jira Query Language) and can formulate complex queries from natural language. "
            "You are also capable of creating new issues in Jira when requested. "
            "You are cautious and always validate that a project exists before attempting to create an issue in it. "
            "You are skilled at analyzing user requests, deciding which tool to use, and then summarizing the findings or confirming the action."
        ),
        tools=[
            get_issue_details,
            validate_project_key,
            search_issues,
            create_issue,
            add_comment_to_issue,
            transition_issue
        ],
        allow_delegation=False,
        verbose=True,
        llm=llm,
    )
    # Create a generic task that uses the user's prompt
    analysis_task = Task(
        description=prompt,
        expected_output="A clear, concise, and user-friendly answer to the user's request in plain text. "
        "If an issue is created, confirm its key. "
        "If information is retrieved, summarize it in natural language, avoiding raw JSON or technical details unless specifically requested. "
        "For multiple search results, list them clearly with relevant summary information.",
        agent=jira_product_manager,
    )
    jira_crew = Crew(
        agents=[jira_product_manager], tasks=[analysis_task], process=Process.sequential, verbose=True
    )
    return jira_crew.kickoff()


# --- API Endpoints ---
@app.post("/invoke")
async def invoke_agent(request: JiraTaskRequest):
    """Endpoint to invoke the Jira agent with a natural language prompt."""
    try:
        if not request.prompt:
            raise HTTPException(status_code=400, detail="Prompt cannot be empty.")
        result = run_crew(request.prompt)
        return {"response": result}
    except Exception as e:
        # It's good practice to log the exception on the server
        print(f"An error occurred: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
def read_root():
    return {"status": "Jira MCP Server is running."}
