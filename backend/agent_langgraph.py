import os
import asyncio
from groq import Groq
from dotenv import load_dotenv
from tools import search_with_mcp
from langgraph.graph import StateGraph, END
from typing import TypedDict, Optional
import time

load_dotenv()
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

INPUT_COST_PER_1M  = 0.59
OUTPUT_COST_PER_1M = 0.79

# ─── State definition ─────────────────────────────────────────
# LangGraph passes this state between every node
class ResearchState(TypedDict):
    topic:              str
    queries:            Optional[str]
    approved_queries:   Optional[str]
    search_context:     Optional[str]
    summary:            Optional[str]
    synthesis:          Optional[str]
    report:             Optional[str]
    prompt_tokens:      int
    completion_tokens:  int
    start_time:         float
    error:              Optional[str]

def call_groq(messages, max_tokens=300):
    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        max_tokens=max_tokens
    )
    return response.choices[0].message.content, response.usage

# ─── Nodes ────────────────────────────────────────────────────

def planner_node(state: ResearchState) -> ResearchState:
    content, usage = call_groq(
        messages=[{
            "role": "user",
            "content": f"Break this research topic into 3 specific search queries: {state['topic']}. Return only a numbered list."
        }],
        max_tokens=200
    )
    return {
        **state,
        "queries": content,
        "prompt_tokens":     state["prompt_tokens"] + usage.prompt_tokens,
        "completion_tokens": state["completion_tokens"] + usage.completion_tokens,
    }

def doc_reader_node(state: ResearchState) -> ResearchState:
    content, usage = call_groq(
        messages=[{
            "role": "user",
            "content": f"Summarise these search results in bullet points:\n{state['search_context']}"
        }],
        max_tokens=300
    )
    return {
        **state,
        "summary": content,
        "prompt_tokens":     state["prompt_tokens"] + usage.prompt_tokens,
        "completion_tokens": state["completion_tokens"] + usage.completion_tokens,
    }

def synthesizer_node(state: ResearchState) -> ResearchState:
    content, usage = call_groq(
        messages=[{
            "role": "user",
            "content": f"Synthesize these findings about '{state['topic']}' into a coherent analysis:\n{state['summary']}"
        }],
        max_tokens=400
    )
    return {
        **state,
        "synthesis": content,
        "prompt_tokens":     state["prompt_tokens"] + usage.prompt_tokens,
        "completion_tokens": state["completion_tokens"] + usage.completion_tokens,
    }

def report_node(state: ResearchState) -> ResearchState:
    content, usage = call_groq(
        messages=[{
            "role": "user",
            "content": f"Write a structured research report about '{state['topic']}' based on:\n{state['synthesis']}\n\nFormat with markdown: # Title, ## Executive Summary, ## Key Findings, ## Conclusion."
        }],
        max_tokens=600
    )
    return {
        **state,
        "report": content,
        "prompt_tokens":     state["prompt_tokens"] + usage.prompt_tokens,
        "completion_tokens": state["completion_tokens"] + usage.completion_tokens,
    }

# ─── Build graph ──────────────────────────────────────────────

def build_graph():
    graph = StateGraph(ResearchState)

    graph.add_node("planner",     planner_node)
    graph.add_node("doc_reader",  doc_reader_node)
    graph.add_node("synthesizer", synthesizer_node)
    graph.add_node("report",      report_node)

    graph.set_entry_point("planner")
    graph.add_edge("planner",     "doc_reader")
    graph.add_edge("doc_reader",  "synthesizer")
    graph.add_edge("synthesizer", "report")
    graph.add_edge("report",      END)

    return graph.compile()

# ─── Streaming wrapper ────────────────────────────────────────
# LangGraph runs synchronously so we wrap it to yield SSE events

async def run_langgraph_agent(topic: str, session_id: str, pending_approvals: dict):
    start_time = time.time()

    yield {"node": "input", "status": "active", "log": f'Topic received: "{topic}"'}
    yield {"node": "input", "status": "done",   "log": "Topic queued for planning"}

    yield {"node": "planner", "status": "active", "log": "LangGraph: running planner node..."}

    # Run planner first to get queries for HITL
    initial_state: ResearchState = {
        "topic":            topic,
        "queries":          None,
        "approved_queries": None,
        "search_context":   None,
        "summary":          None,
        "synthesis":        None,
        "report":           None,
        "prompt_tokens":    0,
        "completion_tokens":0,
        "start_time":       start_time,
        "error":            None,
    }

    loop = asyncio.get_event_loop()
    planner_result = await loop.run_in_executor(None, lambda: planner_node(initial_state))
    queries = planner_result["queries"]

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

    yield {"node": "planner", "status": "done", "log": "Approved! LangGraph continuing..."}

    # Web search
    yield {"node": "web_search", "status": "active", "log": "LangGraph: searching via MCP..."}
    search_context = await search_with_mcp(approved_queries)
    yield {"node": "web_search", "status": "done", "log": "Search complete"}

    # Run remaining nodes through LangGraph
    state_after_search = {
        **planner_result,
        "approved_queries": approved_queries,
        "search_context":   search_context,
    }

    yield {"node": "doc_reader",  "status": "active", "log": "LangGraph: doc reader node..."}
    state_after_reader = await loop.run_in_executor(None, lambda: doc_reader_node(state_after_search))
    yield {"node": "doc_reader",  "status": "done",   "log": "Key points extracted"}

    yield {"node": "synthesizer", "status": "active", "log": "LangGraph: synthesizer node..."}
    state_after_synth  = await loop.run_in_executor(None, lambda: synthesizer_node(state_after_reader))
    yield {"node": "synthesizer", "status": "done",   "log": "Findings merged"}

    yield {"node": "report",      "status": "active", "log": "LangGraph: report writer node..."}
    final_state        = await loop.run_in_executor(None, lambda: report_node(state_after_synth))
    yield {"node": "report",      "status": "done",   "log": "Report ready"}

    elapsed      = round(time.time() - start_time, 1)
    total_tokens = final_state["prompt_tokens"] + final_state["completion_tokens"]
    cost         = round(
        (final_state["prompt_tokens"] / 1_000_000) * 0.59 +
        (final_state["completion_tokens"] / 1_000_000) * 0.79, 6
    )

    yield {
        "node": "report",
        "status": "done",
        "log": "Report ready",
        "report": final_state["report"],
        "framework": "LangGraph",
        "usage": {
            "prompt_tokens":     final_state["prompt_tokens"],
            "completion_tokens": final_state["completion_tokens"],
            "total_tokens":      total_tokens,
            "estimated_cost":    cost,
            "elapsed_seconds":   elapsed
        }
    }