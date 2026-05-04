import os
from groq import Groq
from tavily import TavilyClient
from dotenv import load_dotenv

load_dotenv()

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
tavily_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

async def run_agent(topic: str):

    # Step 1 — Input
    yield {"node": "input", "status": "active", "log": f'Topic received: "{topic}"'}
    yield {"node": "input", "status": "done",   "log": "Topic queued for planning"}

    # Step 2 — Planner
    yield {"node": "planner", "status": "active", "log": "Breaking topic into subtasks..."}
    planner_response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{
            "role": "user",
            "content": f"Break this research topic into 3 specific search queries: {topic}. Return only a numbered list."
        }],
        max_tokens=200
    )
    queries_text = planner_response.choices[0].message.content
    yield {"node": "planner", "status": "done", "log": queries_text[:120]}

    # Step 3 — Web Search
    yield {"node": "web_search", "status": "active", "log": "Searching the web..."}
    search_results = tavily_client.search(query=topic, max_results=5)
    sources = search_results["results"]
    search_context = "\n".join([f"- {r['title']}: {r['content'][:200]}" for r in sources])
    yield {"node": "web_search", "status": "done", "log": f"Found {len(sources)} sources"}

    # Step 4 — Doc Reader (summarise each source)
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
    yield {"node": "doc_reader", "status": "done", "log": f"Extracted key points from {len(sources)} sources"}

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
            "content": f"Write a structured research report about '{topic}' based on this analysis:\n{synthesis}\n\nFormat: Title, Executive Summary, Key Findings, Conclusion."
        }],
        max_tokens=600
    )
    report = report_response.choices[0].message.content
    # print(report)
    yield {"node": "report", "status": "done", "log": "Report Ready", "report": report}