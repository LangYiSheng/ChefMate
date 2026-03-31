from __future__ import annotations

import json

from app.agent.runtime import AgentTurnContext
from app.domain.enums import ConversationStage
from app.utils.time import shanghai_now


def build_stage_prompt(turn: AgentTurnContext) -> str:
    prompt_sections = [
        _build_system_section(turn),
        _build_memory_section(turn),
        _build_current_turn_section(turn),
    ]
    return "\n\n".join(section for section in prompt_sections if section.strip())


def _build_system_section(turn: AgentTurnContext) -> str:
    current_time_text = shanghai_now().strftime("%Y-%m-%d %H:%M:%S %Z")
    base_rules = [
        "你是 ChefMate，一个真实可用的中文智能烹饪助手，要温柔、自然、接地气。",
        f"当前时间是 {current_time_text}，在涉及今天、今晚、明天、用餐时段等表述时要结合这个时间理解。",
        "你是一个多阶段工作流智能体，一次用户回合里允许先切换阶段，再继续思考和调用新阶段工具，最后再统一回复用户。",
        "阶段流转主线是：无任务(idea) -> 推荐中(planning) -> 备料中(shopping) -> 烹饪中(cooking) -> 无任务(idea)。",
        "你必须使用工具读取和修改真实状态，不要编造用户偏好、任务状态、菜谱详情或图片识别结果。",
        "最终回复使用简洁的中文 Markdown，不要在正文里输出 JSON。",
        "如果需要让前端展示卡片，必须调用对应的展示工具；推荐卡片只会由推荐工具自动挂上。",
        "任务阶段推进必须依赖任务推进工具，不要在没有调用工具的情况下口头宣布阶段已经变化。",
        "如果工具返回错误或校验失败，要根据错误继续决策，不要忽略约束。",
        "如果某个工具刚刚导致阶段变化，不要立刻结束本轮；要根据新阶段重新判断目标，必要时继续调用下一阶段工具。",
        "如果用户一开口就是想找菜、推荐晚餐、看冰箱做什么，就应该在同一轮里完成进入推荐阶段和推荐动作，而不是只口头说会推荐。",
        "不要在同一批并行工具调用里同时做阶段切换和目标阶段展示；例如应先 advance_to_cooking，等工具结果返回后，再调用 show_cooking_card。",
        "在备料中和烹饪中，即使展示了卡片，你也必须用自然语言主动说明当前进度、关键细节、剩余事项和下一步建议，不能只丢卡片不解释。",
        "只有当任务推进工具真正成功后，才能向用户宣告阶段变化或任务完成；如果工具失败，必须如实说明当前状态，不得报喜不报忧。",
    ]
    stage_rules = {
        ConversationStage.IDLE: [
            "当前处于无任务阶段。优先满足闲聊需求，或在用户表达想做菜、想找菜、想看推荐时进入推荐中。",
            "当前阶段重点工具：start_recommendation_task。用户明确想要推荐时，可以先进入推荐中，再继续调用推荐相关工具。",
        ],
        ConversationStage.RECOMMENDING: [
            "当前处于推荐中阶段，核心目标是帮用户选定一道菜，或现场创建一道新菜。",
            "可使用推荐、图片识别、创建/覆盖任务菜谱、展示菜谱详情、推进到备料、取消任务等工具。",
            "当前阶段重点工具：recommend_recipes、create_or_update_task_recipe、show_recipe_detail_card、recognize_image_ingredients、advance_to_preparation、cancel_recommendation_task。",
            "如果用户只是想看看某道菜的详情，可以先展示菜谱详情卡，不一定立刻覆盖当前任务菜谱。",
            "如果当前没有任务菜谱，就不能推进到备料阶段。",
        ],
        ConversationStage.PREPARING: [
            "当前处于备料中阶段，核心目标是帮助用户把食材准备状态推进完整。",
            "优先根据用户描述更新食材状态、补充说明，必要时展示备菜清单卡。",
            "当前阶段重点工具：update_task_recipe_for_preparation、show_pantry_card、advance_to_cooking、rollback_to_recommendation、cancel_preparation_task。",
            "只有在必需食材都备齐后才能推进到烹饪阶段。",
            "如果用户改主意想换菜，可以回滚到推荐中或取消任务。",
            "当用户说“这些都备齐了”“可以开始做了”时，先更新食材状态，再推进到烹饪阶段；成功后要说明当前将从哪一步开始做。",
        ],
        ConversationStage.COOKING: [
            "当前处于烹饪中阶段，核心目标是一步步指导用户完成烹饪，同时回答烹饪问题。",
            "优先更新步骤状态、必要时展示烹饪步骤卡。",
            "当前阶段重点工具：update_task_recipe_for_cooking、show_cooking_card、complete_cooking_task、rollback_to_preparation、cancel_cooking_task。",
            "只有在步骤都完成后才能正常完成任务；如果中途放弃，可以取消任务。",
            "当用户说“做好了”“做完了”时，如果当前还有未完成步骤，先把真实完成的步骤状态更新正确，再尝试 complete_cooking_task；只有 complete_cooking_task 成功后，才能告诉用户这次烹饪已完成。",
        ],
    }[turn.active_stage]
    tag_catalog_text = ""
    if turn.active_stage == ConversationStage.RECOMMENDING and turn.tag_catalog:
        tag_catalog_text = "可用标签目录：\n" + json.dumps(turn.tag_catalog, ensure_ascii=False, indent=2)
    return "\n".join(base_rules + stage_rules + ([tag_catalog_text] if tag_catalog_text else []))


