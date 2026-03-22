from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
import html
import json
import os
import re
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib import parse
from openai import OpenAI


BASE_DIR = Path(__file__).resolve().parent
DISHES_DIR = BASE_DIR.parent / "dishes"
WORKSPACE_DIR = BASE_DIR / "workspace"
APPROVED_DIR = WORKSPACE_DIR / "approved"
REJECTED_DIR = WORKSPACE_DIR / "rejected"
RAW_DIR = WORKSPACE_DIR / "raw"
STATE_FILE = WORKSPACE_DIR / "review_state.json"
PROMPT_FILE = BASE_DIR / "prompt_template.md"
TAG_CATALOG_FILE = BASE_DIR / "tag_catalog.json"
ENV_FILE = BASE_DIR / ".env"

HOST = "127.0.0.1"
PORT = 8765


def load_dotenv_file() -> None:
    if not ENV_FILE.exists():
        return
    for raw_line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def ensure_dirs() -> None:
    for path in [WORKSPACE_DIR, APPROVED_DIR, REJECTED_DIR, RAW_DIR]:
        path.mkdir(parents=True, exist_ok=True)


def load_tag_catalog() -> dict[str, list[str]]:
    return json.loads(TAG_CATALOG_FILE.read_text(encoding="utf-8"))


TAG_CATALOG = load_tag_catalog()
DIFFICULTY_OPTIONS = ["简单", "中等", "困难"]


def build_tag_guide() -> str:
    lines: list[str] = []
    for category, tags in TAG_CATALOG.items():
        joined = "、".join(tags)
        lines.append(f"- {category}: {joined}")
    return "\n".join(lines)


def build_json_schema_text() -> str:
    schema = {
        "name": "菜品名称",
        "image_path": None,
        "description": "菜品描述",
        "difficulty": "简单",
        "estimated_minutes": 15,
        "servings": 2,
        "tags": {
            "flavor": ["酸甜"],
            "method": ["炒"],
            "scene": ["家常", "下饭"],
            "health": ["低油"],
            "time": ["10到20分钟"],
            "tool": ["炒锅"],
        },
        "ingredients": [
            {
                "name": "西红柿",
                "amount_value": 2,
                "amount_text": "2个",
                "unit": "个",
                "optional": False,
                "purpose": "主体风味",
            }
        ],
        "steps": [
            {
                "step_no": 1,
                "title": "处理食材",
                "instruction": "将主要食材洗净并切配。",
                "timer_seconds": None,
                "notes": None,
            }
        ],
        "tips": ["原文中的做菜提示"],
    }
    return json.dumps(schema, ensure_ascii=False, indent=2)


PROMPT_TEMPLATE = PROMPT_FILE.read_text(encoding="utf-8")
JSON_SCHEMA_TEXT = build_json_schema_text()
TAG_GUIDE_TEXT = build_tag_guide()


@dataclass
class RecipeItem:
    index: int
    rel_path: str
    abs_path: Path


def scan_markdown_files() -> list[RecipeItem]:
    files = sorted(path for path in DISHES_DIR.rglob("*.md") if path.is_file())
    return [
        RecipeItem(index=i + 1, rel_path=str(path.relative_to(DISHES_DIR)), abs_path=path)
        for i, path in enumerate(files)
    ]


def generate_recipe_for_item(item: RecipeItem) -> str:
    markdown_text = item.abs_path.read_text(encoding="utf-8")
    return call_openai_compatible(markdown_text)


def load_state(items: list[RecipeItem]) -> dict[str, Any]:
    if STATE_FILE.exists():
        state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    else:
        state = {"items": {}, "last_index": 1}

    for item in items:
        state["items"].setdefault(
            item.rel_path,
            {
                "index": item.index,
                "status": "pending",
                "generated_file": None,
                "approved_file": None,
                "rejected_file": None,
                "updated_at": None,
            },
        )

    state["items"] = {
        key: value
        for key, value in state["items"].items()
        if any(item.rel_path == key for item in items)
    }
    return state


