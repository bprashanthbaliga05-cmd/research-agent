from agent_langgraph import run_langgraph_agent
from agent_crewai import run_crewai_agent
from agent_groq import run_agent_groq

pending_approvals = {}

async def run_agent(topic: str, session_id: str, framework: str = "langgraph"):
    if framework == "crewai":
        print("crewai")
        async for event in run_crewai_agent(topic, session_id, pending_approvals):
            yield event
    elif framework == "langgraph":
        print("Langgraph")
        async for event in run_langgraph_agent(topic, session_id, pending_approvals):
            yield event
    else:
        print("Groq")
        async for event in run_agent_groq(topic, session_id, pending_approvals):
            yield event