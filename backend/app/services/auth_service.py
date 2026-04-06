from __future__ import annotations

import re
from collections import defaultdict
from datetime import datetime

from app.domain.models import TagSelections, UserProfileSnapshot
from app.repositories.account_repository import account_repository
from app.schemas.auth import AuthResponse, LoginRequest, RegisterRequest
from app.utils.security import digest_token, generate_session_token, hash_password, verify_password
from app.utils.time import session_expires_at, utc_now


USERNAME_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_]{3,19}$")
PASSWORD_PATTERN = re.compile(r"^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d~!@#$%^&*_\-+=.?]{8,32}$")


class AuthConflictError(RuntimeError):
    pass


class AuthCredentialsError(RuntimeError):
    pass


class AuthValidationError(RuntimeError):
    pass


class AuthService:
    def register(self, payload: RegisterRequest) -> AuthResponse:
        username = payload.username.strip()
        if not USERNAME_PATTERN.fullmatch(username):
            raise AuthValidationError("用户名格式不符合要求。")
        if not PASSWORD_PATTERN.fullmatch(payload.password):
            raise AuthValidationError("密码格式不符合要求。")
        if account_repository.get_user_by_username(username) is not None:
            raise AuthConflictError("该用户名已被占用。")

        user_id = account_repository.create_user(
            username=username,
            email=payload.email.strip() if payload.email else None,
            password_hash=hash_password(payload.password),
            display_name=username,
        )
        token = self._create_session(user_id)
        return AuthResponse(token=token, user=self.get_user_profile(user_id))

    def login(self, payload: LoginRequest) -> AuthResponse:
        user = account_repository.get_user_by_username(payload.username.strip())
        if user is None or not verify_password(payload.password, user["password_hash"]):
            raise AuthCredentialsError("用户名或密码错误。")
        token = self._create_session(int(user["id"]))
        account_repository.update_user_profile(
            int(user["id"]),
            {
                "is_first_workspace_visit": 0,
                "updated_at": utc_now(),
            },
        )
        return AuthResponse(token=token, user=self.get_user_profile(int(user["id"])))

    def get_user_profile_by_token(self, token: str) -> UserProfileSnapshot | None:
        session = account_repository.get_active_session_by_token_hash(digest_token(token))
        if session is None:
            return None
        expires_at = session["expires_at"]
        if isinstance(expires_at, datetime) and expires_at < utc_now().replace(tzinfo=None):
            return None
        return self.get_user_profile(int(session["user_id"]))

    def get_user_profile(self, user_id: int) -> UserProfileSnapshot:
        user = account_repository.get_user_by_id(user_id)
        if user is None:
            raise AuthCredentialsError("用户不存在。")
        grouped: dict[str, list[str]] = defaultdict(list)
        for row in account_repository.get_user_tags(user_id):
            grouped[row["category_code"]].append(row["tag_name"])
        return UserProfileSnapshot(
            id=int(user["id"]),
            username=user["username"],
            email=user.get("email"),
            display_name=user.get("display_name") or user["username"],
            allow_auto_update=bool(user.get("allow_auto_update", 1)),
            auto_start_step_timer=bool(user.get("auto_start_step_timer", 0)),
            cooking_preference_text=user.get("cooking_preference_text") or "",
            tag_selections=TagSelections(
                flavor=grouped.get("flavor", []),
                method=grouped.get("method", []),
                scene=grouped.get("scene", []),
                health=grouped.get("health", []),
                time=grouped.get("time", []),
                tool=grouped.get("tool", []),
            ),
            is_first_workspace_visit=bool(user.get("is_first_workspace_visit", 1)),
            has_completed_workspace_onboarding=bool(user.get("has_completed_workspace_onboarding", 0)),
            profile_completed_at=(
                user["profile_completed_at"].isoformat()
                if user.get("profile_completed_at")
                else None
            ),
            voice_wake_word_enabled=bool(user.get("voice_wake_word_enabled", 0)),
            voice_wake_word_prompted=bool(user.get("voice_wake_word_prompted", 0)),
        )

    def logout(self, token: str) -> None:
        account_repository.revoke_session(digest_token(token), utc_now())

    def _create_session(self, user_id: int) -> str:
        token = generate_session_token()
        account_repository.create_session(
            user_id=user_id,
            token_hash=digest_token(token),
            expires_at=session_expires_at(),
        )
        return token


auth_service = AuthService()
