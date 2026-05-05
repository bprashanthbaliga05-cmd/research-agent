from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import json, traceback
from agent import run_agent

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

@app.get("/run")
async def run(topic: str):
    async def event_stream():
        try:
            async for event in run_agent(topic):
                yield f"data: {json.dumps(event)}\n\n"
        except Exception as e:
            print("STREAM ERROR:", traceback.format_exc())  # visible in Railway logs
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