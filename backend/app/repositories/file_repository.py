from __future__ import annotations

from typing import Any

from sqlalchemy import text

from app.db.connection import engine


class FileRepository:
    def create_asset(
        self,
        *,
        asset_id: str,
        user_id: int,
        kind: str,
        original_name: str,
        mime_type: str,
        storage_key: str,
        byte_size: int,
    ) -> None:
        query = text(
            """
            INSERT INTO uploaded_asset (
                id,
                user_id,
                kind,
                original_name,
                mime_type,
                storage_key,
                byte_size
            ) VALUES (
                :id,
                :user_id,
                :kind,
                :original_name,
                :mime_type,
                :storage_key,
                :byte_size
            )
            """
        )
        with engine.begin() as conn:
            conn.execute(
                query,
                {
                    "id": asset_id,
                    "user_id": user_id,
                    "kind": kind,
                    "original_name": original_name,
                    "mime_type": mime_type,
                    "storage_key": storage_key,
                    "byte_size": byte_size,
                },
            )

    def get_asset(self, asset_id: str) -> dict[str, Any] | None:
        query = text(
            """
            SELECT *
            FROM uploaded_asset
            WHERE id = :asset_id
            LIMIT 1
            """
        )
        with engine.connect() as conn:
            row = conn.execute(query, {"asset_id": asset_id}).mappings().first()
        return dict(row) if row else None


file_repository = FileRepository()
