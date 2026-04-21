from __future__ import annotations

import logging
import re


logger = logging.getLogger(__name__)


def handle_agent_tool_error(exc: Exception) -> str:
    logger.exception("[agent-tool] recoverable error: %s", exc)
    detail = str(exc).strip() or exc.__class__.__name__
    tool_match = re.search(r"tool '([^']+)'", detail)
    tool_name = tool_match.group(1) if tool_match else ""
    guidance = {
        "search_recipes": (
            "search_recipes 只搜索数据库，不会现写菜谱。用户指定一道菜时，"
            "传 query=完整菜名原文，并尽量传 ingredients=从菜名中明确拆出的食材；"
            "如果返回未找到，请告知用户未收录，并询问是否需要现写。"
        ),
        "recommend_recipes": (
            "recommend_recipes 用于开放式推荐。用户点名某一道菜时，优先改用 search_recipes；"
            "不要把没有命中的指定菜名改成默认推荐。"
        ),
        "create_or_update_task_recipe": (
            "create_or_update_task_recipe 只能二选一传参：复制数据库菜谱时传 recipe_id；"
            "用户明确同意现写时传完整 recipe。recipe 至少包含 name、ingredients、steps；"
            "ingredients 需要 ingredient_name 和 amount_text，steps 需要 step_no 和 instruction。"
        ),
        "update_task_recipe_for_planning": (
            "update_task_recipe_for_planning 只能在推荐阶段使用，用于局部修改当前任务菜谱快照；"
            "它不会搜索数据库，也不会创建新任务。若没有当前任务菜谱，请先复制数据库菜谱或在用户同意后现写。"
        ),
        "update_task_recipe_for_preparation": (
            "update_task_recipe_for_preparation 只能在备料阶段使用，主要更新 ingredients 的 status/note，"
            "用 id 或 ingredient_name 定位食材；status 只能是 pending、ready、skipped。"
        ),
        "update_task_recipe_for_cooking": (
            "update_task_recipe_for_cooking 只能在烹饪阶段使用，主要更新 steps 的 status/note，"
            "用 id 或 step_no 定位步骤；status 只能是 pending、current、done。"
        ),
        "recognize_image_ingredients": (
            "recognize_image_ingredients 只能在推荐中或备料中使用。推荐中可用识别出的食材做搜索/推荐；"
            "备料中可结合图片判断哪些食材已准备好，再调用备料更新工具写入状态。"
        ),
    }.get(tool_name)
    if guidance is None:
        guidance = "请根据错误信息调整参数、阶段或调用顺序后再试；不要忽略工具约束。"
    return f"工具调用失败：{detail}\n修正建议：{guidance}"
