"""Auth routes: OAuth authorize/callback (GitHub + Google) and /me."""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.oauth import OAuthNotConfiguredError, build_authorize_url, exchange_code
from app.core.deps import get_db
from app.core.security import create_access_token
from app.db.models import User

router = APIRouter()


@router.get("/github")
def github_authorize(state: str | None = None):
    try:
        url = build_authorize_url("github", state)
    except OAuthNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return RedirectResponse(url)


@router.get("/google")
def google_authorize(state: str | None = None):
    try:
        url = build_authorize_url("google", state)
    except OAuthNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return RedirectResponse(url)


async def _handle_callback(provider: str, code: str, db: Session) -> dict:
    try:
        profile = await exchange_code(provider, code)
    except OAuthNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if not profile.get("email"):
        raise HTTPException(
            status_code=400, detail="provider did not return an email address"
        )
    user = db.query(User).filter(User.email == profile["email"]).first()
    if user is None:
        user = User(
            email=profile["email"],
            name=profile.get("name", ""),
            provider=provider,
            provider_id=profile.get("provider_id", ""),
            role="student",
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    token = create_access_token(subject=str(user.id), role=user.role)
    return {"access_token": token, "token_type": "bearer", "role": user.role}


@router.get("/github/callback")
async def github_callback(code: str = Query(...), db: Session = Depends(get_db)):
    return await _handle_callback("github", code, db)


@router.get("/google/callback")
async def google_callback(code: str = Query(...), db: Session = Depends(get_db)):
    return await _handle_callback("google", code, db)


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return {"id": user.id, "email": user.email, "name": user.name, "role": user.role}
