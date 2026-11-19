from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User


class AccountConflictError(Exception):
    """The email already belongs to a different Google account."""


def get_or_create_google_user(
    db: Session, *, google_id: str, email: str, name: str, picture: str | None
) -> User:
    # 1. Returning user: found by Google ID
    user = db.scalar(select(User).where(User.google_id == google_id))

    # 2. Same email already exists (e.g. created earlier): link it to this Google account
    if user is None:
        user = db.scalar(select(User).where(User.email == email))
        if user is not None and user.google_id and user.google_id != google_id:
            raise AccountConflictError("Email belongs to a different Google account")

    # 3. Brand new user
    if user is None:
        user = User(email=email)
        db.add(user)

    user.google_id = google_id
    user.name = name
    user.picture_url = picture
    db.commit()
    db.refresh(user)
    return user