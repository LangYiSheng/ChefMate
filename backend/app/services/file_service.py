from __future__ import annotations

import re
import logging
from pathlib import Path
from uuid import uuid4

from app.config import settings
from app.schemas.file import UploadedImageResponse
from app.repositories.file_repository import file_repository


SAFE_NAME_PATTERN = re.compile(r"[^A-Za-z0-9._-]+")
logger = logging.getLogger(__name__)


class FileService:
    def save_image(
        self,
        *,
        user_id: int,
        payload: bytes,
        filename: str,
        mime_type: str,
    ) -> UploadedImageResponse:
        if len(payload) > settings.max_upload_size_bytes:
            raise ValueError("上传图片超过大小限制。")

        asset_id = str(uuid4())
        safe_name = SAFE_NAME_PATTERN.sub("_", Path(filename).name or "image")
        storage_key = f"{asset_id}_{safe_name}"
        target_path = settings.upload_path / storage_key
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_bytes(payload)

        file_repository.create_asset(
            asset_id=asset_id,
            user_id=user_id,
            kind="image",
            original_name=filename,
            mime_type=mime_type,
            storage_key=storage_key,
            byte_size=len(payload),
        )
        public_url = f"{settings.asset_url_prefix}/{storage_key}"
        logger.info(
            "[upload] saved image user_id=%s asset_id=%s filename=%r mime=%s size=%s storage_key=%s",
            user_id,
            asset_id,
            filename,
            mime_type,
            len(payload),
            storage_key,
        )
        return UploadedImageResponse(
            id=asset_id,
            name=filename,
            preview_url=public_url,
            file_url=public_url,
        )


file_service = FileService()
