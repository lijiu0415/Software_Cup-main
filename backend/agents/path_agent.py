"""
路径规划Agent - 基于完整学生画像，用大模型规划个性化学习路径
==============================================================

规则算法（kg_engine.compute_learning_path）已做硬约束：
前置校验、未完成过滤、候选池生成。本 Agent 在此基础上，
由大模型结合画像的 6 个维度（learn_goal / learn_preference /
cognitive_style / error_type / learn_speed / base_level）对候选
知识点重排序，并给出整体规划说明与每一步推荐理由。
"""
import json
import re
from typing import Dict, List, Optional
from agents.spark_client import call_spark_pro

# 传给 LLM 的候选知识点上限（超出部分由调用方按规则顺序追加到末尾）
MAX_CANDIDATES = 50

SYSTEM_PROMPT = """你是一位资深的学习路径规划专家，擅长根据学生的完整画像为其规划个性化的知识点学习顺序。

【任务】对给定的候选知识点进行排序，输出一条最适合该学生的个性化学习路径，并为每一步给出简洁的推荐理由。

【排序需综合考虑画像维度】
- learn_goal 学习目标：考研→系统夯实基础、由浅入深；就业→优先偏实践/项目；竞赛→优先算法与进阶；兴趣→优先有趣易上手。
- learn_preference 资源偏好：偏好习题/代码者，优先安排适合练习、可动手实践的知识点。
- error_type 易错类型：优先安排能补其短板的知识点。
- learn_speed 学习速度：快者适当提高节奏、多安排进阶；慢者放缓、夯实基础。
- base_level 基础水平：难度与水平匹配，从略低于水平的过渡内容开始。
- 同时遵守知识点难度由易到难、前后依赖的合理递进。

【输出格式】必须是 JSON（不要用代码块包裹）：
{"summary":"整体规划说明（1-3句话）","path":[{"kp_id":"...","reason":"单步推荐理由（一句话）"}]}
- path 必须包含所有给出的候选知识点（kp_id 一一对应，不要遗漏、不要新增）。
- 每个元素只能有 kp_id 和 reason 两个字段。"""


def _build_plan_prompt(student_profile: Dict, candidates: List[Dict]) -> str:
    """根据画像 + 候选知识点构建用户提示词"""
    lines = []
    lines.append("【学生画像】")
    lines.append(f"- 课程: {student_profile.get('course') or '人工智能导论'}")
    lines.append(f"- 知识基础: {student_profile.get('base_level', 3)}/5")
    lines.append(f"- 学习目标: {student_profile.get('learn_goal', '全面掌握')}")
    lines.append(f"- 资源偏好: {student_profile.get('learn_preference', '综合')}")
    lines.append(f"- 认知风格: {student_profile.get('cognitive_style', '文本型')}")
    lines.append(f"- 易错类型: {student_profile.get('error_type', '概念混淆')}")
    lines.append(f"- 学习速度: {student_profile.get('learn_speed', 3)}/5")
    lines.append("")
    lines.append("【候选知识点】（请全部纳入排序）")
    for c in candidates:
        desc = (c.get("description") or "").strip()
        if len(desc) > 40:
            desc = desc[:40] + "…"
        mastery = c.get("mastery", 0.0)
        lines.append(
            f"- kp_id={c['kp_id']} | 名称={c['name']} | 难度={c['difficulty']}/5 | "
            f"章节={c.get('chapter_id', '')} | 掌握度={round(mastery * 100)}% | 描述={desc}"
        )
    lines.append("")
    lines.append("请输出 JSON：")
    return "\n".join(lines)


def _parse_plan_reply(full_reply: str) -> Optional[Dict]:
    """稳健解析 LLM 输出的 JSON（去掉代码块 + 花括号兜底）"""
    clean = full_reply
    clean = re.sub(r"```(?:json)?", "", clean).replace("```", "").strip()

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
    if not isinstance(data, dict):
        return None
    return data


async def plan_learning_path(
    student_profile: Dict,
    candidates: List[Dict],
) -> Optional[Dict]:
    """
    规划个性化学习路径

    Args:
        student_profile: 完整学生画像（含 course 及 6 维特征）
        candidates: 候选知识点列表（由 kg_engine.compute_learning_path 产出，
                    已含前置校验与未完成过滤）

    Returns:
        {"summary": str, "path": [{"kp_id", "reason"}]}；AI 失败/结果为空时返回 None
    """
    if not candidates:
        return None

    selected = candidates[:MAX_CANDIDATES]
    prompt_text = _build_plan_prompt(student_profile, selected)
    messages = [{"role": "user", "content": prompt_text}]

    try:
        reply = await call_spark_pro(messages)
    except Exception as e:
        print(f"[路径规划Agent] 调用失败: {str(e)[:100]}")
        return None

    data = _parse_plan_reply(reply)
    if not data:
        return None

    summary = str(data.get("summary") or "").strip()
    raw_path = data.get("path")
    if not isinstance(raw_path, list):
        return None

    # 只保留候选池内的 kp_id，按序去重
    valid_ids = {c["kp_id"] for c in selected}
    path = []
    seen = set()
    for item in raw_path:
        if not isinstance(item, dict):
            continue
        kp_id = item.get("kp_id")
        if not kp_id or kp_id not in valid_ids or kp_id in seen:
            continue
        seen.add(kp_id)
        path.append({"kp_id": kp_id, "reason": str(item.get("reason") or "").strip()})

    if not path:
        return None

    return {"summary": summary, "path": path}
