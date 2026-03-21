from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass

from agent_app.models import Recipe, SessionStage, SessionState, UserProfile
from agent_app.ui_schema import CardBlock, CardField, TextBlock, TraceStep, TurnResult, card_to_payload


INGREDIENT_ALIASES = {
    "西红柿": "番茄",
    "番茄": "番茄",
    "鸡蛋": "鸡蛋",
    "米饭": "米饭",
    "剩饭": "米饭",
    "土豆": "土豆",
    "青椒": "青椒",
    "生菜": "生菜",
    "蒜": "大蒜",
    "大蒜": "大蒜",
    "鸡翅": "鸡翅中",
    "鸡中翅": "鸡翅中",
    "面条": "挂面",
    "挂面": "挂面",
    "葱": "葱花",
    "小葱": "葱花",
}

SUBSTITUTIONS = {
    "葱花": "没有葱花也能做，出锅前少量蒜末提香即可。",
    "生抽": "没有生抽可以用少量盐加一点点糖顶一下，但鲜味会弱一些。",
    "番茄": "没有番茄就不建议做番茄类菜，直接换成青椒土豆丝或蛋炒饭更稳。",
    "鸡蛋": "鸡蛋是很多家常菜的关键材料，没有的话建议换菜。",
}

PROFILE_KEYWORDS = {
    "清淡": ("flavor", "清淡"),
    "酸甜": ("flavor", "酸甜"),
    "下饭": ("flavor", "下饭"),
    "辣": ("flavor", "香辣"),
    "减脂": ("health", "减脂"),
    "低油": ("health", "低油"),
    "新手": ("skill", "新手"),
    "熟练": ("skill", "熟练"),
}

PANTRY_INGREDIENTS = {"盐", "食用油"}


@dataclass(slots=True)
class Recommendation:
    recipe: Recipe
    score: float
    reasons: list[str]


