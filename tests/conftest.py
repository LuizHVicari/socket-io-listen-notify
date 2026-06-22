import os
import signal
import socket as socketlib
import subprocess
import time
from collections.abc import Generator

import httpx
import pytest
from fastapi.testclient import TestClient

WORKERS = 4


@pytest.fixture(scope="session", autouse=True)
def _postgres() -> Generator[None]:
    """Ephemeral Postgres for the whole test session.

    Env vars are set BEFORE any `app.*` import (and before gunicorn is spawned)
    so Settings and the Socket.IO manager pick up the container's connection.
    """
    from testcontainers.postgres import PostgresContainer

    with PostgresContainer("postgres:18-alpine") as pg:
        os.environ["POSTGRES_HOST"] = pg.get_container_host_ip()
        os.environ["POSTGRES_PORT"] = str(pg.get_exposed_port(5432))
        os.environ["POSTGRES_USER"] = pg.username
        os.environ["POSTGRES_PASSWORD"] = pg.password
        os.environ["POSTGRES_DB"] = pg.dbname
        yield


@pytest.fixture
def client(_postgres: None) -> Generator[TestClient]:
    """TestClient over the app (single in-process worker) for plain HTTP tests."""
    from app.api import app

    with TestClient(app) as test_client:
        yield test_client


def _free_port() -> int:
    with socketlib.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.fixture
def gunicorn_server(_postgres: None) -> Generator[str]:
    """Boot the real app under gunicorn with WORKERS uvicorn workers.

    Yields the base URL. Multiple workers (distinct PIDs) exercise the Postgres
    pub/sub fan-out: a notify handled by any worker must reach a client
    connected to any other worker.
    """
    port = _free_port()
    base_url = f"http://127.0.0.1:{port}"
    proc = subprocess.Popen(
        [
            "uv", "run", "gunicorn", "app.api:socket_app",
            "-k", "uvicorn.workers.UvicornWorker",
            "-b", f"127.0.0.1:{port}",
            "-w", str(WORKERS),
        ],
        env={**os.environ, "PYTHONPATH": "."},
        start_new_session=True,  # own process group for clean teardown
    )
    try:
        deadline = time.time() + 30
        while time.time() < deadline:
            try:
                if httpx.get(f"{base_url}/health", timeout=1).status_code == 200:
                    break
            except httpx.RequestError:
                time.sleep(0.2)
        else:
            raise RuntimeError("gunicorn did not become ready")
        yield base_url
    finally:
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        proc.wait(timeout=10)
