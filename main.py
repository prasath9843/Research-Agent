import re
import uuid
import threading
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request

from db import init_db, get_db_connection
from models import ResearchRequest, ResearchStatusResponse, UpdateReportRequest
from evidence_store import EvidenceStore
from pipeline import ResearchPipeline
from pdf_exporter import export_report_files, generate_pdf_from_markdown

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="Autonomous Research Agent API", version="1.0.0")

# Mount Static & Template directories
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Global dictionary to track active pipeline threads
active_tasks = {}

@app.on_event("startup")
def startup_event():
    init_db()

def run_pipeline_worker(session_id: str, query: str, config_override: dict):
    try:
        pipeline = ResearchPipeline(session_id=session_id, query=query, config_override=config_override)
        pipeline.run()
    except Exception as e:
        print(f"[Worker] Pipeline error for {session_id}: {e}")

import os
import requests
from config import settings

@app.get("/api/models")
def get_nvidia_models():
    api_key = settings.NVIDIA_API_KEY or os.getenv("NVIDIA_API_KEY", "")
    base_url = settings.NVIDIA_BASE_URL or os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
    
    models = []
    try:
        headers = {}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        
        resp = requests.get(f"{base_url.rstrip('/')}/models", headers=headers, timeout=8)
        if resp.status_code == 200:
            data = resp.json()
            raw_list = data.get("data", [])
            for item in raw_list:
                model_id = item.get("id", "")
                if model_id and not any(x in model_id for x in ["embed", "guard", "deplot", "clip", "parse", "safety", "video-detector"]):
                    models.append(model_id)
    except Exception as e:
        print(f"[API] Error fetching models from NVIDIA endpoint: {e}")

    # Fallback default models if API fails or empty
    if not models:
        models = [
            "meta/llama-3.1-8b-instruct", "meta/llama-3.1-70b-instruct", "meta/llama-3.3-70b-instruct",
            "meta/llama-3.1-405b-instruct", "meta/llama-3.2-3b-instruct", "meta/llama-3.2-1b-instruct",
            "meta/llama-3.2-11b-vision-instruct", "meta/llama-3.2-90b-vision-instruct",
            "deepseek-ai/deepseek-r1", "deepseek-ai/deepseek-coder-6.7b-instruct",
            "nvidia/llama-3.1-nemotron-70b-instruct", "nvidia/llama-3.1-nemotron-51b-instruct",
            "nvidia/nemotron-4-340b-instruct", "nvidia/nemotron-mini-4b-instruct",
            "mistralai/mistral-large-2-instruct", "mistralai/mistral-7b-instruct-v0.3",
            "mistralai/mixtral-8x22b-v0.1", "mistralai/mixtral-8x7b-instruct-v0.1",
            "google/gemma-2-27b-it", "google/gemma-2-9b-it", "google/gemma-2-2b-it",
            "qwen/qwen2.5-72b-instruct", "qwen/qwen2.5-7b-instruct", "qwen/qwen3-next-80b-a3b-instruct",
            "microsoft/phi-3.5-moe-instruct", "ibm/granite-3.0-8b-instruct", "01-ai/yi-large"
        ]

    models = sorted(list(set(models)))

    # Categorize models by provider/family
    categorized = {}
    for m in models:
        prefix = m.split('/')[0] if '/' in m else 'Other'
        if prefix not in categorized:
            categorized[prefix] = []
        categorized[prefix].append(m)

    return {
        "models": models,
        "count": len(models),
        "categorized": categorized
    }

