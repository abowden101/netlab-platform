"""Console info endpoint (the WebSocket itself lives in app/console)."""

from fastapi import APIRouter, Depends, HTTPException
from netlab_drivers import get_driver
from netlab_shared.errors import LabNotFoundError
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.core.deps import get_db
from app.db.models import User
from app.labs.manager import LabManager

router = APIRouter()


@router.get("/sessions/{session_id}/nodes/{node}/console-info")
def console_info(
    session_id: str,
    node: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    manager = LabManager(db)
    try:
        session = manager.get_session(session_id)
    except LabNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if session.user_id != user.id and user.role not in {"instructor", "admin"}:
        raise HTTPException(status_code=403, detail="not your session")
    _, topology = manager.get_lab(session.lab_slug)
    topo_node = topology.nodes.get(node)
    if topo_node is None:
        raise HTTPException(status_code=404, detail=f"unknown node {node!r}")
    driver = get_driver(topo_node.kind)
    node_spec = manager._node_spec(topo_node, topology)
    container = f"clab-{session.clab_name}-{node}"
    return {
        "session_id": session.id,
        "node": node,
        "driver": driver.name,
        "console_method": driver.console_method.value,
        "websocket_url": f"/ws/console/{session.id}/{node}",
        "container": container,
        "command": driver.console_command(node_spec, container),
    }
