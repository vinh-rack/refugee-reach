import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import ArticleStatus


class Article(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "articles"
    __table_args__ = (
        UniqueConstraint("source_id", "external_id", name="uq_articles_source_external_id"),
        Index("ix_articles_published_at", "published_at"),
        Index("ix_articles_fetched_at", "fetched_at"),
        Index("ix_articles_status", "status"),
        Index("ix_articles_normalized_hash", "normalized_hash"),
        Index("ix_articles_event_id", "event_id"),
    )

    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sources.id", ondelete="RESTRICT"),
        nullable=False,
    )

    event_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("event_clusters.id", ondelete="SET NULL"),
        nullable=True,
    )

    external_id: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary_hint: Mapped[str | None] = mapped_column(Text, nullable=True)

    raw_payload_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_html_path: Mapped[str | None] = mapped_column(Text, nullable=True)

    language: Mapped[str | None] = mapped_column(String(16), nullable=True)
    author: Mapped[str | None] = mapped_column(String(255), nullable=True)

    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    normalized_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)

    region_hint: Mapped[str | None] = mapped_column(String(100), nullable=True)
    topic_hint: Mapped[str | None] = mapped_column(String(100), nullable=True)

    entities: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    keywords: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    extra_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    quality_score: Mapped[float | None] = mapped_column(nullable=True)

    status: Mapped[ArticleStatus] = mapped_column(
        Enum(ArticleStatus, name="article_status_enum"),
        nullable=False,
        default=ArticleStatus.INGESTED,
    )

    source = relationship("Source", back_populates="articles")
    event = relationship("EventCluster", back_populates="articles")
    event_links = relationship(
        "EventArticle",
        back_populates="article",
        cascade="all, delete-orphan",
    )