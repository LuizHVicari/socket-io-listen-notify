from collections.abc import Awaitable, Callable

import psycopg
from psycopg import sql


class PgListener:
    """Listen/notify over a dedicated Postgres connection.

    The connection must be exclusive to this listener (do not pull it from a
    pool): `listen` blocks indefinitely consuming notifications.
    """

    def __init__(self, connection: psycopg.AsyncConnection) -> None:
        self.__pg_connection = connection

    async def listen(self, channel: str, callback: Callable[[str], Awaitable[None]]) -> None:
        # LISTEN/NOTIFY requires autocommit so notifications are not trapped in
        # an open transaction.
        if not self.__pg_connection.autocommit:
            await self.__pg_connection.set_autocommit(True)

        await self.__pg_connection.execute(sql.SQL("LISTEN {}").format(sql.Identifier(channel)))
        async for notify in self.__pg_connection.notifies():
            if notify.channel == channel:
                await callback(notify.payload)

    async def notify(self, channel: str, payload: str) -> None:
        await self.__pg_connection.execute(
            sql.SQL("NOTIFY {}, {}").format(sql.Identifier(channel), sql.Literal(payload))
        )
