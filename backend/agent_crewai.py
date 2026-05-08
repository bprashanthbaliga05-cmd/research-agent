import os
import asyncio
from sys import base_prefix
import time
from dotenv import load_dotenv
from crewai import Agent, Task, Crew, LLM
from tools import search_with_mcp

load_dotenv()

# ─── LLM config ───────────────────────────────────────────────
llm = LLM(
    model="groq/llama-3.3-70b-versatile",
    api_key=os.getenv("GROQ_API_KEY"),
    max_tokens=500,          # ← limit output tokens per call
    temperature=0.3          # ← lower = less verbose
)

# ─── Agents ───────────────────────────────────────────────────
planner_agent = Agent(
    role="Planner",
    goal="Break down research topic into 3 search queries",
    backstory="Expert Researcher",
    llm=llm,
    verbose=False
)

synthesizer_agent = Agent(
    role="Research Synthesizer",
    goal="Synthesize information from multiple sources into coherent analysis",
    backstory="Expert at combining information from multiple sources, identifying patterns and key insights",
    llm=llm,
    verbose=False
)

writer_agent = Agent(
    role="Research Report Writer",
    goal="Write clear, structured, professional research reports",
    backstory="Expert technical writer who produces well-structured reports with clear executive summaries and actionable findings",
    llm=llm,
    verbose=False
)

# ─── Streaming wrapper ────────────────────────────────────────

async def run_crewai_agent(topic: str, session_id: str, pending_approvals: dict):
    start_time = time.time()

    yield {"node": "input", "status": "active", "log": f'Topic received: "{topic}"'}
    yield {"node": "input", "status": "done",   "log": "Topic queued for planning"}

    # Step 1 — Planner agent
    yield {"node": "planner", "status": "active", "log": "CrewAI: planner agent working..."}

    plan_task = Task(
        description=f"Break this research topic into 3 specific search queries: {topic}. Return only a numbered list.",
        expected_output="A numbered list of 3 search queries",
        agent=planner_agent
    )

    loop = asyncio.get_event_loop()
    plan_crew = Crew(agents=[planner_agent], tasks=[plan_task], verbose=False, 
    memory=False,     # ← disable crew memory
    cache=False       # ← disable caching overhead
    )
    queries = await loop.run_in_executor(None, lambda: plan_crew.kickoff().raw)

    # HITL pause
    approval_event = asyncio.Event()
    pending_approvals[session_id] = {
        "event": approval_event,
        "queries": queries,
        "approved_queries": None
    }

    yield {
        "node": "planner",
        "status": "awaiting_approval",
        "log": "Waiting for your approval...",
        "data": queries
    }

    await approval_event.wait()

    approved_queries = pending_approvals[session_id]["approved_queries"]
    del pending_approvals[session_id]

    yield {"node": "planner", "status": "done", "log": "Approved! CrewAI continuing..."}

    # Step 2 — Web Search via MCP
    yield {"node": "web_search", "status": "active", "log": "CrewAI: searching via MCP..."}
    search_context = await search_with_mcp(approved_queries)
    yield {"node": "web_search", "status": "done", "log": "Search complete"}

    # Step 3 — Doc reader (synthesizer agent summarises)
    yield {"node": "doc_reader", "status": "active", "log": "CrewAI: extracting key points..."}

    doc_task = Task(
        description=f"Summarise these search results in bullet points:\n{search_context}",
        expected_output="Bullet point summary of key findings",
        agent=synthesizer_agent
    )

    doc_crew = Crew(agents=[synthesizer_agent], tasks=[doc_task], verbose=False, 
    memory=False,     # ← disable crew memory
    cache=False       # ← disable caching overhead
    )
    summary = await loop.run_in_executor(None, lambda: doc_crew.kickoff().raw)
    yield {"node": "doc_reader", "status": "done", "log": "Key points extracted"}

    # Step 4 — Synthesizer
    yield {"node": "synthesizer", "status": "active", "log": "CrewAI: synthesizer agent working..."}

    synth_task = Task(
        description=f"Synthesize these findings about '{topic}' into a coherent analysis:\n{summary}",
        expected_output="Coherent analytical synthesis of findings",
        agent=synthesizer_agent
    )

    synth_crew = Crew(agents=[synthesizer_agent], tasks=[synth_task], verbose=False, 
    memory=False,     # ← disable crew memory
    cache=False       # ← disable caching overhead
    )
    synthesis = await loop.run_in_executor(None, lambda: synth_crew.kickoff().raw)
    yield {"node": "synthesizer", "status": "done", "log": "Findings merged"}

    # Step 5 — Report Writer agent
    yield {"node": "report", "status": "active", "log": "CrewAI: writer agent working..."}

    write_task = Task(
        description=f"Write a structured research report about '{topic}' based on:\n{synthesis}\n\nFormat with markdown: # Title, ## Executive Summary, ## Key Findings, ## Conclusion.",
        expected_output="Full markdown research report",
        agent=writer_agent
    )

    write_crew = Crew(agents=[writer_agent], tasks=[write_task], 
    verbose=False, 
    memory=False,     # ← disable crew memory
    cache=False       # ← disable caching overhead
    )
    report = await loop.run_in_executor(None, lambda: write_crew.kickoff().raw)

    elapsed = round(time.time() - start_time, 1)

    yield {
        "node": "report",
        "status": "done",
        "log": "Report ready",
        "report": report,
        "framework": "CrewAI",
        "usage": {
            "prompt_tokens":     0,     # CrewAI doesn't expose token counts easily
            "completion_tokens": 0,
            "total_tokens":      0,
            "estimated_cost":    0,
            "elapsed_seconds":   elapsed
        }
    }