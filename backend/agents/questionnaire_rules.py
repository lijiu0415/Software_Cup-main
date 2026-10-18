"""
问卷规则映射 - 将 27 题作答确定性映射到 6 维画像 + 课程
=======================================================

问卷结构（详见 docs/多智能体学习系统用户评估问卷.md）：
- 单选：q1-q5, q8, q9, q11, q13, q17, q21, q23, q24  → 字母 "A"~"G"
- 多选：q6, q12, q15, q16, q18, q19                     → 字母数组 ["A", "B", ...]
- 量表：q7, q10, q14, q20, q22（1-5 分）                → int 数组或 {条目: 分数}
- 开放：q25, q26, q27                                   → 文本

输出画像字段（与 StudentProfile 6 维 + course 对齐）：
course / base_level / learn_goal / learn_preference / cognitive_style / error_type / learn_speed
"""
from typing import Dict, List, Optional

from agents.diagnose_agent import ALLOWED_VALUES, DEFAULTS


def _letter_index(letter) -> Optional[int]:
    """'A' -> 0, 'B' -> 1 ..."""
    if not letter or not isinstance(letter, str):
        return None
    c = letter.strip().upper()
    if len(c) == 1 and "A" <= c <= "Z":
        return ord(c) - ord("A")
    return None


def _as_list(value) -> List:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, (tuple, set)):
        return list(value)
    return [value]


def _scale_values(value) -> List[int]:
    """量表题统一转成数值列表（兼容 list / dict）"""
    if isinstance(value, dict):
        raw = list(value.values())
    else:
        raw = _as_list(value)
    nums = []
    for v in raw:
        try:
            n = int(v)
        except (TypeError, ValueError):
            continue
        if 1 <= n <= 5:
            nums.append(n)
    return nums


def _avg(values: List[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _clamp_int(n, lo=1, hi=5) -> int:
    try:
        n = int(round(float(n)))
    except (TypeError, ValueError):
        n = lo
    return max(lo, min(hi, n))


def _pick_first(present: set, priority: List[str]) -> Optional[str]:
    """按优先级取第一个命中的选项字母"""
    for p in priority:
        if p in present:
            return p
    return None


def _valid_or_default(field: str, value) -> object:
    """枚举校验，非法则回退默认值"""
    if field in ALLOWED_VALUES and value in ALLOWED_VALUES[field]:
        return value
    return DEFAULTS.get(field)


def _derive_course(answers: Dict, course: Optional[str] = None) -> str:
    """课程：由提交方传入的 course 决定（每门课独立问卷与画像）。

    若未传入，回退为「人工智能导论」。两门课问卷同构，课程不参与规则推导，
    仅作为画像快照与学习数据隔离的归属键。
    """
    if course:
        return _valid_or_default("course", course)
    return _valid_or_default("course", "人工智能导论")


def _derive_base_level(answers: Dict) -> int:
    """基础水平：编程经验 + AI 知识熟悉度 + 项目实践综合"""
    prog = _letter_index(answers.get("q5"))  # 0-4
    ml = _letter_index(answers.get("q8"))    # 0-4
    project = _letter_index(answers.get("q9"))  # 0-4

    # AI 知识熟悉度：q7（基础概念）+ q10（应用领域）
    knowledge = _scale_values(answers.get("q7")) + _scale_values(answers.get("q10"))
    avg_knowledge = _avg(knowledge) or 3.0  # 1-5

    exp = 0.0
    n = 0
    for e in (prog, ml, project):
        if e is not None:
            exp += e
            n += 1
    exp_score = (exp / n) if n else 2.0  # 0-4
    # 60% 知识熟悉度 + 40% 实践经验（经验 0-4 映射到 1-5）
    return _clamp_int(0.6 * avg_knowledge + 0.4 * (exp_score + 1))


def _derive_learn_goal(answers: Dict) -> str:
    """学习目标：Q18 学习目的多选"""
    q18 = set(_as_list(answers.get("q18")))
    # 就业 > 考研/科研 > 兴趣 > 全面掌握
    if q18 & {"B", "C", "F"}:
        return _valid_or_default("learn_goal", "就业")
    if q18 & {"A", "E"}:
        return _valid_or_default("learn_goal", "考研")
    if "D" in q18:
        return _valid_or_default("learn_goal", "兴趣")
    return _valid_or_default("learn_goal", "全面掌握")


def _derive_preference_and_style(answers: Dict):
    """资源偏好 + 认知风格：Q15 学习方式多选"""
    q15 = set(_as_list(answers.get("q15")))
    # 资源偏好
    if len(q15) >= 3:
        preference = "综合"
    elif q15 & {"C", "E"}:
        preference = "代码案例"
    elif "D" in q15:
        preference = "习题练习"
    elif "A" in q15:
        preference = "教案文档"
    elif "B" in q15:
        preference = "拓展阅读"
    else:
        preference = "综合"
    # 认知风格：动手/练习/项目 → 实践型；视频 → 视觉型；文字 → 文本型
    if q15 & {"C", "D", "E"}:
        style = "实践型"
    elif "B" in q15:
        style = "视觉型"
    elif "A" in q15:
        style = "文本型"
    else:
        style = "文本型"
    return (
        _valid_or_default("learn_preference", preference),
        _valid_or_default("cognitive_style", style),
    )


def _derive_error_type(answers: Dict) -> str:
    """易错类型：Q19 学习困难多选"""
    q19 = set(_as_list(answers.get("q19")))
    if "C" in q19:
        return _valid_or_default("error_type", "概念混淆")
    if q19 & {"B", "D"}:
        return _valid_or_default("error_type", "实践不足")
    if "A" in q19:
        return _valid_or_default("error_type", "计算错误")
    return _valid_or_default("error_type", "概念混淆")


def _derive_learn_speed(answers: Dict) -> int:
    """学习速度：Q17 每周时间 + Q5 编程经验"""
    time_map = {"A": 1, "B": 2, "C": 3, "D": 4, "E": 5}
    q17 = (answers.get("q17") or "").strip().upper()
    time_score = time_map.get(q17, 3)
    prog = _letter_index(answers.get("q5"))
    prog_score = (prog + 1) if prog is not None else 3
    return _clamp_int(0.5 * time_score + 0.5 * prog_score)


def derive_profile(answers: Dict, course: Optional[str] = None) -> Dict:
    """将问卷作答映射为画像（规则层，未含 LLM 精修）"""
    if not isinstance(answers, dict):
        answers = {}

    preference, style = _derive_preference_and_style(answers)

    profile = {
        "course": _derive_course(answers, course),
        "base_level": _derive_base_level(answers),
        "learn_goal": _derive_learn_goal(answers),
        "learn_preference": preference,
        "cognitive_style": style,
        "error_type": _derive_error_type(answers),
        "learn_speed": _derive_learn_speed(answers),
    }
    return profile
