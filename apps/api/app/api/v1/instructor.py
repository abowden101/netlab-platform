"""Instructor routes: students and per-lab progress (instructor/admin only)."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.roles import require_instructor
from app.core.deps import get_db
from app.db.models import LabProgress, LabSession, User

router = APIRouter()


@router.get("/students")
def list_students(
    user: User = Depends(require_instructor), db: Session = Depends(get_db)
):
    users = db.query(User).order_by(User.email).all()
    out = []
    for u in users:
        sessions = (
            db.query(LabSession).filter(LabSession.user_id == u.id).count()
        )
        passed = (
            db.query(LabProgress)
            .filter(LabProgress.user_id == u.id, LabProgress.status == "passed")
            .count()
        )
        out.append(
            {
                "id": u.id,
                "email": u.email,
                "name": u.name,
                "role": u.role,
                "sessions": sessions,
                "objectives_passed": passed,
            }
        )
    return out


@router.get("/labs/{slug}/progress")
def lab_progress(
    slug: str,
    user: User = Depends(require_instructor),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(LabProgress)
        .filter(LabProgress.lab_slug == slug)
        .order_by(LabProgress.checked_at.desc())
        .all()
    )
    return [
        {
            "user_id": r.user_id,
            "objective_id": r.objective_id,
            "status": r.status,
            "detail": r.detail,
            "checked_at": r.checked_at,
        }
        for r in rows
    ]
