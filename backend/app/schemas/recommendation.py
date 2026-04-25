from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel


class RecommendationSchema(BaseModel):
    id: int
    type: str
    name: str
    confidence: float
    evidence: dict[str, Any]
    status: str
    illumio_payload: Optional[dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RecommendationUpdate(BaseModel):
    status: Optional[str] = None
    name: Optional[str] = None
    illumio_payload: Optional[dict[str, Any]] = None
