from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_bearer_token, get_current_user_profile
from app.domain.models import UserProfileSnapshot
from app.schemas.auth import (
    AuthResponse,
    LoginRequest,
    RegisterRequest,
)
from app.services.auth_service import AuthConflictError, AuthCredentialsError, AuthValidationError, auth_service

router = APIRouter()


@router.post("/register", response_model=AuthResponse)
def register(payload: RegisterRequest) -> AuthResponse:
    try:
        return auth_service.register(payload)
    except AuthValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except AuthConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest) -> AuthResponse:
    try:
        return auth_service.login(payload)
    except AuthValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except AuthCredentialsError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc


@router.get("/me", response_model=UserProfileSnapshot)
def get_current_user(profile: UserProfileSnapshot = Depends(get_current_user_profile)) -> UserProfileSnapshot:
    return profile


@router.post("/logout")
def logout(token: str = Depends(get_bearer_token)) -> dict[str, str]:
    auth_service.logout(token)
    return {"message": "已退出登录。"}
