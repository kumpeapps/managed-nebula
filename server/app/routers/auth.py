from __future__ import annotations
from fastapi import APIRouter, Request, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
import os
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from ..db import get_session
from ..models.user import User
from ..core.auth import verify_password, get_current_user

router = APIRouter(tags=["auth"])


class JsonLoginRequest(BaseModel):
    email: str
    password: str


class MeResponse(BaseModel):
    id: int
    email: str
    is_active: bool
    role: Optional[str]
    is_admin: bool


@router.post("/api/v1/auth/login", tags=["auth"])
async def api_login(body: JsonLoginRequest, request: Request, session: AsyncSession = Depends(get_session)):
    user = (
        await session.execute(
            select(User).options(selectinload(User.role)).where(User.email == body.email)
        )
    ).scalars().first()
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="User inactive")
    request.session["user_id"] = user.id
    return {
        "id": user.id,
        "email": user.email,
        "is_active": user.is_active,
        "role": user.role.name if user.role else None,
        "is_admin": bool(user.role and user.role.name == "admin"),
    }


@router.post("/api/v1/auth/logout", tags=["auth"])
async def api_logout(request: Request):
    request.session.clear()
    return {"ok": True}


@router.get("/api/v1/auth/me", response_model=MeResponse, tags=["auth"])
async def api_me(user: User = Depends(get_current_user)):
    return MeResponse(
        id=user.id,
        email=user.email,
        is_active=user.is_active,
        role=user.role.name if user.role else None,
        is_admin=bool(user.role and user.role.name == "admin"),
    )


if os.getenv("DEBUG_AUTH", "false").lower() in ("true", "1", "yes"):
    @router.get("/api/v1/auth/debug/users", tags=["auth"])
    async def list_users_debug(session: AsyncSession = Depends(get_session)):
        rows = (await session.execute(select(User.email))).scalars().all()
        return {"emails": rows}