def _build_memory_section(turn: AgentTurnContext) -> str:
    sections: list[str] = []
    sections.append(
        "用户长期记忆：\n"
        + json.dumps(
            {
                "display_name": turn.user.display_name,
                "allow_auto_update": turn.user.allow_auto_update,
                "cooking_preference_text": turn.user.cooking_preference_text,
                "tag_selections": turn.user.tag_selections.model_dump(),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    if turn.recent_finished_tasks:
        sections.append(
            "用户最近历史任务：\n"
            + json.dumps(turn.recent_finished_tasks, ensure_ascii=False, indent=2)
        )
    if turn.conversation_summary:
        sections.append(f"当前对话的远程摘要：\n{turn.conversation_summary}")
    if turn.recent_messages:
        sections.append(
            "当前对话最近消息窗口：\n"
            + "\n".join(
                f"- {item['role']}: {item['content']}"
                for item in turn.recent_messages
                if item.get("content")
            )
        )
    if turn.current_task_snapshot is not None:
        sections.append(
            "当前任务菜谱快照：\n"
            + json.dumps(
                turn.current_task_snapshot.model_dump(mode="json"),
                ensure_ascii=False,
                indent=2,
            )
        )
        sections.append(_build_task_progress_section(turn))
    else:
        sections.append("当前没有活动中的任务菜谱。")
    return "\n\n".join(sections)


def _build_task_progress_section(turn: AgentTurnContext) -> str:
    snapshot = turn.current_task_snapshot
    if snapshot is None:
        return ""

    ready_ingredients = [item.ingredient_name for item in snapshot.ingredients if str(item.status) == "ready"]
    pending_ingredients = [item.ingredient_name for item in snapshot.ingredients if str(item.status) == "pending"]
    skipped_ingredients = [item.ingredient_name for item in snapshot.ingredients if str(item.status) == "skipped"]
    current_step = next((step for step in snapshot.steps if str(step.status) == "current"), None)
    done_steps = [step.step_no for step in snapshot.steps if str(step.status) == "done"]
    pending_steps = [step.step_no for step in snapshot.steps if str(step.status) == "pending"]

    progress = {
        "active_stage": turn.active_stage,
        "ready_ingredients": ready_ingredients,
        "pending_ingredients": pending_ingredients,
        "skipped_ingredients": skipped_ingredients,
        "current_step": {
            "step_no": current_step.step_no,
            "title": current_step.title,
            "instruction": current_step.instruction,
        } if current_step else None,
        "done_steps": done_steps,
        "pending_steps": pending_steps,
    }
    return "当前任务进度摘要：\n" + json.dumps(progress, ensure_ascii=False, indent=2)


def _build_current_turn_section(turn: AgentTurnContext) -> str:
    attachment_lines = []
    for attachment in turn.latest_attachments:
        attachment_lines.append(
            f"- {attachment.kind}: {attachment.name} ({attachment.file_url or attachment.preview_url})"
        )
    action_payload = turn.latest_user_action.model_dump(mode="json") if turn.latest_user_action else None
    current_turn = {
        "user_message": turn.latest_user_content,
        "user_action": action_payload,
        "attachments": attachment_lines,
        "current_stage": turn.active_stage,
    }
    return "本轮输入：\n" + json.dumps(current_turn, ensure_ascii=False, indent=2)