def save_state(state: dict[str, Any]) -> None:
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def normalize_json_text(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```json\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^```\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def parse_and_validate_response_text(content: str) -> dict[str, Any]:
    normalized = normalize_json_text(content)
    parsed = json.loads(normalized)
    validate_recipe_json(parsed)
    return parsed


def get_time_bucket(minutes: int) -> str:
    if minutes <= 10:
        return "10分钟内"
    if minutes <= 20:
        return "10到20分钟"
    if minutes <= 30:
        return "20到30分钟"
    if minutes <= 60:
        return "30到60分钟"
    if minutes <= 120:
        return "60到120分钟"
    return "120分钟以上"


def build_payload(prompt: str, model_name: str, temperature: float, use_json_mode: bool) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": model_name,
        "temperature": temperature,
        "messages": [
            {"role": "system", "content": "你是一个严格输出 JSON 的菜谱结构化助手。"},
            {"role": "user", "content": prompt},
        ],
    }
    if use_json_mode:
        payload["response_format"] = {"type": "json_object"}
    return payload


def should_retry_without_json_mode(detail: str) -> bool:
    lowered = detail.lower()
    return "json_object" in lowered and "not supported" in lowered


def request_via_openai_package(
    base_url: str,
    api_key: str,
    payload: dict[str, Any],
    timeout_seconds: float,
) -> str:
    client = OpenAI(base_url=base_url, api_key=api_key, timeout=timeout_seconds)
    response = client.chat.completions.create(**payload)
    content = response.choices[0].message.content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            text = getattr(item, "text", None)
            if text:
                parts.append(text)
        content = "\n".join(parts)
    if not isinstance(content, str):
        raise RuntimeError("模型返回内容不是字符串，无法解析。")
    return content


def call_openai_compatible(markdown_text: str) -> str:
    base_url = os.environ.get("OPENAI_BASE_URL", "").rstrip("/")
    api_key = os.environ.get("OPENAI_API_KEY", "")
    model_name = os.environ.get("OPENAI_MODEL_NAME", "")
    timeout_seconds = float(os.environ.get("OPENAI_TIMEOUT_SECONDS", "120"))
    temperature = float(os.environ.get("OPENAI_TEMPERATURE", "0.2"))
    use_json_mode = os.environ.get("OPENAI_USE_JSON_MODE", "1") != "0"

    if not base_url or not api_key or not model_name:
        raise RuntimeError("缺少 OPENAI_BASE_URL / OPENAI_API_KEY / OPENAI_MODEL_NAME 环境变量。")
    if OpenAI is None:
        raise RuntimeError("当前未安装 openai Python 包，请先安装后再运行。")

    prompt = (
        PROMPT_TEMPLATE.replace("{{TAG_GUIDE}}", TAG_GUIDE_TEXT)
        .replace("{{JSON_SCHEMA}}", JSON_SCHEMA_TEXT)
        .replace("{{RECIPE_MARKDOWN}}", markdown_text)
    )

    payload = build_payload(prompt, model_name, temperature, use_json_mode)
    try:
        return request_via_openai_package(base_url, api_key, payload, timeout_seconds)
    except Exception as exc:  # noqa: BLE001
        detail = str(exc)
        if use_json_mode and should_retry_without_json_mode(detail):
            fallback_payload = build_payload(prompt, model_name, temperature, False)
            try:
                return request_via_openai_package(base_url, api_key, fallback_payload, timeout_seconds)
            except Exception as retry_exc:  # noqa: BLE001
                raise RuntimeError(f"模型请求失败：{retry_exc}") from retry_exc
        raise RuntimeError(f"模型请求失败：{exc}") from exc


