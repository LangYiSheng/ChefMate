from app.core.semantic_models import ConversationStage, SemanticQuery, WorkflowCard, WorkflowResult
from app.skills.cooking import cooking_skill
from app.skills.preparation import preparation_skill
from app.skills.recommendation import recommendation_skill


class WorkflowOrchestrator:
    """
    当前先使用简化工作流骨架。
    后续这里会替换为 LangGraph StateGraph。
    """

    def route(self, task, user_input: str) -> WorkflowResult:
        semantic_query = SemanticQuery(raw_text=user_input)
        text = user_input.lower()

        if "图片" in user_input or "食材" in user_input:
            return WorkflowResult(
                next_stage=ConversationStage.RECOMMEND,
                semantic_query=semantic_query,
                user_facing_message="如果你要根据现有食材推荐菜品，请上传一张摆放好的食材图片，我会先识别食材列表，再继续推荐。",
                card=WorkflowCard(
                    card_type="vision_upload_hint",
                    payload={
                        "endpoint": "/api/vision/ingredients/detect",
                        "tip": "当前建议拍摄摆放出来的食材，不建议直接拍冰箱内部。",
                    },
                ),
            )

        if "做" in text or "吃" in text:
            recommendation = recommendation_skill.recommend_from_query(user_input)
            return WorkflowResult(
                next_stage=ConversationStage.RECOMMEND,
                semantic_query=semantic_query,
                user_facing_message="已生成候选菜品，请确认目标菜品。",
                card=WorkflowCard(card_type="recommendation", payload=recommendation),
            )

        if "开始" in user_input or "下一步" in user_input:
            cooking = cooking_skill.guide_placeholder()
            return WorkflowResult(
                next_stage=ConversationStage.COOKING,
                semantic_query=semantic_query,
                user_facing_message="已进入烹饪指导阶段。",
                card=WorkflowCard(card_type="cooking", payload=cooking),
            )

        preparation = preparation_skill.check_placeholder()
        return WorkflowResult(
            next_stage=ConversationStage.PREPARATION,
            semantic_query=semantic_query,
            user_facing_message="已进入备料检查阶段。",
            card=WorkflowCard(card_type="preparation", payload=preparation),
        )


workflow = WorkflowOrchestrator()
