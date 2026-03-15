import uuid

from sqlalchemy import ForeignKey, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.base import TimestampMixin


class EventArticle(TimestampMixin, Base):
    __tablename__ = "event_articles"
    __table_args__ = (
        UniqueConstraint("event_id", "article_id", name="uq_event_articles_event_article"),
        Index("ix_event_articles_event_id", "event_id"),
        Index("ix_event_articles_article_id", "article_id"),
    )

    event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("event_clusters.id", ondelete="CASCADE"),
        primary_key=True,
    )

    article_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("articles.id", ondelete="CASCADE"),
        primary_key=True,
    )

    event = relationship("EventCluster", back_populates="event_articles")
    article = relationship("Article", back_populates="event_links")