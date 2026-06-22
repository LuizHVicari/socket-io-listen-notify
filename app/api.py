import os
from typing import Literal

import socketio
from fastapi import FastAPI
from pydantic import BaseModel

from app.db import Connection
from app.lifespan import lifespan
from app.socket_server import Sio, sio

app = FastAPI(lifespan=lifespan)


class HealthCheckResponse(BaseModel):
    api: Literal["healthy", "degraded"]
    postgres: Literal["healthy", "degraded"]


@app.get("/health")
async def health_check(connection: Connection) -> HealthCheckResponse:
    async with connection.cursor() as cur:
        await cur.execute("SELECT 1")
        result = await cur.fetchone()

    postgres = "healthy" if result and result[0] == 1 else "degraded"
    return HealthCheckResponse(api="healthy", postgres=postgres)


class NotifyRequest(BaseModel):
    message: str


class NotifyResponse(BaseModel):
    pid: int


@app.post("/notify/{channel}")
async def notify(channel: str, request: NotifyRequest, sio: Sio) -> NotifyResponse:
    # Formal Socket.IO emit: the pub/sub manager propagates it across workers.
    await sio.emit("message", request.message, room=channel)
    # PID of the worker that handled this request (lets tests prove fan-out).
    return NotifyResponse(pid=os.getpid())


# Top-level ASGI app: Socket.IO handles /socket.io/* (incl. websocket upgrade),
# everything else falls through to FastAPI. Serve this (app.api:socket_app).
socket_app = socketio.ASGIApp(sio, other_asgi_app=app)
