"""
编程测试Agent - 章节测试中的编程题出题与实时批改
====================================================

每次章节测试，由该 Agent 随机生成一道与该章知识点相关的编程题；
学生作答后 Agent 实时批改，给出对应知识点与标准答案。
结果不计入测试分值，但作为画像变化依据（主要影响 error_type / learn_preference）。
"""
import json
import re
import random
from typing import Dict, List

from agents.llm_adapter import chat_completion

GENERATE_SYSTEM = """你是「智育万象」学习平台的编程测试出题Agent。根据指定知识点，随机生成一道贴合该知识点的编程题。

【要求】
1. 题目必须与指定知识点直接相关，难度与学生知识基础匹配（基础1-2出基础题，3-4出综合题，5出挑战题）。
2. 题目应让学生能通过编写 Python 代码作答，题干清晰、无歧义、可执行。
3. 输出严格 JSON（不要代码块），格式：
{"question":"题目完整描述","difficulty":3}
"""

GRADE_SYSTEM = """你是「智育万象」学习平台的编程测试批改Agent。根据题目与学生作答，实时批改并给出反馈。

【要求】
1. 评判正确性：correctness 取值「正确」「部分正确」「错误」之一。
2. feedback 用中文给出针对性点评：指出亮点、问题与改进建议，并结合对应知识点。
3. standard_answer 给出该题的参考实现（Python 代码 + 简要说明）。
4. profile_changes 用于反映学生编程能力对画像的影响，仅允许调整以下两个字段（不需要调整则返回空数组 []）：
   - error_type：当作答明显缺乏动手/编码能力（代码空泛、无法实现、思路错误）时置为「实践不足」；逻辑混乱时可为「逻辑漏洞」。
   - learn_preference：当学生表现出明显代码实践偏好时可为「代码案例」。
   每个调整需附 confidence（0-1，需 ≥ 0.7 才被采纳）与 reason（一句话依据）。
5. 输出严格 JSON（不要代码块），格式：
{"correctness":"正确","feedback":"...","standard_answer":"...","profile_changes":[{"field":"error_type","value":"实践不足","confidence":0.85,"reason":"..."}]}
"""


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


def _profile_desc(profile: Dict) -> str:
    return (
        f"知识基础：{profile.get('base_level', 3)}/5\n"
        f"认知风格：{profile.get('cognitive_style', '文本型')}\n"
        f"资源偏好：{profile.get('learn_preference', '综合')}\n"
        f"易错类型：{profile.get('error_type', '概念混淆')}"
    )


async def generate_program_question(chapter_name: str, kps: List[Dict], student_profile: Dict) -> Dict:
    """随机选题生成一道编程题，返回 {question, kp_id, kp_name, difficulty}"""
    if not kps:
        return None
    kp = random.choice(kps)
    prompt = (
        f"【章节】{chapter_name}\n"
        f"【知识点】{kp['name']}（{kp['kp_id']}）\n"
        f"【学生画像】\n{_profile_desc(student_profile)}\n\n"
        f"请为该知识点生成一道编程题，输出 JSON。"
    )
    try:
        reply = await chat_completion(
            [{"role": "user", "content": prompt}],
            system_prompt=GENERATE_SYSTEM, model="standard", temperature=0.8,
        )
    except Exception as e:
        print(f"[编程测试Agent] 出题 LLM 调用失败: {e}")
        return None
    data = _parse_json(reply)
    question = str(data.get("question") or "").strip()
    if not question:
        question = f"请围绕知识点「{kp['name']}」编写一段 Python 代码，实现其核心逻辑并给出示例运行结果。"
    try:
        difficulty = int(data.get("difficulty") or 3)
    except (TypeError, ValueError):
        difficulty = 3
    return {
        "question": question,
        "kp_id": kp["kp_id"],
        "kp_name": kp["name"],
        "difficulty": max(1, min(5, difficulty)),
    }


async def grade_program_answer(
    question: str,
    kp_id: str,
    kp_name: str,
    student_answer: str,
    student_profile: Dict,
) -> Dict:
    """批改编程作答，返回 {correctness, feedback, kp_id, kp_name, standard_answer, profile_changes(raw)}"""
    prompt = (
        f"【题目】\n{question}\n\n"
        f"【对应知识点】{kp_name or kp_id or '未指定'}\n\n"
        f"【学生作答】\n{student_answer}\n\n"
        f"【学生画像】\n{_profile_desc(student_profile)}\n\n"
        f"请批改并输出 JSON。"
    )
    try:
        reply = await chat_completion(
            [{"role": "user", "content": prompt}],
            system_prompt=GRADE_SYSTEM, model="standard", temperature=0.2,
        )
    except Exception as e:
        print(f"[编程测试Agent] 批改 LLM 调用失败: {e}")
        return None
    data = _parse_json(reply)
    correctness = str(data.get("correctness") or "无法判定").strip()
    feedback = str(data.get("feedback") or "").strip()
    standard_answer = str(data.get("standard_answer") or "").strip()
    profile_changes = data.get("profile_changes") or []
    if not isinstance(profile_changes, list):
        profile_changes = []
    if not feedback:
        feedback = "批改服务暂时不可用，请稍后再试。"
    return {
        "correctness": correctness,
        "feedback": feedback,
        "kp_id": kp_id,
        "kp_name": kp_name,
        "standard_answer": standard_answer,
        "profile_changes": profile_changes,
    }