@app.get("/", response_class=HTMLResponse)
def index_page(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

@app.post("/api/research")
def start_research(payload: ResearchRequest, background_tasks: BackgroundTasks):
    if not payload.query or not payload.query.strip():
        raise HTTPException(status_code=400, detail="Research query cannot be empty.")

    session_id = str(uuid.uuid4())
    config_override = {}
    if payload.fast_model:
        config_override["fast_model"] = payload.fast_model
    if payload.strong_model:
        config_override["strong_model"] = payload.strong_model
    if payload.max_rounds:
        config_override["max_rounds"] = payload.max_rounds
    if payload.max_sources:
        config_override["max_sources"] = payload.max_sources
    if payload.user_suggestions:
        config_override["user_suggestions"] = payload.user_suggestions
    if payload.target_pages:
        config_override["target_pages"] = payload.target_pages

    # Start background execution thread
    thread = threading.Thread(
        target=run_pipeline_worker,
        args=(session_id, payload.query.strip(), config_override),
        daemon=True
    )
    thread.start()
    active_tasks[session_id] = thread

    return {
        "session_id": session_id,
        "query": payload.query.strip(),
        "status": "started",
        "message": "Research pipeline launched successfully."
    }

@app.get("/api/research/{session_id}")
def get_research_status(session_id: str):
    store = EvidenceStore(session_id)
    session_data = store.get_session_status()
    if not session_data:
        raise HTTPException(status_code=404, detail="Session not found.")

    sources = store.get_sources()
    claims = store.get_claims()
    logs = store.get_logs()

    # Calculate stage progress percentage and ETA
    stage_info = {
        "initialized": {"progress": 5, "eta": 20},
        "planning": {"progress": 15, "eta": 18},
        "web_search": {"progress": 30, "eta": 15},
        "page_scraping": {"progress": 45, "eta": 12},
        "claim_extraction": {"progress": 60, "eta": 10},
        "contradiction_analysis": {"progress": 75, "eta": 8},
        "synthesis": {"progress": 85, "eta": 5},
        "report_synthesis": {"progress": 85, "eta": 5},
        "citation_verification": {"progress": 92, "eta": 3},
        "report_assembly": {"progress": 95, "eta": 2},
        "quality_evaluation": {"progress": 98, "eta": 1},
        "done": {"progress": 100, "eta": 0},
        "error": {"progress": 0, "eta": 0}
    }
    info = stage_info.get(session_data["stage"], {"progress": 50, "eta": 10})

    return {
        "session_id": session_id,
        "query": session_data["query"],
        "status": session_data["status"],
        "stage": session_data["stage"],
        "progress_percentage": info["progress"],
        "estimated_seconds_remaining": info["eta"],
        "rounds_completed": session_data["rounds_completed"],
        "total_sources": len(sources),
        "total_claims": len(claims),
        "logs": logs
    }

@app.get("/api/research/{session_id}/evidence")
def get_research_evidence(session_id: str):
    store = EvidenceStore(session_id)
    return {
        "sub_questions": store.get_sub_questions(),
        "sources": store.get_sources(),
        "claims": store.get_claims()
    }

@app.get("/api/research/{session_id}/contradictions")
def get_research_contradictions(session_id: str):
    store = EvidenceStore(session_id)
    return {"contradictions": store.get_contradictions()}

@app.get("/api/research/{session_id}/report")
def get_research_report(session_id: str):
    store = EvidenceStore(session_id)
    report = store.get_latest_report()
    if not report:
        return {"report": None, "message": "Report not yet generated."}
    return report

@app.put("/api/research/{session_id}/report")
def update_research_report(session_id: str, payload: UpdateReportRequest):
    store = EvidenceStore(session_id)
    report = store.get_latest_report()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found to update.")

    new_content = payload.markdown_content
    store.save_report(
        markdown_content=new_content,
        verified_count=report.get("verified_citations_count", 0) or 0,
        total_count=report.get("total_citations_count", 0) or 0
    )

    session_data = store.get_session_status()
    raw_query = session_data["query"] if session_data else "Research_Report"
    export_report_files(session_id, new_content, BASE_DIR / "exports")
    pdf_path = BASE_DIR / "exports" / f"report_{session_id}.pdf"
    generate_pdf_from_markdown(new_content, pdf_path, title=raw_query)

    return {"status": "success", "message": "Report updated and PDF re-rendered successfully."}

@app.get("/api/research/{session_id}/download/pdf")
def download_pdf_report(session_id: str):
    store = EvidenceStore(session_id)
    session_data = store.get_session_status()
    report = store.get_latest_report()
    if not report:
        raise HTTPException(status_code=404, detail="Report not generated yet.")

    raw_query = session_data["query"] if session_data else "Research_Report"
    pdf_path = BASE_DIR / "exports" / f"report_{session_id}.pdf"
    
    # Always regenerate PDF from latest saved markdown content to ensure all user edits are included
    generate_pdf_from_markdown(report["markdown_content"], pdf_path, title=raw_query)

    # Clean title for filename (e.g. Sustainable_Agriculture_in_Tamil_Nadu.pdf)
    clean_title = re.sub(r'[^a-zA-Z0-9_\- ]', '', raw_query).strip().replace(' ', '_')
    if not clean_title:
        clean_title = f"Research_Report_{session_id[:8]}"
    filename = f"{clean_title}.pdf"

    return FileResponse(
        path=str(pdf_path),
        filename=filename,
        media_type="application/pdf",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        }
    )

@app.get("/api/research/{session_id}/download/md")
def download_md_report(session_id: str):
    store = EvidenceStore(session_id)
    session_data = store.get_session_status()
    report = store.get_latest_report()
    if not report:
        raise HTTPException(status_code=404, detail="Report not generated yet.")

    md_path = BASE_DIR / "exports" / f"report_{session_id}.md"
    if not md_path.exists():
        export_report_files(session_id, report["markdown_content"], BASE_DIR / "exports")

    raw_query = session_data["query"] if session_data else "Research_Report"
    clean_title = re.sub(r'[^a-zA-Z0-9_\- ]', '', raw_query).strip().replace(' ', '_')
    filename = f"{clean_title}.md"

    return FileResponse(
        path=str(md_path),
        filename=filename,
        media_type="text/markdown"
    )

@app.get("/api/research/{session_id}/download/html")
def download_html_report(session_id: str):
    store = EvidenceStore(session_id)
    session_data = store.get_session_status()
    report = store.get_latest_report()
    if not report:
        raise HTTPException(status_code=404, detail="Report not generated yet.")

    html_path = BASE_DIR / "exports" / f"report_{session_id}.html"
    if not html_path.exists():
        export_report_files(session_id, report["markdown_content"], BASE_DIR / "exports")
    
    raw_query = session_data["query"] if session_data else "Research_Report"
    clean_title = re.sub(r'[^a-zA-Z0-9_\- ]', '', raw_query).strip().replace(' ', '_')
    filename = f"{clean_title}.html"

    return FileResponse(
        path=str(html_path),
        filename=filename,
        media_type="text/html"
    )

@app.get("/api/sessions")
def list_sessions():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT session_id, query, status, stage, created_at FROM sessions ORDER BY created_at DESC LIMIT 20")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return {"sessions": rows}
