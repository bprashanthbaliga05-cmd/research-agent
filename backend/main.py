from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import json, traceback, uuid, os
from agent import run_agent, pending_approvals
from groq import Groq
from validators import validate_topic          # ← import validator


# ─── Rate limiter setup ───────────────────────────────────────
# get_remote_address uses the user's IP as the key
# so each user gets their own limit independently
limiter = Limiter(key_func=get_remote_address)

app = FastAPI()
app.state.limiter = limiter

# When rate limit is exceeded, return clean JSON instead of crashing
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

class ApprovalBody(BaseModel):
    queries: str

@app.get("/run")
@limiter.limit("5/minute")   # ← max 5 agent runs per minute per user
async def run(request: Request, topic: str, framework: str = "langgraph"):
    # ─── Validate input ───────────────────────────────────────
    is_valid, error_message = validate_topic(topic)
    if not is_valid:
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": error_message}
        )

    session_id = str(uuid.uuid4())

    async def event_stream():
        try:
            # Send session_id to frontend first so it can approve later
            yield f"data: {json.dumps({'session_id': session_id, 'node': 'session', 'status': 'started', 'log': ''})}\n\n"
            async for event in run_agent(topic, session_id, framework=framework):
                print("\n\n\n")
                print(json.dumps(event))
                yield f"data: {json.dumps(event)}\n\n"
        except Exception as e:
            print("STREAM ERROR:", traceback.format_exc())
            yield f"data: {json.dumps({'node': 'error', 'status': 'error', 'log': str(e)})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )

@app.post("/approve/{session_id}")
@limiter.limit("10/minute")   # ← approvals can happen more often
async def approve(request: Request, session_id: str, body: ApprovalBody):
    if session_id not in pending_approvals:
        return JSONResponse(
            status_code=404,
            content={"status": "error", "message": "Session not found or already approved"}
        )
    pending_approvals[session_id]["approved_queries"] = body.queries
    pending_approvals[session_id]["event"].set()
    return {"status": "approved"}

@app.get("/health")
@limiter.limit("30/minute")   # ← health checks can be frequent
async def health(request: Request):
    checks = {}

    # Check 1 — Groq connection
    try:
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": "ping"}],
            max_tokens=1
        )
        checks["groq"] = "ok"
    except Exception as e:
        checks["groq"] = f"error: {str(e)}"

    # Check 2 — Tavily API key present
    try:
        tavily_key = os.getenv("TAVILY_API_KEY")
        checks["tavily"] = "ok" if tavily_key else "error: missing API key"
    except Exception as e:
        checks["tavily"] = f"error: {str(e)}"

    # Check 3 — Pending approvals count
    checks["pending_sessions"] = len(pending_approvals)

    # Overall status
    has_errors = any(
        str(v).startswith("error") 
        for v in checks.values() 
        if isinstance(v, str)
    )

    return {
        "status": "degraded" if has_errors else "ok",
        "version": "1.0.0",
        "checks": checks
    }