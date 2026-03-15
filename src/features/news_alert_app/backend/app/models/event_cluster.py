from datetime import datetime

from sqlalchemy import DateTime, Enum, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import AlertLevel, EventStatus


class EventCluster(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "event_clusters"
    __table_args__ = (
        Index("ix_event_clusters_last_seen_at", "last_seen_at"),
        Index("ix_event_clusters_first_seen_at", "first_seen_at"),
        Index("ix_event_clusters_topic_region", "topic", "region"),
        Index("ix_event_clusters_status", "status"),
    )

    canonical_title: Mapped[str] = mapped_column(Text, nullable=False)
    topic: Mapped[str | None] = mapped_column(String(100), nullable=True)
    region: Mapped[str | None] = mapped_column(String(100), nullable=True)

    status: Mapped[EventStatus] = mapped_column(
        Enum(EventStatus, name="event_status_enum"),
        nullable=False,
        default=EventStatus.ACTIVE,
    )

    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    source_count: Mapped[int] = mapped_column(nullable=False, default=0)
    trusted_source_count: Mapped[int] = mapped_column(nullable=False, default=0)

    entities: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    labels: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    latest_severity_score: Mapped[float | None] = mapped_column(nullable=True)
    latest_confidence_score: Mapped[float | None] = mapped_column(nullable=True)
    latest_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    last_alert_level: Mapped[AlertLevel | None] = mapped_column(
        Enum(AlertLevel, name="event_last_alert_level_enum"),
        nullable=True,
    )
    last_alert_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cooldown_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    articles = relationship("Article", back_populates="event")
    event_articles = relationship(
        "EventArticle",
        back_populates="event",
        cascade="all, delete-orphan",
    )
    analyses = relationship(
        "Analysis",
        back_populates="event",
        cascade="all, delete-orphan",
        order_by="desc(Analysis.created_at)",
    )
    alerts = relationship(
        "Alert",
        back_populates="event",
        cascade="all, delete-orphan",
        order_by="desc(Alert.created_at)",
    )