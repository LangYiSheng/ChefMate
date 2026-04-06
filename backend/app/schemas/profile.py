from __future__ import annotations

from pydantic import BaseModel

from app.domain.models import TagSelections, UserProfileSnapshot


class TagCatalogResponse(TagSelections):
    pass


class UpdateProfileRequest(BaseModel):
    allow_auto_update: bool | None = None
    auto_start_step_timer: bool | None = None
    cooking_preference_text: str | None = None
    tag_selections: TagSelections | None = None
    display_name: str | None = None
    email: str | None = None
    complete_workspace_onboarding: bool | None = None
    voice_wake_word_enabled: bool | None = None
    voice_wake_word_prompted: bool | None = None


ProfileResponse = UserProfileSnapshot
