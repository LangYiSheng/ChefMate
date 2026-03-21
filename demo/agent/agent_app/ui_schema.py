from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass(slots=True)
class TraceStep:
    label: str
    status: str = "已完成"


@dataclass(slots=True)
class CardField:
    label: str
    value: str


@dataclass(slots=True)
class TextBlock:
    text: str
    placement: str = "after_cards"


@dataclass(slots=True)
class CardBlock:
    card_type: str
    title: str
    chrome_title: str | None = None
    subtitle: str = ""
    tags: list[str] = field(default_factory=list)
    fields: list[CardField] = field(default_factory=list)
    items: list[str] = field(default_factory=list)
    footer: str = ""


OutputBlock = TextBlock | CardBlock


@dataclass(slots=True)
class TurnResult:
    trace_steps: list[TraceStep] = field(default_factory=list)
    blocks: list[OutputBlock] = field(default_factory=list)

    def plain_text(self) -> str:
        texts: list[str] = []
        for block in self.blocks:
            if isinstance(block, TextBlock):
                texts.append(block.text)
            else:
                texts.append(block.title)
                if block.subtitle:
                    texts.append(block.subtitle)
                texts.extend(f"{field.label}: {field.value}" for field in block.fields)
                texts.extend(block.items)
                if block.footer:
                    texts.append(block.footer)
        return "\n".join(texts)


def card_to_payload(card: CardBlock) -> dict:
    return asdict(card)
