import streamlit as st
import requests
import json
import os

# --- Configuration ---
# Assuming your FastAPI app runs on http://127.0.0.1:8000
# If your FastAPI app is deployed elsewhere, update this URL.
FASTAPI_ENDPOINT = os.getenv("FASTAPI_BACKEND_URL", "http://127.0.0.1:8000/invoke")

# --- Streamlit UI ---
st.set_page_config(page_title="Jira Agent Interface", layout="centered")

st.title("🚀 Jira Agent Interface")

st.subheader("💡 How to use the Jira Agent:")
with st.expander("Click to see available commands and examples"):
    st.markdown("""
    This agent can interact with Jira using the following capabilities:

    * **Jira Issue Retriever Tool**: Get detailed information about a specific Jira issue.
        * _Example:_ `What are the details of SCRUM-123?`

    * **Jira Issue Searcher Tool**: Find Jira issues based on criteria (JQL).
        * _Example:_ `Find all issues in project SCRUM that are 'In Progress'.`

    * **Jira Issue Creator Tool**: Create new issues in a specified project.
        * _Example:_ `Create a new task in project PROJ with summary 'Implement login page' and description 'Design and code the user login interface.'`

    * **Jira Project Validator Tool**: Check if a Jira project key exists and is accessible.
        * _Example:_ `Is 'MYPROJECT' a valid Jira project?`

    * **Jira Issue Commenter Tool**: Add comments to an existing Jira issue.
        * _Example:_ `Add a comment to SCRUM-456: 'The backend changes for this task are complete.'`

    * **Jira Issue Transitioner Tool**: Change the status/workflow of a Jira issue.
        * _Example:_ `Transition issue SCRUM-789 to 'Done'.`

    ---
    **Pro Tip:** Be specific in your requests, especially with project keys and issue keys!
    """)

st.markdown("Enter your request below to interact with the Jira Agent.")

# Input for the user's prompt
user_prompt = st.text_area(
    "Your Request:",
    placeholder="e.g., 'Create a new Jira task in the SCRUM project with the summary 'Fix bug in login flow' and description 'Users are unable to log in due to an unhandled exception in the authentication service.''"
)

# Button to send the request
if st.button("Send to Jira Agent"):
    if user_prompt:
        with st.spinner("Sending request to Jira Agent..."):
            try:
                # Prepare the payload for the FastAPI endpoint
                payload = {"prompt": user_prompt}
                headers = {"Content-Type": "application/json"}

                # Make the POST request to your FastAPI application
                response = requests.post(FASTAPI_ENDPOINT, data=json.dumps(payload), headers=headers)

                # Check if the request was successful
                if response.status_code == 200:
                    full_api_response = response.json()
                    st.success("Request successful!")
                    st.subheader("Agent Response:")

                    # Get the content associated with the 'response' key
                    agent_output = full_api_response.get("response")

                    agent_response_content = "No user-friendly response content found."

                    if isinstance(agent_output, dict):
                        # If the 'response' is a dictionary (like the CrewOutput structure)
                        agent_response_content = agent_output.get("raw", "No 'raw' content found in agent response dictionary.")
                    elif isinstance(agent_output, str):
                        # If the 'response' is a direct string
                        agent_response_content = agent_output
                    elif agent_output is None:
                        agent_response_content = "Agent did not return any response content."
                    else:
                        # Fallback for unexpected types; display raw output for debugging
                        st.json(agent_output)
                        agent_response_content = "Unexpected agent response format. Displayed raw output above for debugging."
                    st.write(agent_response_content)
                else:
                    st.error(f"Error from agent: Status Code {response.status_code}")
                    st.json(response.json()) # Display the full error response from FastAPI
            except requests.exceptions.ConnectionError:
                st.error("Could not connect to the FastAPI server. Please ensure it is running at "
                         f"`{FASTAPI_ENDPOINT}`.")
            except json.JSONDecodeError:
                st.error("Received an invalid JSON response from the server.")
                st.write(response.text) # Show raw text if JSON decoding fails
            except Exception as e:
                st.error(f"An unexpected error occurred: {e}")
    else:
        st.warning("Please enter a request before sending.")

st.markdown("---")