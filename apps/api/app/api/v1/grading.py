"""Grading routes: run checks for a session, list stored results."""

from fastapi import APIRouter, Depends, HTTPException
from netlab_shared.errors import LabNotFoundError, RunnerError
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.core.deps import get_db
from app.db.models import Grade, LabProgress, User
from app.grading.engine import run_checks
from app.labs.manager import LabManager
from app.labs.runner import ContainerlabRunner

router = APIRouter()


@router.post("/sessions/{session_id}/grade")
def grade_session(
    session_id: str,
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
    if session.status != "running":
        raise HTTPException(
            status_code=409, detail=f"session is {session.status}, not running"
        )
    lab, topology = manager.get_lab(session.lab_slug)
    runner = ContainerlabRunner(session.clab_name, "/dev/null")
    try:
        results = run_checks(db, manager, session, lab, runner)
    except RunnerError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {
        "session_id": session.id,
        "score": sum(1 for r in results if r.passed),
        "total": len(results),
        "results": [
            {
                "objective_id": r.objective_id,
                "passed": r.passed,
                "evidence": r.evidence,
                "engine": r.engine,
            }
            for r in results
        ],
    }


@router.get("/sessions/{session_id}/results")
def session_results(
    session_id: str,
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
    rows = (
        db.query(LabProgress)
        .filter(
            LabProgress.user_id == session.user_id,
            LabProgress.lab_slug == session.lab_slug,
        )
        .order_by(LabProgress.checked_at.desc())
        .all()
    )
    grades = (
        db.query(Grade)
        .filter(Grade.session_id == session.id)
        .order_by(Grade.created_at.desc())
        .all()
    )
    return {
        "session_id": session.id,
        "progress": [
            {
                "objective_id": r.objective_id,
                "status": r.status,
                "detail": r.detail,
                "checked_at": r.checked_at,
            }
            for r in rows
        ],
        "grades": [
            {"score": g.score, "total": g.total, "created_at": g.created_at}
            for g in grades
        ],
    }
