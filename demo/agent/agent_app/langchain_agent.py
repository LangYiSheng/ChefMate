from __future__ import annotations

import ast
import re
from collections.abc import Iterator

from agent_app.config import AppConfig
from agent_app.prompts import SYSTEM_PROMPT
from agent_app.tools import ChefMateToolkit
from agent_app.ui_schema import TurnResult

try:
    from langchain.agents import create_agent
    from langchain.tools import ToolRuntime
    from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
    from langchain_core.tools import tool
    from langchain_openai import ChatOpenAI

    LANGCHAIN_IMPORT_OK = True
except ImportError:
    LANGCHAIN_IMPORT_OK = False
    SystemMessage = None


class LangChainChefMateAgent:
    def __init__(self, toolkit: ChefMateToolkit, config: AppConfig):
        self.toolkit = toolkit
        self.config = config
        self.chat_history = []
        self.agent = None
        self._build_agent()

    def _build_agent(self) -> None:
        if not LANGCHAIN_IMPORT_OK:
            raise RuntimeError("当前环境未安装 LangChain 依赖，请先执行 `pip install -e .`。")
        if not self.config.openai_api_key:
            raise RuntimeError("未检测到 `OPENAI_API_KEY`，请先配置模型访问凭证。")

        def bind_runtime(runtime: ToolRuntime | None) -> None:
            writer = runtime.stream_writer if runtime else None
            self.toolkit.set_stream_writer(writer)

        # 这里把业务能力都包装成工具，方便 LangChain 按需调用。
        @tool
        def recommend_dishes(user_request: str, *, runtime: ToolRuntime) -> str:
            """根据用户需求推荐 1 到 3 道合适的家常菜。"""
            bind_runtime(runtime)
            try:
                return self.toolkit.recommend_dishes(user_request)
            finally:
                bind_runtime(None)

        @tool
        def get_recipe_requirements(recipe_name: str, *, runtime: ToolRuntime) -> str:
            """给出目标菜品的所需食材和准备事项。"""
            bind_runtime(runtime)
            try:
                return self.toolkit.get_recipe_requirements(recipe_name)
            finally:
                bind_runtime(None)

        @tool
        def check_ingredients(user_input: str, *, runtime: ToolRuntime) -> str:
            """根据用户提供的现有食材判断是否具备开做条件。"""
            bind_runtime(runtime)
            try:
                ingredients = self.toolkit.extract_ingredients(user_input)
                return self.toolkit.check_ingredients(ingredients)
            finally:
                bind_runtime(None)

        @tool
        def suggest_missing_items(*, runtime: ToolRuntime) -> str:
            """列出当前菜品还缺少哪些关键食材，以及补买建议。"""
            bind_runtime(runtime)
            try:
                return self.toolkit.suggest_missing_items()
            finally:
                bind_runtime(None)

        @tool
        def suggest_alternative_dishes(user_input: str, *, runtime: ToolRuntime) -> str:
            """在当前食材不够时，推荐更容易完成的替代菜品。"""
            bind_runtime(runtime)
            try:
                ingredients = self.toolkit.extract_ingredients(user_input)
                return self.toolkit.suggest_alternative_dishes(ingredients)
            finally:
                bind_runtime(None)

        @tool
        def start_cooking(*, runtime: ToolRuntime) -> str:
            """进入当前菜品的分步骤烹饪指导。"""
            bind_runtime(runtime)
            try:
                return self.toolkit.start_cooking()
            finally:
                bind_runtime(None)

        @tool
        def next_cooking_step(*, runtime: ToolRuntime) -> str:
            """返回当前菜品的下一步操作。"""
            bind_runtime(runtime)
            try:
                return self.toolkit.next_cooking_step()
            finally:
                bind_runtime(None)

        @tool
        def answer_cooking_question(question: str, *, runtime: ToolRuntime) -> str:
            """结合当前烹饪阶段回答用户追问。"""
            bind_runtime(runtime)
            try:
                return self.toolkit.answer_cooking_question(question)
            finally:
                bind_runtime(None)

        @tool
        def update_user_profile(user_input: str, *, runtime: ToolRuntime) -> str:
            """根据用户输入更新长期偏好信息。"""
            bind_runtime(runtime)
            try:
                return self.toolkit.update_profile_from_text(user_input) or "未识别到需要更新的偏好。"
            finally:
                bind_runtime(None)

        # 统一在这里组织模型参数，后面如果要换服务商会更好改。
        llm_kwargs = {
            "api_key": self.config.openai_api_key,
            "model": self.config.model_name,
            "temperature": 0.2,
        }
        if self.config.base_url:
            llm_kwargs["base_url"] = self.config.base_url

        llm = ChatOpenAI(**llm_kwargs)
        self.agent = create_agent(
            model=llm,
            tools=[
                recommend_dishes,
                get_recipe_requirements,
                check_ingredients,
                suggest_missing_items,
                suggest_alternative_dishes,
                start_cooking,
                next_cooking_step,
                answer_cooking_question,
                update_user_profile,
            ],
            system_prompt=SYSTEM_PROMPT,
        )

    def extract_text_chunk(self, token) -> str:
        content_blocks = getattr(token, "content_blocks", None)
        if content_blocks:
            text_parts: list[str] = []
            for block in content_blocks:
                if isinstance(block, dict) and block.get("type") == "text":
                    text_parts.append(block.get("text", ""))
            return "".join(text_parts)

        content = getattr(token, "content", "")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            text_parts = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    text_parts.append(item.get("text", ""))
            return "".join(text_parts)
        return ""

    def format_tool_args(self, args) -> str:
        if not isinstance(args, dict) or not args:
            return ""
        parts = [f"{key}={value}" for key, value in args.items()]
        preview = ", ".join(parts)
        return preview[:80] + ("..." if len(preview) > 80 else "")

    def safe_eval_ordinal_expression(self, expression: str) -> int | None:
        expression = expression.strip()
        if not expression or not re.fullmatch(r"[0-9+\-*/()\s]+", expression):
            return None

        def eval_node(node) -> int:
            if isinstance(node, ast.Expression):
                return eval_node(node.body)
            if isinstance(node, ast.Constant) and isinstance(node.value, int):
                return node.value
            if isinstance(node, ast.BinOp):
                left = eval_node(node.left)
                right = eval_node(node.right)
                if isinstance(node.op, ast.Add):
                    return left + right
                if isinstance(node.op, ast.Sub):
                    return left - right
                if isinstance(node.op, ast.Mult):
                    return left * right
                if isinstance(node.op, ast.FloorDiv):
                    return left // right
                if isinstance(node.op, ast.Div):
                    return left // right
                raise ValueError("unsupported operator")
            if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
                operand = eval_node(node.operand)
                return operand if isinstance(node.op, ast.UAdd) else -operand
            raise ValueError("unsupported expression")

        try:
            parsed = ast.parse(expression, mode="eval")
            value = eval_node(parsed)
        except Exception:
            return None

        return value if isinstance(value, int) else None

    def extract_ordinal_index(self, message: str) -> int | None:
        expr_match = re.search(r"第\s*([0-9+\-*/()\s]+)\s*[个道项]", message)
        if expr_match:
            evaluated = self.safe_eval_ordinal_expression(expr_match.group(1))
            if evaluated is not None:
                return evaluated

        chinese_ordinals = {
            "第一个": 1,
            "第二个": 2,
            "第三个": 3,
            "第一个菜": 1,
            "第二个菜": 2,
            "第三个菜": 3,
            "第一道": 1,
            "第二道": 2,
            "第三道": 3,
        }
        for text, index in chinese_ordinals.items():
            if text in message:
                return index
        return None

    def build_reference_resolution_message(self, message: str) -> SystemMessage | None:
        if SystemMessage is None:
            return None
        if not self.toolkit.state.last_recommendations:
            return None

        resolved_index = self.extract_ordinal_index(message)
        if resolved_index is None:
            return None
        if resolved_index < 1 or resolved_index > len(self.toolkit.state.last_recommendations):
            return None

        recipe_name = self.toolkit.state.last_recommendations[resolved_index - 1]
        return SystemMessage(
            content=(
                f"引用解析结果：用户本轮提到的序号表达式解析后等于第 {resolved_index} 个，"
                f"它指的是刚才推荐卡片中的“{recipe_name}”。"
                "请在不改写用户原始输入的前提下，按这道菜继续推进备料或烹饪流程。"
            )
        )

    def build_card_context_message(self) -> SystemMessage | None:
        if SystemMessage is None:
            return None
        card_contexts = self.toolkit.state.current_card_contexts
        if not card_contexts:
            return None

        lines = [
            "以下是当前已经展示给用户的卡片上下文，用户后续可能会用“第2个”“刚才那个”来指代它们：",
        ]
        for index, summary in enumerate(card_contexts, start=1):
            lines.append(f"{index}. {summary}")
        if self.toolkit.state.target_recipe:
            lines.append(f"当前目标菜品：{self.toolkit.state.target_recipe}")
        return SystemMessage(content="\n".join(lines))

    def iter_update_events(self, chunk: dict) -> Iterator[dict]:
        for node_data in chunk.values():
            messages = node_data.get("messages", [])
            if not messages:
                continue
            last_message = messages[-1]
            if isinstance(last_message, AIMessage):
                for tool_call in getattr(last_message, "tool_calls", []):
                    yield {
                        "type": "tool_call",
                        "tool_name": tool_call.get("name", "unknown"),
                        "args_preview": self.format_tool_args(tool_call.get("args")),
                    }
            elif isinstance(last_message, ToolMessage):
                yield {
                    "type": "tool_result",
                    "tool_name": getattr(last_message, "name", None) or "tool",
                }

    def stream(self, message: str) -> Iterator[dict]:
        if self.agent is None:
            raise RuntimeError("ChefMate 尚未完成初始化。")

        try:
            # LangChain 模式下保留历史消息，让模型知道当前处在哪个做饭阶段。
            self.toolkit.begin_turn()
            messages = [*self.chat_history]
            card_context_message = self.build_card_context_message()
            if card_context_message is not None:
                messages.append(card_context_message)
            reference_resolution_message = self.build_reference_resolution_message(message)
            if reference_resolution_message is not None:
                messages.append(reference_resolution_message)
            messages.append(HumanMessage(content=message))
            final_text_parts: list[str] = []
            text_started = False

            for chunk in self.agent.stream(
                {"messages": messages},
                stream_mode=["custom", "updates", "messages"],
                version="v2",
            ):
                chunk_type = chunk.get("type")
                chunk_data = chunk.get("data")

                if chunk_type == "custom":
                    if isinstance(chunk_data, dict):
                        yield chunk_data
                    continue

                if chunk_type == "updates":
                    if isinstance(chunk_data, dict):
                        yield from self.iter_update_events(chunk_data)
                    continue

                if chunk_type != "messages":
                    continue

                if not isinstance(chunk_data, tuple) or len(chunk_data) != 2:
                    continue

                token, metadata = chunk_data
                if metadata.get("langgraph_node") != "model":
                    continue

                text_chunk = self.extract_text_chunk(token)
                if not text_chunk:
                    continue

                if not text_started:
                    yield {"type": "text_start"}
                    text_started = True
                final_text_parts.append(text_chunk)
                yield {"type": "text_delta", "text": text_chunk}

            output = "".join(final_text_parts).strip()
            self.chat_history.append(HumanMessage(content=message))
            self.chat_history.append(AIMessage(content=output))
            yield {
                "type": "turn_end",
                "turn": self.toolkit.build_turn_result(output),
                "model_text": output,
            }
        except Exception as exc:  # pragma: no cover
            # 线上调用失败时直接抛错，让调用方明确知道问题来自模型侧。
            raise RuntimeError(f"模型调用失败：{exc}") from exc

    def handle(self, message: str) -> TurnResult:
        final_turn: TurnResult | None = None
        for event in self.stream(message):
            if event.get("type") == "turn_end":
                final_turn = event["turn"]
        if final_turn is None:
            raise RuntimeError("本轮对话未生成可用结果。")
        return final_turn
