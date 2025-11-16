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
from ..models.permissions import UserGroup, UserGroupMembership
from ..core.auth import verify_password, get_current_user
from ..core.config import settings
from ..core.auth import hash_password

router = APIRouter(tags=["auth"])


class JsonLoginRequest(BaseModel):
    email: str
    password: str


class MeResponse(BaseModel):
    id: int
    email: str
    is_active: bool
    is_admin: bool


class MeUpdateRequest(BaseModel):
    email: Optional[str] = None
    current_password: str
    new_password: Optional[str] = None


@router.post("/api/v1/auth/login", tags=["auth"])
async def api_login(body: JsonLoginRequest, request: Request, session: AsyncSession = Depends(get_session)):
    user = (
        await session.execute(
            select(User).where(User.email == body.email)
        )
    ).scalars().first()
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="User inactive")
    request.session["user_id"] = user.id
    # Determine admin via group membership (is_admin=True)
    admins_membership = await session.execute(
        select(UserGroupMembership)
        .join(UserGroup, UserGroup.id == UserGroupMembership.user_group_id)
        .where(UserGroupMembership.user_id == user.id, UserGroup.is_admin == True)
    )
    is_admin = admins_membership.scalars().first() is not None
    return {
        "id": user.id,
        "email": user.email,
        "is_active": user.is_active,
        "is_admin": is_admin,
    }


@router.post("/api/v1/auth/logout", tags=["auth"])
async def api_logout(request: Request):
    request.session.clear()
    return {"ok": True}


@router.get("/api/v1/auth/me", response_model=MeResponse, tags=["auth"])
async def api_me(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    admins_membership = await session.execute(
        select(UserGroupMembership)
        .join(UserGroup, UserGroup.id == UserGroupMembership.user_group_id)
        .where(UserGroupMembership.user_id == user.id, UserGroup.is_admin == True)
    )
    is_admin = admins_membership.scalars().first() is not None
    return MeResponse(
        id=user.id,
        email=user.email,
        is_active=user.is_active,
        is_admin=is_admin,
    )


@router.put("/api/v1/auth/me", response_model=MeResponse, tags=["auth"])
async def api_update_me(
    body: MeUpdateRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user)
):
    # Block when users are externally managed
    if settings.externally_managed_users:
        raise HTTPException(status_code=403, detail="Users are managed externally; local profile changes are disabled")

    # Reload user from DB
    db_user = (
        await session.execute(
            select(User).where(User.id == user.id)
        )
    ).scalars().first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Verify current password
    if not verify_password(body.current_password, db_user.hashed_password):
        raise HTTPException(status_code=401, detail="Current password is incorrect")

    # Update email if requested
    if body.email and body.email != db_user.email:
        # Ensure unique
        dup = await session.execute(select(User).where(User.email == body.email, User.id != db_user.id))
        if dup.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Email already exists")
        db_user.email = body.email

    # Update password if requested
    if body.new_password:
        db_user.hashed_password = hash_password(body.new_password)

    await session.commit()

    # Return updated me response
    admins_membership = await session.execute(
        select(UserGroupMembership)
        .join(UserGroup, UserGroup.id == UserGroupMembership.user_group_id)
        .where(UserGroupMembership.user_id == db_user.id, UserGroup.is_admin == True)
    )
    is_admin = admins_membership.scalars().first() is not None

    return MeResponse(
        id=db_user.id,
        email=db_user.email,
        is_active=db_user.is_active,
        is_admin=is_admin,
    )


if os.getenv("DEBUG_AUTH", "false").lower() in ("true", "1", "yes"):
    @router.get("/api/v1/auth/debug/users", tags=["auth"])
    async def list_users_debug(session: AsyncSession = Depends(get_session)):
        rows = (await session.execute(select(User.email))).scalars().all()
        return {"emails": rows}
