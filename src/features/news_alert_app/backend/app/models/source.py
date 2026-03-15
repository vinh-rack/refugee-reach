from sqlalchemy import Boolean, Enum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import SourceType, TrustTier


class Source(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "sources"

    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)

    source_type: Mapped[SourceType] = mapped_column(
        Enum(SourceType, name="source_type_enum"),
        nullable=False,
    )

    base_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    rss_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    api_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    trust_tier: Mapped[TrustTier] = mapped_column(
        Enum(TrustTier, name="trust_tier_enum"),
        nullable=False,
        default=TrustTier.MEDIUM,
    )

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    polling_interval_seconds: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=300,
    )

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    articles = relationship(
        "Article",
        back_populates="source",
        cascade="all, delete-orphan",
    )