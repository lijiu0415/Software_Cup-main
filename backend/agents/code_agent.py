"""
代码Agent - 生成可运行Python代码+逐行注释
对接讯飞Spark Lite
"""
from typing import Dict, List
from agents.spark_client import call_spark_code


async def generate_code(
    kp_id: str,
    kp_name: str,
    kp_description: str,
    student_profile: Dict,
    rag_context: str = "",
    related_kps: List[Dict] = None,
) -> str:
    """生成Python代码案例"""
    level = student_profile.get("base_level", 3)
    style = student_profile.get("cognitive_style", "实践型")
    course = student_profile.get("course", "人工智能导论")

    complexity_hint = {
        1: "代码尽量简单，使用基础Python语法，避免复杂库",
        2: "可以使用numpy等基础库，代码控制在50行以内",
        3: "可以使用sklearn等标准库，展示完整流程",
        4: "可以使用PyTorch/TensorFlow，展示高级用法",
        5: "展示前沿实现，包含性能优化技巧",
    }

    from agents.lesson_agent import _build_related_kp_section
    related_section = _build_related_kp_section(related_kps or [])

    user_prompt = f"""你是一位Python编程教师，擅长为{course}课程生成可运行的代码示例。

请为以下知识点生成完整的Python代码示例：

**知识点**: {kp_name}
**描述**: {kp_description}
**学生水平**: {level}/5
**认知风格**: {style}
**复杂度要求**: {complexity_hint.get(level, complexity_hint[3])}

**知识库参考**:
{rag_context if rag_context else '无额外参考'}
{related_section}
**输出要求**：
1. 使用Markdown格式输出
2. 生成完整可运行的Python代码
3. 每行关键代码添加中文注释说明
4. 包含以下完整内容：
   - 代码功能说明（简要说明代码目的和使用场景）
   - 完整代码（不要省略任何部分）
   - 运行结果（预期输出示例）
   - 代码解析（逐段解释代码逻辑）
5. 当代码注释中提到相关知识点时，使用真实链接格式
6. 代码要完整、可运行，不要使用省略号

请生成完整的Python代码示例："""

    messages = [{"role": "user", "content": user_prompt}]
    return await call_spark_code(messages)