class ChefMateToolkit:
    def __init__(self, recipes: list[Recipe], profile: UserProfile, state: SessionState):
        self.recipes = recipes
        self.profile = profile
        self.state = state
        self.stream_writer: Callable[[dict], None] | None = None
        self.turn_trace_steps: list[TraceStep] = []
        self.turn_blocks: list[TextBlock | CardBlock] = []
        self.turn_card_keys: set[str] = set()
        # 这里顺手建一个别名索引，后面按菜名或别名查菜谱会更快。
        self.recipe_lookup = {}
        for recipe in recipes:
            self.recipe_lookup[recipe.name] = recipe
            for alias in recipe.aliases:
                self.recipe_lookup[alias] = recipe

    def begin_turn(self) -> None:
        self.turn_trace_steps = []
        self.turn_blocks = []
        self.turn_card_keys = set()
        self.stream_writer = None

    def set_stream_writer(self, writer: Callable[[dict], None] | None) -> None:
        self.stream_writer = writer

    def emit_stream_event(self, payload: dict) -> None:
        if self.stream_writer is None:
            return
        self.stream_writer(payload)

    def build_turn_result(self, fallback_text: str) -> TurnResult:
        blocks = self.turn_blocks[:] if self.turn_blocks else [TextBlock(text=fallback_text)]
        self.state.current_card_contexts = self.summarize_blocks_for_context(blocks)
        return TurnResult(trace_steps=self.turn_trace_steps[:], blocks=blocks)

    def summarize_blocks_for_context(self, blocks: list[TextBlock | CardBlock]) -> list[str]:
        summaries: list[str] = []
        for block in blocks:
            if not isinstance(block, CardBlock):
                continue
            parts = [block.title]
            if block.subtitle:
                parts.append(block.subtitle)
            if block.tags:
                parts.append(f"标签：{' / '.join(block.tags)}")
            if block.fields:
                parts.append("；".join(f"{field.label}:{field.value}" for field in block.fields))
            if block.items:
                parts.append("；".join(block.items[:3]))
            summaries.append(" | ".join(parts))
        return summaries

    def add_trace(self, label: str) -> None:
        self.turn_trace_steps.append(TraceStep(label=label))
        self.emit_stream_event({"type": "trace", "label": label, "status": "已完成"})

    def add_text(self, text: str, placement: str = "after_cards") -> None:
        if text:
            self.turn_blocks.append(TextBlock(text=text, placement=placement))

    def add_card(self, card: CardBlock, key: str | None = None) -> None:
        if key and key in self.turn_card_keys:
            return
        if key:
            self.turn_card_keys.add(key)
        self.turn_blocks.append(card)
        self.emit_stream_event({"type": "card", "card": card_to_payload(card)})

    def list_recipe_names(self) -> list[str]:
        return [recipe.name for recipe in self.recipes]

    def find_recipe(self, text: str) -> Recipe | None:
        for key, recipe in self.recipe_lookup.items():
            if key in text:
                return recipe
        return None

    def normalize_ingredient(self, name: str) -> str:
        cleaned = re.sub(r"[，、。,\s]", "", name)
        return INGREDIENT_ALIASES.get(cleaned, cleaned)

    def extract_ingredients(self, text: str) -> list[str]:
        known = {
            self.normalize_ingredient(ingredient.name)
            for recipe in self.recipes
            for ingredient in recipe.ingredients
        }
        found: list[str] = []
        for ingredient in known:
            if ingredient and ingredient in text and ingredient not in found:
                found.append(ingredient)
        for alias, normalized in INGREDIENT_ALIASES.items():
            if alias in text and normalized not in found:
                found.append(normalized)
        return found

    def extract_time_limit(self, text: str) -> int | None:
        match = re.search(r"(\d+)\s*分钟", text)
        if match:
            return int(match.group(1))
        return None

    def update_profile_from_text(self, text: str) -> str | None:
        updates: list[str] = []
        for keyword, (target, value) in PROFILE_KEYWORDS.items():
            if keyword not in text:
                continue
            if target == "flavor" and value not in self.profile.flavor_preferences:
                self.profile.flavor_preferences.append(value)
                updates.append(f"口味偏好记成“{value}”")
            elif target == "health":
                self.profile.health_goal = value
                updates.append(f"健康目标更新成“{value}”")
            elif target == "skill":
                self.profile.cooking_skill_level = value
                updates.append(f"做饭熟练度更新成“{value}”")

        restriction_match = re.findall(r"不吃([^\s，。,；;]+)", text)
        for item in restriction_match:
            normalized = self.normalize_ingredient(item)
            if normalized not in self.profile.dietary_restrictions:
                self.profile.dietary_restrictions.append(normalized)
                updates.append(f"忌口加入“{normalized}”")

        time_limit = self.extract_time_limit(text)
        if time_limit:
            self.profile.max_cook_time = time_limit
            updates.append(f"做饭时长上限改成 {time_limit} 分钟")

        if not updates:
            return None
        return "我先帮你记住这些偏好：" + "；".join(updates) + "。"

    def recipe_tags_for_card(self, recipe: Recipe) -> list[str]:
        tags: list[str] = []
        if recipe.difficulty == "简单":
            tags.append("新手友好")
        if recipe.estimated_minutes <= 15:
            tags.append("快手")
        if "清淡" in recipe.flavor_tags:
            tags.append("清爽")
        if "下饭" in recipe.flavor_tags:
            tags.append("家常")
        if recipe.name == "蛋炒饭":
            tags.append("剩饭利用")
        return tags[:3] or recipe.flavor_tags[:3]

    def recommend_dishes(self, user_request: str, available_ingredients: list[str] | None = None) -> str:
        # 推荐逻辑走“规则过滤 + 简单打分”，尽量贴近项目文档里的方法路线。
        self.add_trace("解析用户意图")
        available = available_ingredients or self.extract_ingredients(user_request)
        self.add_trace("提取约束条件")
        time_limit = self.extract_time_limit(user_request) or self.profile.max_cook_time
        recommendations: list[Recommendation] = []

        for recipe in self.recipes:
            if recipe.estimated_minutes > time_limit + 5:
                continue
            recipe_ingredients = [self.normalize_ingredient(item.name) for item in recipe.ingredients]
            if any(restriction in recipe_ingredients for restriction in self.profile.dietary_restrictions):
                continue
            if any(tool not in self.profile.available_tools for tool in recipe.available_tools):
                continue

            score = 0.0
            reasons: list[str] = []

            ingredient_names = [self.normalize_ingredient(item.name) for item in recipe.ingredients if not item.optional]
            if available:
                overlap = len(set(available) & set(ingredient_names))
                score += overlap * 2
                if overlap:
                    reasons.append(f"能利用你手头的 {overlap} 种食材")

            for flavor in self.profile.flavor_preferences:
                if flavor in recipe.flavor_tags:
                    score += 1.5
                    reasons.append(f"符合你偏好的“{flavor}”口味")

            if self.profile.health_goal in recipe.health_tags:
                score += 1.0
                reasons.append(f"和你的“{self.profile.health_goal}”目标比较贴")

            if recipe.estimated_minutes <= time_limit:
                score += 1.0
                reasons.append(f"{recipe.estimated_minutes} 分钟内能完成")

            if self.profile.cooking_skill_level == "新手" and recipe.difficulty == "简单":
                score += 1.0
                reasons.append("步骤对新手比较友好")

            if any(keyword in user_request for keyword in recipe.flavor_tags):
                score += 1.0

            recommendations.append(Recommendation(recipe=recipe, score=score, reasons=reasons))

        self.add_trace("生成推荐候选")
        recommendations.sort(key=lambda item: item.score, reverse=True)
        top = recommendations[:3]
        if not top:
            return "我这边没筛出特别合适的菜，可能是时长、厨具或忌口限制太紧了。你可以放宽一个条件，我再重新帮你挑。"

        self.state.stage = SessionStage.RECOMMENDATION
        self.state.last_recommendations = [item.recipe.name for item in top]
        for index, item in enumerate(top, start=1):
            self.add_card(
                CardBlock(
                    card_type="recipe_recommendation",
                    chrome_title=f"菜品 {index}",
                    title=item.recipe.name,
                    subtitle=item.recipe.summary,
                    tags=self.recipe_tags_for_card(item.recipe),
                    fields=[CardField(label="时间", value=f"{item.recipe.estimated_minutes} 分钟")],
                    footer=f"推荐理由：{'，'.join(item.reasons[:2]) if item.reasons else '整体比较均衡'}",
                ),
                key=f"recipe:{item.recipe.name}",
            )

        self.add_trace("整理回复内容")
        self.add_text("你想选哪一道？直接说名字，我就给你列需要的食材和准备事项。", placement="after_cards")
        return "已生成 3 道推荐菜品卡片，请引导用户选择菜名。"

    def get_recipe_requirements(self, recipe_name: str | None = None) -> str:
        self.add_trace("定位目标菜品")
        recipe = self.find_recipe(recipe_name or "") if recipe_name else None
        if recipe is None and self.state.target_recipe:
            recipe = self.find_recipe(self.state.target_recipe)
        if recipe is None:
            return "我还没定位到具体菜品，你直接告诉我想做哪道菜就行。"

        self.state.target_recipe = recipe.name
        self.state.stage = SessionStage.PREPARATION
        self.state.current_step_index = 0
        self.add_trace("提取备料信息")
        self.add_card(
            CardBlock(
                card_type="recipe_detail",
                chrome_title="菜谱信息",
                title=recipe.name,
                subtitle=recipe.summary,
                tags=self.recipe_tags_for_card(recipe),
                fields=[
                    CardField(label="时间", value=f"{recipe.estimated_minutes} 分钟"),
                    CardField(label="难度", value=recipe.difficulty),
                    CardField(label="份量", value=f"{recipe.servings} 人份"),
                ],
                items=[
                    f"{ingredient.name}：{ingredient.amount}{'（可选）' if ingredient.optional else ''}"
                    for ingredient in recipe.ingredients
                ],
                footer="默认不把盐、食用油这类基础调味算成卡点食材。",
            ),
            key=f"recipe-detail:{recipe.name}",
        )
        self.add_trace("整理回复内容")
        self.add_text("你可以直接告诉我现有食材，比如“我有番茄、鸡蛋、葱花”，我来帮你判断够不够。", placement="after_cards")
        return f"已生成 {recipe.name} 的备料卡片，请引导用户继续提供现有食材。"

    def check_ingredients(self, available_ingredients: list[str] | None = None, recipe_name: str | None = None) -> str:
        self.add_trace("识别现有食材")
        recipe = self.find_recipe(recipe_name or "") if recipe_name else None
        if recipe is None and self.state.target_recipe:
            recipe = self.find_recipe(self.state.target_recipe)
        if recipe is None:
            return "你还没选定要做哪道菜，我先没法帮你判断食材够不够。"

        if available_ingredients:
            normalized_available = []
            for item in available_ingredients:
                normalized = self.normalize_ingredient(item)
                if normalized not in normalized_available:
                    normalized_available.append(normalized)
            self.state.available_ingredients = normalized_available

        # 基础调味默认视为厨房常备，不把它们当成阻塞开做的关键食材。
        required = [
            self.normalize_ingredient(item.name)
            for item in recipe.ingredients
            if not item.optional and self.normalize_ingredient(item.name) not in PANTRY_INGREDIENTS
        ]
        self.add_trace("核对关键食材")
        available = set(self.state.available_ingredients)
        missing = [ingredient for ingredient in required if ingredient not in available]
        self.state.missing_ingredients = missing
        self.state.target_recipe = recipe.name
        self.state.stage = SessionStage.PREPARATION

        if not self.state.available_ingredients:
            return "你还没告诉我手头有什么食材，直接列出来就行，我来帮你对。"

        if not missing:
            self.add_card(
                CardBlock(
                    card_type="ingredient_check",
                    chrome_title="备料检查",
                    title=recipe.name,
                    subtitle="关键食材已齐备，可以开始烹饪",
                    fields=[CardField(label="状态", value="可开做")],
                    items=[f"已有：{', '.join(self.state.available_ingredients)}"],
                ),
                key=f"check-ready:{recipe.name}",
            )
            self.add_trace("整理回复内容")
            self.add_text("你现在回复“开始做”或者“下一步”，我就进入分步骤指导。", placement="after_cards")
            return f"{recipe.name} 的关键食材已经齐备。"

        self.add_card(
            CardBlock(
                card_type="missing_ingredients",
                chrome_title="缺失食材",
                title=recipe.name,
                subtitle=f"还差 {len(missing)} 种关键食材",
                fields=[CardField(label="当前已有", value=", ".join(self.state.available_ingredients))],
                items=missing,
            ),
            key=f"missing:{recipe.name}",
        )
        missing_advice = self.suggest_missing_items()
        alternative = self.suggest_alternative_dishes(self.state.available_ingredients)
        self.add_trace("整理回复内容")
        self.add_text(missing_advice, placement="after_cards")
        if alternative:
            self.add_text(alternative, placement="after_cards")
        return f"{recipe.name} 当前还缺少关键食材：{', '.join(missing)}。"

    def suggest_missing_items(self) -> str:
        if not self.state.target_recipe or not self.state.missing_ingredients:
            return "当前没有需要补买的关键食材。"
        self.add_trace("生成补买建议")
        lines = ["补买建议我给你压缩成最实用的版本："]
        for ingredient in self.state.missing_ingredients:
            if ingredient == "番茄":
                lines.append("- 番茄：这是番茄类菜的主体风味，建议优先买。")
            elif ingredient == "鸡蛋":
                lines.append("- 鸡蛋：核心材料，基本没法省。")
            elif ingredient == "土豆":
                lines.append("- 土豆：主料，不建议省。")
            else:
                lines.append(f"- {ingredient}：建议补齐，做出来会更稳定。")
        return "\n".join(lines)

    def suggest_alternative_dishes(self, available_ingredients: list[str] | None = None) -> str:
        available = available_ingredients or self.state.available_ingredients
        if not available:
            return ""
        ranked = []
        for recipe in self.recipes:
            ingredient_names = [self.normalize_ingredient(item.name) for item in recipe.ingredients if not item.optional]
            overlap = len(set(available) & set(ingredient_names))
            missing = len(set(ingredient_names) - set(available))
            ranked.append((overlap, -missing, recipe))
        ranked.sort(reverse=True, key=lambda item: (item[0], item[1], -item[2].estimated_minutes))
        alternatives = [item[2].name for item in ranked if item[2].name != self.state.target_recipe and item[0] > 0][:2]
        if not alternatives:
            return ""
        self.add_card(
            CardBlock(
                card_type="alternative_recipes",
                chrome_title="替代方案",
                title="如果你不想补买，也可以换菜",
                items=alternatives,
            ),
            key=f"alternatives:{self.state.target_recipe}",
        )
        return "如果你不想出门补买，也可以考虑换成：" + "、".join(alternatives) + "。"

    def start_cooking(self) -> str:
        self.add_trace("确认开始烹饪")
        if not self.state.target_recipe:
            return "先确定一道菜，我们再开做。"
        recipe = self.find_recipe(self.state.target_recipe)
        if recipe is None:
            return "我没找到当前菜谱，咱们重新选一道更稳。"
        if self.state.missing_ingredients:
            return "关键食材还没补齐，直接开始会比较悬。你要么先补买，要么我帮你换一道菜。"

        # 真正开做时，把阶段切到 cooking，并把步骤指针归零。
        self.state.stage = SessionStage.COOKING
        self.state.current_step_index = 0
        return self.current_step_text(recipe)

    def current_step_text(self, recipe: Recipe | None = None) -> str:
        recipe = recipe or self.find_recipe(self.state.target_recipe or "")
        if recipe is None:
            return "当前没有在做的菜。"
        step_no = self.state.current_step_index + 1
        if self.state.current_step_index >= len(recipe.steps):
            self.state.stage = SessionStage.COMPLETE
            return f"{recipe.name} 的主要步骤已经完成了，可以准备出锅开吃啦。"
        self.add_trace("整理步骤信息")
        self.add_card(
            CardBlock(
                card_type="cooking_step",
                chrome_title="当前步骤",
                title=f"{recipe.name} · 第 {step_no} 步",
                subtitle=recipe.steps[self.state.current_step_index],
                fields=[CardField(label="阶段", value="烹饪中")],
                footer="你可以继续问“下一步”“现在火候可以吗”“没有某个调料怎么办”。",
            ),
            key=f"step:{recipe.name}:{step_no}",
        )
        return (
            f"现在做到第 {step_no} 步：{recipe.steps[self.state.current_step_index]}\n"
            "你可以继续问我“下一步”“现在火候可以吗”“没有某个调料怎么办”。"
        )

    def next_cooking_step(self) -> str:
        recipe = self.find_recipe(self.state.target_recipe or "")
        if recipe is None:
            return "当前还没有进入做菜阶段。"
        self.state.stage = SessionStage.COOKING
        self.state.current_step_index += 1
        return self.current_step_text(recipe)

    def answer_cooking_question(self, question: str) -> str:
        recipe = self.find_recipe(self.state.target_recipe or "")
        if recipe is None:
            return "你还没开始做具体菜品，我先没法结合步骤回答。"

        if any(keyword in question for keyword in ["下一步", "然后", "接下来"]):
            return self.next_cooking_step()

        if any(keyword in question for keyword in ["当前", "这一步", "做到哪"]):
            return self.current_step_text(recipe)

        substitute_match = re.search(r"没有([^\s，。,；;]+)怎么办", question)
        if substitute_match:
            ingredient = self.normalize_ingredient(substitute_match.group(1))
            return SUBSTITUTIONS.get(ingredient, f"没有 {ingredient} 也别慌，这步可以先略过，但成品风味会淡一点。")

        if any(keyword in question for keyword in ["多久", "还要几步", "还要多久"]):
            remaining_steps = max(0, len(recipe.steps) - self.state.current_step_index - 1)
            return f"后面大概还剩 {remaining_steps} 步，按正常节奏估计再花 5 到 10 分钟。"

        tip = recipe.tips[0] if recipe.tips else "这道菜先盯住火候和下锅顺序，基本就不会翻车。"
        return f"结合你现在的步骤看，优先注意这件事：{tip}"
