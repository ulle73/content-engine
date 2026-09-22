"""Recover accepted provider work while the existing ASGI service is awake."""
import asyncio
import logging
from contextlib import asynccontextmanager

from django.db import connections, close_old_connections

logger = logging.getLogger(__name__)


def recovery_pass():
    from .media import recover_media_jobs
    close_old_connections()
    try:
        return recover_media_jobs(limit=10)
    finally:
        connections.close_all()


async def recovery_loop(stop):
    while not stop.is_set():
        try:
            result = await asyncio.to_thread(recovery_pass)
            if result["checked"]:
                logger.info("Media recovery: %s", result)
        except Exception as exc:
            # Log the class, never provider payloads, tokens or database credentials.
            logger.warning("Media recovery deferred (%s)", type(exc).__name__)
        try:
            await asyncio.wait_for(stop.wait(), timeout=60)
        except TimeoutError:
            pass


def install_recovery(app):
    original = app.router.lifespan_context

    @asynccontextmanager
    async def lifespan(application):
        async with original(application) as state:
            stop = asyncio.Event()
            task = asyncio.create_task(recovery_loop(stop))
            try:
                yield state
            finally:
                stop.set()
                # Do not cancel a thread midway through securing already-paid output.
                await task

    app.router.lifespan_context = lifespan
