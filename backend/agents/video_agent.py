"""
视频推荐Agent - 根据知识点和学生画像推荐网络教学视频
通过LLM生成精准搜索词和平台链接（B站、YouTube等）
"""
from typing import Dict, List
from agents.spark_client import call_spark_lite


async def generate_video(
    kp_id: str,
    kp_name: str,
    kp_description: str,
    student_profile: Dict,
    rag_context: str = "",
    related_kps: List[Dict] = None,
) -> str:
    """推荐与知识点匹配的教学视频链接"""
    level = student_profile.get("base_level", 3)
    goal = student_profile.get("learn_goal", "全面掌握")
    style = student_profile.get("cognitive_style", "文本型")

    # 根据基础等级决定难度关键词
    if level <= 2:
        difficulty_tag = "入门 基础 通俗"
        length_hint = "短小精悍的入门教程（10-20分钟）"
    elif level == 3:
        difficulty_tag = "中级 实战"
        length_hint = "系统性讲解（20-40分钟）"
    else:
        difficulty_tag = "进阶 深入原理"
        length_hint = "深度分析或源码级讲解（不限时长）"

    # 根据认知风格决定推荐偏向
    if style == "实践型":
        style_hint = "偏实操、项目驱动的视频"
    elif style == "视觉型":
        style_hint = "有图解、动画演示的视频"
    else:
        style_hint = "逻辑清晰、讲解详细的视频"

    prompt = f"""你是一位课程资源推荐专家。请为正在学习「{kp_name}」的学生推荐教学视频资源。

学生画像：
- 知识基础：{level}/5（{'入门' if level<=2 else '中级' if level<=3 else '进阶'}）
- 认知风格：{style}
- 学习目标：{goal}
- 知识点描述：{kp_description}

请生成 Markdown 格式的视频推荐（不要用代码块包裹）：

## 一、推荐搜索关键词
为以下平台列出3-5个精准搜索词（中文为主，配合{difficulty_tag}）：
- B站(bilibili)：列出搜索词
- YouTube：列出英文搜索词
- 中国大学MOOC：列出搜索词（如有相关课程）

## 二、学习建议
- 推荐视频时长：{length_hint}
- 推荐风格：{style_hint}
- 学习顺序建议：先用关键词搜索，看播放量高、评论区反馈好的视频

## 三、自我评估指引
观看后尝试回答：
1. {kp_name}的核心概念是什么？
2. 能否用自己的话给同学讲一遍？
3. 视频中的例子你能否举一反三？

要求：简洁实用，总计300-500字，不要输出  ``` 代码块。"""

    try:
        result = await call_spark_lite(
            messages=[{"role": "user", "content": prompt}],
            system_prompt="你是课程资源推荐专家，擅长为不同水平的学生推荐精准的学习资源。",
        )
        result = result.strip()
        if result.startswith("```"):
            lines = result.split("\n")
            result = "\n".join(lines[1:]) if len(lines) > 1 else result
        if result.endswith("```"):
            result = result[:result.rindex("```")].strip()
        return result
    except Exception as e:
        return f"## 视频学习推荐\n\n搜索「{kp_name} {difficulty_tag}」相关教学视频。\n\n- B站: https://search.bilibili.com/all?keyword={kp_name}\n- YouTube: https://www.youtube.com/results?search_query={kp_name}+tutorial"
