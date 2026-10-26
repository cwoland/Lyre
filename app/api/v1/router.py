from fastapi import APIRouter

from app.api.v1 import auth, boards, invites, members

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(boards.router)
api_router.include_router(members.router)
api_router.include_router(invites.board_invites_router)
api_router.include_router(invites.invites_router)
