"""
思维导图Agent - 调用 LLM 生成 Markdown 嵌套列表，前端 markmap 渲染
"""
from typing import Dict, List
from agents.spark_client import call_spark_lite


async def generate_mindmap(
    kp_id: str,
    kp_name: str,
    student_profile: Dict,
    mastery_data: List[Dict],
    related_kps: List[Dict] = None,
) -> str:
    """调用大模型生成知识点思维导图（Markdown 嵌套列表格式）"""
    related_names = [r.get("name", "") for r in (related_kps or [])[:5]]
    related_str = "、".join(related_names) if related_names else "无"

    prompt = f"""你是一位课程教学设计专家。请为知识点「{kp_name}」生成一份思维导图。

输出格式：Markdown 嵌套列表（# 标题、## 二级、- 三级），前端会用 markmap 渲染。

结构要求（5个分支）：
## 前置知识
- 列出学习本知识点需要的前置知识（相关知识点: {related_str}）
- 每个前置知识简要说明其与本知识点的关系

## 核心概念
- 拆解本知识点的核心概念（至少3个子点）
- 每个概念用一句话定义

## 关键方法/算法
- 列出相关的方法、算法或技术手段
- 简要说明其作用

## 应用场景
- 列举2-3个实际应用场景
- 说明在各场景中的具体应用方式

## 易错点提示
- 列出2-3个常见误区或易错点
- 给出正确的理解或做法

要求：
1. 严格使用 Markdown 嵌套列表格式
2. 内容简洁，每项不超过30字
3. 标题用 # 和 ##，子项用 -
4. 不要用 ``` 代码块包裹
5. 总计 15-20 个子条目
6. 内容紧扣「{kp_name}」知识点"""

    try:
        result = await call_spark_lite(
            messages=[{"role": "user", "content": prompt}],
            system_prompt="你是课程教学设计专家，擅长制作知识点思维导图。",
        )
        # 清洗输出，移除可能的代码块标记
        result = result.strip()
        if result.startswith("```"):
            lines = result.split("\n")
            result = "\n".join(lines[1:]) if len(lines) > 1 else result
        if result.endswith("```"):
            result = result[:result.rindex("```")].strip()
        # 确保以 # 开头
        if not result.startswith("#"):
            result = f"# {kp_name}\n\n{result}"
        return result
    except Exception as e:
        # 降级：返回基础模板
        return _build_fallback(kp_name, related_kps or [])


def _build_fallback(kp_name: str, related_kps: List[Dict]) -> str:
    """降级模板（LLM 不可用时使用）"""
    lines = [f"# {kp_name}\n"]
    lines.append("## 前置知识")
    if related_kps:
        for r in related_kps[:5]:
            lines.append(f"- {r.get('name', '')}")
    else:
        lines.append("- 基础概念理解")
    lines.append("")
    lines.append("## 核心概念")
    for label in ["定义与原理", "关键特性", "核心要点"]:
        lines.append(f"- {label}")
    lines.append("")
    lines.append("## 关键方法/算法")
    for label in ["基础方法", "进阶技术"]:
        lines.append(f"- {label}")
    lines.append("")
    lines.append("## 应用场景")
    for label in ["理论应用", "实践案例"]:
        lines.append(f"- {label}")
    lines.append("")
    lines.append("## 易错点提示")
    for label in ["概念辨析", "常见误区"]:
        lines.append(f"- {label}")
    return "\n".join(lines)
