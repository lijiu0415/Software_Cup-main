"""
评估Agent - 动态画像评估
======================

收集学生在「答疑助手」中的提问，分析其反映出的真实学习状态与当前画像
是否一致，并对不一致的维度做**受约束**的调整。

触发方式:
  - 自动：每次答疑结束后后台检查，新增提问达到阈值即评估
  - 手动：POST /api/qa/evaluate

调整规则（强约束，防止画像被单次提问噪声带偏）:
  1. 仅评估 5 个「状态型」维度：base_level / learn_speed / cognitive_style /
     learn_preference / error_type。learn_goal 与 course 属「意图型」，不动态改。
  2. 数值维度（base_level / learn_speed）单次调整幅度 ≤ ±1，并夹紧到 1-5。
  3. 枚举维度取值必须落在 diagnose_agent.ALLOWED_VALUES 内。
  4. 仅当 LLM 置信度 ≥ MIN_CONFIDENCE 时才采纳该维度调整。
"""
import json
import re
from typing import Dict, List

from db import crud
from agents.diagnose_agent import ALLOWED_VALUES

# ============================================================
# 评估规则常量
# ============================================================
WINDOW = 10              # 每次分析取最近 N 条用户提问
EVAL_THRESHOLD = 5       # 自上次评估以来新增提问达到该数量才自动评估
MIN_CONFIDENCE = 0.7     # 维度调整的最低置信度
STATE_DIMS = ["base_level", "learn_speed", "cognitive_style", "learn_preference", "error_type"]

SYSTEM_PROMPT = """你是一名学习画像动态评估专家。根据学生在答疑助手中的提问，判断学生的真实学习状态是否与当前画像一致，并给出需要调整的维度。

【可调整维度与允许取值】
- base_level（知识基础）：1-5 整数
- learn_speed（学习速度）：1-5 整数
- cognitive_style（认知风格）：文本型 / 实践型 / 视觉型
- learn_preference（资源偏好）：教案文档 / 习题练习 / 代码案例 / 思维导图 / 拓展阅读 / 综合
- error_type（易错类型）：概念混淆 / 计算错误 / 逻辑漏洞 / 实践不足

【规则】
1. 只评估上述 5 个维度，不得改动 learn_goal（学习目标）与 course（课程）。
2. 仅当学生提问中有明确证据表明其真实水平/偏好与当前画像不符时，才给出该维度调整。
3. 数值维度（base_level / learn_speed）单次调整幅度不超过 ±1。
4. 每个调整附带 confidence（0-1，你的把握度）与 reason（一句话依据）。
5. 输出严格 JSON（不要代码块），格式：
{"summary":"一句话总体结论","changes":[{"field":"base_level","value":4,"confidence":0.9,"reason":"..."}]}
6. 若无需调整，changes 返回空数组 []。"""


def _build_prompt(current_profile: Dict, questions: List[str]) -> str:
    q_lines = "\n".join(f"{i + 1}. {q}" for i, q in enumerate(questions))
    return (
        f"【当前画像】\n{json.dumps(current_profile, ensure_ascii=False)}\n\n"
        f"【学生近期答疑提问】\n{q_lines}\n\n"
        f"请评估这些提问反映出的学习状态是否与当前画像一致，输出 JSON。"
    )


def _parse_json(reply: str) -> Dict:
    """稳健解析 LLM 输出的 JSON（去代码块、首尾 {} 截取）"""
    clean = re.sub(r"```(?:json)?", "", reply or "").replace("```", "").strip()
    data = None
    try:
        data = json.loads(clean)
    except (json.JSONDecodeError, TypeError):
        data = None
    if not isinstance(data, dict):
        start = clean.find("{")
        end = clean.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                data = json.loads(clean[start:end + 1])
            except (json.JSONDecodeError, TypeError):
                data = None
    return data if isinstance(data, dict) else {}


def _normalize_changes(changes: List, current: Dict) -> List[Dict]:
    """校验并夹紧 LLM 建议的画像调整，返回实际生效的变更列表"""
    out = []
    for c in changes:
        if not isinstance(c, dict):
            continue
        field = c.get("field")
        if field not in STATE_DIMS:
            continue
        value = c.get("value")
        try:
            confidence = float(c.get("confidence", 0))
        except (TypeError, ValueError):
            confidence = 0.0
        if confidence < MIN_CONFIDENCE:
            continue
        reason = str(c.get("reason", "")).strip()

        if field in ("base_level", "learn_speed"):
            try:
                value = int(value)
            except (TypeError, ValueError):
                continue
            value = max(1, min(5, value))
            old = int(current.get(field) or 3)
            # 单次幅度 ≤ ±1，再夹紧到 1-5
            value = max(1, min(5, old + max(-1, min(1, value - old))))
            if value == old:
                continue
        else:
            if value not in ALLOWED_VALUES[field]:
                continue
            if value == current.get(field):
                continue

        out.append({
            "field": field,
            "value": value,
            "confidence": round(confidence, 2),
            "reason": reason,
        })
    return out


async def _analyze(current_profile: Dict, questions: List[str]) -> Dict:
    """调用 LLM 分析提问，返回 {summary, changes(原始建议)}"""
    from agents.llm_adapter import chat_completion
    messages = [{"role": "user", "content": _build_prompt(current_profile, questions)}]
    try:
        reply = await chat_completion(
            messages, system_prompt=SYSTEM_PROMPT, model="standard", temperature=0.2,
        )
    except Exception as e:
        print(f"[评估Agent] LLM 调用失败: {e}")
        return {"summary": "", "changes": []}
    data = _parse_json(reply)
    changes = data.get("changes") or []
    if not isinstance(changes, list):
        changes = []
    return {"summary": str(data.get("summary", "")).strip(), "changes": changes}


def _current_profile(student) -> Dict:
    return {
        "base_level": student.base_level,
        "learn_speed": student.learn_speed,
        "cognitive_style": student.cognitive_style,
        "learn_preference": student.learn_preference,
        "error_type": student.error_type,
        "learn_goal": student.learn_goal,
        "course": student.course,
    }


async def maybe_evaluate(db, student_id: str, force: bool = False):
    """动态画像评估入口。满足条件则评估并落库，返回 EvaluationRecord 或 None"""
    student = await crud.get_student(db, student_id)
    if not student:
        return None

    latest = await crud.get_latest_evaluation(db, student_id)
    since = latest.create_time if latest else None
    new_count = await crud.count_user_questions_since(db, student_id, since)
    if not force and new_count < EVAL_THRESHOLD:
        return None

    questions = await crud.get_user_questions(db, student_id, limit=WINDOW)
    if len(questions) < 2:
        return None

    current = _current_profile(student)
    result = await _analyze(current, questions)
    changes = _normalize_changes(result["changes"], current)

    applied_changes = {c["field"]: c["value"] for c in changes}
    after = {**current, **applied_changes}

    if applied_changes:
        await crud.update_student(db, student_id, **applied_changes)

    record = await crud.add_evaluation(
        db,
        student_id=student_id,
        before_profile=current,
        after_profile=after,
        questions=questions,
        changes=changes,
        summary=result["summary"],
        applied=bool(applied_changes),
    )
    return record
