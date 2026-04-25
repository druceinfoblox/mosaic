import uuid
import asyncio
from concurrent.futures import ThreadPoolExecutor
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import get_db, AsyncSessionLocal

_executor = ThreadPoolExecutor(max_workers=2)
from app.models.dns_event import DnsEvent
from app.services.parser import parse_dns_logs
from app.services.normalizer import bulk_insert_events, clear_events
from app.services.enricher import seed_demo_subnet_context
from app.services.correlator import run_correlation
from app.services.enricher import run_enrichment
from app.services.recommender import run_recommendations
from app.fixtures.generator import generate_csv

router = APIRouter(prefix="/api/v1/ingest", tags=["ingest"])

_jobs: dict[str, dict] = {}


async def _run_generate_demo(job_id: str) -> None:
    _jobs[job_id] = {"status": "running", "phase": "generating", "events_inserted": 0, "error": None}
    try:
        # Run CPU-heavy generation in thread pool so event loop stays free
        loop = asyncio.get_event_loop()
        csv_content = await loop.run_in_executor(_executor, lambda: generate_csv(days=90, clients_per_subnet=50))
        events = await loop.run_in_executor(_executor, lambda: parse_dns_logs(csv_content))
        async with AsyncSessionLocal() as db:
            await clear_events(db)
            await seed_demo_subnet_context(db)
            inserted = await bulk_insert_events(db, events)
        _jobs[job_id]["phase"] = "analyzing"
        _jobs[job_id]["events_inserted"] = inserted
        async with AsyncSessionLocal() as db:
            await run_correlation(db)
            await run_enrichment(db)
            await run_recommendations(db)
        _jobs[job_id] = {"status": "done", "phase": "complete", "events_inserted": inserted, "error": None}
    except Exception as e:
        _jobs[job_id] = {"status": "error", "phase": "failed", "events_inserted": 0, "error": str(e)}


@router.post("")
async def ingest_file(file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    content = await file.read()
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        text = content.decode("latin-1")

    events = parse_dns_logs(text)
    if not events:
        raise HTTPException(status_code=422, detail="No valid DNS events parsed from file")

    inserted = await bulk_insert_events(db, events)
    return {"status": "ok", "parsed": len(events), "inserted": inserted, "filename": file.filename}


@router.post("/generate-demo", status_code=202)
async def generate_demo(background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    background_tasks.add_task(_run_generate_demo, job_id)
    return {"status": "started", "job_id": job_id}


@router.get("/generate-demo/status/{job_id}")
async def generate_demo_status(job_id: str):
    job = _jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/status")
async def ingest_status(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(func.count(DnsEvent.id)))
    total = result.scalar() or 0

    result2 = await db.execute(select(func.count(func.distinct(DnsEvent.client_ip))))
    unique_clients = result2.scalar() or 0

    result3 = await db.execute(select(func.count(func.distinct(DnsEvent.fqdn))))
    unique_fqdns = result3.scalar() or 0

    result4 = await db.execute(select(func.min(DnsEvent.timestamp), func.max(DnsEvent.timestamp)))
    row = result4.first()
    min_ts, max_ts = (row[0], row[1]) if row else (None, None)

    return {
        "total_events": total,
        "unique_clients": unique_clients,
        "unique_fqdns": unique_fqdns,
        "earliest": min_ts.isoformat() if min_ts else None,
        "latest": max_ts.isoformat() if max_ts else None,
    }