def collect_recipe_issues(data: dict[str, Any]) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    required_top = [
        "name",
        "image_path",
        "description",
        "difficulty",
        "estimated_minutes",
        "servings",
        "tags",
        "ingredients",
        "steps",
        "tips",
    ]
    for key in required_top:
        if key not in data:
            errors.append(f"结构化结果缺少字段：{key}")

    if errors:
        return errors, warnings

    if not isinstance(data["name"], str) or not data["name"].strip():
        errors.append("name 必须是非空字符串。")
    if data["image_path"] is not None and not isinstance(data["image_path"], str):
        errors.append("image_path 必须是字符串或 null。")
    if not isinstance(data["description"], str) or not data["description"].strip():
        errors.append("description 必须是非空字符串。")
    if not isinstance(data["estimated_minutes"], int) or data["estimated_minutes"] <= 0:
        errors.append("estimated_minutes 必须是正整数。")
    if not isinstance(data["servings"], int) or data["servings"] <= 0:
        errors.append("servings 必须是正整数。")

    if data["difficulty"] not in DIFFICULTY_OPTIONS:
        errors.append("difficulty 字段不在固定集合中。")

    tags = data["tags"]
    if not isinstance(tags, dict):
        errors.append("tags 必须是对象。")
        return errors, warnings

    for category, allowed in TAG_CATALOG.items():
        if category not in tags:
            errors.append(f"tags 缺少分类：{category}")
            continue
        if not isinstance(tags[category], list):
            errors.append(f"tags.{category} 必须是数组。")
            continue
        invalid = [tag for tag in tags[category] if tag not in allowed]
        if invalid:
            errors.append(f"tags.{category} 出现非法标签：{', '.join(invalid)}")
        if len(tags[category]) != len(set(tags[category])):
            warnings.append(f"tags.{category} 存在重复标签。")

    if isinstance(tags.get("time"), list) and len(tags["time"]) != 1:
        errors.append("tags.time 必须且只能有一个值。")

    if not isinstance(tags.get("tool"), list):
        errors.append("tags.tool 必须是数组。")
    elif not tags["tool"]:
        warnings.append("tags.tool 当前为空，若原文能判断厨具，建议补上。")

    if isinstance(data["estimated_minutes"], int) and isinstance(tags.get("time"), list) and len(tags["time"]) == 1:
        expected_time_tag = get_time_bucket(data["estimated_minutes"])
        if tags["time"][0] != expected_time_tag:
            warnings.append(f"estimated_minutes 推导出的时间标签应为“{expected_time_tag}”，当前为“{tags['time'][0]}”。")

    ingredients = data["ingredients"]
    if not isinstance(ingredients, list) or not ingredients:
        errors.append("ingredients 必须是非空数组。")
    else:
        for idx, ingredient in enumerate(ingredients, start=1):
            if not isinstance(ingredient, dict):
                errors.append(f"ingredients[{idx}] 必须是对象。")
                continue
            if not ingredient.get("name"):
                errors.append(f"ingredients[{idx}].name 不能为空。")
            if not ingredient.get("amount_text"):
                errors.append(f"ingredients[{idx}].amount_text 不能为空。")
            if "optional" not in ingredient or not isinstance(ingredient["optional"], bool):
                errors.append(f"ingredients[{idx}].optional 必须是布尔值。")

    steps = data["steps"]
    if not isinstance(steps, list) or not steps:
        errors.append("steps 必须是非空数组。")
    else:
        step_numbers: list[int] = []
        for idx, step in enumerate(steps, start=1):
            if not isinstance(step, dict):
                errors.append(f"steps[{idx}] 必须是对象。")
                continue
            step_no = step.get("step_no")
            if not isinstance(step_no, int) or step_no <= 0:
                errors.append(f"steps[{idx}].step_no 必须是正整数。")
            else:
                step_numbers.append(step_no)
            if not isinstance(step.get("instruction"), str) or not step["instruction"].strip():
                errors.append(f"steps[{idx}].instruction 不能为空。")
            timer_seconds = step.get("timer_seconds")
            if timer_seconds is not None and (not isinstance(timer_seconds, int) or timer_seconds < 0):
                errors.append(f"steps[{idx}].timer_seconds 必须是非负整数或 null。")
        if step_numbers and step_numbers != list(range(1, len(step_numbers) + 1)):
            warnings.append("steps.step_no 不是从 1 开始连续递增。")

    tips = data["tips"]
    if not isinstance(tips, list):
        errors.append("tips 必须是数组。")
    elif any(not isinstance(tip, str) for tip in tips):
        errors.append("tips 中的所有项都必须是字符串。")

    return errors, warnings


def validate_recipe_json(data: dict[str, Any]) -> None:
    errors, _warnings = collect_recipe_issues(data)
    if errors:
        raise RuntimeError("；".join(errors))


def build_validation_summary(json_text: str) -> tuple[str, list[str], list[str]]:
    normalized = normalize_json_text(json_text)
    try:
        parsed = json.loads(normalized)
    except Exception as exc:  # noqa: BLE001
        return json_text, [f"JSON 解析失败：{exc}"], []
    errors, warnings = collect_recipe_issues(parsed)
    pretty = json.dumps(parsed, ensure_ascii=False, indent=2)
    return pretty, errors, warnings


