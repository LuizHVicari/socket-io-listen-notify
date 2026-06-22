from typing import Literal

from fastapi import FastAPI, WebSocket
from pydantic import BaseModel

from app.db import Connection, Listener
from app.lifespan import lifespan

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


@app.websocket("/{channel}")
async def websocket_listener(channel: str, websocket: WebSocket, listener: Listener) -> None:
    await websocket.accept()
    # Blocks forwarding each NOTIFY payload to the client until disconnect.
    await listener.listen(channel, websocket.send_text)


class NotifyRequest(BaseModel):
    message: str


@app.post("/notify/{channel}")
async def notify(channel: str, request: NotifyRequest, listener: Listener) -> None:
    await listener.notify(channel, request.message)
