from __future__ import annotations

from app.domain.models import TagSelections, UserProfileSnapshot
from app.repositories.account_repository import account_repository
from app.repositories.recipe_repository import recipe_repository
from app.schemas.profile import TagCatalogResponse, UpdateProfileRequest
from app.services.auth_service import auth_service
from app.services.recipe_catalog_service import recipe_catalog_service
from app.utils.time import utc_now


class ProfileService:
    def get_profile(self, user_id: int) -> UserProfileSnapshot:
        return auth_service.get_user_profile(user_id)

    def get_tag_catalog(self) -> TagCatalogResponse:
        taxonomy = recipe_catalog_service.get_tag_taxonomy()
        return TagCatalogResponse(
            flavor=taxonomy.get("flavor", []),
            method=taxonomy.get("method", []),
            scene=taxonomy.get("scene", []),
            health=taxonomy.get("health", []),
            time=taxonomy.get("time", []),
            tool=taxonomy.get("tool", []),
        )

    def update_profile(self, user_id: int, payload: UpdateProfileRequest) -> UserProfileSnapshot:
        updates: dict[str, object] = {}
        if payload.allow_auto_update is not None:
            updates["allow_auto_update"] = int(payload.allow_auto_update)
        if payload.auto_start_step_timer is not None:
            updates["auto_start_step_timer"] = int(payload.auto_start_step_timer)
        if payload.cooking_preference_text is not None:
            updates["cooking_preference_text"] = payload.cooking_preference_text.strip()
        if payload.display_name is not None:
            updates["display_name"] = payload.display_name.strip() or payload.display_name
        if payload.email is not None:
            updates["email"] = payload.email.strip() or None
        if payload.complete_workspace_onboarding:
            updates["has_completed_workspace_onboarding"] = 1
            updates["profile_completed_at"] = utc_now()
        if updates:
            updates["updated_at"] = utc_now()
            account_repository.update_user_profile(user_id, updates)

        if payload.tag_selections is not None:
            normalized_selections = self.validate_tag_selections(payload.tag_selections)
            account_repository.replace_user_tags(
                user_id,
                self._resolve_tag_ids(normalized_selections),
            )

        return self.get_profile(user_id)

    def validate_tag_selections(self, selections: TagSelections) -> TagSelections:
        normalized = recipe_catalog_service.validate_tag_filters(
            selections.model_dump(),
            categories=TagSelections.model_fields.keys(),
            allow_alias=False,
        )
        return TagSelections(**normalized)

    def _resolve_tag_ids(self, selections: TagSelections) -> list[int]:
        requested = {
            name
            for values in selections.model_dump().values()
            for name in values
            if isinstance(name, str) and name.strip()
        }
        if not requested:
            return []
        return recipe_repository.get_tag_ids_by_names(sorted(requested))


profile_service = ProfileService()
