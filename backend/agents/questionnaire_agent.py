"""
问卷分析 Agent - 用 LLM 对开放题作答做画像精修
================================================

客观题已由 questionnaire_rules.derive_profile 确定性映射，
本 Agent 只处理开放题（Q25 想学主题 / Q26 期待建议 / Q27 优势短板），
对规则画像做精修/覆盖，并产出一段画像摘要。

失败 / 超时 / 解析异常时完全回退规则结果，绝不阻塞问卷提交。
"""
import json
import re
from typing import Dict, Optional, Tuple

from agents.spark_client import call_spark_pro
from agents.diagnose_agent import _normalize_profile

SYSTEM_INSTRUCTION = """你是一位学习画像分析专家。根据学生问卷的开放题作答，精修其学习画像并给出简要画像摘要。

【画像字段与允许取值】
- course（课程）：人工智能导论 / 软件安全技术
- base_level（知识基础）：1-5 整数
- learn_goal（学习目标）：考研 / 就业 / 兴趣 / 竞赛 / 全面掌握
- learn_preference（资源偏好）：教案文档 / 习题练习 / 代码案例 / 思维导图 / 拓展阅读 / 综合
- cognitive_style（认知风格）：文本型 / 实践型 / 视觉型
- error_type（易错类型）：概念混淆 / 计算错误 / 逻辑漏洞 / 实践不足
- learn_speed（学习速度）：1-5 整数

【规则】
1. 只精修你「有把握」的字段，没把握的字段保持原值（不要编造）。
2. 字段取值必须严格限定在允许取值内。
3. 课程字段保持「规则推导画像」中的 course 原值，不要因开放题作答而改写。
4. 输出必须是 JSON（不要代码块包裹）：
{"course":"...","base_level":3,"learn_goal":"...","learn_preference":"...","cognitive_style":"...","error_type":"...","learn_speed":3,"summary":"1-2句话的画像摘要"}"""


def _parse_json(full_reply: str) -> Optional[Dict]:
    """稳健解析 LLM 输出的 JSON"""
    clean = re.sub(r"```(?:json)?", "", full_reply).replace("```", "").strip()
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
    return data if isinstance(data, dict) else None


def _open_answers_text(answers: Dict) -> str:
    labels = [("想学主题", "q25"), ("期待与建议", "q26"), ("优势与短板", "q27")]
    parts = []
    for label, key in labels:
        v = (answers.get(key) or "").strip()
        if v:
            parts.append(f"- {label}：{v}")
    return "\n".join(parts) if parts else "（无开放题作答）"


async def analyze_open(answers: Dict, rule_profile: Dict, course: Optional[str] = None) -> Tuple[Dict, str]:
    """对开放题做 LLM 精修，返回 (画像, 摘要)。失败回退规则画像。

    course 仅用于在规则画像缺 course 时补齐（规则层通常已带 course，此处兜底）。
    """
    if not isinstance(answers, dict):
        answers = {}
    if not rule_profile.get("course") and course:
        rule_profile = dict(rule_profile)
        rule_profile["course"] = course

    open_text = _open_answers_text(answers)
    # 无任何开放题作答时，直接回退规则结果，省一次 LLM 调用
    if open_text.startswith("（无"):
        return dict(rule_profile), ""

    prompt = (
        f"{SYSTEM_INSTRUCTION}\n\n"
        f"【规则推导的画像】\n{json.dumps(rule_profile, ensure_ascii=False)}\n\n"
        f"【专业领域（Q4）】{answers.get('q4') or '未知'}\n\n"
        f"【开放题作答】\n{open_text}\n\n"
        f"请输出 JSON："
    )

    try:
        reply = await call_spark_pro([{"role": "user", "content": prompt}])
    except Exception as e:
        print(f"[问卷分析Agent] 调用失败: {str(e)[:100]}")
        return dict(rule_profile), ""

    data = _parse_json(reply)
    if not data:
        return dict(rule_profile), ""

    # 校验并规范化（枚举约束 + 数值夹紧）
    normalized = _normalize_profile(data)
    merged = dict(rule_profile)
    merged.update(normalized)

    summary = str(data.get("summary") or "").strip()
    return merged, summary
