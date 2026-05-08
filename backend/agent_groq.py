import os
import asyncio
import time
from groq import Groq
from dotenv import load_dotenv
from tools import search_with_mcp
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

load_dotenv()

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

GROQ_TIMEOUT_SECONDS = 15

INPUT_COST_PER_1M  = 0.59   # $ per 1M input tokens
OUTPUT_COST_PER_1M = 0.79   # $ per 1M output tokens

def calculate_cost(prompt_tokens: int, completion_tokens: int) -> float:
    input_cost  = (prompt_tokens / 1_000_000) * INPUT_COST_PER_1M
    output_cost = (completion_tokens / 1_000_000) * OUTPUT_COST_PER_1M
    return round(input_cost + output_cost, 6)



# ─── Retry wrapper ───────────────────────────────────────────
# Retries up to 3 times
# Waits 2s, then 4s, then 8s between attempts (exponential backoff)
# Only retries on Exception — not on validation errors

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=8),
    retry=retry_if_exception_type(Exception),
    reraise=True   # ← if all retries fail, raise the original error
)
def call_groq(messages: list, max_tokens: int = 300) -> str:
    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        max_tokens=max_tokens
    )
    return response.choices[0].message.content, response.usage

# ─── Timeout wrapper ──────────────────────────────────────────
async def call_groq_with_timeout(messages: list, max_tokens: int = 300):
    try:
        # run_in_executor lets us await a sync function (call_groq) 
        # asyncio.timeout cancels it if it takes too long
        async with asyncio.timeout(GROQ_TIMEOUT_SECONDS):
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None,           # ← use default thread pool
                lambda: call_groq(messages, max_tokens)
            )
    except asyncio.TimeoutError:
        raise Exception(f"LLM call timed out after {GROQ_TIMEOUT_SECONDS} seconds")

# ─── Agent ───────────────────────────────────────────────────

async def run_agent_groq(topic: str, session_id: str, pending_approvals: dict):
    # Track across entire run
    total_prompt_tokens     = 0
    total_completion_tokens = 0
    start_time              = time.time()

    # Step 1 — Input
    yield {"node": "input", "status": "active", "log": f'Topic received: "{topic}"'}
    yield {"node": "input", "status": "done", "log": "Topic queued for planning"}

    # Step 2 — Planner
    yield {"node": "planner", "status": "active", "log": "Breaking topic into subtasks..."}
    try:
        queries, usage = await call_groq_with_timeout(
            messages=[{
                "role": "user",
                "content": f"Break this research topic into 3 specific search queries: {topic}. Return only a numbered list, nothing else."
            }],
            max_tokens=200
        )
        total_prompt_tokens     += usage.prompt_tokens
        total_completion_tokens += usage.completion_tokens
    except Exception as e:
        yield {"node": "planner", "status": "error", "log": f"Planner failed after 3 retries: {str(e)}"}
        return

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
    try:
        search_context = await search_with_mcp(approved_queries)
    except Exception as e:
        yield {"node": "web_search", "status": "error", "log": f"Search failed: {str(e)}"}
        return
    yield {"node": "web_search", "status": "done", "log": "MCP search complete"}

    # Step 4 — Doc Reader
    yield {"node": "doc_reader", "status": "active", "log": "Reading and extracting content..."}
    try:
        summary, usage = await call_groq_with_timeout(
            messages=[{
                "role": "user",
                "content": f"Summarise these search results in bullet points:\n{search_context}"
            }],
            max_tokens=300
        )
        total_prompt_tokens     += usage.prompt_tokens
        total_completion_tokens += usage.completion_tokens
    except Exception as e:
        yield {"node": "doc_reader", "status": "error", "log": f"Doc reader failed after 3 retries: {str(e)}"}
        return
    yield {"node": "doc_reader", "status": "done", "log": "Key points extracted"}

    # Step 5 — Synthesizer
    yield {"node": "synthesizer", "status": "active", "log": "Merging and synthesizing findings..."}
    try:
        synthesis, usage = await call_groq_with_timeout(
            messages=[{
                "role": "user",
                "content": f"Synthesize these findings about '{topic}' into a coherent analysis:\n{summary}"
            }],
            max_tokens=400
        )
        total_prompt_tokens     += usage.prompt_tokens
        total_completion_tokens += usage.completion_tokens
    except Exception as e:
        yield {"node": "synthesizer", "status": "error", "log": f"Synthesizer failed after 3 retries: {str(e)}"}
        return
    yield {"node": "synthesizer", "status": "done", "log": "Findings merged successfully"}

    # Step 6 — Report Writer
    yield {"node": "report", "status": "active", "log": "Writing final report..."}
    try:
        report, usage = await call_groq_with_timeout(
            messages=[{
                "role": "user",
                "content": f"Write a structured research report about '{topic}' based on:\n{synthesis}\n\nFormat with markdown: # Title, ## Executive Summary, ## Key Findings, ## Conclusion."
            }],
            max_tokens=600
        )
        total_prompt_tokens     += usage.prompt_tokens
        total_completion_tokens += usage.completion_tokens
    except Exception as e:
        yield {"node": "report", "status": "error", "log": f"Report writer failed after 3 retries: {str(e)}"}
        return
    # ─── Final cost summary ───────────────────────────────────
    elapsed      = round(time.time() - start_time, 1)
    total_tokens = total_prompt_tokens + total_completion_tokens
    total_cost   = calculate_cost(total_prompt_tokens, total_completion_tokens)

    yield {
        "node": "report",
        "status": "done",
        "log": "Report ready",
        "report": report,
        "usage": {
            "prompt_tokens":     total_prompt_tokens,
            "completion_tokens": total_completion_tokens,
            "total_tokens":      total_tokens,
            "estimated_cost":    total_cost,
            "elapsed_seconds":   elapsed
        }
    }