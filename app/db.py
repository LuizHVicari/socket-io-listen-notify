from collections.abc import AsyncGenerator
from typing import Annotated

import psycopg
from fastapi import Depends, Request
from psycopg_pool import AsyncConnectionPool

from app.config import settings
from app.listener import PgListener


def get_pool(request: Request) -> AsyncConnectionPool:
    return request.app.state.pool


async def get_connection(
    pool: Annotated[AsyncConnectionPool, Depends(get_pool)],
) -> AsyncGenerator[psycopg.AsyncConnection]:
    async with pool.connection() as connection:
        yield connection


Connection = Annotated[psycopg.AsyncConnection, Depends(get_connection)]


async def connect_listener() -> PgListener:
    # Listener factory: each call opens its own dedicated autocommit connection.
    # LISTEN blocks while consuming notifications, so it cannot share the pool.
    connection = await psycopg.AsyncConnection.connect(settings.database_url, autocommit=True)
    return PgListener(connection)
