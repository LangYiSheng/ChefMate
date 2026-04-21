import random

from langchain_core.tools import BaseTool, tool
from langgraph.prebuilt.tool_node import ToolRuntime
import logging

from app.agent.recipe_tool_helpers import (
    build_planning_patch_payload,
    build_task_patch_payload,
    format_recipe_candidate,
    has_ingredient_status_updates,
    has_step_status_updates,
    rank_candidate_ids,
    search_candidate_scores,
    set_recipe_recommendation_card,
    validate_recipe_tag_filters,
)
from app.agent.runtime import AgentTurnContext
from app.agent.tool_errors import handle_agent_tool_error
from app.agent.tool_schemas import (
    GeneratedRecipeInput,
    ImageRecognitionInput,
    IngredientPatchInput,
    PlanningRecipePatchInput,
    RecipeDetailDisplayInput,
    RecipeSearchInput,
    RecommendRecipesInput,
    StepPatchInput,
    TaskRecipePatchInput,
    TaskRecipeUpsertInput,
    UserMemoryUpdateInput,
)
from app.domain.cards import (
    build_cooking_guide_card,
    build_pantry_status_card,
    build_recipe_detail_card,
)
from app.domain.enums import ConversationStage
from app.domain.models import TagSelections
from app.services.profile_service import profile_service
from app.services.recipe_catalog_service import recipe_catalog_service
from app.services.task_service import task_service
from app.services.vision_service import vision_service
from app.schemas.profile import UpdateProfileRequest
from app.utils.recipe_snapshot import (
    apply_client_card_state_overlay,
    build_task_recipe_snapshot_from_catalog,
)

logger = logging.getLogger(__name__)


TOOL_STATUS_LABELS = {
    "get_user_memory": "正在读取你的长期记忆...",
    "update_user_memory": "正在更新你的长期记忆...",
    "start_recommendation_task": "正在开启推荐任务...",
    "search_recipes": "正在搜索菜谱库...",
    "recommend_recipes": "正在推荐菜谱候选...",
    "create_or_update_task_recipe": "正在更新当前任务菜谱...",
    "update_task_recipe_for_planning": "正在调整当前任务菜谱...",
    "show_recipe_detail_card": "正在整理菜谱详情卡片...",
    "recognize_image_ingredients": "正在识别图片中的食材...",
    "advance_to_preparation": "正在推进到备料阶段...",
    "cancel_recommendation_task": "正在取消当前任务...",
    "update_task_recipe_for_preparation": "正在更新备料状态...",
    "show_pantry_card": "正在整理备菜清单...",
    "advance_to_cooking": "正在推进到烹饪阶段...",
    "rollback_to_recommendation": "正在回到推荐阶段...",
    "cancel_preparation_task": "正在取消当前任务...",
    "update_task_recipe_for_cooking": "正在更新烹饪步骤...",
    "show_cooking_card": "正在整理烹饪步骤卡片...",
    "complete_cooking_task": "正在完成本次烹饪任务...",
    "rollback_to_preparation": "正在回到备料阶段...",
    "cancel_cooking_task": "正在取消当前任务...",
}


