"""
King Makers Consulting Autopilot - API Server
==============================================
FastAPI wrapper around the agent pipeline.

Usage:
    uvicorn api:app --reload --port 8000

Endpoints:
    POST   /diagnostics         Submit a new diagnostic job
    GET    /diagnostics          List all jobs
    GET    /diagnostics/{id}     Get job status and results
"""

import asyncio
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl

from coordinator import run_diagnostic


# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = FastAPI(
    title="King Makers Consulting Autopilot",
    description="AI-powered diagnostic brief generator",
    version="0.1.0",
)

# Allow the Next.js frontend to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",           # Local Next.js dev
        "http://localhost:3001",           # Local Next.js dev (alt port)
        "https://consulting.kingmakersinc.ca",  # Production frontend
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# In-memory job store
# ---------------------------------------------------------------------------
# For a portfolio demo, an in-memory dict is fine.
# For production, swap this for Redis or a database table.

jobs: dict[str, dict] = {}


# ---------------------------------------------------------------------------
# Request and response models
# ---------------------------------------------------------------------------

class DiagnosticRequest(BaseModel):
    """What the client sends to start a diagnostic."""
    company_url: str
    problem_statement: str

    class Config:
        json_schema_extra = {
            "example": {
                "company_url": "https://shopify.com",
                "problem_statement": "struggling to retain mid-market merchants"
            }
        }


class DiagnosticJob(BaseModel):
    """What the API returns for each job."""
    job_id: str
    status: str            # "queued", "researching", "analyzing", "writing", "complete", "failed"
    company_url: str
    problem_statement: str
    created_at: str
    completed_at: str | None = None
    brief_path: str | None = None
    brief_content: str | None = None
    error: str | None = None


# ---------------------------------------------------------------------------
# Background runner
# ---------------------------------------------------------------------------

async def run_diagnostic_job(job_id: str):
    """
    Run the diagnostic pipeline in the background.
    Updates the job dict as each stage progresses.
    """
    job = jobs[job_id]

    try:
        job["status"] = "running"

        brief_path = await run_diagnostic(
            company_url=job["company_url"],
            problem_statement=job["problem_statement"],
            output_dir="output",
        )

        # Read the generated brief content
        brief_content = ""
        if brief_path and Path(brief_path).exists():
            brief_content = Path(brief_path).read_text(encoding="utf-8")

        job["status"] = "complete"
        job["completed_at"] = datetime.now().isoformat()
        job["brief_path"] = brief_path
        job["brief_content"] = brief_content

    except Exception as e:
        job["status"] = "failed"
        job["completed_at"] = datetime.now().isoformat()
        job["error"] = str(e)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.post("/diagnostics", response_model=DiagnosticJob, status_code=202)
async def create_diagnostic(request: DiagnosticRequest):
    """
    Submit a new diagnostic job.

    Returns immediately with a job ID. The diagnostic runs in the background.
    Poll GET /diagnostics/{job_id} to check progress.
    """
    job_id = str(uuid.uuid4())[:8]

    job = {
        "job_id": job_id,
        "status": "queued",
        "company_url": request.company_url,
        "problem_statement": request.problem_statement,
        "created_at": datetime.now().isoformat(),
        "completed_at": None,
        "brief_path": None,
        "brief_content": None,
        "error": None,
    }

    jobs[job_id] = job

    # Fire the diagnostic in the background
    asyncio.create_task(run_diagnostic_job(job_id))

    return DiagnosticJob(**job)


@app.get("/diagnostics", response_model=list[DiagnosticJob])
async def list_diagnostics():
    """List all diagnostic jobs, most recent first."""
    sorted_jobs = sorted(
        jobs.values(),
        key=lambda j: j["created_at"],
        reverse=True,
    )
    return [DiagnosticJob(**j) for j in sorted_jobs]


@app.get("/diagnostics/{job_id}", response_model=DiagnosticJob)
async def get_diagnostic(job_id: str):
    """Get the status and results of a specific diagnostic job."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    return DiagnosticJob(**jobs[job_id])


@app.get("/health")
async def health_check():
    """Simple health check for monitoring."""
    return {
        "status": "healthy",
        "service": "consulting-autopilot",
        "timestamp": datetime.now().isoformat(),
    }