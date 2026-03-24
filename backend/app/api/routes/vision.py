from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.schemas.vision import IngredientDetectionResponse
from app.services.vision_service import VisionConfigurationError
from app.skills.vision import vision_skill

router = APIRouter()


@router.post("/ingredients/detect", response_model=IngredientDetectionResponse)
async def detect_ingredients(
    image: UploadFile = File(...),
    user_hint: str | None = Form(default=None),
) -> IngredientDetectionResponse:
    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="仅支持图片文件。")

    image_bytes = await image.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="上传的图片为空。")

    try:
        return vision_skill.detect_ingredients(
            image_bytes=image_bytes,
            mime_type=image.content_type,
            filename=image.filename,
            user_hint=user_hint,
        )
    except VisionConfigurationError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except NotImplementedError as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=f"图像识别返回结果解析失败：{exc}") from exc
