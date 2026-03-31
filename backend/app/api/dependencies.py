from __future__ import annotations

from fastapi import Depends, Header, HTTPException, status

from app.domain.models import UserProfileSnapshot
from app.services.auth_service import auth_service


def get_bearer_token(authorization: str | None = Header(default=None)) -> str:
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未提供登录令牌。")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="登录令牌格式不正确。")
    return token


def get_current_user_profile(token: str = Depends(get_bearer_token)) -> UserProfileSnapshot:
    profile = auth_service.get_user_profile_by_token(token)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="登录态已失效，请重新登录。")
    return profile
