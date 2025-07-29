import os
from dotenv import load_dotenv
from jira import JIRA
from jira.exceptions import JIRAError
from typing import Optional
from crewai.tools import tool

# Load environment variables from the .env file
load_dotenv()

# Initialize the Jira client once to be reused by tools
try:
    jira_client = JIRA(
        server=os.getenv("JIRA_SERVER"),
        basic_auth=(os.getenv("JIRA_USERNAME"), os.getenv("JIRA_API_TOKEN")),
    )
    print("\n✅ Listing accessible Jira projects:\n")
    for project in jira_client.projects():
        print(f"{project.key} - {project.name}")

except Exception as e:
    print(f"Warning: Failed to initialize Jira client in jira_tools.py: {e}")
    jira_client = None


@tool("Jira Issue Retriever Tool")
def get_issue_details(issue_key: str) -> str:
    """
    Retrieves the details of a specific Jira issue.
    The input to this tool must be a valid Jira issue key, like 'PROJ-123'.
    It returns a string with the issue's summary, status, and assignee.
    """
    if not jira_client:
        return "Error: Jira client is not initialized. Check your .env configuration."
    try:
        issue = jira_client.issue(issue_key)
        assignee = issue.fields.assignee
        assignee_name = assignee.displayName if assignee else "Unassigned"
        return f"Issue: {issue.key}, Summary: {issue.fields.summary}, Status: {issue.fields.status.name}, Assignee: {assignee_name}"
    except Exception as e:
        return f"Error retrieving issue {issue_key}: {e}"


@tool("Jira Search Tool")
def search_issues(jql_query: str) -> str:
    """
    Searches for Jira issues using a JQL (Jira Query Language) query.
    The input must be a valid JQL string.
    For example: 'project = "PROJ" AND status = "To Do" ORDER BY created DESC'
    Returns a list of issue keys and their summaries, or an error message.
    """
    if not jira_client:
        return "Error: Jira client is not initialized. Check your .env configuration."
    try:
        issues = jira_client.search_issues(jql_query, maxResults=10)  # Limit results to avoid huge outputs
        if not issues:
            return f"No issues found for JQL query: '{jql_query}'"
        results = [f"- {issue.key}: {issue.fields.summary}" for issue in issues]
        return "Found issues:\n" + "\n".join(results)
    except Exception as e:
        return f"Error searching for issues with JQL '{jql_query}': {e}"

@tool("Jira Issue Creator Tool")
def create_issue(project_key: str, summary: str, description: str, issue_type: Optional[str] = "Task") -> str:
    """
    Creates a new Jira issue with the given project key, summary, description, and issue type.
    The input must be the project key (e.g., 'PROJ'), a summary string, a description string,
    and an optional issue type string (defaults to 'Task').
    Returns the key of the newly created issue (e.g., 'PROJ-123') or an error message.
    """
    if not jira_client:
        return "Error: Jira client is not initialized. Check your .env configuration."
    try:
        issue_dict = {
            'project': {'key': project_key},
            'summary': summary,
            'description': description, 
            'issuetype': {'name': issue_type},
        }
        new_issue = jira_client.create_issue(fields=issue_dict)
        return f"Successfully created issue {new_issue.key}."
    except JIRAError as e:
        if "issuetype" in e.text.lower():
            try:
                project = jira_client.project(project_key)
                available_types = [it.name for it in project.issueTypes]
                return (
                    f"Error: Failed to create issue. The issue type '{issue_type}' is likely invalid for project '{project_key}'. "
                    f"Please use one of the following available issue types: {', '.join(available_types)}."
                )
            except Exception:
                return f"Error: Failed to create issue with type '{issue_type}'. It might be an invalid issue type for project '{project_key}'. Original error: {e.text}"
        return f"Error creating issue: {e.text}"
    except Exception as e:
        return f"Error creating issue: {e}"

@tool("Jira Project Validator Tool")
def validate_project_key(project_key: str) -> str:
    """
    Validates if a Jira project key exists and is accessible.
    The input must be a Jira project key, like 'PROJ'.
    Returns a confirmation message if the project exists, or an error message if it does not.
    This tool should be used before attempting to create an issue if there is any uncertainty about the project key.
    """
    if not jira_client:
        return "Error: Jira client is not initialized. Check your .env configuration."
    try:
        project = jira_client.project(project_key)
        return f"Success: Project with key '{project.key}' and name '{project.name}' is valid and accessible."
    except JIRAError as e:
        if e.status_code == 404:
            return f"Error: Project with key '{project_key}' was not found. Please provide a correct project key."
        return f"Error: An error occurred while validating project '{project_key}'. You may not have permission to view it. Details: {e.text}"
    except Exception as e:
        return f"An unexpected error occurred while validating project '{project_key}': {e}"


@tool("Jira Comment Adder Tool")
def add_comment_to_issue(issue_key: str, comment_body: str) -> str:
    """
    Adds a comment to a specific Jira issue.
    The input must be a valid Jira issue key (e.g., 'PROJ-123') and the text for the comment.
    Returns a confirmation message upon success or an error message.
    """
    if not jira_client:
        return "Error: Jira client is not initialized. Check your .env configuration."
    try:
        jira_client.add_comment(issue_key, comment_body)
        return f"Successfully added comment to issue {issue_key}."
    except JIRAError as e:
        return f"Error adding comment to issue {issue_key}: {e.text}"
    except Exception as e:
        return f"An unexpected error occurred while adding a comment to {issue_key}: {e}"
    
@tool("Jira Issue Transitioner Tool")
def transition_issue(issue_key: str, transition_name: str) -> str:
    """
    Transitions a Jira issue to a new status (workflow step).
    The input to this tool must be a valid Jira issue key (e.g., 'PROJ-123')
    and the exact name of the desired transition (e.g., 'Done', 'In Progress', 'To Do').
    The tool will find the correct transition ID and attempt to move the issue.
    Returns a success message or an error message.
    """
    if not jira_client:
        return "Error: Jira client is not initialized. Check your .env configuration."
    try:
        issue = jira_client.issue(issue_key)
        
        # Get all available transitions for the issue
        transitions = jira_client.transitions(issue)
        
        transition_id = None
        for t in transitions:
            if t['name'].lower() == transition_name.lower(): # Case-insensitive match
                transition_id = t['id']
                break
        
        if not transition_id:
            available_transitions = ", ".join([t['name'] for t in transitions])
            return (f"Error: Transition '{transition_name}' not found for issue '{issue_key}'. "
                    f"Available transitions are: {available_transitions}.")

        # Perform the transition
        jira_client.transition_issue(issue, transition_id)
        
        # Verify the new status (optional, but good for confirmation)
        updated_issue = jira_client.issue(issue_key)
        return f"Successfully transitioned issue '{issue_key}' to status '{updated_issue.fields.status.name}' using transition '{transition_name}'."
    
    except JIRAError as e:
        return f"Error transitioning issue '{issue_key}' with transition '{transition_name}': {e.text}"
    except Exception as e:
        return f"An unexpected error occurred while transitioning issue '{issue_key}': {e}"
