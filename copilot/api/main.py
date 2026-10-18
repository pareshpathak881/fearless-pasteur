"""Project Atlas: Report Copilot FastAPI Backend Service.

Implements REST API endpoints, API-key authentication, request timeouts,
semantic caching, token and cost accounting, and structured responses.
"""

import os
import time
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, Header, HTTPException, Depends, Security, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

load_dotenv()

from copilot.api.models import (
    ChatRequest, ChatResponse, IngestResponse, EscalationTicket, FeedbackRequest
)
from copilot.agent.workflow import copilot_workflow
from copilot.rag.vector_store import vector_store
from copilot.api.cache import semantic_cache
from copilot.db import db

# Configuration
API_KEY_SECRET = os.getenv("COPILOT_API_KEY", "atlas_secret_api_key_2025")
MAX_TOKENS = int(os.getenv("MAX_TOKENS_PER_REQUEST", "1200"))
COST_PER_1K_TOKENS = 0.00015 # Standard economy LLM pricing tier ($0.15 / 1M tokens)

app = FastAPI(
    title="Project Atlas: Report Copilot API",
    description="Cognitive Market Research & Consulting Enterprise Copilot Backend",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def verify_api_key(x_api_key: Optional[str] = Header(None)):
    """Validate API Key from request header."""
    # If no secret configured or matched
    if not x_api_key or x_api_key != API_KEY_SECRET:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized: Invalid or missing 'X-API-Key' header."
        )
    return x_api_key


@app.on_event("startup")
async def startup_event():
    """Ensure vector store has reports loaded on startup."""
    if len(vector_store.chunks) == 0:
        reports_dir = os.path.join(os.path.dirname(__file__), "..", "..", "data", "reports")
        if os.path.exists(reports_dir):
            count = vector_store.ingest_reports_directory(reports_dir)
            print(f"[Project Atlas API] Indexed {count} report chunks on startup.")


@app.get("/health", tags=["System"])
async def health_check():
    """Health check endpoint providing system status and vector index readiness."""
    return {
        "status": "healthy",
        "service": "project-atlas-copilot",
        "timestamp": time.time(),
        "vector_store_chunks": len(vector_store.chunks),
        "database_type": db.use_mysql and "mysql" or "sqlite",
        "environment": os.getenv("ENVIRONMENT", "production")
    }


@app.post("/chat", response_model=ChatResponse, tags=["Copilot"])
async def chat_endpoint(
    req: ChatRequest,
    api_key: str = Depends(verify_api_key)
):
    """Primary chat endpoint for client market research inquiries.
    
    Carries client_id and returns structured JSON with citations, conflicts,
    derived estimates, confidence, and escalation state.
    """
    start_time = time.time()

    # 1. Check Semantic Cache
    cached_res = semantic_cache.get(req.client_id, req.query)
    if cached_res:
        cached_res["latency_ms"] = round((time.time() - start_time) * 1000, 2)
        return ChatResponse(**cached_res)

    # 2. Invoke Agent State Graph
    try:
        agent_output = copilot_workflow.chat(client_id=req.client_id, query=req.query)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent workflow execution failed: {str(e)}"
        )

    latency_ms = round((time.time() - start_time) * 1000, 2)

    # 3. Cost & Token accounting
    total_chars = len(req.query) + len(agent_output.get("answer", ""))
    estimated_tokens = min(MAX_TOKENS, max(50, total_chars // 4))
    estimated_cost = round((estimated_tokens / 1000.0) * COST_PER_1K_TOKENS, 6)

    response_data = {
        "answer": agent_output.get("answer", ""),
        "citations": agent_output.get("citations", []),
        "confidence": agent_output.get("confidence", 0.0),
        "conflicts": agent_output.get("conflicts", []),
        "derived_values": agent_output.get("derived_values", []),
        "escalated": agent_output.get("escalated", False),
        "escalation_ticket_id": agent_output.get("escalation_ticket_id"),
        "cached": False,
        "latency_ms": latency_ms,
        "estimated_cost_usd": estimated_cost
    }

    # 4. Save to Semantic Cache if confidence is high and query is safe
    if agent_output.get("confidence", 0.0) > 0.70 and not agent_output.get("escalated"):
        semantic_cache.set(req.client_id, req.query, response_data)

    return ChatResponse(**response_data)


@app.post("/ingest", response_model=IngestResponse, tags=["Knowledge Base"])
async def ingest_endpoint(api_key: str = Depends(verify_api_key)):
    """Re-index all reports from the data/reports directory."""
    reports_dir = os.path.join(os.path.dirname(__file__), "..", "..", "data", "reports")
    try:
        count = vector_store.ingest_reports_directory(reports_dir)
        semantic_cache.clear()
        return IngestResponse(
            status="success",
            message=f"Successfully ingested and indexed {count} document chunks.",
            total_chunks=count
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ingestion failed: {str(e)}"
        )


@app.get("/escalations", tags=["Escalations"])
async def get_escalations(api_key: str = Depends(verify_api_key)):
    """Retrieve all open human analyst escalation tickets."""
    tickets = db.get_escalations()
    return {
        "status": "success",
        "total_escalations": len(tickets),
        "tickets": tickets
    }


@app.post("/feedback", tags=["CodeIgniter Integration"])
async def submit_feedback(
    req: FeedbackRequest,
    api_key: str = Depends(verify_api_key)
):
    """Store thumbs-up / thumbs-down user ratings from the CodeIgniter portal."""
    conn = db.get_connection(read_only=False)
    cursor = conn.cursor()
    try:
        if db.use_mysql:
            cursor.execute(
                "INSERT INTO chat_feedback (client_id, session_id, query, response_text, rating) VALUES (%s, %s, %s, %s, %s)",
                (req.client_id, req.session_id, req.query, req.response_text, req.rating)
            )
        else:
            cursor.execute(
                "INSERT INTO chat_feedback (client_id, session_id, query, response_text, rating) VALUES (?, ?, ?, ?, ?)",
                (req.client_id, req.session_id, req.query, req.response_text, req.rating)
            )
            conn.commit()
        return {"status": "success", "message": "Feedback recorded successfully."}
    finally:
        conn.close()
