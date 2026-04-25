from datetime import datetime
from sqlalchemy import Integer, String, DateTime, JSON, Float
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class ClientProfile(Base):
    __tablename__ = "client_profiles"

    client_ip: Mapped[str] = mapped_column(String(45), primary_key=True)
    first_seen: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_seen: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    total_queries: Mapped[int] = mapped_column(Integer, default=0)
    unique_fqdns: Mapped[int] = mapped_column(Integer, default=0)
    top_fqdns: Mapped[list] = mapped_column(JSON, default=list)
    subnet: Mapped[str | None] = mapped_column(String(50), nullable=True)
    owner: Mapped[str | None] = mapped_column(String(100), nullable=True)
    site: Mapped[str | None] = mapped_column(String(100), nullable=True)
    business_unit: Mapped[str | None] = mapped_column(String(100), nullable=True)
    hostname: Mapped[str | None] = mapped_column(String(253), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
