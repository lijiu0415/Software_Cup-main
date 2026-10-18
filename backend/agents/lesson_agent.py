"""
教案Agent - 生成个性化课程讲解文档
对接讯飞Spark Lite，输出Markdown格式教案
"""
from typing import Dict, List, Optional
from agents.spark_client import call_spark_pro
from agents.agent_msg import AgentMessage


def _build_related_kp_section(related_kps: List[Dict]) -> str:
    """构建可引用的相关知识点列表（注入Prompt用）"""
    if not related_kps:
        return ""
    lines = ["\n## 可引用的相关知识点（请在教案中使用真实 Markdown 链接引用）"]
    for kp in related_kps[:10]:
        lines.append(f"- [{kp['name']}](/learn/{kp['kp_id']})")
    lines.append("当提到上述概念时，请使用 [概念名](/learn/kp_id) 格式生成可点击链接。\n")
    return "\n".join(lines)


async def generate_lesson(
    kp_id: str,
    kp_name: str,
    kp_description: str,
    student_profile: Dict,
    mastery_data: List[Dict],
    rag_context: str = "",
    related_kps: List[Dict] = None,
) -> str:
    """生成个性化教案"""
    level = student_profile.get("base_level", 3)
    style = student_profile.get("cognitive_style", "文本型")
    speed = student_profile.get("learn_speed", 3)
    course = student_profile.get("course", "人工智能导论")

    difficulty_hint = {
        1: "请从最基础的概念讲起，使用生活中的类比，避免复杂公式",
        2: "请从基础概念讲起，适当引入公式，给出直观解释",
        3: "请平衡基础与进阶，公式和直觉解释并重",
        4: "可以跳过基础直观解释，直接进入核心原理和公式推导",
        5: "请深入讲解数学原理和前沿进展，适合高水平学生",
    }

    related_section = _build_related_kp_section(related_kps or [])

    user_prompt = f"""你是一位资深的{course}课程教师，擅长为不同水平的学生生成个性化的学习教案。

请为以下知识点生成完整的个性化教案：

**知识点**: {kp_name}
**描述**: {kp_description}

**学生画像**:
- 知识基础: {level}/5
- 认知风格: {style}
- 学习速度: {speed}/5
- 难度要求: {difficulty_hint.get(level, difficulty_hint[3])}

**知识库参考内容**:
{rag_context if rag_context else '无额外参考'}
{related_section}
**输出要求**：
1. 使用Markdown格式输出，结构清晰
2. 必须包含以下完整内容（不要使用占位符）：
   - 知识要点：列出3-5个核心要点
   - 详细讲解：对每个要点进行详细解释，至少100字
   - 例题分析：给出1-2个具体例题并详细解答
   - 小结：总结本知识点的核心内容
3. 在讲解中提到相关知识点时，务必使用真实链接格式
4. 语言通俗易懂，适合本科生水平
5. 内容要完整、详细，不要省略

请生成完整的Markdown教案："""

    messages = [{"role": "user", "content": user_prompt}]
    lesson = await call_spark_pro(messages)
    return lesson
