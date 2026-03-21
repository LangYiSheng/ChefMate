from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class SessionStage(str, Enum):
    DISCOVERY = "discovery"
    RECOMMENDATION = "recommendation"
    PREPARATION = "preparation"
    COOKING = "cooking"
    COMPLETE = "complete"


@dataclass(slots=True)
class IngredientRequirement:
    name: str
    amount: str
    optional: bool = False
    purpose: str = ""


@dataclass(slots=True)
class Recipe:
    name: str
    aliases: list[str]
    summary: str
    estimated_minutes: int
    difficulty: str
    servings: int
    flavor_tags: list[str]
    health_tags: list[str]
    available_tools: list[str]
    ingredients: list[IngredientRequirement]
    steps: list[str]
    tips: list[str] = field(default_factory=list)


@dataclass(slots=True)
class UserProfile:
    flavor_preferences: list[str] = field(default_factory=list)
    dietary_restrictions: list[str] = field(default_factory=list)
    health_goal: str = "均衡"
    cooking_skill_level: str = "新手"
    max_cook_time: int = 30
    available_tools: list[str] = field(default_factory=lambda: ["炒锅", "汤锅", "电饭煲"])

    def summary(self) -> str:
        return "\n".join(
            [
                f"口味偏好：{', '.join(self.flavor_preferences) if self.flavor_preferences else '暂无'}",
                f"忌口/过敏：{', '.join(self.dietary_restrictions) if self.dietary_restrictions else '暂无'}",
                f"健康目标：{self.health_goal}",
                f"做饭熟练度：{self.cooking_skill_level}",
                f"可接受时长：{self.max_cook_time} 分钟",
                f"常用厨具：{', '.join(self.available_tools) if self.available_tools else '暂无'}",
            ]
        )


@dataclass(slots=True)
class SessionState:
    stage: SessionStage = SessionStage.DISCOVERY
    target_recipe: str | None = None
    available_ingredients: list[str] = field(default_factory=list)
    missing_ingredients: list[str] = field(default_factory=list)
    last_recommendations: list[str] = field(default_factory=list)
    current_card_contexts: list[str] = field(default_factory=list)
    current_step_index: int = 0
    servings: int = 2
    notes: list[str] = field(default_factory=list)
    chat_history: list[tuple[str, str]] = field(default_factory=list)

    def reset(self) -> None:
        self.stage = SessionStage.DISCOVERY
        self.target_recipe = None
        self.available_ingredients.clear()
        self.missing_ingredients.clear()
        self.last_recommendations.clear()
        self.current_card_contexts.clear()
        self.current_step_index = 0
        self.servings = 2
        self.notes.clear()
        self.chat_history.clear()
