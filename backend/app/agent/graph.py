from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.prebuilt import create_react_agent
from langgraph.prebuilt.tool_node import ToolNode

from app.agent.prompts import build_stage_prompt
from app.agent.runtime import AgentTurnContext
from app.agent.tools import build_stage_tools, handle_agent_tool_error
from app.config import settings
from app.infra.llm.clients import build_langchain_chat_model


def build_agent_graph(turn: AgentTurnContext):
    model = build_langchain_chat_model(temperature=settings.llm_temperature)
    tools = ToolNode(
        build_stage_tools(turn),
        handle_tool_errors=handle_agent_tool_error,
    )

    def prompt(state):
        return [
            SystemMessage(content=build_stage_prompt(turn)),
            *state["messages"],
        ]

    return create_react_agent(
        model,
        tools=tools,
        prompt=prompt,
        name=f"chefmate_{turn.active_stage.value}_agent",
    )


def build_initial_messages(turn: AgentTurnContext) -> dict:
    user_content = turn.latest_user_content.strip()
    if not user_content:
        if turn.latest_user_action is not None:
            user_content = f"用户触发动作：{turn.latest_user_action.action_type} {turn.latest_user_action.payload}"
        elif turn.latest_attachments:
            user_content = "用户上传了一张图片，请结合系统上下文决定是否需要识别其中食材。"
        else:
            user_content = "请根据系统上下文处理本轮请求。"
    return {"messages": [HumanMessage(content=user_content)]}
