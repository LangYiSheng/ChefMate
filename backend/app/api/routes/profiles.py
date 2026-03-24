from fastapi import APIRouter

from app.schemas.profile import ProfileResponse, ProfileUpdateRequest
from app.services.profile_service import profile_service

router = APIRouter()


@router.get("", response_model=ProfileResponse)
def get_profile(user_id: str) -> ProfileResponse:
    return profile_service.get_profile(user_id)


@router.put("", response_model=ProfileResponse)
def update_profile(user_id: str, payload: ProfileUpdateRequest) -> ProfileResponse:
    return profile_service.update_profile(user_id, payload)
