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


async def require_admin(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)) -> User:
    """
    Legacy admin check - checks if user belongs to admin group or has admin role.
    For new code, use require_permission instead.
    """
    # Check new permission system - user in admin group
    if await user.has_permission(session, "users", "delete"):  # Admin groups have all permissions
        return user
    
    # Fallback to legacy role check
    if user.role and user.role.name == "admin":
        return user
    
    raise HTTPException(status_code=403, detail="Admin required")


def require_permission(resource: str, action: str):
    """
    Dependency factory that creates a permission check dependency.
    Usage: @router.get("/clients", dependencies=[Depends(require_permission("clients", "read"))])
    """
    async def permission_checker(
        user: User = Depends(get_current_user),
        session: AsyncSession = Depends(get_session)
    ) -> User:
        if not await user.has_permission(session, resource, action):
            raise HTTPException(
                status_code=403,
                detail=f"Insufficient permissions: {resource}:{action} required"
            )
        return user
    
    return permission_checker
