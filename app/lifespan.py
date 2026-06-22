from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from psycopg_pool import AsyncConnectionPool

from app.config import settings


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[dict[str, AsyncConnectionPool]]:
    pool = AsyncConnectionPool(settings.database_url, open=False)
    await pool.open()
    try:
        # exposed on request.app.state.pool for dependencies
        yield {"pool": pool}
    finally:
        await pool.close()
