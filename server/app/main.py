from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from pathlib import Path
from starlette.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from fastapi.exceptions import HTTPException
from fastapi.exception_handlers import http_exception_handler as fastapi_http_exception_handler

from .routers import api, auth, public
from .core.scheduler import init_scheduler
from .services.schema_sync import sync_schema
from .db import engine, Base
from .db import AsyncSessionLocal
from .models import GlobalSettings, IPAssignment, IPPool
from .core.config import DEFAULT_NEBULA_VERSION
from sqlalchemy import select


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    # Startup
    try:
        paths = [getattr(r, 'path', str(r)) for r in app.routes]
        print("[startup] Registered routes:\n" + "\n".join(paths))
    except Exception as e:
        print(f"[startup] Failed to list routes: {e}")
    
    # Create tables
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("[db-init] Created all tables from models")
    except Exception as e:
        print(f"[db-init] Failed to create tables: {e}")
    
    # Sync schema
    from .core.config import settings as app_settings
    if app_settings.enable_schema_autosync:
        try:
            await sync_schema(engine, Base)
            print("[schema-sync] Completed additive schema synchronization")
        except Exception as e:
            print(f"[schema-sync] Failed: {e}")
    else:
        print("[schema-sync] Disabled (set ENABLE_SCHEMA_AUTOSYNC=true to enable)")
    
    # Bootstrap defaults
    await bootstrap_defaults()
    
    # Ensure correct Nebula version is installed
    await ensure_nebula_version()
    
    # Start scheduler (must be done after event loop is running)
    from .core.scheduler import start_scheduler
    await start_scheduler(app)
    
    yield
    
    # Shutdown scheduler
    if hasattr(app.state, 'scheduler') and app.state.scheduler.running:
        app.state.scheduler.shutdown(wait=False)
        print("[scheduler] Shutdown background scheduler")


async def bootstrap_defaults():
    """Bootstrap default settings and data."""
    # Ensure a GlobalSettings row exists
    async with AsyncSessionLocal() as session:
        existing = (await session.execute(select(GlobalSettings))).scalars().first()
        if not existing:
            session.add(GlobalSettings())
            await session.commit()

    # Backfill pool_id for any IP assignments missing it, based on pool CIDRs.
    async with AsyncSessionLocal() as session:
        import ipaddress
        from .services.ip_allocator import ensure_default_pool
        from .core.config import settings as app_settings

        settings_row = (await session.execute(select(GlobalSettings))).scalars().first()
        default_cidr = settings_row.default_cidr_pool if settings_row else "10.100.0.0/16"

        assignments = (await session.execute(
            select(IPAssignment)
        )).scalars().all()
        if not assignments:
            return
        pools = (await session.execute(select(IPPool))).scalars().all()
        # Build quick lookup of networks
        pool_networks = []
        for p in pools:
            try:
                pool_networks.append((p, ipaddress.ip_network(p.cidr, strict=False)))
            except Exception:
                continue

        changed = False
        for ia in assignments:
            if ia.pool_id:
                continue
            try:
                ip_obj = ipaddress.ip_address(ia.ip_address)
            except Exception:
                continue
            matched_pool = None
            for (p, net) in pool_networks:
                if ip_obj in net:
                    matched_pool = p
                    break
            if not matched_pool:
                matched_pool = await ensure_default_pool(session, default_cidr)
                try:
                    pool_networks.append((matched_pool, ipaddress.ip_network(matched_pool.cidr, strict=False)))
                except Exception:
                    pass
            ia.pool_id = matched_pool.id
            changed = True

        if changed:
            await session.commit()

    # Ensure default user groups exist (Administrators, Users)
    try:
        async with AsyncSessionLocal() as session:
            from .models.permissions import UserGroup
            # Administrators group (is_admin=True)
            admins = (await session.execute(select(UserGroup).where(UserGroup.name == "Administrators"))).scalars().first()
            if not admins:
                admins = UserGroup(name="Administrators", description="Administrators with full access", is_admin=True)
                session.add(admins)
                await session.flush()
            # Users group (default)
            users_group = (await session.execute(select(UserGroup).where(UserGroup.name == "Users"))).scalars().first()
            if not users_group:
                users_group = UserGroup(name="Users", description="Default users group", is_admin=False)
                session.add(users_group)
                await session.flush()
            await session.commit()
    except Exception as e:
        print(f"[bootstrap] Failed ensuring default user groups: {e}")

    # Optional admin bootstrap from env
    try:
        async with AsyncSessionLocal() as session:
            from .models.user import User
            from .models.permissions import UserGroup, UserGroupMembership
            import os
            
            admin_email = os.getenv("ADMIN_EMAIL")
            admin_password = os.getenv("ADMIN_PASSWORD")
            
            if not admin_email or not admin_password:
                print("[bootstrap] ADMIN_EMAIL or ADMIN_PASSWORD not set, skipping auto-bootstrap")
                print("[bootstrap] Use 'docker exec <container> python manage.py create-admin <email>' to create admin manually")
                return
            
            print(f"[bootstrap] Checking admin bootstrap: email={admin_email}")
            
            user_count = (await session.execute(select(User))).scalars().all()
            if len(user_count) > 0:
                print(f"[bootstrap] Database already has {len(user_count)} user(s), skipping auto-bootstrap")
                return
            
            print(f"[bootstrap] No users found, creating initial admin user: {admin_email}")
            
            from .core.auth import hash_password
            u = User(
                email=admin_email, 
                hashed_password=hash_password(admin_password), 
                is_active=True
            )
            session.add(u)
            await session.flush()
            
            # Add to Administrators group (required for admin access)
            admins_group = (await session.execute(select(UserGroup).where(UserGroup.name == "Administrators"))).scalars().first()
            if admins_group:
                session.add(UserGroupMembership(user_id=u.id, user_group_id=admins_group.id))
            else:
                print("[bootstrap] WARNING: Administrators group not found, user will not have admin access")
            
            await session.commit()
            print(f"[bootstrap] ✅ Admin user created successfully: {admin_email}")
            print(f"[bootstrap] User added to Administrators group for admin access")
            
    except Exception as e:
        print(f"[bootstrap] ❌ Failed to create admin user: {e}")
        import traceback
        traceback.print_exc()
        print("[bootstrap] You can manually create an admin using:")
        print("[bootstrap]   docker exec <container> python manage.py create-admin <email>")


