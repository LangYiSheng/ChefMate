from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_current_user_profile
from app.domain.models import UserProfileSnapshot
from app.schemas.profile import ProfileResponse, TagCatalogResponse, UpdateProfileRequest
from app.services.profile_service import profile_service

router = APIRouter()


@router.get("", response_model=ProfileResponse)
def get_profile(profile: UserProfileSnapshot = Depends(get_current_user_profile)) -> ProfileResponse:
    return profile_service.get_profile(profile.id)


@router.patch("", response_model=ProfileResponse)
def update_profile(
    payload: UpdateProfileRequest,
    profile: UserProfileSnapshot = Depends(get_current_user_profile),
) -> ProfileResponse:
    try:
        return profile_service.update_profile(profile.id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/tag-catalog", response_model=TagCatalogResponse)
def get_tag_catalog(_: UserProfileSnapshot = Depends(get_current_user_profile)) -> TagCatalogResponse:
    return profile_service.get_tag_catalog()
