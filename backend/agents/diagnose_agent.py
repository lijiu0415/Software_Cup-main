"""
诊断Agent - LLM 主导的画像构建
阶段一：3 轮核心冷启动（course / base_level / learn_goal）
阶段二：自由对话精炼（LLM 自然回应 + 主动引导缺失维度）
画像抽取：LLM 结构化 JSON 输出（替代关键词匹配）
"""
import json
import re
from typing import Dict, List, Tuple, AsyncGenerator
from agents.spark_client import call_spark_lite

# ============================================================
# 阶段一：核心冷启动问题（3 个）
# ============================================================
CORE_QUESTIONS = [
    {"field": "course", "question": "你想学哪门课程？"},
    {"field": "base_level", "question": "你目前对该课程的掌握程度如何？（1-5分，1=零基础，5=精通）"},
    {"field": "learn_goal", "question": "你学这门课的主要目标是什么？（考研/就业/竞赛/兴趣）"},
]

# ============================================================
# 画像维度与强约束枚举
# ============================================================
ALLOWED_VALUES = {
    "course": ["人工智能导论", "软件安全技术"],
    "learn_goal": ["考研", "就业", "兴趣", "竞赛", "全面掌握"],
    "learn_preference": ["教案文档", "习题练习", "代码案例", "思维导图", "拓展阅读", "综合"],
    "cognitive_style": ["文本型", "实践型", "视觉型"],
    "error_type": ["概念混淆", "计算错误", "逻辑漏洞", "实践不足"],
}

DEFAULTS = {
    "course": "人工智能导论",
    "base_level": 3,
    "learn_goal": "全面掌握",
    "learn_preference": "综合",
    "cognitive_style": "文本型",
    "error_type": "概念混淆",
    "learn_speed": 3,
}

MAX_ROUNDS = 8  # 超过后强制完成画像

SYSTEM_PROMPT = """你是一位专业的AI学习诊断助手，通过自然对话逐步构建学生的学习画像。

【画像维度与允许取值】
- course（课程）：人工智能导论 / 软件安全技术
- base_level（知识基础）：1-5 整数
- learn_goal（学习目标）：考研 / 就业 / 兴趣 / 竞赛 / 全面掌握
- learn_preference（资源偏好）：教案文档 / 习题练习 / 代码案例 / 思维导图 / 拓展阅读 / 综合
- cognitive_style（认知风格）：文本型 / 实践型 / 视觉型
- error_type（易错类型）：概念混淆 / 计算错误 / 逻辑漏洞 / 实践不足
- learn_speed（学习速度）：1-5 整数

【规则】
1. 从学生的输入中抽取你「确定」的画像字段，没把握的不要填、不要编造。
2. 字段取值必须严格限定在上述允许取值内。
3. 输出必须是 JSON（不要用代码块包裹），格式：{"reply":"...","profile":{...},"done":true/false}
   - reply：给学生的自然回复
   - profile：本轮新确定的画像字段（只填有把握的）
   - done：所有画像维度是否已收集完整"""


def _build_profile_prompt(round_num: int, chat_history: List[dict], student_profile: Dict, content: str) -> str:
    """根据阶段构建本轮用户提示词"""
    context = ""
    for msg in chat_history[-10:]:
        role = "学生" if msg["role"] == "user" else "AI"
        context += f"{role}：{msg['content'].strip()}\n"
    context += f"学生（本轮）：{content.strip()}\n"

    if round_num < len(CORE_QUESTIONS):
        core_q = CORE_QUESTIONS[round_num]
        instruction = (
            f"当前处于【核心问卷阶段】（第 {round_num + 1}/{len(CORE_QUESTIONS)} 问）。\n"
            f"请自然回应学生，然后问出这个核心问题：「{core_q['question']}」。\n"
            f"如果学生本轮输入里已经包含了「{core_q['field']}」的信息，抽取到 profile 中。"
        )
    else:
        instruction = (
            "核心问卷已完成，进入【自由对话阶段】。\n"
            "请自然回应学生，并在对话中主动引导尚未收集的画像维度"
            "（认知风格、易错类型、学习速度、资源偏好等），不要重复已确定的维度。"
        )

    if round_num >= MAX_ROUNDS:
        instruction += "\n本轮请完成画像收尾：缺失字段用最合理的值补齐，done 设为 true。"

    prompt = (
        f"{instruction}\n\n"
        f"【当前已收集画像】\n{json.dumps(student_profile or {}, ensure_ascii=False)}\n\n"
        f"【对话历史】\n{context}\n"
        f"【输出格式】必须是 JSON（不要代码块）：\n"
        f'{{"reply":"你的回复","profile":{{已确定字段}},"done":true/false}}'
    )
    return prompt


