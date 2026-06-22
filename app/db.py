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


async def get_listener() -> AsyncGenerator[PgListener]:
    # A listener needs its own connection: LISTEN blocks while consuming
    # notifications, so it cannot share the pool.
    async with await psycopg.AsyncConnection.connect(
        settings.database_url, autocommit=True
    ) as connection:
        yield PgListener(connection)


Listener = Annotated[PgListener, Depends(get_listener)]
