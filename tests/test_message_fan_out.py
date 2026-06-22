import asyncio

import httpx
import socketio

CHANNEL = "room"
MESSAGES = 50


async def test_message_fan_out(gunicorn_server: str) -> None:
    received: list[str] = []
    all_received = asyncio.Event()

    listener = socketio.AsyncClient()

    @listener.on("message")
    async def _on_message(data: str) -> None:
        received.append(data)
        if len(received) >= MESSAGES:
            all_received.set()

    # websocket transport pins the client to one worker (no sticky-session needed)
    await listener.connect(gunicorn_server, socketio_path="/socket.io", transports=["websocket"])
    await listener.emit("subscribe", CHANNEL)
    await asyncio.sleep(0.5)  # let the subscribe (enter_room) settle

    # Fire requests concurrently so they open multiple connections and spread
    # across workers (a single keep-alive connection would pin to one worker).
    async with httpx.AsyncClient(base_url=gunicorn_server) as http:

        async def fire(i: int) -> int:
            response = await http.post(f"/notify/{CHANNEL}", json={"message": str(i)})
            return response.json()["pid"]

        worker_pids = set(await asyncio.gather(*(fire(i) for i in range(MESSAGES))))

    # Wake up exactly when the last message is delivered (no busy-polling).
    await asyncio.wait_for(all_received.wait(), timeout=5)

    await listener.disconnect()

    # Requests really hit more than one worker.
    assert len(worker_pids) > 1, f"all requests hit a single worker: {worker_pids}"
    # Every message reached the client, regardless of which worker emitted it.
    assert sorted(received) == sorted(str(i) for i in range(MESSAGES))
