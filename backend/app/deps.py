"""Shared FastAPI dependencies."""

from datetime import datetime

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session as DBSession

from app.db import get_db
from app.models import Session, User
from app.security import SESSION_COOKIE, hash_token


def get_current_user(request: Request, db: DBSession = Depends(get_db)) -> User:
    """Resolve the user from the session cookie, or raise 401."""
    token = request.cookies.get(SESSION_COOKIE)
    if token is None:
        raise HTTPException(status_code=401, detail="Not authenticated")

    row = db.query(Session).filter_by(token_hash=hash_token(token)).first()
    if row is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    if row.expires_at < datetime.now():
        db.delete(row)
        db.commit()
        raise HTTPException(status_code=401, detail="Session expired")
    return row.user
