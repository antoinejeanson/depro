"""Authentication endpoints: register, login, logout, me."""

import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import delete
from sqlalchemy.orm import Session as DBSession

from app.db import get_db
from app.deps import get_current_user
from app.models import Session, User
from app.schemas import UserCreate, UserLogin, UserRead
from app.security import (
    SESSION_COOKIE,
    SESSION_DAYS,
    hash_password,
    hash_token,
    new_token,
    session_max_age,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _issue_session(db: DBSession, user: User, response: Response) -> None:
    """Create a session row and set the httpOnly cookie (caller commits)."""
    token = new_token()
    db.add(
        Session(
            user_id=user.id,
            token_hash=hash_token(token),
            expires_at=datetime.now() + timedelta(days=SESSION_DAYS),
        )
    )
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=session_max_age(),
        httponly=True,
        samesite="lax",
        path="/",
    )


@router.post("/register", status_code=201)
def register(
    payload: UserCreate,
    response: Response,
    db: DBSession = Depends(get_db),
) -> UserRead:
    existing = db.query(User).filter_by(email=payload.email).first()
    if existing is not None:
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(
        id=uuid.uuid4(),
        email=payload.email,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    _issue_session(db, user, response)
    db.commit()
    db.refresh(user)
    return UserRead(id=user.id, email=user.email, created_at=user.created_at)


@router.post("/login")
def login(
    payload: UserLogin,
    response: Response,
    db: DBSession = Depends(get_db),
) -> UserRead:
    user = db.query(User).filter_by(email=payload.email).first()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # Housekeeping: drop this user's expired sessions.
    db.execute(
        delete(Session).where(
            Session.user_id == user.id,
            Session.expires_at < datetime.now(),
        )
    )
    _issue_session(db, user, response)
    db.commit()
    return UserRead(id=user.id, email=user.email, created_at=user.created_at)


@router.post("/logout", status_code=204)
def logout(request: Request, db: DBSession = Depends(get_db)) -> Response:
    token = request.cookies.get(SESSION_COOKIE)
    if token is not None:
        db.execute(delete(Session).where(Session.token_hash == hash_token(token)))
        db.commit()
    response = Response(status_code=204)
    response.delete_cookie(SESSION_COOKIE, path="/")
    return response


@router.get("/me")
def me(user: User = Depends(get_current_user)) -> UserRead:
    return UserRead(id=user.id, email=user.email, created_at=user.created_at)
