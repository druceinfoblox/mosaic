from datetime import datetime
from sqlalchemy import Integer, String, DateTime, Float, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class Dependency(Base):
    __tablename__ = "dependencies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    client_ip: Mapped[str] = mapped_column(String(45), index=True)
    fqdn: Mapped[str] = mapped_column(String(253), index=True)
    first_seen: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_seen: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    query_count: Mapped[int] = mapped_column(Integer, default=0)
    days_observed: Mapped[int] = mapped_column(Integer, default=0)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0)
    is_internal: Mapped[bool] = mapped_column(Boolean, default=False)
    answer_ips_stable: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
