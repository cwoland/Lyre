from enum import StrEnum
from uuid import UUID

from sqlalchemy import Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class BoardRole(StrEnum):
    owner = "owner"
    editor = "editor"
    viewer = "viewer"


board_role_column = Enum(
    BoardRole,
    name="board_role",
    native_enum=False,
    create_constraint=True,
    validate_strings=True,
    values_callable=lambda enum: [member.value for member in enum],
    length=16,
)


class BoardMember(TimestampMixin, Base):
    __tablename__ = "board_members"

    board_id: Mapped[UUID] = mapped_column(
        ForeignKey("boards.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True, index=True
    )
    role: Mapped[BoardRole] = mapped_column(board_role_column)
