from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.models import BoardRole, InviteStatus


class InviteCreate(BaseModel):
    role: Literal[BoardRole.editor, BoardRole.viewer] = BoardRole.editor
    ttl_hours: int = Field(default=48, ge=1, le=720)


class InviteResponse(BaseModel):
    id: UUID
    board_id: UUID
    role: BoardRole
    status: InviteStatus
    expires_at: datetime
    created_at: datetime


class InviteCreatedResponse(InviteResponse):
    token: str


class InvitePreview(BaseModel):
    board_id: UUID
    board_title: str
    role: BoardRole
    expires_at: datetime
