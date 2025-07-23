



#import sys; print(sys.executable)
from google.adk.agents import Agent
from google.adk.tools import google_search




root_agent = Agent(
    name="linkedin-agent",
    model="gemini-2.0-flash", # Or your preferred Gemini model
    instruction=".",
    description="An automated linkedin posting Agent",
    tools=[google_search]
)