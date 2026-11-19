"""Lab routes: catalogue, deploy, sessions, snapshot, reset."""

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from netlab_shared.errors import LabNotFoundError, RunnerError
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.core.config import settings
from app.core.deps import get_db
from app.db.models import User
from app.labs.manager import LabManager
from app.labs.models import (
    LabDetailOut,
    LabOut,
    LinkOut,
    NodeOut,
    ObjectiveOut,
    SessionCreate,
    SessionDetailOut,
    SessionOut,
    SnapshotOut,
)

router = APIRouter()


def _manager(db: Session) -> LabManager:
    return LabManager(db)


@router.get("", response_model=list[LabOut])
def list_labs(db: Session = Depends(get_db)):
    labs = _manager(db).list_labs()
    return [
        LabOut(
            id=lab.id,
            title=lab.title,
            description=lab.description,
            estimated_minutes=lab.estimated_minutes,
            objectives=[
                ObjectiveOut(
                    id=o.id,
                    title=o.title,
                    description=o.description,
                    engine=o.check.engine,
                    node=o.check.node,
                )
                for o in lab.objectives
            ],
        )
        for lab in labs
    ]


@router.get("/{slug}", response_model=LabDetailOut)
def get_lab(slug: str, db: Session = Depends(get_db)):
    try:
        lab, _ = _manager(db).get_lab(slug)
    except LabNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    guide_path = Path(settings.labs_dir) / slug / "guide.md"
    guide = guide_path.read_text() if guide_path.exists() else ""
    return LabDetailOut(
        id=lab.id,
        title=lab.title,
        description=lab.description,
        estimated_minutes=lab.estimated_minutes,
        objectives=[
            ObjectiveOut(
                id=o.id,
                title=o.title,
                description=o.description,
                engine=o.check.engine,
                node=o.check.node,
            )
            for o in lab.objectives
        ],
        guide=guide,
    )


@router.post("", response_model=SessionOut, status_code=201)
def deploy_lab(
    payload: SessionCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    manager = _manager(db)
    try:
        session = manager.create_session(user, payload.lab_slug, payload.ttl_seconds)
    except LabNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RunnerError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    queue_position = None
    if session.status == "queued":
        queue_position = manager.queue.position(user.id, payload.lab_slug)
    return SessionOut(
        id=session.id,
        lab_slug=session.lab_slug,
        status=session.status,
        created_at=session.created_at,
        expires_at=session.expires_at,
        queue_position=queue_position,
    )


@router.get("/sessions", response_model=list[SessionOut])
def list_sessions(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    from app.db.models import LabSession

    rows = (
        db.query(LabSession)
        .filter(LabSession.user_id == user.id)
        .order_by(LabSession.created_at.desc())
        .all()
    )
    return [
        SessionOut(
            id=r.id,
            lab_slug=r.lab_slug,
            status=r.status,
            created_at=r.created_at,
            expires_at=r.expires_at,
        )
        for r in rows
    ]


@router.get("/sessions/{session_id}", response_model=SessionDetailOut)
def get_session(
    session_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    manager = _manager(db)
    try:
        session = manager.get_session(session_id)
    except LabNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if session.user_id != user.id and user.role not in {"instructor", "admin"}:
        raise HTTPException(status_code=403, detail="not your session")
    _, topology = manager.get_lab(session.lab_slug)
    return SessionDetailOut(
        id=session.id,
        lab_slug=session.lab_slug,
        status=session.status,
        created_at=session.created_at,
        expires_at=session.expires_at,
        nodes=[
            NodeOut(name=n.name, kind=n.kind, image=n.image, status=session.status)
            for n in topology.nodes.values()
        ],
        links=[
            LinkOut(from_node=link.endpoints[0].split(":")[0], to_node=link.endpoints[1].split(":")[0])
            for link in topology.links
        ],
    )


@router.post("/sessions/{session_id}/destroy", response_model=SessionOut)
def destroy_session(
    session_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    manager = _manager(db)
    session = _owned_session(manager, session_id, user)
    manager.destroy(session)
    return SessionOut(
        id=session.id,
        lab_slug=session.lab_slug,
        status=session.status,
        created_at=session.created_at,
        expires_at=session.expires_at,
    )


@router.post("/sessions/{session_id}/snapshot", response_model=SnapshotOut)
def snapshot_session(
    session_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    manager = _manager(db)
    session = _owned_session(manager, session_id, user)
    if session.status != "running":
        raise HTTPException(
            status_code=409, detail=f"session is {session.status}, not running"
        )
    try:
        configs = manager.snapshot(session)
    except RunnerError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return SnapshotOut(session_id=session.id, configs=configs)


@router.post("/sessions/{session_id}/reset", response_model=SessionOut)
def reset_session(
    session_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    manager = _manager(db)
    session = _owned_session(manager, session_id, user)
    try:
        manager.reset(session)
    except RunnerError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return SessionOut(
        id=session.id,
        lab_slug=session.lab_slug,
        status=session.status,
        created_at=session.created_at,
        expires_at=session.expires_at,
    )


def _owned_session(manager: LabManager, session_id: str, user: User):
    try:
        session = manager.get_session(session_id)
    except LabNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if session.user_id != user.id and user.role not in {"instructor", "admin"}:
        raise HTTPException(status_code=403, detail="not your session")
    return session
