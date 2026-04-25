import os
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.recommendation import Recommendation
from app.services.illumio import get_illumio_client

router = APIRouter(prefix="/api/v1/illumio", tags=["illumio"])

_app_settings: dict = {}


def get_settings() -> dict:
    return {
        "ILLUMIO_PCE_URL": os.environ.get("ILLUMIO_PCE_URL", ""),
        "ILLUMIO_ORG_ID": os.environ.get("ILLUMIO_ORG_ID", "1"),
        "ILLUMIO_API_KEY_USERNAME": os.environ.get("ILLUMIO_API_KEY_USERNAME", ""),
        "ILLUMIO_API_KEY_SECRET": os.environ.get("ILLUMIO_API_KEY_SECRET", ""),
        "ILLUMIO_DRY_RUN": os.environ.get("ILLUMIO_DRY_RUN", "true"),
        **_app_settings,
    }


@router.get("/config")
async def get_illumio_config():
    settings = get_settings()
    configured = bool(
        settings.get("ILLUMIO_PCE_URL")
        and settings["ILLUMIO_PCE_URL"] != "https://your-pce.illumio.com"
        and settings.get("ILLUMIO_API_KEY_USERNAME")
    )
    return {
        "configured": configured,
        "pce_url": settings.get("ILLUMIO_PCE_URL", ""),
        "org_id": settings.get("ILLUMIO_ORG_ID", "1"),
        "dry_run": settings.get("ILLUMIO_DRY_RUN", "true").lower() == "true",
        "has_credentials": bool(settings.get("ILLUMIO_API_KEY_USERNAME")),
    }


@router.post("/test")
async def test_illumio_connection():
    settings = get_settings()
    client = get_illumio_client(settings)
    if not client:
        return {
            "connected": False,
            "message": "Illumio PCE not configured. Set ILLUMIO_PCE_URL and credentials in settings.",
        }
    result = await client.test_connection()
    return result


@router.get("/workloads")
async def get_illumio_workloads(max_results: int = Query(100, ge=1, le=500)):
    settings = get_settings()
    client = get_illumio_client(settings)
    if not client:
        return {"error": "Illumio PCE not configured", "workloads": []}
    workloads = await client.get_workloads(max_results=max_results)
    return {"workloads": workloads if isinstance(workloads, list) else []}


@router.post("/push")
async def push_to_illumio(
    dry_run: bool = Query(True),
    db: AsyncSession = Depends(get_db),
):
    settings = get_settings()
    client = get_illumio_client(settings, dry_run=dry_run)

    # Get approved recommendations
    result = await db.execute(
        select(Recommendation).where(Recommendation.status == "APPROVED")
    )
    approved = result.scalars().all()

    if not approved:
        return {"message": "No approved recommendations to push", "pushed": 0}

    if not client:
        # Return dry-run payloads without actual PCE
        return {
            "dry_run": True,
            "message": "PCE not configured — showing payloads only",
            "pushed": len(approved),
            "results": [
                {
                    "id": r.id,
                    "name": r.name,
                    "type": r.type,
                    "payload": r.illumio_payload,
                    "result": {"dry_run": True, "simulated": True},
                }
                for r in approved
            ],
        }

    results = []
    for rec in approved:
        payload = rec.illumio_payload or {}
        obj_type = payload.get("object_type", rec.type.lower())
        try:
            if obj_type == "ip_list":
                result = await client.create_ip_list_draft(
                    name=rec.name,
                    description=payload.get("description", ""),
                    ranges=payload.get("ip_ranges", []),
                )
            elif obj_type == "service":
                result = await client.create_service_draft(
                    name=rec.name,
                    description=payload.get("description", ""),
                    service_ports=payload.get("service_ports", []),
                )
            elif obj_type == "ruleset":
                result = await client.create_ruleset_draft(
                    name=rec.name,
                    description=payload.get("description", ""),
                    scopes=payload.get("scopes", []),
                )
            elif obj_type == "workload_group":
                result = {"dry_run": dry_run, "message": "Workload group push via bulk API"}
            else:
                result = {"skipped": True, "reason": f"Unknown object type: {obj_type}"}

            if not dry_run:
                rec.status = "DRAFT_CREATED"
                await db.commit()

            results.append({"id": rec.id, "name": rec.name, "type": rec.type, "result": result})
        except Exception as e:
            results.append({"id": rec.id, "name": rec.name, "type": rec.type, "error": str(e)})

    return {"dry_run": dry_run, "pushed": len(results), "results": results}
