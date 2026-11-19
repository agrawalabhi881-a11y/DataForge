from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import get_current_user, oauth
from app.database.session import get_db
from app.models.user import User
from app.schemas.user import UserOut
from app.services.user_service import AccountConflictError, get_or_create_google_user

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.get("/google/login", summary="Start Google login (open this in the browser)")
async def google_login(request: Request):
    if not settings.google_client_id or not settings.google_client_secret:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "Google login is not configured"
        )
    return await oauth.google.authorize_redirect(request, settings.google_redirect_uri)


@router.get("/google/callback", include_in_schema=False)
async def google_callback(request: Request, db: Session = Depends(get_db)):
    try:
        token = await oauth.google.authorize_access_token(request)
    except Exception:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Google login failed")

    info = token.get("userinfo") or {}
    if not info.get("sub") or not info.get("email"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Google did not return an email")
    if not info.get("email_verified"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Google email is not verified")

    try:
        user = get_or_create_google_user(
            db,
            google_id=info["sub"],
            email=info["email"],
            name=info.get("name") or info["email"],
            picture=info.get("picture"),
        )
    except AccountConflictError:
        raise HTTPException(status.HTTP_409_CONFLICT, "Email belongs to a different account")

    request.session.clear()
    request.session["user_id"] = user.id
    return RedirectResponse(settings.post_login_redirect)


@router.get("/me", response_model=UserOut, summary="Who is logged in?")
def me(user: User = Depends(get_current_user)):
    return user


@router.post("/logout", summary="Log out")
def logout(request: Request):
    request.session.clear()
    return {"message": "Logged out"}