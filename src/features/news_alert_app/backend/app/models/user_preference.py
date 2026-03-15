import uuid

from sqlalchemy import Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.base import TimestampMixin


class UserPreference(TimestampMixin, Base):
    __tablename__ = "user_preferences"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )

    min_severity: Mapped[float] = mapped_column(nullable=False, default=0.8)

    topics: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    regions: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    telegram_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    telegram_chat_id: Mapped[str | None] = mapped_column(nullable=True)

    whatsapp_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    whatsapp_phone: Mapped[str | None] = mapped_column(nullable=True)

    messenger_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    messenger_psid: Mapped[str | None] = mapped_column(nullable=True)

    user = relationship("User", back_populates="preference")