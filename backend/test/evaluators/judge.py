from __future__ import annotations

import json
from typing import Any

from app.infra.llm.clients import build_langchain_chat_model
from test.case_schema import AgentEvalCase


JUDGE_SYSTEM_PROMPT = """你是 ChefMate Agent 的评测裁判。
请只评估自然语言回复质量，不要覆盖规则判分结果。
输出严格 JSON，格式如下：
{
  "state_awareness": 1-5,
  "instruction_fidelity": 1-5,
  "practical_helpfulness": 1-5,
  "honesty_constraint_respect": 1-5,
  "summary": "一句中文总结"
}
不要输出 Markdown。"""


def _parse_judge_payload(text: str) -> dict[str, Any]:
    raw = text.strip()
    if raw.startswith("```"):
        lines = raw.splitlines()
        if len(lines) >= 3:
            raw = "\n".join(lines[1:-1]).strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        start = raw.find("{")
        end = raw.rfind("}")
        if start >= 0 and end > start:
            return json.loads(raw[start : end + 1])
        raise


async def judge_case(case: AgentEvalCase, trace: dict[str, Any]) -> dict[str, Any]:
    if not case.llm_judge_enabled:
        return {"skipped": True, "reason": "case_disabled"}
    if trace.get("unexpected_error"):
        return {"skipped": True, "reason": "unexpected_error"}

    turns = trace.get("turns", [])
    if not turns:
        return {"skipped": True, "reason": "no_turns"}

    final_turn = turns[-1]
    assistant_content = final_turn.get("assistant_content", "").strip()
    if not assistant_content:
        return {"skipped": True, "reason": "empty_response"}

    model = build_langchain_chat_model(temperature=0.0)
    final_task = trace.get("final_task") or {}
    prompt = {
        "case_id": case.case_id,
        "title": case.title,
        "goal": case.goal,
        "suite": case.suite,
        "user_turns": [
            {
                "content": item.content,
                "action": item.action.model_dump(mode="json") if item.action else None,
                "client_card_state": item.client_card_state,
            }
            for item in case.turns
        ],
        "assistant_reply": assistant_content,
        "final_conversation_stage": trace.get("final_conversation", {}).get("stage"),
        "final_task_snapshot": final_task.get("recipe_snapshot_json"),
        "hard_failures": trace.get("rule_result", {}).get("failures", []),
    }
    response = await model.ainvoke(
        [
            ("system", JUDGE_SYSTEM_PROMPT),
            ("user", json.dumps(prompt, ensure_ascii=False, indent=2)),
        ]
    )
    raw_text = getattr(response, "content", response)
    if isinstance(raw_text, list):
        raw_text = "\n".join(
            item.get("text", "")
            for item in raw_text
            if isinstance(item, dict) and item.get("text")
        )
    parsed = _parse_judge_payload(str(raw_text))
    scores = {
        "state_awareness": int(parsed["state_awareness"]),
        "instruction_fidelity": int(parsed["instruction_fidelity"]),
        "practical_helpfulness": int(parsed["practical_helpfulness"]),
        "honesty_constraint_respect": int(parsed["honesty_constraint_respect"]),
    }
    return {
        "skipped": False,
        "scores": scores,
        "average_score": round(sum(scores.values()) / len(scores), 4),
        "summary": str(parsed.get("summary") or "").strip(),
        "raw_text": str(raw_text),
    }

