from typing import Annotated

import socketio
from fastapi import Depends

from app.db import connect_listener
from app.pub_sub_manager import PostgresPubSubManager

# Postgres-backed manager so multiple workers/instances share events. The
# connections are opened lazily (on first use, inside the event loop).
manager = PostgresPubSubManager(connect_listener)
sio = socketio.AsyncServer(async_mode="asgi", client_manager=manager)


@sio.event
async def connect(sid: str, environ: dict[str, object], auth: object) -> None:
    pass


@sio.event
async def disconnect(sid: str) -> None:
    pass


@sio.event
async def subscribe(sid: str, channel: str) -> None:
    # Join a room so room-targeted emits reach this client.
    await sio.enter_room(sid, channel)


@sio.event
async def unsubscribe(sid: str, channel: str) -> None:
    await sio.leave_room(sid, channel)


def get_sio() -> socketio.AsyncServer:
    return sio


Sio = Annotated[socketio.AsyncServer, Depends(get_sio)]
