from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta

from ..db import AsyncSessionLocal
from ..models import CACertificate
from ..services.cert_manager import CertManager
from .config import settings


def init_scheduler(app):
    """Initialize scheduler but don't start it yet (will be started in lifespan)."""
    scheduler = AsyncIOScheduler()

    # Daily check for CA rotation
    scheduler.add_job(check_ca_rotation, CronTrigger(hour=3, minute=0))
    scheduler.add_job(cleanup_old_cas, CronTrigger(hour=4, minute=0))
    
    # Don't start here - will be started in lifespan context when event loop is running
    app.state.scheduler = scheduler


async def start_scheduler(app):
    """Start the scheduler (must be called from async context with running event loop)."""
    if hasattr(app.state, 'scheduler'):
        # Check if scheduler is already running to avoid errors in tests
        if not app.state.scheduler.running:
            app.state.scheduler.start()
            print("[scheduler] Started background scheduler")
        else:
            print("[scheduler] Scheduler already running, skipping start")


async def check_ca_rotation():
    async with AsyncSessionLocal() as session:  # type: AsyncSession
        cas = (await session.execute(select(CACertificate).where(CACertificate.is_active == True))).scalars().all()
        if not cas:
            return
        now = datetime.utcnow()
        for ca in cas:
            # If within 6 months (approx 182 days) of expiration, ensure next CA exists
            if ca.not_after - now <= timedelta(days=182):
                cm = CertManager(session)
                await cm.ensure_future_ca()


async def cleanup_old_cas():
    async with AsyncSessionLocal() as session:
        now = datetime.utcnow()
        cas = (await session.execute(select(CACertificate))).scalars().all()
        if not cas:
            return
        changed = False
        for ca in cas:
            if ca.is_previous:
                # If previous and overlap window has passed since created_at, deactivate
                if now - ca.created_at > timedelta(days=settings.ca_overlap_days):
                    ca.is_active = False
                    changed = True
        if changed:
            await session.commit()