def _parse_profile_reply(full_reply: str) -> Tuple[str, Dict, bool]:
    """稳健解析 LLM 输出的 JSON（reply + profile + done）"""
    clean = full_reply
    if "学生：" in clean:
        clean = clean[:clean.index("学生：")]
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
        data = {}

    reply = data.get("reply") or clean
    profile = data.get("profile") or {}
    if not isinstance(profile, dict):
        profile = {}
    done = bool(data.get("done", False))
    return reply, profile, done


def _normalize_profile(profile: Dict) -> Dict:
    """校验并规范化画像字段（枚举约束 + 数值夹紧）"""
    result = {}

    if "course" in profile:
        v = profile["course"]
        result["course"] = v if v in ALLOWED_VALUES["course"] else DEFAULTS["course"]

    for field in ("base_level", "learn_speed"):
        if field in profile:
            try:
                result[field] = max(1, min(5, int(profile[field])))
            except (TypeError, ValueError):
                pass

    for field in ("learn_goal", "learn_preference", "cognitive_style", "error_type"):
        if field in profile:
            v = profile[field]
            if v in ALLOWED_VALUES[field]:
                result[field] = v

    return result


async def run_diagnose(
    student_id: str,
    chat_history: List[dict],
    student_profile: Dict = None,
    content: str = "",
) -> Tuple[str, Dict, bool]:
    """执行诊断对话（非流式），返回 (reply, profile_update, core_complete)"""
    round_num = len(chat_history) // 2
    prompt_text = _build_profile_prompt(round_num, chat_history, student_profile, content)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt_text},
    ]
    reply = await call_spark_lite(messages)

    display_reply, profile, _done = _parse_profile_reply(reply)
    profile_update = _normalize_profile(profile)
    core_complete = round_num >= len(CORE_QUESTIONS)
    return display_reply, profile_update, core_complete


async def run_diagnose_stream(
    student_id: str,
    chat_history: List[dict],
    student_profile: Dict = None,
    content: str = "",
) -> AsyncGenerator[str, None]:
    """流式诊断对话，done 事件透传 core_complete 与 chatMode"""
    from agents.llm_adapter import chat_completion_stream

    round_num = len(chat_history) // 2
    prompt_text = _build_profile_prompt(round_num, chat_history, student_profile, content)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt_text},
    ]

    full_reply = ""
    try:
        async for chunk in chat_completion_stream(messages, model="fast"):
            full_reply += chunk
    except Exception as e:
        yield json.dumps({"type": "error", "message": f"流式调用失败: {str(e)[:100]}"}, ensure_ascii=False)
        return

    display_reply, profile, _done = _parse_profile_reply(full_reply)
    profile_update = _normalize_profile(profile)
    core_complete = round_num >= len(CORE_QUESTIONS)
    chat_mode = "free" if core_complete else "questionnaire"

    yield json.dumps({
        "type": "done",
        "reply": display_reply,
        "profile_update": profile_update,
        "core_complete": core_complete,
        "chatMode": chat_mode,
    }, ensure_ascii=False)
