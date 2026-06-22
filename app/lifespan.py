from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from psycopg_pool import AsyncConnectionPool

from app.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    pool = AsyncConnectionPool(settings.database_url, open=False)
    await pool.open()
    app.state.pool = pool
    try:
        yield
    finally:
        await pool.close()
