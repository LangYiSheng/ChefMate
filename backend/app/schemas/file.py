from pydantic import BaseModel

from app.domain.enums import AttachmentKind


class UploadedImageResponse(BaseModel):
    id: str
    kind: AttachmentKind = AttachmentKind.IMAGE
    name: str
    preview_url: str
    file_url: str
