from app.services.vision_service import vision_service


class VisionSkill:
    name = "vision"

    def detect_ingredients(
        self,
        *,
        image_bytes: bytes,
        mime_type: str,
        filename: str | None = None,
        user_hint: str | None = None,
    ):
        return vision_service.detect_ingredients_from_image(
            image_bytes=image_bytes,
            mime_type=mime_type,
            filename=filename,
            user_hint=user_hint,
        )


vision_skill = VisionSkill()