async def ensure_nebula_version():
    """Ensure the configured Nebula version is installed on server startup."""
    try:
        async with AsyncSessionLocal() as session:
            from .services.nebula_installer import NebulaInstaller
            
            # Get configured version from settings
            settings_row = (await session.execute(select(GlobalSettings))).scalars().first()
            if not settings_row:
                print("[nebula-check] No settings found, skipping version check")
                return
            
            configured_version = getattr(settings_row, 'nebula_version', DEFAULT_NEBULA_VERSION).lstrip('v')
            
            # Use the service's ensure_version_installed method to avoid duplicating logic
            installer = NebulaInstaller()
            print(f"[nebula-check] Checking Nebula installation (configured version: {configured_version})...")
            success, message = await installer.ensure_version_installed(configured_version)
            
            if success:
                print(f"[nebula-check] ✅ {message}")
            else:
                print(f"[nebula-check] ⚠️  {message}")
                
    except Exception as e:
        print(f"[nebula-check] ⚠️  Failed to check/install Nebula version: {e}")
        import traceback
        traceback.print_exc()
        print("[nebula-check] Server will continue, but nebula-cert commands may fail")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Managed Nebula API", 
        version="0.1.0",
        openapi_version="3.1.0",
        description="A comprehensive VPN management platform for Nebula mesh networks",
        docs_url="/docs",
        redoc_url=None,  # Disable default ReDoc to create custom one
        lifespan=lifespan
    )

    # Custom ReDoc endpoint with working JS library
    from fastapi.responses import HTMLResponse
    
    @app.get("/redoc", response_class=HTMLResponse, include_in_schema=False)
    async def custom_redoc():
        return HTMLResponse(content="""
        <!DOCTYPE html>
        <html>
        <head>
        <title>Managed Nebula API - ReDoc</title>
        <meta charset="utf-8"/>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link href="https://fonts.googleapis.com/css?family=Montserrat:300,400,700|Roboto:300,400,700" rel="stylesheet">
        <link rel="shortcut icon" href="/static/favicon.png">
        <style>
          body { margin: 0; padding: 0; }
        </style>
        </head>
        <body>
        <noscript>ReDoc requires Javascript to function. Please enable it to browse the documentation.</noscript>
        <redoc spec-url="/openapi.json"></redoc>
        <script src="https://cdn.jsdelivr.net/npm/redoc@2.1.3/bundles/redoc.standalone.js"></script>
        </body>
        </html>
        """)

    # Sessions for auth (used by both SPA and client agent)
    # MUST be added before CORS to ensure cookie is set properly
    from .core.config import settings as app_settings
    app.add_middleware(
        SessionMiddleware,
        secret_key=app_settings.secret_key,
        max_age=604800,  # 7 days in seconds
    same_site="lax",
    https_only=False  # Allow cookies over HTTP for local dev
    )

    # CORS for SPA frontend
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routers
    app.include_router(public.router)  # Public endpoints (no prefix)
    app.include_router(api.router, prefix="/api")
    app.include_router(auth.router)

    # Background scheduler for rotations
    init_scheduler(app)

    @app.exception_handler(HTTPException)
    async def custom_http_exception_handler(request: Request, exc: HTTPException):
        # All responses are JSON now (no HTML redirects)
        return await fastapi_http_exception_handler(request, exc)

    return app


app = create_app()
static_path = str(Path(__file__).resolve().parents[1] / "static")
try:
    # Mount a static files directory at /static (optional; created by update script)
    app.mount("/static", StaticFiles(directory=static_path), name="static")
except Exception:
    pass
