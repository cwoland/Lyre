from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models import BoardRole


class BoardCreate(BaseModel):
    title: str = Field(min_length=1, max_length=120)


class BoardUpdate(BaseModel):
    title: str = Field(min_length=1, max_length=120)


class BoardResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    owner_id: UUID
    created_at: datetime
    updated_at: datetime


class BoardListItem(BoardResponse):
    role: BoardRole
