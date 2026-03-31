from __future__ import annotations

from typing import Any

from app.utils.recipe_snapshot import load_task_recipe_snapshot
from test.case_schema import AgentEvalCase, Expectations, ResponseConstraints, TaskAssertions, TurnExpectations


def contains_in_order(actual: list[str], expected_sequence: list[str]) -> bool:
    if not expected_sequence:
        return True
    cursor = 0
    for item in actual:
        if item == expected_sequence[cursor]:
            cursor += 1
            if cursor >= len(expected_sequence):
                return True
    return False


def check_response_constraints(text: str, constraints: ResponseConstraints | None) -> list[str]:
    if constraints is None:
        return []
    failures: list[str] = []
    if constraints.contains_any and not any(token in text for token in constraints.contains_any):
        failures.append(f"回复未命中 contains_any：{constraints.contains_any}")
    for token in constraints.contains_all:
        if token not in text:
            failures.append(f"回复缺少关键词：{token}")
    for token in constraints.not_contains:
        if token in text:
            failures.append(f"回复出现禁止关键词：{token}")
    return failures


def check_task_assertions(task_row: dict[str, Any] | None, assertions: TaskAssertions | None) -> list[str]:
    if assertions is None:
        return []

    failures: list[str] = []
    if assertions.current_task_exists is not None:
        if assertions.current_task_exists and task_row is None:
            failures.append("期望存在当前任务，但实际没有。")
        if assertions.current_task_exists is False and task_row is not None:
            failures.append("期望没有当前任务，但实际仍存在。")

    if task_row is None:
        return failures

    if assertions.current_task_stage is not None and task_row.get("stage") != assertions.current_task_stage:
        failures.append(f"任务阶段不匹配：期望 {assertions.current_task_stage}，实际 {task_row.get('stage')}")

    if assertions.source_recipe_id_exists is True and task_row.get("source_recipe_id") is None:
        failures.append("期望 source_recipe_id 存在，但实际为空。")
    if assertions.source_recipe_id_exists is False and task_row.get("source_recipe_id") is not None:
        failures.append("期望 source_recipe_id 为空，但实际存在。")
    if assertions.source_recipe_id is not None and int(task_row.get("source_recipe_id") or 0) != assertions.source_recipe_id:
        failures.append(f"source_recipe_id 不匹配：期望 {assertions.source_recipe_id}，实际 {task_row.get('source_recipe_id')}")

    snapshot = load_task_recipe_snapshot(task_row.get("recipe_snapshot_json"))
    if snapshot is None:
        failures.append("任务缺少 recipe_snapshot_json。")
        return failures

    if assertions.recipe_name and snapshot.name != assertions.recipe_name:
        failures.append(f"菜谱名称不匹配：期望 {assertions.recipe_name}，实际 {snapshot.name}")

    for item in assertions.ingredient_status:
        target = None
        if item.id:
            target = next((entry for entry in snapshot.ingredients if entry.id == item.id), None)
        if target is None and item.ingredient_name:
            target = next((entry for entry in snapshot.ingredients if entry.ingredient_name == item.ingredient_name), None)
        if target is None:
            failures.append(f"找不到被断言的食材：{item.id or item.ingredient_name}")
            continue
        if item.status and str(target.status) != item.status:
            failures.append(f"食材状态不匹配：{target.ingredient_name} 期望 {item.status}，实际 {target.status}")

    for item in assertions.step_status:
        target = None
        if item.id:
            target = next((entry for entry in snapshot.steps if entry.id == item.id), None)
        if target is None and item.step_no is not None:
            target = next((entry for entry in snapshot.steps if entry.step_no == item.step_no), None)
        if target is None:
            failures.append(f"找不到被断言的步骤：{item.id or item.step_no}")
            continue
        if item.status and str(target.status) != item.status:
            failures.append(f"步骤状态不匹配：step {target.step_no} 期望 {item.status}，实际 {target.status}")

    return failures


def evaluate_turn_expectations(turn_trace: dict[str, Any], expectations: TurnExpectations | None) -> list[str]:
    if expectations is None:
        return []

    failures: list[str] = []
    tools = turn_trace.get("tool_sequence", [])
    for tool_name in expectations.required_tools:
        if tool_name not in tools:
            failures.append(f"本轮缺少必需工具：{tool_name}")
    for tool_name in expectations.forbidden_tools:
        if tool_name in tools:
            failures.append(f"本轮命中禁止工具：{tool_name}")

    final_stage = turn_trace.get("conversation_stage_after_turn")
    if expectations.expected_stage_after_turn is not None and final_stage != expectations.expected_stage_after_turn:
        failures.append(f"本轮阶段不匹配：期望 {expectations.expected_stage_after_turn}，实际 {final_stage}")

    failures.extend(
        check_response_constraints(
            turn_trace.get("assistant_content", ""),
            expectations.expected_response_constraints,
        )
    )
    return failures


def evaluate_case_rules(case: AgentEvalCase, trace: dict[str, Any]) -> dict[str, Any]:
    failures: list[str] = []
    all_tools = [tool for turn in trace.get("turns", []) for tool in turn.get("tool_sequence", [])]
    final_turn = trace.get("turns", [])[-1] if trace.get("turns") else {}

    if case.expectations.max_turns is not None and len(trace.get("turns", [])) > case.expectations.max_turns:
        failures.append(f"超出最大轮数：{len(trace.get('turns', []))} > {case.expectations.max_turns}")

    for tool_name in case.expectations.required_tools:
        if tool_name not in all_tools:
            failures.append(f"缺少必需工具：{tool_name}")

    for tool_name in case.expectations.forbidden_tools:
        if tool_name in all_tools:
            failures.append(f"命中禁止工具：{tool_name}")

    for ordered_tools in case.expectations.tool_order_constraints:
        if not contains_in_order(all_tools, ordered_tools):
            failures.append(f"工具顺序不符合预期：{ordered_tools}")

    final_stage = trace.get("final_conversation", {}).get("stage")
    if case.expectations.expected_final_stage is not None and final_stage != case.expectations.expected_final_stage:
        failures.append(f"最终阶段不匹配：期望 {case.expectations.expected_final_stage}，实际 {final_stage}")

    failures.extend(
        check_task_assertions(
            trace.get("final_task"),
            case.expectations.expected_task_assertions,
        )
    )
    failures.extend(
        check_response_constraints(
            final_turn.get("assistant_content", ""),
            case.expectations.expected_response_constraints,
        )
    )

    for index, turn in enumerate(case.turns):
        failures.extend(
            f"Turn {index + 1}: {item}"
            for item in evaluate_turn_expectations(
                trace.get("turns", [])[index] if len(trace.get("turns", [])) > index else {},
                turn.expectations,
            )
        )

    unexpected_error = trace.get("unexpected_error")
    if unexpected_error:
        failures.append(f"出现未预期异常：{unexpected_error}")

    passed = not failures
    return {
        "passed": passed,
        "failures": failures,
        "metrics": {
            "required_tools_ok": not any("缺少必需工具" in item for item in failures),
            "forbidden_tools_ok": not any("禁止工具" in item for item in failures),
            "tool_order_ok": not any("工具顺序" in item for item in failures),
            "final_stage_ok": not any("最终阶段不匹配" in item for item in failures),
            "task_assertions_ok": not any("食材状态不匹配" in item or "步骤状态不匹配" in item or "任务" in item or "source_recipe_id" in item or "菜谱名称" in item for item in failures),
            "error_free_ok": unexpected_error is None,
            "response_constraints_ok": not any("回复" in item for item in failures),
            "end_to_end_ok": passed if case.suite == "end_to_end" else None,
        },
    }

