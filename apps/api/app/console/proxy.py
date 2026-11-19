"""Console WebSocket proxy.

The browser never gets a shell on the lab host. For each node the proxy
spawns exactly one command — the one the node's driver returns from
``console_command`` — with an argument list (never ``shell=True``), streams
bytes between the WebSocket and the process, and appends everything to a
per-session transcript on disk.

Frames (JSON):
  client -> server: {"type": "input", "data": "..."} | {"type": "resize", "cols": 80, "rows": 24}
  server -> client: {"type": "output", "data": "..."} | {"type": "status", "state": "..."}

Instructors may join with ``?observer=1``: input frames are dropped
server-side. Reconnect is a fresh attach; the previous process is reaped.

Limitation: the proxy streams over pipes, not a PTY, so line editing on
the remote CLI is limited (no arrow-key history). The SERIAL path
(``docker exec`` into vtysh) is unaffected in practice.
"""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path

from fastapi import WebSocket, WebSocketDisconnect
from netlab_drivers import get_driver
from netlab_drivers.base import NodeSpec

from app.core.config import settings
from app.core.security import decode_access_token
from app.db.models import User
from app.db.session import SessionLocal
from app.labs.manager import LabManager

logger = logging.getLogger(__name__)


def _console_command(node: NodeSpec, container: str) -> list[str]:
    """Resolve the driver's console command into a pipe-streamable form:
    ``docker exec -it`` becomes ``docker exec -i`` (no TTY on pipes)."""
    driver = get_driver(node.driver)
    cmd = driver.console_command(node, container)
    if len(cmd) >= 4 and cmd[0] == "docker" and cmd[1] == "exec":
        cmd = ["docker", "exec", "-i"] + cmd[3:]
    return cmd


async def console_websocket(
    websocket: WebSocket, session_id: str, node: str, observer: bool = False
) -> None:
    token = websocket.query_params.get("token", "")
    await websocket.accept()

    db = SessionLocal()
    try:
        # Authenticate the JWT and authorise the session: the owner, or an
        # instructor/admin. Observers must be instructor/admin.
        try:
            payload = decode_access_token(token)
            user = db.get(User, int(payload["sub"]))
        except Exception:
            user = None
        if user is None:
            await websocket.send_json({"type": "status", "state": "error: invalid token"})
            await websocket.close()
            return
        if observer and user.role not in {"instructor", "admin"}:
            await websocket.send_json(
                {"type": "status", "state": "error: observer mode is instructor-only"}
            )
            await websocket.close()
            return
        manager = LabManager(db)
        try:
            session = manager.get_session(session_id)
        except Exception as exc:
            await websocket.send_json({"type": "status", "state": f"error: {exc}"})
            await websocket.close()
            return
        if session.user_id != user.id and user.role not in {"instructor", "admin"}:
            await websocket.send_json({"type": "status", "state": "error: not your session"})
            await websocket.close()
            return
        if session.status != "running":
            await websocket.send_json(
                {"type": "status", "state": f"session is {session.status}"}
            )
            await websocket.close()
            return
        _, topology = manager.get_lab(session.lab_slug)
        topo_node = topology.nodes.get(node)
        if topo_node is None:
            await websocket.send_json(
                {"type": "status", "state": f"unknown node {node!r}"}
            )
            await websocket.close()
            return
        node_spec = LabManager._node_spec(topo_node, topology)
        container = f"clab-{session.clab_name}-{node}"
        cmd = _console_command(node_spec, container)
    finally:
        db.close()

    log_dir = Path(settings.console_log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"{session_id}-{node}.log"

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
    except FileNotFoundError as exc:
        await websocket.send_json(
            {"type": "status", "state": f"console failed: {exc}"}
        )
        await websocket.close()
        return

    async def pump_output() -> None:
        try:
            while True:
                chunk = await process.stdout.read(4096)
                if not chunk:
                    break
                text = chunk.decode(errors="replace")
                with open(log_path, "a", encoding="utf-8") as log:
                    log.write(text)
                await websocket.send_json({"type": "output", "data": text})
        except (WebSocketDisconnect, asyncio.CancelledError):
            pass

    async def pump_input() -> None:
        try:
            while True:
                message = await websocket.receive_text()
                frame = json.loads(message)
                if frame.get("type") == "input":
                    if observer:
                        continue  # read-only: drop input server-side
                    data = frame.get("data", "")
                    if process.stdin is not None and not process.stdin.is_closing():
                        process.stdin.write(data.encode())
                        await process.stdin.drain()
                elif frame.get("type") == "resize":
                    # No PTY to resize; recorded for future PTY support.
                    logger.debug(
                        "resize %s %s", frame.get("cols"), frame.get("rows")
                    )
        except (WebSocketDisconnect, asyncio.CancelledError, json.JSONDecodeError):
            pass

    output_task = asyncio.create_task(pump_output())
    input_task = asyncio.create_task(pump_input())
    try:
        await asyncio.wait(
            [output_task, input_task], return_when=asyncio.FIRST_COMPLETED
        )
    finally:
        output_task.cancel()
        input_task.cancel()
        if process.returncode is None:
            process.terminate()
            try:
                await asyncio.wait_for(process.wait(), timeout=5)
            except TimeoutError:
                process.kill()
        await websocket.send_json({"type": "status", "state": "closed"})
