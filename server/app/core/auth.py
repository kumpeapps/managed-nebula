from passlib.context import CryptContext
from fastapi import HTTPException, Request, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from ..db import get_session
from ..models.user import User, Role

# Use bcrypt_sha256 to avoid bcrypt's 72-byte password truncation/limit and backend quirks
pwd_context = CryptContext(schemes=["bcrypt_sha256"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


async def get_current_user(request: Request, session: AsyncSession = Depends(get_session)) -> User:
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user = (
        await session.execute(
            select(User).options(selectinload(User.role)).where(User.id == user_id)
        )
    ).scalars().first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Invalid user")
    return user


async def require_login(user: User = Depends(get_current_user)) -> User:
    return user


async def require_admin(user: User = Depends(get_current_user)) -> User:
    if not user.role or user.role.name != "admin":
        raise HTTPException(status_code=403, detail="Admin required")
    return user
