from __future__ import annotations

import base64
import json
from typing import Any

from openai import OpenAIError

from app.config import settings
from app.infra.llm.clients import build_openai_client, resolve_vision_llm_config
from app.schemas.vision import IngredientDetectionItem, IngredientDetectionResponse


class VisionConfigurationError(RuntimeError):
    pass


class VisionService:
    SYSTEM_PROMPT = (
        "你是一个厨房食材识别助手。"
        "请根据图片识别可见的、适合做菜决策的食材，并输出严格 JSON。"
        "不要输出重量、数量、品牌、包装描述、器皿、厨具、调味状态。"
        "如果无法确定，就不要乱猜。"
        "不要使用 Markdown，不要加解释文字。"
        '输出格式必须是：{"ingredients":["番茄","鸡蛋","葱"]}'
    )

    def detect_ingredients_from_image(
        self,
        *,
        image_bytes: bytes,
        mime_type: str,
        filename: str | None = None,
        user_hint: str | None = None,
    ) -> IngredientDetectionResponse:
        backend = settings.vision_backend.strip().lower()
        if backend == "llm":
            return self._detect_by_llm(
                image_bytes=image_bytes,
                mime_type=mime_type,
                filename=filename,
                user_hint=user_hint,
            )
        if backend == "local_model":
            raise NotImplementedError("本地自训练图像识别模型尚未接入，当前请先将 CHEFMATE_VISION_BACKEND 设置为 llm。")
        raise VisionConfigurationError(f"不支持的图像识别后端：{settings.vision_backend}")

    def _detect_by_llm(
        self,
        *,
        image_bytes: bytes,
        mime_type: str,
        filename: str | None = None,
        user_hint: str | None = None,
    ) -> IngredientDetectionResponse:
        config = resolve_vision_llm_config()
        if not config.api_key:
            raise VisionConfigurationError("未配置 CHEFMATE_LLM_API_KEY 或 CHEFMATE_VISION_LLM_API_KEY，无法调用大模型图像识别。")

        client = build_openai_client(config)
        prompt = self._build_user_prompt(filename=filename, user_hint=user_hint)
        image_base64 = base64.b64encode(image_bytes).decode("utf-8")
        image_url = f"data:{mime_type};base64,{image_base64}"

        try:
            response = client.chat.completions.create(
                model=config.model,
                temperature=0.1,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": image_url}},
                        ],
                    },
                ],
            )
        except OpenAIError as exc:
            raise VisionConfigurationError(f"调用图像识别模型失败：{exc}") from exc

        raw_text = self._extract_response_text(response)
        parsed = self._parse_json_text(raw_text)
        ingredients = self._normalize_ingredients(parsed.get("ingredients", []))
        return IngredientDetectionResponse(
            backend="llm",
            model=config.model,
            ingredients=[IngredientDetectionItem(name=name) for name in ingredients],
            raw_text=raw_text,
        )

    def _build_user_prompt(self, *, filename: str | None, user_hint: str | None) -> str:
        lines = [
            "请识别图片中清晰可见、适合作为做菜决策依据的食材。",
            "只返回食材名称列表，使用常见中文名。",
            "像盘子、碗、锅、包装袋、调料瓶不要算作食材。",
            "如果图片里是摆出来的原材料，请尽量识别原材料本身。",
        ]
        if filename:
            lines.append(f"图片文件名：{filename}")
        if user_hint:
            lines.append(f"补充提示：{user_hint}")
        return "\n".join(lines)

    def _extract_response_text(self, payload: Any) -> str:
        if hasattr(payload, "model_dump"):
            payload = payload.model_dump(mode="json")
        if not isinstance(payload, dict):
            raise ValueError("大模型返回内容格式不正确。")

        choices = payload.get("choices") or []
        if not choices:
            raise ValueError("大模型返回中缺少 choices。")

        message = choices[0].get("message") or {}
        content = message.get("content")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            text_parts: list[str] = []
            for item in content:
                if item.get("type") == "text" and item.get("text"):
                    text_parts.append(item["text"])
            if text_parts:
                return "\n".join(text_parts)
        raise ValueError("无法从大模型响应中提取文本内容。")

    def _parse_json_text(self, raw_text: str) -> dict[str, Any]:
        # 有些模型会把 JSON 包在代码块里，这里先做一次轻量清洗。
        raw_text = raw_text.strip()
        if raw_text.startswith("```"):
            lines = raw_text.splitlines()
            if len(lines) >= 3:
                raw_text = "\n".join(lines[1:-1]).strip()

        try:
            parsed = json.loads(raw_text)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

        start = raw_text.find("{")
        end = raw_text.rfind("}")
        if start >= 0 and end > start:
            snippet = raw_text[start : end + 1]
            parsed = json.loads(snippet)
            if isinstance(parsed, dict):
                return parsed
        raise ValueError("大模型返回内容不是合法 JSON。")

    def _normalize_ingredients(self, values: Any) -> list[str]:
        if not isinstance(values, list):
            return []

        normalized: list[str] = []
        seen: set[str] = set()
        for item in values:
            if not isinstance(item, str):
                continue
            name = item.strip()
            if not name:
                continue
            if name not in seen:
                normalized.append(name)
                seen.add(name)
        return normalized


vision_service = VisionService()
