from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json, traceback, uuid
from agent import run_agent, pending_approvals

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

class ApprovalBody(BaseModel):
    queries: str

@app.get("/run")
async def run(topic: str):
    session_id = str(uuid.uuid4())

    async def event_stream():
        try:
            # Send session_id to frontend first so it can approve later
            yield f"data: {json.dumps({'session_id': session_id, 'node': 'session', 'status': 'started', 'log': ''})}\n\n"
            async for event in run_agent(topic, session_id):
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
async def approve(session_id: str, body: ApprovalBody):
    if session_id not in pending_approvals:
        return {"status": "error", "message": "Session not found or already approved"}
    pending_approvals[session_id]["approved_queries"] = body.queries
    pending_approvals[session_id]["event"].set()
    return {"status": "approved"}

@app.get("/health")
async def health():
    return {"status": "ok"}