def build_stage_tools(turn: AgentTurnContext) -> list[BaseTool]:
    stage_labels = {
        ConversationStage.IDLE: "无任务",
        ConversationStage.RECOMMENDING: "推荐中",
        ConversationStage.PREPARING: "备料中",
        ConversationStage.COOKING: "烹饪中",
    }

    def _turn(runtime: ToolRuntime) -> AgentTurnContext:
        return turn

    def _require_task(runtime: ToolRuntime) -> AgentTurnContext:
        current_turn = _turn(runtime)
        if current_turn.current_task_id is None:
            raise ValueError("当前会话没有活动中的任务。")
        return current_turn

    def _log_tool_event(tool_name: str, detail: str) -> None:
        logger.info(
            "[agent-tool] conversation=%s stage=%s tool=%s detail=%s",
            turn.conversation_id,
            turn.active_stage.value,
            tool_name,
            detail,
        )

    def _ensure_stage(
        current_turn: AgentTurnContext,
        *expected: ConversationStage,
    ) -> None:
        if current_turn.active_stage in expected:
            return
        expected_text = " / ".join(stage_labels[item] for item in expected)
        raise ValueError(
            f"当前阶段是{stage_labels[current_turn.active_stage]}，不能直接使用这个工具。"
            f"请先进入 {expected_text} 阶段。"
        )

    def _ensure_recommendation_turn(runtime: ToolRuntime) -> AgentTurnContext:
        current_turn = _turn(runtime)
        if current_turn.active_stage == ConversationStage.IDLE or current_turn.current_task_id is None:
            task = task_service.start_recommendation_task(
                user_id=current_turn.user.id,
                conversation_id=current_turn.conversation_id,
            )
            current_turn.conversation_stage = ConversationStage.RECOMMENDING
            current_turn.current_task_id = task["id"]
            current_turn.current_task_stage = ConversationStage.RECOMMENDING
            current_turn.current_task_source_recipe_id = task.get("source_recipe_id")
            current_turn.current_task_snapshot = None
            current_turn.response_recipe_name = None
            return current_turn
        _ensure_stage(current_turn, ConversationStage.RECOMMENDING)
        return current_turn

    @tool("get_user_memory")
    def get_user_memory(runtime: ToolRuntime) -> str:
        """读取用户长期记忆，包括偏好标签、偏好文本和最近历史任务。"""
        current_turn = _turn(runtime)
        payload = {
            "display_name": current_turn.user.display_name,
            "cooking_preference_text": current_turn.user.cooking_preference_text,
            "tag_selections": current_turn.user.tag_selections.model_dump(),
            "recent_finished_tasks": current_turn.recent_finished_tasks,
        }
        return str(payload)

    @tool("update_user_memory", args_schema=UserMemoryUpdateInput)
    def update_user_memory(
        cooking_preference_text: str | None = None,
        tag_selections: TagSelections | None = None,
        complete_workspace_onboarding: bool | None = None,
        *,
        runtime: ToolRuntime,
    ) -> str:
        """更新用户长期记忆中的偏好文本和标签。只有用户明确要求时才应该调用。"""
        current_turn = _turn(runtime)
        payload = {
            "cooking_preference_text": cooking_preference_text,
            "tag_selections": tag_selections,
            "complete_workspace_onboarding": complete_workspace_onboarding,
        }
        updated = profile_service.update_profile(current_turn.user.id, UpdateProfileRequest(**payload))
        current_turn.user = updated
        return "用户长期记忆已更新。如果你刚才修改了标签，后续推荐会按新的长期记忆继续进行。"

    @tool("start_recommendation_task")
    def start_recommendation_task(runtime: ToolRuntime) -> str:
        """在无任务阶段开启一个新的推荐任务。没有输入参数。"""
        current_turn = _turn(runtime)
        if current_turn.active_stage == ConversationStage.RECOMMENDING and current_turn.current_task_id:
            _log_tool_event("start_recommendation_task", "already_recommending")
            return "当前已经处于推荐中阶段。"
        _ensure_stage(current_turn, ConversationStage.IDLE)
        task = task_service.start_recommendation_task(
            user_id=current_turn.user.id,
            conversation_id=current_turn.conversation_id,
        )
        current_turn.conversation_stage = ConversationStage.RECOMMENDING
        current_turn.current_task_id = task["id"]
        current_turn.current_task_stage = ConversationStage.RECOMMENDING
        current_turn.current_task_source_recipe_id = task.get("source_recipe_id")
        current_turn.current_task_snapshot = None
        _log_tool_event("start_recommendation_task", f"task_id={task['id']}")
        return "已进入推荐中阶段。"

    @tool("search_recipes", args_schema=RecipeSearchInput)
    def search_recipes(
        query: str | None = None,
        ingredients: list[str] | None = None,
        step_text: str | None = None,
        flavor: list[str] | None = None,
        method: list[str] | None = None,
        scene: list[str] | None = None,
        health: list[str] | None = None,
        time: list[str] | None = None,
        tool: list[str] | None = None,
        difficulty: list[str] | None = None,
        name_match_first: bool = True,
        limit: int = 3,
        *,
        runtime: ToolRuntime,
    ) -> str:
        """
        搜索数据库菜谱，不会生成新菜谱。

        用户点名想吃或想做某一道菜时优先调用本工具，例如 query="西红柿炒鸡蛋"，
        ingredients=["西红柿", "鸡蛋"]。工具会先按完整菜名匹配数据库，未命中时再按
        食材、标签和步骤文本找相关候选；如果仍未找到，会明确返回“未收录”，此时不要现编菜谱。
        """
        current_turn = _ensure_recommendation_turn(runtime)
        if not query and not ingredients and not step_text and not any([flavor, method, scene, health, time, tool, difficulty]):
            raise ValueError(
                "search_recipes 至少需要 query、ingredients、step_text 或标签之一。"
                "用户指定菜名时请传 query=完整菜名原文；能拆出食材时同步传 ingredients。"
            )
        tag_filters = validate_recipe_tag_filters(
            flavor=flavor,
            method=method,
            scene=scene,
            health=health,
            time=time,
            tool=tool,
            difficulty=difficulty,
            allow_alias=True,
        )
        resolved_limit = max(1, min(int(limit or 3), 6))
        _log_tool_event(
            "search_recipes",
            f"query={query!r}, ingredients={(ingredients or [])}, step_text={step_text!r}, "
            f"name_match_first={name_match_first}, filters={tag_filters}",
        )
        entries = {entry.id: entry for entry in recipe_catalog_service.list_entries()}
        candidate_scores, attempted, resolved_ingredients, candidate_sources = search_candidate_scores(
            query=query,
            ingredients=ingredients,
            step_text=step_text,
            tag_filters=tag_filters,
            limit=resolved_limit,
            name_match_first=name_match_first,
        )
        ranked_ids = rank_candidate_ids(entries, candidate_scores)
        if not ranked_ids:
            attempted_text = "；".join(attempted) if attempted else "未提供有效检索条件"
            ingredient_text = f"；自动识别到的食材：{'、'.join(resolved_ingredients)}" if resolved_ingredients else ""
            _log_tool_event("search_recipes", "no_candidates")
            return (
                f"数据库里暂时没有找到与「{query or '这些条件'}」匹配的菜谱。"
                f"已尝试：{attempted_text}{ingredient_text}。"
                "请不要编造菜谱内容；请直接告诉用户暂未收录，并询问是否需要你现写一份。"
                "只有用户明确同意现写后，才可以调用 create_or_update_task_recipe 并传 recipe。"
            )

        chosen_ids = ranked_ids[:resolved_limit]
        chosen_entries = [entries[item_id] for item_id in chosen_ids]
        set_recipe_recommendation_card(current_turn, chosen_entries)
        has_name_match = any("name" in candidate_sources.get(item_id, set()) for item_id in chosen_ids)
        summary = [format_recipe_candidate(entry) for entry in chosen_entries]
        _log_tool_event("search_recipes", f"selected_recipe_ids={chosen_ids}")
        if has_name_match:
            return "已在数据库中按菜名找到这些候选：\n" + "\n".join(summary)
        fallback_text = "、".join(resolved_ingredients) if resolved_ingredients else "提供的条件"
        return (
            f"没有找到与「{query or fallback_text}」同名的数据库菜谱；"
            f"已改按食材/标签/步骤文本找到这些相关候选：\n" + "\n".join(summary)
        )

    @tool("recommend_recipes", args_schema=RecommendRecipesInput)
    def recommend_recipes(
        keyword: str | None = None,
        ingredients: list[str] | None = None,
        flavor: list[str] | None = None,
        method: list[str] | None = None,
        scene: list[str] | None = None,
        health: list[str] | None = None,
        time: list[str] | None = None,
        tool: list[str] | None = None,
        difficulty: list[str] | None = None,
        *,
        runtime: ToolRuntime,
    ) -> str:
        """
        根据食材、标签和开放偏好推荐数据库菜谱候选，并自动展示推荐卡片。

        适合“推荐几道快手晚餐”“冰箱有鸡蛋和番茄能做什么”。如果用户点名
        “我想吃西红柿炒鸡蛋”这类具体菜名，应优先调用 search_recipes。
        """
        current_turn = _ensure_recommendation_turn(runtime)
        _log_tool_event(
            "recommend_recipes",
            f"keyword={keyword!r}, ingredients={(ingredients or [])}, filters="
            f"{ {'flavor': flavor or [], 'method': method or [], 'scene': scene or [], 'health': health or [], 'time': time or [], 'tool': tool or [], 'difficulty': difficulty or []} }",
        )
        entries = {entry.id: entry for entry in recipe_catalog_service.list_entries()}
        candidate_scores: dict[int, float] = {}

        if keyword:
            for item in recipe_catalog_service.search_recipes_by_name(keyword, exact=False, limit=12)["candidates"]:
                candidate_scores[item["id"]] = max(candidate_scores.get(item["id"], 0.0), item.get("score", 0.0))
        resolved_ingredients = [item.strip() for item in (ingredients or []) if item and item.strip()]
        if keyword and not resolved_ingredients and not candidate_scores:
            resolved_ingredients = recipe_catalog_service.extract_ingredient_terms_from_text(keyword)
        if resolved_ingredients:
            for item in recipe_catalog_service.find_recipes_by_ingredients(resolved_ingredients, exact_only=False, limit=12)["candidates"]:
                candidate_scores[item["id"]] = max(candidate_scores.get(item["id"], 0.0), item.get("score", 0.0))
        tag_filters = validate_recipe_tag_filters(
            flavor=flavor,
            method=method,
            scene=scene,
            health=health,
            time=time,
            tool=tool,
            difficulty=difficulty,
            allow_alias=False,
        )
        if any(tag_filters.values()):
            for item in recipe_catalog_service.filter_recipes_by_tags(match_mode="fuzzy", limit=12, **tag_filters)["candidates"]:
                candidate_scores[item["id"]] = max(candidate_scores.get(item["id"], 0.0), item.get("score", 0.0))

        if not candidate_scores:
            if keyword and not any(tag_filters.values()):
                _log_tool_event("recommend_recipes", "keyword_no_candidates")
                return (
                    f"没有按关键词「{keyword}」推荐到合适的数据库菜谱。"
                    "如果用户是在指定某一道菜，请改用 search_recipes(query=完整菜名, ingredients=可拆出的食材)；"
                    "如果 search_recipes 也未找到，请告知用户暂未收录，并询问是否需要现写。"
                )
            for item in recipe_catalog_service.default_recommendations(limit=12)["candidates"]:
                candidate_scores[item["id"]] = item.get("score", 0.0)

        ranked_ids = rank_candidate_ids(entries, candidate_scores)
        if not ranked_ids:
            raise ValueError("当前没有找到合适的菜谱候选。")

        chooser = random.Random(f"{current_turn.conversation_id}:{current_turn.latest_user_content}")
        chosen_ids = ranked_ids[: max(6, len(ranked_ids))]
        if len(chosen_ids) > 3:
            chosen_ids = chooser.sample(chosen_ids, k=3)
        chosen_entries = [entries[item_id] for item_id in chosen_ids[:3]]
        set_recipe_recommendation_card(current_turn, chosen_entries)
        summary = [format_recipe_candidate(entry) for entry in chosen_entries]
        _log_tool_event("recommend_recipes", f"selected_recipe_ids={chosen_ids[:3]}")
        return "已推荐这些候选：\n" + "\n".join(summary)

    @tool("create_or_update_task_recipe", args_schema=TaskRecipeUpsertInput)
    def create_or_update_task_recipe(
        recipe_id: int | None = None,
        recipe: GeneratedRecipeInput | None = None,
        *,
        runtime: ToolRuntime,
    ) -> str:
        """
        为当前任务创建或覆盖菜谱快照。

        二选一使用：
        1. 用户选择了数据库候选时，传 recipe_id，把该数据库菜谱复制为当前任务快照。
        2. 用户明确同意“现写/新建”菜谱时，传完整 recipe。

        不要在 search_recipes 未找到指定菜时直接调用 recipe 现编；必须先问用户是否需要现写。
        """
        current_turn = _ensure_recommendation_turn(runtime)
        if recipe_id is None and recipe is None:
            raise ValueError(
                "create_or_update_task_recipe 必须提供 recipe_id 或 recipe 二选一。"
                "复制数据库菜谱传 recipe_id；用户明确同意现写后才传完整 recipe。"
            )
        if recipe_id is not None and recipe is not None:
            raise ValueError("recipe_id 和 recipe 不能同时提供。请选择复制数据库菜谱，或创建一份现写菜谱。")
        if recipe_id is not None:
            result = task_service.overwrite_recipe_from_catalog(
                task_id=current_turn.current_task_id,
                recipe_id=recipe_id,
            )
            current_turn.current_task_source_recipe_id = recipe_id
            current_turn.current_task_snapshot = result["recipe_snapshot"]
            current_turn.response_recipe_name = result["recipe_snapshot"].name
            _log_tool_event("create_or_update_task_recipe", f"from_catalog recipe_id={recipe_id}")
            return f"已把数据库菜谱 #{recipe_id} 复制到当前任务中。"
        if recipe is None or not recipe.ingredients or not recipe.steps:
            raise ValueError("现写菜谱必须包含至少 1 项食材 ingredients 和至少 1 个步骤 steps。")
        result = task_service.overwrite_recipe_from_generated(
            task_id=current_turn.current_task_id,
            recipe_payload=recipe.model_dump(mode="json") if recipe else {},
        )
        current_turn.current_task_source_recipe_id = None
        current_turn.current_task_snapshot = result["recipe_snapshot"]
        current_turn.response_recipe_name = result["recipe_snapshot"].name
        _log_tool_event("create_or_update_task_recipe", f"generated recipe_name={result['recipe_snapshot'].name}")
        return f"已把当前任务菜谱更新为「{result['recipe_snapshot'].name}」。"

    @tool("update_task_recipe_for_planning", args_schema=PlanningRecipePatchInput)
    def update_task_recipe_for_planning(
        ingredients: list[IngredientPatchInput] | None = None,
        steps: list[StepPatchInput] | None = None,
        name: str | None = None,
        description: str | None = None,
        difficulty: str | None = None,
        estimated_minutes: int | None = None,
        servings: int | None = None,
        tags: dict[str, list[str]] | None = None,
        tips: str | None = None,
        *,
        runtime: ToolRuntime,
    ) -> str:
        """
        在推荐阶段局部修改当前任务菜谱快照。

        用于用户已选定或已同意现写后的菜谱微调，例如调整份量、补一个食材、
        改步骤措辞。它不会创建新任务，也不要作为搜索失败后的自动现编兜底。
        """
        current_turn = _require_task(runtime)
        _ensure_stage(current_turn, ConversationStage.RECOMMENDING)
        if current_turn.current_task_snapshot is None:
            raise ValueError("当前任务还没有菜谱，无法局部更新。请先复制数据库菜谱，或在用户同意后现写一份。")
        patch_payload = build_planning_patch_payload(
            PlanningRecipePatchInput(
                ingredients=ingredients or [],
                steps=steps or [],
                name=name,
                description=description,
                difficulty=difficulty,
                estimated_minutes=estimated_minutes,
                servings=servings,
                tags=tags,
                tips=tips,
            )
        )
        if not patch_payload:
            raise ValueError(
                "没有可更新的推荐阶段菜谱字段。请传 name、servings、ingredients、steps、tips 等需要修改的字段。"
            )
        result = task_service.patch_recipe(
            task_id=current_turn.current_task_id,
            patch=patch_payload,
            mode="planning",
        )
        current_turn.current_task_snapshot = result["recipe_snapshot"]
        current_turn.current_task_source_recipe_id = result.get("source_recipe_id")
        current_turn.response_recipe_name = result["recipe_snapshot"].name
        _log_tool_event("update_task_recipe_for_planning", f"fields={sorted(patch_payload)}")
        return f"已局部更新当前任务菜谱「{result['recipe_snapshot'].name}」。"

    @tool("show_recipe_detail_card", args_schema=RecipeDetailDisplayInput)
    def show_recipe_detail_card(recipe_id: int | None = None, *, runtime: ToolRuntime) -> str:
        """展示菜谱详情卡。可传 recipe_id 查看数据库菜谱，留空则展示当前任务里的菜谱。"""
        current_turn = _turn(runtime)
        if recipe_id is not None:
            _ensure_stage(current_turn, ConversationStage.IDLE, ConversationStage.RECOMMENDING)
            lookup = recipe_catalog_service.get_recipe_by_id(recipe_id, include=["recipe", "tags", "ingredients", "steps"])
            snapshot = build_task_recipe_snapshot_from_catalog(lookup)
            current_turn.response_card_type = "recipe-detail"
            current_turn.response_card = build_recipe_detail_card(
                snapshot,
                source_recipe_id=recipe_id,
                include_try_action=True,
            ).model_dump(mode="json")
            _log_tool_event("show_recipe_detail_card", f"catalog recipe_id={recipe_id}")
            return f"已准备好菜谱 #{recipe_id} 的详情卡。"
        _ensure_stage(current_turn, ConversationStage.RECOMMENDING)
        if current_turn.current_task_snapshot is None:
            raise ValueError("当前任务还没有菜谱，无法展示详情卡。")
        current_turn.response_card_type = "recipe-detail"
        current_turn.response_card = build_recipe_detail_card(
            current_turn.current_task_snapshot,
            source_recipe_id=current_turn.current_task_source_recipe_id,
            include_try_action=current_turn.current_task_source_recipe_id is not None,
        ).model_dump(mode="json")
        _log_tool_event("show_recipe_detail_card", f"task recipe_name={current_turn.current_task_snapshot.name}")
        return f"已准备好「{current_turn.current_task_snapshot.name}」的详情卡。"

    @tool("recognize_image_ingredients", args_schema=ImageRecognitionInput)
    def recognize_image_ingredients(
        image_url: str,
        user_hint: str | None = None,
        *,
        runtime: ToolRuntime,
    ) -> str:
        """识别图片中的食材。推荐阶段可用于找菜；备料阶段可辅助判断食材准备状态。"""
        current_turn = _turn(runtime)
        _ensure_stage(current_turn, ConversationStage.RECOMMENDING, ConversationStage.PREPARING)
        _log_tool_event("recognize_image_ingredients", f"image_url={image_url!r}, user_hint={user_hint!r}")
        result = vision_service.detect_ingredients_from_image_url(
            image_url=image_url,
            user_hint=user_hint,
        )
        names = [item.name for item in result.ingredients]
        _log_tool_event("recognize_image_ingredients", f"detected={names}")
        return f"识别到这些食材：{', '.join(names) if names else '暂未识别到明确食材'}。"

    @tool("advance_to_preparation")
    def advance_to_preparation(runtime: ToolRuntime) -> str:
        """把当前任务从推荐中推进到备料中。没有输入参数。"""
        current_turn = _require_task(runtime)
        _ensure_stage(current_turn, ConversationStage.RECOMMENDING)
        result = task_service.transition_to_preparation(current_turn.conversation_id)
        current_turn.conversation_stage = ConversationStage.PREPARING
        current_turn.current_task_stage = ConversationStage.PREPARING
        current_turn.current_task_snapshot = result["recipe_snapshot"]
        current_turn.response_recipe_name = result["recipe_snapshot"].name if result["recipe_snapshot"] else None
        _log_tool_event("advance_to_preparation", f"recipe_name={current_turn.response_recipe_name}")
        return "已进入备料阶段。"

    @tool("cancel_recommendation_task")
    def cancel_recommendation_task(runtime: ToolRuntime) -> str:
        """取消推荐中的任务，并且不写入历史任务。"""
        current_turn = _require_task(runtime)
        _ensure_stage(current_turn, ConversationStage.RECOMMENDING)
        task_service.cancel_task(current_turn.conversation_id, record_in_history=False)
        current_turn.conversation_stage = ConversationStage.IDLE
        current_turn.current_task_id = None
        current_turn.current_task_stage = None
        current_turn.current_task_snapshot = None
        current_turn.current_task_source_recipe_id = None
        current_turn.response_recipe_name = None
        _log_tool_event("cancel_recommendation_task", "cancelled_without_history")
        return "当前任务已取消，并回到无任务阶段。"

    @tool("update_task_recipe_for_preparation", args_schema=TaskRecipePatchInput)
    def update_task_recipe_for_preparation(
        ingredients: list[IngredientPatchInput] | None = None,
        steps: list[StepPatchInput] | None = None,
        *,
        runtime: ToolRuntime,
    ) -> str:
        """
        在备料阶段更新当前任务菜谱快照。

        主要用于把食材标为 ready/pending/skipped 或补充食材备注。用 id 或
        ingredient_name 定位食材；如果只是展示清单，请调用 show_pantry_card。
        """
        current_turn = _require_task(runtime)
        _ensure_stage(current_turn, ConversationStage.PREPARING)
        patch_payload = build_task_patch_payload(
            ingredients=ingredients,
            steps=steps,
        )
        if not patch_payload:
            raise ValueError(
                "没有可更新的备料字段。请传 ingredients 或 steps；"
                "更新食材时至少提供 id 或 ingredient_name，并设置 status/note 等要修改的字段。"
            )
        result = task_service.patch_recipe(
            task_id=current_turn.current_task_id,
            patch=patch_payload,
            mode="shopping",
        )
        next_snapshot = result["recipe_snapshot"]
        if not has_ingredient_status_updates(ingredients):
            next_snapshot = apply_client_card_state_overlay(
                next_snapshot,
                {"pantry_status": current_turn.client_card_state.get("pantry_status")}
                if current_turn.client_card_state.get("pantry_status")
                else {},
                stage=ConversationStage.PREPARING,
            ) or next_snapshot
        current_turn.current_task_snapshot = next_snapshot
        current_turn.response_recipe_name = result["recipe_snapshot"].name
        _log_tool_event(
            "update_task_recipe_for_preparation",
            f"ingredients={len(patch_payload.get('ingredients', []))}, steps={len(patch_payload.get('steps', []))}",
        )
        return "备料相关状态已更新。"

    @tool("show_pantry_card")
    def show_pantry_card(runtime: ToolRuntime) -> str:
        """展示当前任务的备菜清单卡。没有输入参数。"""
        current_turn = _require_task(runtime)
        _ensure_stage(current_turn, ConversationStage.PREPARING)
        if current_turn.current_task_snapshot is None:
            raise ValueError("当前任务还没有菜谱。")
        current_turn.response_card_type = "pantry-status"
        current_turn.response_card = build_pantry_status_card(current_turn.current_task_snapshot).model_dump(mode="json")
        _log_tool_event("show_pantry_card", f"recipe_name={current_turn.current_task_snapshot.name}")
        return "已准备好备菜清单卡。"

    @tool("advance_to_cooking")
    def advance_to_cooking(runtime: ToolRuntime) -> str:
        """把当前任务从备料中推进到烹饪中。没有输入参数。"""
        current_turn = _require_task(runtime)
        _ensure_stage(current_turn, ConversationStage.PREPARING)
        result = task_service.transition_to_cooking(current_turn.conversation_id)
        current_turn.conversation_stage = ConversationStage.COOKING
        current_turn.current_task_stage = ConversationStage.COOKING
        current_turn.current_task_snapshot = result["recipe_snapshot"]
        current_turn.response_recipe_name = result["recipe_snapshot"].name if result["recipe_snapshot"] else None
        _log_tool_event("advance_to_cooking", f"recipe_name={current_turn.response_recipe_name}")
        return "已进入烹饪阶段。"

    @tool("rollback_to_recommendation")
    def rollback_to_recommendation(runtime: ToolRuntime) -> str:
        """把当前任务从备料阶段回滚到推荐阶段。没有输入参数。"""
        current_turn = _require_task(runtime)
        _ensure_stage(current_turn, ConversationStage.PREPARING)
        result = task_service.rollback_to_recommendation(current_turn.conversation_id)
        current_turn.conversation_stage = ConversationStage.RECOMMENDING
        current_turn.current_task_stage = ConversationStage.RECOMMENDING
        current_turn.current_task_snapshot = result["recipe_snapshot"]
        current_turn.response_recipe_name = result["recipe_snapshot"].name if result["recipe_snapshot"] else None
        _log_tool_event("rollback_to_recommendation", f"recipe_name={current_turn.response_recipe_name}")
        return "已回到推荐阶段。"

    @tool("cancel_preparation_task")
    def cancel_preparation_task(runtime: ToolRuntime) -> str:
        """取消备料中的任务，并写入历史任务。"""
        current_turn = _require_task(runtime)
        _ensure_stage(current_turn, ConversationStage.PREPARING)
        task_service.cancel_task(current_turn.conversation_id, record_in_history=True)
        current_turn.conversation_stage = ConversationStage.IDLE
        current_turn.current_task_id = None
        current_turn.current_task_stage = None
        current_turn.current_task_snapshot = None
        current_turn.current_task_source_recipe_id = None
        current_turn.response_recipe_name = None
        _log_tool_event("cancel_preparation_task", "cancelled_with_history")
        return "当前任务已取消，并回到无任务阶段。"

    @tool("update_task_recipe_for_cooking", args_schema=TaskRecipePatchInput)
    def update_task_recipe_for_cooking(
        ingredients: list[IngredientPatchInput] | None = None,
        steps: list[StepPatchInput] | None = None,
        *,
        runtime: ToolRuntime,
    ) -> str:
        """
        在烹饪阶段更新当前任务菜谱快照。

        只能用于步骤推进、步骤备注或步骤说明微调。用 id 或 step_no 定位步骤；
        status 只能是 pending/current/done。烹饪阶段不要修改食材。
        """
        current_turn = _require_task(runtime)
        _ensure_stage(current_turn, ConversationStage.COOKING)
        patch_payload = build_task_patch_payload(
            ingredients=ingredients,
            steps=steps,
        )
        if not patch_payload:
            raise ValueError(
                "没有可更新的烹饪字段。请传 steps；"
                "更新步骤时至少提供 id 或 step_no，并设置 status/note/instruction 等要修改的字段。"
            )
        result = task_service.patch_recipe(
            task_id=current_turn.current_task_id,
            patch=patch_payload,
            mode="cooking",
        )
        next_snapshot = result["recipe_snapshot"]
        if not has_step_status_updates(steps):
            next_snapshot = apply_client_card_state_overlay(
                next_snapshot,
                {"cooking_guide": current_turn.client_card_state.get("cooking_guide")}
                if current_turn.client_card_state.get("cooking_guide")
                else {},
                stage=ConversationStage.COOKING,
            ) or next_snapshot
        current_turn.current_task_snapshot = next_snapshot
        current_turn.response_recipe_name = result["recipe_snapshot"].name
        _log_tool_event(
            "update_task_recipe_for_cooking",
            f"ingredients={len(patch_payload.get('ingredients', []))}, steps={len(patch_payload.get('steps', []))}",
        )
        return "烹饪步骤已更新。"

    @tool("show_cooking_card")
    def show_cooking_card(runtime: ToolRuntime) -> str:
        """展示当前任务的烹饪步骤卡。没有输入参数。"""
        current_turn = _require_task(runtime)
        _ensure_stage(current_turn, ConversationStage.COOKING)
        if current_turn.current_task_snapshot is None:
            raise ValueError("当前任务还没有菜谱。")
        current_turn.response_card_type = "cooking-guide"
        current_turn.response_card = build_cooking_guide_card(current_turn.current_task_snapshot).model_dump(mode="json")
        _log_tool_event("show_cooking_card", f"recipe_name={current_turn.current_task_snapshot.name}")
        return "已准备好烹饪步骤卡。"

    @tool("complete_cooking_task")
    def complete_cooking_task(runtime: ToolRuntime) -> str:
        """完成当前烹饪任务，并记录到历史任务。"""
        current_turn = _require_task(runtime)
        _ensure_stage(current_turn, ConversationStage.COOKING)
        task_service.complete_task(current_turn.conversation_id)
        current_turn.conversation_stage = ConversationStage.IDLE
        current_turn.current_task_id = None
        current_turn.current_task_stage = None
        current_turn.current_task_snapshot = None
        current_turn.current_task_source_recipe_id = None
        current_turn.response_recipe_name = None
        _log_tool_event("complete_cooking_task", "completed")
        return "本次烹饪任务已完成。"

    @tool("rollback_to_preparation")
    def rollback_to_preparation(runtime: ToolRuntime) -> str:
        """把当前任务从烹饪阶段回滚到备料阶段。没有输入参数。"""
        current_turn = _require_task(runtime)
        _ensure_stage(current_turn, ConversationStage.COOKING)
        result = task_service.rollback_to_preparation(current_turn.conversation_id)
        current_turn.conversation_stage = ConversationStage.PREPARING
        current_turn.current_task_stage = ConversationStage.PREPARING
        current_turn.current_task_snapshot = result["recipe_snapshot"]
        current_turn.response_recipe_name = result["recipe_snapshot"].name if result["recipe_snapshot"] else None
        _log_tool_event("rollback_to_preparation", f"recipe_name={current_turn.response_recipe_name}")
        return "已回到备料阶段。"

    @tool("cancel_cooking_task")
    def cancel_cooking_task(runtime: ToolRuntime) -> str:
        """取消烹饪中的任务，并写入历史任务。"""
        current_turn = _require_task(runtime)
        _ensure_stage(current_turn, ConversationStage.COOKING)
        task_service.cancel_task(current_turn.conversation_id, record_in_history=True)
        current_turn.conversation_stage = ConversationStage.IDLE
        current_turn.current_task_id = None
        current_turn.current_task_stage = None
        current_turn.current_task_snapshot = None
        current_turn.current_task_source_recipe_id = None
        current_turn.response_recipe_name = None
        _log_tool_event("cancel_cooking_task", "cancelled_with_history")
        return "当前任务已取消，并回到无任务阶段。"

    universal_tools: list[BaseTool] = [get_user_memory, update_user_memory]
    if turn.active_stage == ConversationStage.IDLE:
        workflow_tools = [
            start_recommendation_task,
            search_recipes,
            recommend_recipes,
            create_or_update_task_recipe,
        ]
    elif turn.active_stage == ConversationStage.RECOMMENDING:
        workflow_tools = [
            search_recipes,
            recommend_recipes,
            create_or_update_task_recipe,
            update_task_recipe_for_planning,
            show_recipe_detail_card,
            recognize_image_ingredients,
            advance_to_preparation,
            cancel_recommendation_task,
        ]
    elif turn.active_stage == ConversationStage.PREPARING:
        workflow_tools = [
            update_task_recipe_for_preparation,
            show_pantry_card,
            recognize_image_ingredients,
            advance_to_cooking,
            rollback_to_recommendation,
            cancel_preparation_task,
        ]
    else:
        workflow_tools = [
            update_task_recipe_for_cooking,
            show_cooking_card,
            complete_cooking_task,
            rollback_to_preparation,
            cancel_cooking_task,
        ]
    return universal_tools + workflow_tools
