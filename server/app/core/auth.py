from passlib.context import CryptContext
from fastapi import HTTPException, Request, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..db import get_session
from ..models.user import User
import logging

"""Authentication helpers and password hashing/verification.

We continue to hash new/updated passwords with bcrypt_sha256 to avoid bcrypt's
72-byte truncation behavior. For compatibility with existing/legacy users, we
allow verification against multiple common schemes supported by passlib.
"""

logger = logging.getLogger(__name__)

# Workaround for passlib 1.7.4 + bcrypt 5.x compatibility
# See: https://github.com/pyca/bcrypt/issues/684
# bcrypt 5.0 enforces 72-byte limit and removed __about__
#
# WARNING: This monkeypatch globally modifies bcrypt.hashpw behavior for the entire process.
# Passwords >72 bytes will be silently truncated before hashing, which is required for
# passlib's bcrypt_sha256 wrapper to work correctly with bcrypt 5.x.
#
# Our application always uses bcrypt_sha256 via passlib (not direct bcrypt), which
# pre-hashes passwords with SHA256, so passwords should never exceed 72 bytes in practice.
# This wrapper ensures compatibility if passlib or dependencies call bcrypt directly.
try:
    import bcrypt as _bcrypt_module
    # Check if bcrypt 5.x (missing __about__)
    if not hasattr(_bcrypt_module, '__about__'):
        # Monkeypatch to provide the expected __about__ attribute
        class _About:
            __version__ = _bcrypt_module.__version__
        _bcrypt_module.__about__ = _About()
        
        # Wrap bcrypt.hashpw to auto-truncate passwords >72 bytes for passlib compatibility
        _original_hashpw = _bcrypt_module.hashpw
        
        def _wrapped_hashpw(password, salt):
            """Wrap hashpw to truncate passwords >72 bytes for passlib's wrap-bug detection.
            
            This is a compatibility shim for passlib 1.7.4 + bcrypt 5.x.
            Logs a warning if truncation occurs, since this changes bcrypt's default behavior.
            """
            if isinstance(password, bytes) and len(password) > 72:
                logger.warning(
                    "bcrypt password truncated from %d to 72 bytes. "
                    "This is expected for passlib bcrypt_sha256 compatibility with bcrypt 5.x, "
                    "but may indicate unexpected direct bcrypt usage elsewhere.",
                    len(password)
                )
                password = password[:72]
            return _original_hashpw(password, salt)
        
        _bcrypt_module.hashpw = _wrapped_hashpw
except ImportError:
    pass

# Preferred scheme remains bcrypt_sha256. Enable several legacy schemes for verification only.
# Passlib auto-detects the right hasher based on the stored hash format.
pwd_context = CryptContext(
    schemes=[
        "bcrypt_sha256",   # preferred
        "bcrypt",          # legacy bcrypt
        "pbkdf2_sha256",   # common in many frameworks
        "sha256_crypt",    # legacy
        "sha512_crypt",    # legacy
        "md5_crypt",       # legacy/weak
        "phpass",          # WordPress/Drupal style
    ],
    deprecated=[
        "bcrypt", "pbkdf2_sha256", "sha256_crypt", "sha512_crypt", "md5_crypt", "phpass"
    ],
)


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
            select(User).where(User.id == user_id)
        )
    ).scalars().first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Invalid user")
    return user


async def require_login(user: User = Depends(get_current_user)) -> User:
    return user


async def require_admin(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)) -> User:
    """
    Admin check - checks if user belongs to an admin group.
    For more granular checks, use require_permission instead.
    """
    # Check permission system - user in admin group or has admin-level permissions
    if await user.has_permission(session, "users", "delete"):  # Admin groups have all permissions
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
