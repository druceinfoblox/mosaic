from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import get_db
from app.models.dns_event import DnsEvent
from app.models.client_profile import ClientProfile
from app.models.fqdn_profile import FqdnProfile
from app.models.dependency import Dependency
from app.models.recommendation import Recommendation
from app.schemas.dependency import DependencySchema
from app.schemas.client_profile import ClientProfileSchema
from app.schemas.fqdn_profile import FqdnProfileSchema
from app.services.correlator import run_correlation
from app.services.enricher import run_enrichment
from app.services.recommender import run_recommendations

router = APIRouter(prefix="/api/v1", tags=["analysis"])


@router.post("/analyze")
async def run_analysis(db: AsyncSession = Depends(get_db)):
    correlation_result = await run_correlation(db)
    enrichment_result = await run_enrichment(db)
    recommendation_result = await run_recommendations(db)
    return {
        "status": "ok",
        "correlation": correlation_result,
        "enrichment": enrichment_result,
        "recommendations": recommendation_result,
    }


@router.get("/overview")
async def get_overview(db: AsyncSession = Depends(get_db)):
    total_events = (await db.execute(select(func.count(DnsEvent.id)))).scalar() or 0
    unique_clients = (await db.execute(select(func.count(func.distinct(DnsEvent.client_ip))))).scalar() or 0
    unique_fqdns = (await db.execute(select(func.count(func.distinct(DnsEvent.fqdn))))).scalar() or 0

    min_max = (await db.execute(select(func.min(DnsEvent.timestamp), func.max(DnsEvent.timestamp)))).first()
    earliest, latest = (min_max[0], min_max[1]) if min_max and min_max[0] else (None, None)

    days_history = 0
    if earliest and latest:
        delta = latest - earliest
        days_history = delta.days + 1

    total_deps = (await db.execute(select(func.count(Dependency.id)))).scalar() or 0
    total_recs = (await db.execute(select(func.count(Recommendation.id)))).scalar() or 0

    # Count approved/pending recommendations
    high_conf = (await db.execute(
        select(func.count(Recommendation.id)).where(Recommendation.confidence >= 0.7)
    )).scalar() or 0

    # Count workload groups (subnets / segments)
    segments = (await db.execute(
        select(func.count(func.distinct(ClientProfile.subnet)))
    )).scalar() or 0

    # Count unique app destinations
    app_deps = (await db.execute(
        select(func.count(func.distinct(Dependency.fqdn))).where(Dependency.confidence_score >= 0.5)
    )).scalar() or 0

    return {
        "days_history": days_history,
        "unique_endpoints": unique_clients,
        "unique_fqdns": unique_fqdns,
        "total_events": total_events,
        "candidate_applications": app_deps,
        "candidate_segments": segments,
        "draft_illumio_objects": total_recs,
        "high_confidence_recs": high_conf,
        "time_saved_weeks": 6,
        "earliest": earliest.isoformat() if earliest else None,
        "latest": latest.isoformat() if latest else None,
        "analyzed": total_deps > 0,
    }


@router.get("/dependencies")
async def get_dependencies(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    min_confidence: float = Query(0.0, ge=0.0, le=1.0),
    client_ip: str = Query(None),
    fqdn: str = Query(None),
    is_internal: bool = Query(None),
    db: AsyncSession = Depends(get_db),
):
    query = select(Dependency)
    if min_confidence:
        query = query.where(Dependency.confidence_score >= min_confidence)
    if client_ip:
        query = query.where(Dependency.client_ip == client_ip)
    if fqdn:
        query = query.where(Dependency.fqdn.contains(fqdn))
    if is_internal is not None:
        query = query.where(Dependency.is_internal == is_internal)

    total_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = total_result.scalar() or 0

    query = query.order_by(Dependency.confidence_score.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    deps = result.scalars().all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [DependencySchema.model_validate(d) for d in deps],
    }


@router.get("/workloads")
async def get_workloads(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    business_unit: str = Query(None),
    subnet: str = Query(None),
    db: AsyncSession = Depends(get_db),
):
    query = select(ClientProfile)
    if business_unit:
        query = query.where(ClientProfile.business_unit == business_unit)
    if subnet:
        query = query.where(ClientProfile.subnet == subnet)

    total_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = total_result.scalar() or 0

    query = query.order_by(ClientProfile.total_queries.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    profiles = result.scalars().all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [ClientProfileSchema.model_validate(p) for p in profiles],
    }


@router.get("/workloads/{client_ip}")
async def get_workload_detail(client_ip: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ClientProfile).where(ClientProfile.client_ip == client_ip))
    profile = result.scalar_one_or_none()

    # Get dependencies for this IP
    dep_result = await db.execute(
        select(Dependency).where(Dependency.client_ip == client_ip).order_by(Dependency.confidence_score.desc()).limit(20)
    )
    deps = dep_result.scalars().all()

    # Get RCODE distribution from dns_events
    rcode_result = await db.execute(
        select(DnsEvent.rcode, func.count(DnsEvent.id))
        .where(DnsEvent.client_ip == client_ip)
        .group_by(DnsEvent.rcode)
    )
    rcode_dist = {row[0]: row[1] for row in rcode_result}

    # Get recent timeline (events per day, last 30 days)
    from sqlalchemy import cast, Date
    timeline_result = await db.execute(
        select(cast(DnsEvent.timestamp, Date), func.count(DnsEvent.id))
        .where(DnsEvent.client_ip == client_ip)
        .group_by(cast(DnsEvent.timestamp, Date))
        .order_by(cast(DnsEvent.timestamp, Date))
        .limit(90)
    )
    timeline = [{"date": str(row[0]), "count": row[1]} for row in timeline_result]

    return {
        "profile": ClientProfileSchema.model_validate(profile) if profile else None,
        "dependencies": [DependencySchema.model_validate(d) for d in deps],
        "rcode_distribution": rcode_dist,
        "timeline": timeline,
    }


@router.get("/fqdns")
async def get_fqdns(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    is_internal: bool = Query(None),
    category: str = Query(None),
    db: AsyncSession = Depends(get_db),
):
    query = select(FqdnProfile)
    if is_internal is not None:
        query = query.where(FqdnProfile.is_internal == is_internal)
    if category:
        query = query.where(FqdnProfile.category == category)

    total_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = total_result.scalar() or 0

    query = query.order_by(FqdnProfile.total_queries.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    fqdns = result.scalars().all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [FqdnProfileSchema.model_validate(f) for f in fqdns],
    }
