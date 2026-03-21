from __future__ import annotations

import sys

from agent_app.cli_renderer import StreamConsoleRenderer
from agent_app.config import load_config
from agent_app.data_loader import load_recipes, load_sample_profile
from agent_app.langchain_agent import LangChainChefMateAgent
from agent_app.models import SessionState
from agent_app.tools import ChefMateToolkit
from agent_app.workflow import render_state_snapshot


HELP_TEXT = """
可用命令：
/help     查看帮助
/recipes  查看内置菜谱
/profile  查看当前用户画像
/status   查看当前会话状态
/reset    重置本轮对话
/exit     退出
""".strip()


def build_app() -> tuple[LangChainChefMateAgent, ChefMateToolkit]:
    # 启动时把配置、数据、用户画像和会话状态一次性组好。
    config = load_config()
    recipes = load_recipes()
    profile = load_sample_profile()
    state = SessionState()
    toolkit = ChefMateToolkit(recipes=recipes, profile=profile, state=state)
    agent = LangChainChefMateAgent(toolkit=toolkit, config=config)
    return agent, toolkit


def print_banner(agent: LangChainChefMateAgent) -> None:
    print("ChefMate CLI")
    print("一个基于 LangChain 的命令行烹饪助手。")
    print("开始示例")
    print("- 今晚应该吃点啥呢？")
    print("- 我这里有些鸡蛋，能做点什么？")
    print("- 番茄炒蛋怎么做？")
    print("输入 /help 查看可用命令。")


def main() -> None:
    try:
        agent, toolkit = build_app()
    except Exception as exc:
        print(f"ChefMate 启动失败：{exc}")
        sys.exit(1)

    print_banner(agent)

    while True:
        try:
            # CLI 模式下就保持最朴素的输入输出，方便演示和录屏。
            user_input = input("\n你> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nChefMate> 会话结束。")
            break

        if not user_input:
            continue

        # 斜杠命令专门处理查看状态、重置会话这类控制操作。
        if user_input == "/exit":
            print("ChefMate> 会话结束。")
            break
        if user_input == "/help":
            print(HELP_TEXT)
            continue
        if user_input == "/recipes":
            print("内置菜谱：")
            for name in toolkit.list_recipe_names():
                print(f"- {name}")
            continue
        if user_input == "/profile":
            print(toolkit.profile.summary())
            continue
        if user_input == "/status":
            print(render_state_snapshot(toolkit.state))
            continue
        if user_input == "/reset":
            toolkit.state.reset()
            print("ChefMate> 当前会话已重置。")
            continue

        # 普通输入交给 agent 决策，它会判断是推荐、备料还是做菜阶段。
        try:
            renderer = StreamConsoleRenderer()
            final_turn = None
            model_text_printed = False
            for event in agent.stream(user_input):
                if event.get("type") == "turn_end":
                    final_turn = event["turn"]
                    model_text_printed = bool(event.get("model_text"))
                    continue
                renderer.render_event(event)
        except Exception as exc:
            print(f"ChefMate> {exc}")
            continue

        if final_turn is None:
            print("ChefMate> 本轮没有生成可显示的结果。")
            continue

        renderer.finalize(final_turn, model_text_printed=model_text_printed)
        toolkit.state.chat_history.append((user_input, final_turn.plain_text()))
