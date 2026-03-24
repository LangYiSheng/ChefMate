from app.schemas.profile import ProfileResponse, ProfileUpdateRequest


class ProfileService:
    def __init__(self) -> None:
        self._store: dict[str, ProfileResponse] = {}

    def get_profile(self, user_id: str) -> ProfileResponse:
        return self._store.get(user_id, ProfileResponse(user_id=user_id))

    def update_profile(self, user_id: str, payload: ProfileUpdateRequest) -> ProfileResponse:
        profile = ProfileResponse(user_id=user_id, **payload.model_dump())
        self._store[user_id] = profile
        return profile


profile_service = ProfileService()