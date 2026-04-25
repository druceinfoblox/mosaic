from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import get_db
from app.models.recommendation import Recommendation
from app.schemas.recommendation import RecommendationSchema, RecommendationUpdate
from datetime import datetime

router = APIRouter(prefix="/api/v1/recommendations", tags=["recommendations"])


@router.get("")
async def get_recommendations(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    type: str = Query(None),
    status: str = Query(None),
    min_confidence: float = Query(0.0, ge=0.0, le=1.0),
    db: AsyncSession = Depends(get_db),
):
    query = select(Recommendation)
    if type:
        query = query.where(Recommendation.type == type)
    if status:
        query = query.where(Recommendation.status == status)
    if min_confidence:
        query = query.where(Recommendation.confidence >= min_confidence)

    total_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = total_result.scalar() or 0

    query = query.order_by(Recommendation.confidence.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    recs = result.scalars().all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [RecommendationSchema.model_validate(r) for r in recs],
    }


@router.patch("/{rec_id}")
async def update_recommendation(
    rec_id: int,
    update: RecommendationUpdate,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Recommendation).where(Recommendation.id == rec_id))
    rec = result.scalar_one_or_none()
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found")

    if update.status is not None:
        valid_statuses = {"PENDING", "APPROVED", "REJECTED", "DRAFT_CREATED"}
        if update.status not in valid_statuses:
            raise HTTPException(status_code=422, detail=f"Invalid status. Must be one of {valid_statuses}")
        rec.status = update.status
    if update.name is not None:
        rec.name = update.name
    if update.illumio_payload is not None:
        rec.illumio_payload = update.illumio_payload

    rec.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(rec)
    return RecommendationSchema.model_validate(rec)


@router.get("/{rec_id}/illumio-payload")
async def get_illumio_payload(rec_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Recommendation).where(Recommendation.id == rec_id))
    rec = result.scalar_one_or_none()
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    return {
        "id": rec.id,
        "name": rec.name,
        "type": rec.type,
        "illumio_payload": rec.illumio_payload,
    }
