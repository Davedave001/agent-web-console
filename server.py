"""Interactive Web Console & API Gateway for Agentic Systems Engineering Lab.

Serves the modern single-page testing UI on port 8500 (or configured PORT)
and proxies/coordinates calls between Axiom Runtime, Memory Service,
Evaluation Lab, and Voice Agent Capstone.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

app = FastAPI(
    title="Agentic Systems Lab Web Console",
    version="1.0.0",
    description="Interactive UI & Playground for Agentic Systems Engineering Lab",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Service URLs (configurable via environment variables for Docker / VPS)
AXIOM_URL = os.getenv("AXIOM_URL", "http://127.0.0.1:8001")
MEMORY_URL = os.getenv("MEMORY_URL", "http://127.0.0.1:8002")
EVAL_URL = os.getenv("EVAL_URL", "http://127.0.0.1:8003")
VOICE_URL = os.getenv("VOICE_URL", "http://127.0.0.1:8004")

HTML_PATH = Path(__file__).resolve().parent / "index.html"


def _http_get(url: str, timeout: float = 3.0) -> Dict[str, Any]:
    req = urllib.request.Request(url, headers={"User-Agent": "AxiomWebUI/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def _http_post(url: str, payload: Dict[str, Any], timeout: float = 10.0) -> Dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", "User-Agent": "AxiomWebUI/1.0"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


@app.get("/", response_class=HTMLResponse)
def serve_ui() -> HTMLResponse:
    if not HTML_PATH.exists():
        raise HTTPException(status_code=404, detail="index.html not found")
    return HTMLResponse(content=HTML_PATH.read_text(encoding="utf-8"))


@app.get("/api/system-status")
def system_status() -> Dict[str, Any]:
    """Check health of all 4 microservices."""
    services = {
        "axiom_runtime": {"url": AXIOM_URL, "status": "offline", "data": None},
        "agent_memory": {"url": MEMORY_URL, "status": "offline", "data": None},
        "agent_eval": {"url": EVAL_URL, "status": "offline", "data": None},
        "voice_capstone": {"url": VOICE_URL, "status": "offline", "data": None},
    }
    for key, s in services.items():
        try:
            data = _http_get(f"{s['url']}/health")
            s["status"] = "healthy"
            s["data"] = data
        except Exception as e:
            s["status"] = "offline"
            s["error"] = str(e)
    return services


class VoiceTurnProxyRequest(BaseModel):
    user_id: str = "demo-user"
    customer_email: str = "demo.user@enterprise.com"
    session_id: str = "sess-interactive-01"
    turn_idempotency_key: str
    audio_transcript: str


@app.post("/api/voice/turn")
def proxy_voice_turn(req: VoiceTurnProxyRequest) -> Dict[str, Any]:
    try:
        return _http_post(f"{VOICE_URL}/voice/turn", req.model_dump())
    except urllib.error.HTTPError as e:
        raise HTTPException(status_code=e.code, detail=e.read().decode())
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Voice service unavailable: {e}")


class ApprovalProxyRequest(BaseModel):
    user_id: str = "demo-user"
    session_id: str = "sess-interactive-01"
    run_id: str
    transcript_in: str
    supervisor_id: str = "lead-supervisor-01"


@app.post("/api/voice/approve")
def proxy_approval(req: ApprovalProxyRequest) -> Dict[str, Any]:
    try:
        return _http_post(f"{VOICE_URL}/voice/approve", req.model_dump())
    except urllib.error.HTTPError as e:
        raise HTTPException(status_code=e.code, detail=e.read().decode())
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Approval service unavailable: {e}")


@app.get("/api/facts")
def proxy_list_facts(
    org_id: str = "fde-voice-enterprise",
    user_id: str = "demo-user",
    agent_id: str = "voice-agent-capstone",
) -> Any:
    try:
        return _http_get(f"{MEMORY_URL}/facts/{org_id}/{user_id}/{agent_id}?include_superseded=true")
    except Exception as e:
        return []


class UpsertFactRequest(BaseModel):
    namespace: Dict[str, str]
    fact_id: str
    subject: str
    predicate: str
    object: str
    confidence: float = 1.0


@app.post("/api/facts")
def proxy_upsert_fact(req: UpsertFactRequest) -> Any:
    try:
        return _http_post(f"{MEMORY_URL}/facts", req.model_dump())
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@app.get("/api/benchmark")
def proxy_benchmark() -> Any:
    try:
        return _http_get(f"{EVAL_URL}/benchmark/summary")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Eval service error: {e}")


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8500"))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
