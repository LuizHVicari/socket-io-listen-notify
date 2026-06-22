import asyncio
import json
from collections.abc import AsyncGenerator, Awaitable, Callable
from typing import Any

from socketio.async_pubsub_manager import AsyncPubSubManager

from app.listener import PgListener

# Abstraction the manager depends on: produces a fresh listener (own connection)
# on demand. Lazily called inside the event loop, so the manager can be built at
# import time (the Socket.IO ASGI wrapper needs it module-level).
ListenerFactory = Callable[[], Awaitable[PgListener]]


class PostgresPubSubManager(AsyncPubSubManager):
    name = "postgres"

    def __init__(
        self, listener_factory: ListenerFactory, channel: str = "socketio", **kwargs: dict[str, Any]
    ) -> None:
        super().__init__(channel=channel, **kwargs)
        self.__listener_factory = listener_factory
        self.__channel = channel
        self.__publisher: PgListener | None = None

    async def _publish(self, data: dict[str, Any]) -> None:
        # Publisher and subscriber MUST use separate connections: a connection
        # parked in notifies() cannot run NOTIFY at the same time.
        if self.__publisher is None:
            self.__publisher = await self.__listener_factory()
        await self.__publisher.notify(self.__channel, json.dumps(data))

    async def _listen(self) -> AsyncGenerator[str]:  # ty:ignore[invalid-method-override] Socket.IO doesn't type hint this method as async generator, but it is.
        subscriber = await self.__listener_factory()
        queue: asyncio.Queue[str] = asyncio.Queue()
        task = asyncio.create_task(
            subscriber.listen(self.__channel, queue.put)
        )  # task must be stored to prevent it from being garbage collected and cancelled
        try:
            while True:
                yield await queue.get()
        # ty says this code is unreachable but it is not, it is executed when the generator is closed,
        # which happens on disconnect
        finally:
            task.cancel()  # ensure listener task is cancelled when generator is closed (e.g., on disconnect)
