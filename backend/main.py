# FastAPI + SSE
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import asyncio, json
from agent import run_agent

app = FastAPI()
app.add_middleware(
    CORSMiddleware, 
    allow_origins=["*"],
    allow_methods=["*"], 
    allow_headers=["*"])

@app.get("/run")
async def run(topic: str):
    async def event_stream():
        async for event in run_agent(topic):
            yield f"data: {json.dumps(event)}\n\n"
    return StreamingResponse(
                event_stream(), 
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no"      # ← important for Railway
                })