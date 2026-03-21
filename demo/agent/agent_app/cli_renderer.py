from __future__ import annotations

import sys
import time
import unicodedata

from agent_app.ui_schema import CardBlock, CardField, TextBlock, TurnResult


TOOL_DISPLAY_NAMES = {
    "recommend_dishes": "生成菜品建议",
    "get_recipe_requirements": "展示所需食材",
    "check_ingredients": "判断缺料情况",
    "suggest_missing_items": "生成补买建议",
    "suggest_alternative_dishes": "推荐替代菜品",
    "start_cooking": "进入烹饪指导",
    "next_cooking_step": "推进当前步骤",
    "answer_cooking_question": "回答烹饪追问",
    "update_user_profile": "更新用户信息",
}


def display_width(text: str) -> int:
    width = 0
    for char in text:
        width += 2 if unicodedata.east_asian_width(char) in {"W", "F"} else 1
    return width


def wrap_text(text: str, width: int) -> list[str]:
    if not text:
        return []

    lines: list[str] = []
    current = ""
    current_width = 0
    for char in text:
        char_width = 2 if unicodedata.east_asian_width(char) in {"W", "F"} else 1
        if current and current_width + char_width > width:
            lines.append(current)
            current = char
            current_width = char_width
            continue
        current += char
        current_width += char_width
    if current:
        lines.append(current)
    return lines


def build_card_border(title: str, inner_width: int) -> tuple[str, str]:
    if not title:
        return f"╭{'─' * (inner_width + 2)}╮", f"╰{'─' * (inner_width + 2)}╯"

    title_text = f" {title} "
    title_width = display_width(title_text)
    remaining = inner_width + 2 - title_width
    left = max(0, remaining // 2)
    right = max(0, remaining - left)
    top = f"╭{'─' * left}{title_text}{'─' * right}╮"
    bottom = f"╰{'─' * (inner_width + 2)}╯"
    return top, bottom


def render_card(card: CardBlock, width: int = 62) -> str:
    inner_width = width
    lines: list[str] = []

    if card.title:
        lines.extend(wrap_text(card.title, inner_width))
    if card.subtitle:
        lines.extend(wrap_text(card.subtitle, inner_width))
    if card.tags:
        lines.extend(wrap_text(f"标签: {' / '.join(card.tags)}", inner_width))
    for field in card.fields:
        lines.extend(wrap_text(f"{field.label}: {field.value}", inner_width))
    for item in card.items:
        lines.extend(wrap_text(f"- {item}", inner_width))
    if card.footer:
        lines.extend(wrap_text(card.footer, inner_width))

    top, bottom = build_card_border(card.chrome_title or card.title, inner_width)
    body = []
    for line in lines:
        padding = inner_width - display_width(line)
        body.append(f"│ {line}{' ' * padding} │")

    return "\n".join([top, *body, bottom])


def card_from_payload(payload: dict) -> CardBlock:
    return CardBlock(
        card_type=payload["card_type"],
        title=payload["title"],
        chrome_title=payload.get("chrome_title"),
        subtitle=payload.get("subtitle", ""),
        tags=payload.get("tags", []),
        fields=[CardField(label=field["label"], value=field["value"]) for field in payload.get("fields", [])],
        items=payload.get("items", []),
        footer=payload.get("footer", ""),
    )


def stream_text(text: str, prefix: str = "", delay: float = 0.012) -> None:
    if not text:
        return

    actual_delay = delay if sys.stdout.isatty() else 0.0
    if prefix:
        print(prefix, end="", flush=True)
    if actual_delay <= 0:
        print(text)
        return

    for char in text:
        print(char, end="", flush=True)
        time.sleep(actual_delay)
    print()


def render_turn(turn: TurnResult) -> None:
    if turn.trace_steps:
        max_label_width = max(display_width(step.label) for step in turn.trace_steps)
        for step in turn.trace_steps:
            padding = max_label_width - display_width(step.label)
            print(f"✓ {step.label}{' ' * padding}    {step.status}")
        print()

    first_text = True
    for block in turn.blocks:
        if isinstance(block, TextBlock):
            prefix = "ChefMate> " if first_text else ""
            stream_text(block.text, prefix=prefix)
            first_text = False
            continue

        print(render_card(block))


class StreamConsoleRenderer:
    def __init__(self) -> None:
        self.started_text = False
        self.buffered_cards: list[CardBlock] = []
        self.has_visible_events = False

    def render_event(self, event: dict) -> None:
        event_type = event.get("type")
        if event_type == "trace":
            # trace 事件保留给后续 Web 或调试使用，CLI 默认不展示。
            return

        if event_type == "tool_call":
            display_name = TOOL_DISPLAY_NAMES.get(event["tool_name"], event["tool_name"])
            print(f"→ {display_name}")
            self.has_visible_events = True
            return

        if event_type == "tool_result":
            # 工具完成事件不单独展示，避免刷屏。
            return

        if event_type == "card":
            self.buffered_cards.append(card_from_payload(event["card"]))
            return

        if event_type == "text_start":
            if not self.started_text:
                if self.has_visible_events:
                    print()
                print("ChefMate> ", end="", flush=True)
                self.started_text = True
            return

        if event_type == "text_delta":
            if not self.started_text:
                self.render_event({"type": "text_start"})
            text = event.get("text", "")
            actual_delay = 0.008 if sys.stdout.isatty() else 0.0
            if actual_delay <= 0:
                print(text, end="", flush=True)
                return
            for char in text:
                print(char, end="", flush=True)
                time.sleep(actual_delay)
            return

    def finalize(self, turn: TurnResult, model_text_printed: bool) -> None:
        before_texts = [
            block.text
            for block in turn.blocks
            if isinstance(block, TextBlock) and block.placement == "before_cards"
        ]
        trailing_texts = [
            block.text
            for block in turn.blocks
            if isinstance(block, TextBlock) and block.placement == "after_cards"
        ]

        if self.started_text:
            print()
        elif before_texts:
            stream_text(before_texts[0], prefix="ChefMate> ")
            for text in before_texts[1:]:
                stream_text(text)
        elif not self.buffered_cards and trailing_texts:
            stream_text(trailing_texts[0], prefix="ChefMate> ")
            trailing_texts = trailing_texts[1:]

        if self.buffered_cards:
            for card in self.buffered_cards:
                print(render_card(card))

        if trailing_texts:
            for text in trailing_texts:
                stream_text(text)
