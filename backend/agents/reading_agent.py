"""
拓展阅读Agent - 生成个性化拓展阅读材料
包含延伸文献推荐、相关技术发展脉络、跨学科联系等
"""
from typing import Dict, List
from agents.spark_client import call_spark_pro


async def generate_reading(
    kp_id: str,
    kp_name: str,
    kp_description: str,
    student_profile: Dict,
    rag_context: str = "",
    related_kps: List[Dict] = None,
) -> str:
    """生成个性化拓展阅读材料"""
    level = student_profile.get("base_level", 3)
    goal = student_profile.get("learn_goal", "全面掌握")
    style = student_profile.get("cognitive_style", "实践型")

    related_names = [r.get("name", "") for r in (related_kps or [])[:5]]
    related_str = "、".join(related_names) if related_names else "暂无"

    prompt = f"""你是一位大学课程辅导导师。请为正在学习「{kp_name}」的学生推荐一份个性化拓展阅读材料。

学生画像：
- 知识基础：{level}/5
- 认知风格：{style}
- 学习目标：{goal}
- 知识点描述：{kp_description}
- 关联知识点：{related_str}

知识库参考（如有）：
{rag_context[:500] if rag_context else "无"}

请生成以下内容的 Markdown：

## 一、延伸阅读推荐
推荐2-3篇与该知识点相关的经典文献、行业报告或技术博客，每篇包含：
- 标题与来源
- 核心内容简介（2-3句）
- 适合该学生的阅读理由

## 二、技术发展脉络
简述该知识点的技术演进或研究发展历程（3-5个关键节点），帮助学生建立知识的历史坐标。

## 三、跨学科联系
指出该知识点与其他学科/领域的交叉应用（至少2个），拓宽学生视野。

## 四、前沿动态
介绍当前最新的研究热点或业界实践（1-2项），激发学习兴趣。

## 五、进阶学习建议
根据学生当前水平（{level}/5）和目标（{goal}），给出下一步学习路径建议。

要求：
- 语言通俗易懂，避免过度学术化
- 内容控制在800-1500字
- 用 Markdown 格式输出，适当使用列表
- 不要输出到代码块中"""

    try:
        result = await call_spark_pro(
            messages=[{"role": "user", "content": prompt}],
            system_prompt="你是大学课程辅导导师，擅长推荐个性化拓展阅读材料。",
        )
        result = result.strip()
        if result.startswith("```"):
            lines = result.split("\n")
            result = "\n".join(lines[1:]) if len(lines) > 1 else result
        if result.endswith("```"):
            result = result[:result.rindex("```")].strip()
        return result
    except Exception as e:
        return f"## 拓展阅读（生成失败）\n\n抱歉，拓展阅读生成失败。请稍后重试。\n\n### 建议\n- 在搜索引擎中搜索「{kp_name} 拓展阅读」\n- 查阅教材中关于「{kp_name}」的参考文献部分"
