import os
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from crewai import Agent, Crew, Process, Task, LLM
from fastapi.responses import JSONResponse

# Import our custom tool
from jira_tools import (
    add_comment_to_issue,
    create_issue,
    validate_project_key,
    get_issue_details,
    search_issues,
    transition_issue,
    jira_client
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

@app.get("/context/issue/{issue_key}", tags=["MCP Context API"])
def get_issue_context(issue_key: str):
    """
    MCP-compatible context document for a single Jira issue.
    Returns structured JSON with fields useful for LLMs and agents.
    """
    if not jira_client:
        raise HTTPException(status_code=500, detail="Jira client is not initialized.")
    
    try:
        issue = jira_client.issue(issue_key)
        context = {
            "type": "issue",
            "key": issue.key,
            "summary": issue.fields.summary,
            "description": issue.fields.description or "No description provided.",
            "status": issue.fields.status.name,
            "assignee": issue.fields.assignee.displayName if issue.fields.assignee else "Unassigned",
            "project": issue.fields.project.key,
            "url": f"{os.getenv('JIRA_SERVER')}/browse/{issue.key}"
        }
        return JSONResponse(content=context)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving issue context: {e}")
    
@app.get("/context/issues/{project_key}", tags=["MCP Context API"])
def get_issues_for_project(project_key: str):
    """
    MCP-compatible context documents for issues in a Jira project.
    Returns a list of structured JSON objects, one per issue.
    """
    if not jira_client:
        raise HTTPException(status_code=500, detail="Jira client is not initialized.")

    try:
        jql = f"project = {project_key} ORDER BY created DESC"
        issues = jira_client.search_issues(jql, maxResults=10)

        result = []
        for issue in issues:
            issue_data = {
                "type": "issue",
                "key": issue.key,
                "summary": getattr(issue.fields, "summary", "No summary"),
                "description": getattr(issue.fields, "description", "No description provided."),
                "status": getattr(issue.fields.status, "name", "Unknown"),
                "assignee": (
                    getattr(issue.fields.assignee, "displayName", None)
                    if issue.fields.assignee else "Unassigned"
                ),
                "project": getattr(issue.fields.project, "key", "Unknown"),
                "url": f"{os.getenv('JIRA_SERVER')}/browse/{issue.key}"
            }
            result.append(issue_data)

        return JSONResponse(content=result)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving issues: {str(e)}")

@app.get("/context/projects", tags=["MCP Context API"])
def get_all_projects():
    """
    MCP-compatible context documents for all accessible Jira projects.
    Returns a list of structured JSON objects, one per project.
    """
    if not jira_client:
        raise HTTPException(status_code=500, detail="Jira client is not initialized.")

    try:
        projects = jira_client.projects()

        result = []
        for project in projects:
            result.append({
                "type": "project",
                "key": project.key,
                "name": project.name,
                "id": project.id,
                "url": f"{os.getenv('JIRA_SERVER')}/browse/{project.key}"
            })

        return JSONResponse(content=result)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving projects: {str(e)}")
