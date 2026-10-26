from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.membership import BoardRole, board_role_column


class InviteStatus(StrEnum):
    pending = "pending"
    used = "used"
    revoked = "revoked"
    expired = "expired"


class BoardInvite(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "board_invites"

    board_id: Mapped[UUID] = mapped_column(ForeignKey("boards.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    role: Mapped[BoardRole] = mapped_column(board_role_column)
    created_by: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    used_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), default=None
    )

    @property
    def status(self) -> InviteStatus:
        if self.revoked_at is not None:
            return InviteStatus.revoked
        if self.used_at is not None:
            return InviteStatus.used
        if self.expires_at <= datetime.now(UTC):
            return InviteStatus.expired
        return InviteStatus.pending
