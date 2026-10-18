"""
习题Agent - 基于学生易错点生成针对性练习题+解析
"""
from typing import Dict, List
from agents.spark_client import call_spark_pro
from agents.lesson_agent import _build_related_kp_section


async def generate_exercise(
    kp_id: str,
    kp_name: str,
    student_profile: Dict,
    rag_context: str = "",
    related_kps: List[Dict] = None,
) -> str:
    """生成针对性练习题"""
    error_type = student_profile.get("error_type", "概念混淆")
    level = student_profile.get("base_level", 3)
    course = student_profile.get("course", "人工智能导论")

    difficulty_map = {1: "基础概念题", 2: "简单应用题", 3: "中等综合题", 4: "较难分析题", 5: "挑战题"}
    difficulty = difficulty_map.get(level, "中等综合题")

    related_section = _build_related_kp_section(related_kps or [])

    user_prompt = f"""你是一位{course}课程出题专家，擅长根据学生的易错点生成针对性练习题。

请为以下知识点生成完整的针对性练习题：

**知识点**: {kp_name}
**学生易错类型**: {error_type}
**题目难度**: {difficulty}

**知识库参考**:
{rag_context if rag_context else '无额外参考'}
{related_section}
**输出要求**：
1. 使用Markdown格式输出
2. 生成2-3道完整的练习题
3. 每道题必须包含：
   - 题目描述（清晰明确，不要使用省略号）
   - 解题思路（详细说明）
   - 详细解答步骤（完整过程）
   - 易错点提示（具体说明）
4. 当题目提到相关知识点时，使用真实链接格式
5. 题目内容要完整、详细，不要省略任何部分

请生成完整的练习题："""

    messages = [{"role": "user", "content": user_prompt}]
    return await call_spark_pro(messages)
