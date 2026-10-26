from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, EmailStr

from app.models import BoardRole


class MemberResponse(BaseModel):
    user_id: UUID
    display_name: str
    email: EmailStr
    cursor_color: str
    role: BoardRole
    joined_at: datetime


class MemberRoleUpdate(BaseModel):
    role: Literal[BoardRole.editor, BoardRole.viewer]
