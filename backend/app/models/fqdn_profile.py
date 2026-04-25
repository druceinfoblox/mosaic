from datetime import datetime
from sqlalchemy import Integer, String, DateTime, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class FqdnProfile(Base):
    __tablename__ = "fqdn_profiles"

    fqdn: Mapped[str] = mapped_column(String(253), primary_key=True)
    first_seen: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_seen: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    total_queries: Mapped[int] = mapped_column(Integer, default=0)
    unique_clients: Mapped[int] = mapped_column(Integer, default=0)
    answer_ips: Mapped[list] = mapped_column(JSON, default=list)
    is_internal: Mapped[bool] = mapped_column(Boolean, default=False)
    category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
