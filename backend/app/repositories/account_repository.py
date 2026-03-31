from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import text

from app.db.connection import engine


class AccountRepository:
    def create_user(
        self,
        *,
        username: str,
        email: str | None,
        password_hash: str,
        display_name: str,
    ) -> int:
        query = text(
            """
            INSERT INTO chefmate_user (
                username,
                email,
                password_hash,
                display_name,
                allow_auto_update,
                auto_start_step_timer,
                cooking_preference_text,
                is_first_workspace_visit,
                has_completed_workspace_onboarding
            ) VALUES (
                :username,
                :email,
                :password_hash,
                :display_name,
                1,
                0,
                '',
                1,
                0
            )
            """
        )
        with engine.begin() as conn:
            result = conn.execute(
                query,
                {
                    "username": username,
                    "email": email,
                    "password_hash": password_hash,
                    "display_name": display_name,
                },
            )
            return int(result.lastrowid)

    def get_user_by_username(self, username: str) -> dict[str, Any] | None:
        query = text(
            """
            SELECT *
            FROM chefmate_user
            WHERE username = :username
            LIMIT 1
            """
        )
        with engine.connect() as conn:
            row = conn.execute(query, {"username": username}).mappings().first()
        return dict(row) if row else None

    def get_user_by_id(self, user_id: int) -> dict[str, Any] | None:
        query = text(
            """
            SELECT *
            FROM chefmate_user
            WHERE id = :user_id
            LIMIT 1
            """
        )
        with engine.connect() as conn:
            row = conn.execute(query, {"user_id": user_id}).mappings().first()
        return dict(row) if row else None

    def update_user_profile(self, user_id: int, payload: dict[str, Any]) -> None:
        if not payload:
            return
        assignments = ", ".join(f"{key} = :{key}" for key in payload)
        params = dict(payload)
        params["user_id"] = user_id
        query = text(
            f"""
            UPDATE chefmate_user
            SET {assignments}
            WHERE id = :user_id
            """
        )
        with engine.begin() as conn:
            conn.execute(query, params)

    def replace_user_tags(self, user_id: int, tag_ids: list[int]) -> None:
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM user_preference_tag WHERE user_id = :user_id"), {"user_id": user_id})
            if not tag_ids:
                return
            for tag_id in tag_ids:
                conn.execute(
                    text(
                        """
                        INSERT INTO user_preference_tag (user_id, tag_id)
                        VALUES (:user_id, :tag_id)
                        """
                    ),
                    {"user_id": user_id, "tag_id": tag_id},
                )

    def get_user_tags(self, user_id: int) -> list[dict[str, Any]]:
        query = text(
            """
            SELECT
                c.category_code,
                t.id AS tag_id,
                t.tag_name
            FROM user_preference_tag upt
            JOIN recipe_tag t ON t.id = upt.tag_id
            JOIN recipe_tag_category c ON c.id = t.category_id
            WHERE upt.user_id = :user_id
            ORDER BY c.sort_order, t.sort_order, t.id
            """
        )
        with engine.connect() as conn:
            rows = conn.execute(query, {"user_id": user_id}).mappings().all()
        return [dict(row) for row in rows]

    def create_session(
        self,
        *,
        user_id: int,
        token_hash: str,
        expires_at: datetime,
    ) -> None:
        query = text(
            """
            INSERT INTO auth_session (user_id, token_hash, expires_at)
            VALUES (:user_id, :token_hash, :expires_at)
            """
        )
        with engine.begin() as conn:
            conn.execute(
                query,
                {
                    "user_id": user_id,
                    "token_hash": token_hash,
                    "expires_at": expires_at,
                },
            )

    def get_active_session_by_token_hash(self, token_hash: str) -> dict[str, Any] | None:
        query = text(
            """
            SELECT *
            FROM auth_session
            WHERE token_hash = :token_hash
              AND revoked_at IS NULL
            LIMIT 1
            """
        )
        with engine.connect() as conn:
            row = conn.execute(query, {"token_hash": token_hash}).mappings().first()
        return dict(row) if row else None

    def revoke_session(self, token_hash: str, revoked_at: datetime) -> None:
        query = text(
            """
            UPDATE auth_session
            SET revoked_at = :revoked_at
            WHERE token_hash = :token_hash
              AND revoked_at IS NULL
            """
        )
        with engine.begin() as conn:
            conn.execute(query, {"token_hash": token_hash, "revoked_at": revoked_at})


account_repository = AccountRepository()
