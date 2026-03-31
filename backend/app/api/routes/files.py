from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.api.dependencies import get_current_user_profile
from app.domain.models import UserProfileSnapshot
from app.schemas.file import UploadedImageResponse
from app.services.file_service import file_service

router = APIRouter()


@router.post("/images", response_model=UploadedImageResponse)
async def upload_image(
    image: UploadFile = File(...),
    profile: UserProfileSnapshot = Depends(get_current_user_profile),
) -> UploadedImageResponse:
    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="仅支持上传图片文件。")
    payload = await image.read()
    if not payload:
        raise HTTPException(status_code=400, detail="上传的图片为空。")
    try:
        return file_service.save_image(
            user_id=profile.id,
            payload=payload,
            filename=image.filename or "image",
            mime_type=image.content_type,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
