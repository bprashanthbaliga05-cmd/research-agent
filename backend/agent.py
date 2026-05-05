import os
import asyncio
from groq import Groq
from dotenv import load_dotenv
from tools import search_with_mcp

load_dotenv()

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Global store for pending approvals
pending_approvals = {}

async def run_agent(topic: str, session_id: str):

    # Step 1 — Input
    yield {"node": "input", "status": "active", "log": f'Topic received: "{topic}"'}
    yield {"node": "input", "status": "done", "log": "Topic queued for planning"}

    # Step 2 — Planner
    yield {"node": "planner", "status": "active", "log": "Breaking topic into subtasks..."}
    planner_response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{
            "role": "user",
            "content": f"Break this research topic into 3 specific search queries: {topic}. Return only a numbered list, nothing else."
        }],
        max_tokens=200
    )
    queries = planner_response.choices[0].message.content

    # HITL — pause and wait for human approval
    approval_event = asyncio.Event()
    pending_approvals[session_id] = {
        "event": approval_event,
        "queries": queries,
        "approved_queries": None
    }

    # Tell frontend to show approval UI
    yield {
        "node": "planner",
        "status": "awaiting_approval",
        "log": "Waiting for your approval...",
        "data": queries
    }

    # Agent pauses here until human approves
    await approval_event.wait()

    # Use human approved/edited queries
    approved_queries = pending_approvals[session_id]["approved_queries"]
    del pending_approvals[session_id]

    yield {"node": "planner", "status": "done", "log": f"Approved! Using: {approved_queries[:80]}..."}

    # Step 3 — Web Search via MCP
    yield {"node": "web_search", "status": "active", "log": "Connecting to Tavily MCP server..."}
    search_context = await search_with_mcp(approved_queries)
    yield {"node": "web_search", "status": "done", "log": "MCP search complete"}

    # Step 4 — Doc Reader
    yield {"node": "doc_reader", "status": "active", "log": "Reading and extracting content..."}
    doc_response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{
            "role": "user",
            "content": f"Summarise these search results in bullet points:\n{search_context}"
        }],
        max_tokens=300
    )
    summary = doc_response.choices[0].message.content
    yield {"node": "doc_reader", "status": "done", "log": "Key points extracted"}

    # Step 5 — Synthesizer
    yield {"node": "synthesizer", "status": "active", "log": "Merging and synthesizing findings..."}
    synth_response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{
            "role": "user",
            "content": f"Synthesize these findings about '{topic}' into a coherent analysis:\n{summary}"
        }],
        max_tokens=400
    )
    synthesis = synth_response.choices[0].message.content
    yield {"node": "synthesizer", "status": "done", "log": "Findings merged successfully"}

    # Step 6 — Report Writer
    yield {"node": "report", "status": "active", "log": "Writing final report..."}
    report_response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{
            "role": "user",
            "content": f"Write a structured research report about '{topic}' based on:\n{synthesis}\n\nFormat with markdown: # Title, ## Executive Summary, ## Key Findings, ## Conclusion."
        }],
        max_tokens=600
    )
    report = report_response.choices[0].message.content
    yield {
        "node": "report",
        "status": "done",
        "log": "Report ready",
        "report": report
    }