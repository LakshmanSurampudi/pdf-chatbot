import jwt
from fastapi import Header, HTTPException, status

from app.config import settings


def get_current_user_id(authorization: str = Header(...)) -> str:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing bearer token")
    token = authorization.removeprefix("Bearer ")
    try:
        payload = jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            audience="authenticated",
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token") from exc
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token missing subject")
    return user_id