def find_item_by_index(items: list[RecipeItem], index: int) -> RecipeItem:
    for item in items:
        if item.index == index:
            return item
    raise KeyError(index)


def next_pending_index(items: list[RecipeItem], state: dict[str, Any]) -> int:
    for item in items:
        if state["items"][item.rel_path]["status"] == "pending":
            return item.index
    return items[-1].index if items else 1


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def load_json_if_exists(path: Path | None) -> dict[str, Any] | None:
    if path is None or not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def load_text_if_exists(path: Path | None) -> str | None:
    if path is None or not path.exists():
        return None
    return path.read_text(encoding="utf-8")


def html_page(title: str, body: str) -> bytes:
    page = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>{html.escape(title)}</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 0; background: #f7f7f9; color: #222; }}
    .topbar {{ padding: 14px 18px; background: #fff; border-bottom: 1px solid #ddd; position: sticky; top: 0; }}
    .layout {{ display: flex; gap: 16px; padding: 16px; }}
    .pane {{ flex: 1; background: #fff; border: 1px solid #ddd; border-radius: 10px; overflow: hidden; }}
    .pane h2 {{ margin: 0; padding: 12px 14px; font-size: 16px; border-bottom: 1px solid #eee; background: #fafafa; }}
    .content {{ padding: 14px; }}
    pre {{ white-space: pre-wrap; word-break: break-word; margin: 0; font-family: Consolas, monospace; font-size: 13px; line-height: 1.5; }}
    textarea {{ width: 100%; min-height: 72vh; font-family: Consolas, monospace; font-size: 13px; line-height: 1.5; }}
    .actions {{ display: flex; gap: 8px; flex-wrap: wrap; margin-top: 12px; }}
    button {{ padding: 8px 14px; border-radius: 8px; border: 1px solid #bbb; background: #fff; cursor: pointer; }}
    button.primary {{ background: #222; color: #fff; border-color: #222; }}
    .meta {{ font-size: 14px; color: #555; }}
    .badge {{ display: inline-block; padding: 2px 8px; border-radius: 999px; background: #eee; margin-left: 8px; }}
    .error {{ margin: 12px 0; padding: 10px 12px; border-radius: 8px; background: #fff2f0; color: #a8071a; border: 1px solid #ffccc7; }}
    .warn {{ margin: 12px 0; padding: 10px 12px; border-radius: 8px; background: #fffbe6; color: #8d6b00; border: 1px solid #ffe58f; }}
    .notice {{ margin: 12px 0; padding: 10px 12px; border-radius: 8px; background: #f6ffed; color: #237804; border: 1px solid #b7eb8f; }}
    ul {{ margin: 8px 0 0 18px; }}
  </style>
</head>
<body>{body}</body>
</html>"""
    return page.encode("utf-8")


class ReviewHandler(BaseHTTPRequestHandler):
    items: list[RecipeItem] = []
    state: dict[str, Any] = {}

    def _read_form(self) -> dict[str, str]:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8")
        pairs = [part.split("=", 1) for part in raw.split("&") if "=" in part]
        result: dict[str, str] = {}
        for key, value in pairs:
            key = parse.unquote_plus(key)
            value = parse.unquote_plus(value)
            result[key] = value
        return result

    def _redirect(self, location: str) -> None:
        self.send_response(HTTPStatus.SEE_OTHER)
        self.send_header("Location", location)
        self.end_headers()

    def do_GET(self) -> None:
        parsed = parse.urlparse(self.path)
        query = parse.parse_qs(parsed.query)
        if not self.items:
            self._send_html("无数据", "<div class='topbar'>没有找到任何 Markdown 菜谱文件。</div>")
            return
        index = int(query.get("id", [str(next_pending_index(self.items, self.state))])[0])
        index = max(1, min(index, len(self.items)))
        error_message = query.get("error", [""])[0]
        notice_message = query.get("notice", [""])[0]
        self._render_item(index, error_message=error_message, notice_message=notice_message)

    def do_POST(self) -> None:
        parsed = parse.urlparse(self.path)
        form = self._read_form()
        index = int(form.get("id", "1"))
        item = find_item_by_index(self.items, index)
        item_state = self.state["items"][item.rel_path]

        if parsed.path == "/generate":
            try:
                generated_text = generate_recipe_for_item(item)
                raw_path = RAW_DIR / f"{index:04d}.txt"
                write_text(raw_path, generated_text)
                item_state["generated_file"] = str(raw_path.relative_to(BASE_DIR))
                item_state["status"] = "pending"
                self.state["last_index"] = index
                save_state(self.state)
                _pretty, errors, _warnings = build_validation_summary(generated_text)
                if errors:
                    self._redirect(f"/?id={index}&error={parse.quote_plus('模型返回结果校验失败，请查看右侧结构化 JSON。')}")
                else:
                    self._redirect(f"/?id={index}")
            except Exception as exc:  # noqa: BLE001
                self._redirect(f"/?id={index}&error={parse.quote_plus(str(exc))}")
            return

        if parsed.path == "/generate-batch":
            count = max(1, min(50, int(form.get("batch_count", "5"))))
            concurrency = max(1, min(10, int(form.get("batch_concurrency", "3"))))
            candidates: list[RecipeItem] = []
            for current_item in self.items:
                if current_item.index < index:
                    continue
                current_state = self.state["items"][current_item.rel_path]
                if current_state["status"] == "approved":
                    continue
                candidates.append(current_item)
                if len(candidates) >= count:
                    break

            generated_count = 0
            failed_count = 0
            with ThreadPoolExecutor(max_workers=concurrency) as executor:
                future_map = {executor.submit(generate_recipe_for_item, current_item): current_item for current_item in candidates}
                for future in as_completed(future_map):
                    current_item = future_map[future]
                    current_state = self.state["items"][current_item.rel_path]
                    try:
                        generated_text = future.result()
                        raw_path = RAW_DIR / f"{current_item.index:04d}.txt"
                        write_text(raw_path, generated_text)
                        current_state["generated_file"] = str(raw_path.relative_to(BASE_DIR))
                        current_state["status"] = "pending"
                        self.state["last_index"] = current_item.index
                        generated_count += 1
                    except Exception:
                        failed_count += 1
            save_state(self.state)
            notice = f"批量生成完成 {generated_count} 条，并发数 {concurrency}"
            if failed_count:
                notice += f"，失败 {failed_count} 条"
            self._redirect(f"/?id={index}&notice={parse.quote_plus(notice)}")
            return

        if parsed.path == "/validate":
            json_text = form.get("json_text", "")
            pretty_text, errors, warnings = build_validation_summary(json_text)
            self._render_item(
                index,
                custom_json_text=pretty_text,
                validation_errors=errors,
                validation_warnings=warnings,
            )
            return

        if parsed.path == "/approve":
            json_text = form.get("json_text", "")
            try:
                parsed_json = json.loads(json_text)
                validate_recipe_json(parsed_json)
            except Exception as exc:  # noqa: BLE001
                self._redirect(f"/?id={index}&error={parse.quote_plus(str(exc))}")
                return

            approved_path = APPROVED_DIR / f"{index:04d}.json"
            write_json(approved_path, parsed_json)
            item_state["approved_file"] = str(approved_path.relative_to(BASE_DIR))
            item_state["status"] = "approved"
            self.state["last_index"] = index
            save_state(self.state)
            self._redirect(f"/?id={next_pending_index(self.items, self.state)}")
            return

        if parsed.path == "/reject":
            rejected_payload = {
                "source_file": item.rel_path,
                "status": "rejected",
                "json_text": form.get("json_text", ""),
            }
            rejected_path = REJECTED_DIR / f"{index:04d}.json"
            write_json(rejected_path, rejected_payload)
            item_state["rejected_file"] = str(rejected_path.relative_to(BASE_DIR))
            item_state["status"] = "rejected"
            self.state["last_index"] = index
            save_state(self.state)
            self._redirect(f"/?id={next_pending_index(self.items, self.state)}")
            return

        if parsed.path == "/goto":
            target = int(form.get("target_id", str(index)))
            target = max(1, min(target, len(self.items)))
            self._redirect(f"/?id={target}")
            return

        self.send_error(HTTPStatus.NOT_FOUND)

    def _render_item(
        self,
        index: int,
        error_message: str = "",
        notice_message: str = "",
        custom_json_text: str | None = None,
        validation_errors: list[str] | None = None,
        validation_warnings: list[str] | None = None,
    ) -> None:
        item = find_item_by_index(self.items, index)
        item_state = self.state["items"][item.rel_path]
        markdown_text = item.abs_path.read_text(encoding="utf-8")
        generated_text = None
        if item_state.get("approved_file"):
            approved_json = load_json_if_exists(BASE_DIR / item_state["approved_file"])
            if approved_json is not None:
                generated_text = json.dumps(approved_json, ensure_ascii=False, indent=2)
        elif item_state.get("generated_file"):
            generated_text = load_text_if_exists(BASE_DIR / item_state["generated_file"])

        generated_text = custom_json_text if custom_json_text is not None else (generated_text if generated_text is not None else "{}")
        status = item_state["status"]
        total = len(self.items)
        prev_id = max(1, index - 1)
        next_id = min(total, index + 1)

        error_html = f"<div class='error'>{html.escape(error_message)}</div>" if error_message else ""
        notice_html = f"<div class='notice'>{html.escape(notice_message)}</div>" if notice_message else ""

        if validation_errors is None or validation_warnings is None:
            _pretty, validation_errors, validation_warnings = build_validation_summary(generated_text)

        validation_html = ""
        if validation_errors:
            items_html = "".join(f"<li>{html.escape(msg)}</li>" for msg in validation_errors)
            validation_html += f"<div class='error'><strong>校验错误</strong><ul>{items_html}</ul></div>"
        if validation_warnings:
            items_html = "".join(f"<li>{html.escape(msg)}</li>" for msg in validation_warnings)
            validation_html += f"<div class='warn'><strong>校验提醒</strong><ul>{items_html}</ul></div>"

        body = f"""
        <div class="topbar">
          <div><strong>菜谱结构化审核工具</strong></div>
          <div class="meta">
            第 {index} / {total} 条
            <span class="badge">{html.escape(status)}</span>
            <span class="badge">{html.escape(item.rel_path)}</span>
          </div>
          {error_html}
          {notice_html}
          <form method="post" action="/goto" style="margin-top:10px;">
            <input type="hidden" name="id" value="{index}">
            <label>跳转编号：</label>
            <input type="number" name="target_id" min="1" max="{total}" value="{index}">
            <button type="submit">跳转</button>
            <a href="/?id={prev_id}" style="margin-left:12px;">上一条</a>
            <a href="/?id={next_id}" style="margin-left:12px;">下一条</a>
          </form>
          <form method="post" action="/generate-batch" style="margin-top:10px;">
            <input type="hidden" name="id" value="{index}">
            <label>从当前开始批量生成：</label>
            <input type="number" name="batch_count" min="1" max="50" value="5">
            <label style="margin-left:12px;">并发数：</label>
            <input type="number" name="batch_concurrency" min="1" max="10" value="3">
            <button type="submit">批量生成</button>
          </form>
        </div>
        <div class="layout">
          <div class="pane">
            <h2>原始 Markdown</h2>
            <div class="content"><pre>{html.escape(markdown_text)}</pre></div>
          </div>
          <div class="pane">
            <h2>结构化 JSON</h2>
            <div class="content">
              {validation_html}
              <form method="post" action="/approve">
                <input type="hidden" name="id" value="{index}">
                <textarea name="json_text">{html.escape(generated_text)}</textarea>
                <div class="actions">
                  <button class="primary" formaction="/generate" formmethod="post">生成/重试</button>
                  <button formaction="/validate" formmethod="post">校验</button>
                  <button class="primary" type="submit">通过</button>
                  <button formaction="/reject" formmethod="post">拒绝</button>
                </div>
              </form>
            </div>
          </div>
        </div>
        """
        self._send_html("菜谱结构化审核工具", body)

    def _send_html(self, title: str, body: str) -> None:
        payload = html_page(title, body)
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
        return


def main() -> None:
    load_dotenv_file()
    ensure_dirs()
    items = scan_markdown_files()
    state = load_state(items)
    save_state(state)
    ReviewHandler.items = items
    ReviewHandler.state = state
    server = ThreadingHTTPServer((HOST, PORT), ReviewHandler)
    print(f"审核工具已启动: http://{HOST}:{PORT}")
    print(f"共扫描到 {len(items)} 条 Markdown 菜谱。")
    server.serve_forever()


if __name__ == "__main__":
    main()
