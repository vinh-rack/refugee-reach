import uuid

from sqlalchemy import Enum, ForeignKey, Index, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import AlertLevel


class Alert(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "alerts"
    __table_args__ = (
        Index("ix_alerts_event_id", "event_id"),
        Index("ix_alerts_created_at", "created_at"),
        Index("ix_alerts_alert_level", "alert_level"),
    )

    event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("event_clusters.id", ondelete="CASCADE"),
        nullable=False,
    )

    alert_level: Mapped[AlertLevel] = mapped_column(
        Enum(AlertLevel, name="alert_level_enum"),
        nullable=False,
    )

    reason: Mapped[str] = mapped_column(Text, nullable=False)

    analysis_snapshot: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    event = relationship("EventCluster", back_populates="alerts")
    deliveries = relationship(
        "Delivery",
        back_populates="alert",
        cascade="all, delete-orphan",
    )