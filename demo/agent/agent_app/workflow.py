from __future__ import annotations

from agent_app.models import SessionStage, SessionState


def stage_label(stage: SessionStage) -> str:
    labels = {
        SessionStage.DISCOVERY: "需求澄清",
        SessionStage.RECOMMENDATION: "菜品推荐",
        SessionStage.PREPARATION: "备料确认",
        SessionStage.COOKING: "烹饪指导",
        SessionStage.COMPLETE: "本轮完成",
    }
    return labels[stage]


def render_state_snapshot(state: SessionState) -> str:
    current_step = state.current_step_index + 1 if state.target_recipe else 0
    return "\n".join(
        [
            f"当前阶段：{stage_label(state.stage)}",
            f"目标菜品：{state.target_recipe or '未确定'}",
            f"已有食材：{', '.join(state.available_ingredients) if state.available_ingredients else '暂无'}",
            f"缺少食材：{', '.join(state.missing_ingredients) if state.missing_ingredients else '暂无'}",
            f"当前步骤：{current_step if state.stage == SessionStage.COOKING else '未开始'}",
        ]
    )
