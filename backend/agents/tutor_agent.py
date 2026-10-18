"""
答疑智能体 - 学习过程中的课程答疑

基于 RAG 检索讲义/习题/代码，结合学生画像个性化回答。
与画像诊断Agent（diagnose_agent）完全解耦，独立成智能体。
"""
import json
from typing import Dict, List, AsyncGenerator

SYSTEM_PROMPT = """你是「智育万象」学习平台的答疑导师，在学习过程中解答学生关于课程的问题。

【回答原则】
1. 优先依据【讲义参考】作答，答案要准确、贴合课程；引用了讲义时，可自然说明「根据课程讲义…」。
2. 【讲义参考】为空或未覆盖该问题时，用你的通用知识回答，并先说明「讲义中未检索到相关内容，以下为通用知识解答」。
3. 结合【学习画像】因材施教：
   - 知识基础低（1-2）时从零讲起，多用生活化类比，少堆术语；
   - 知识基础高（4-5）时可直接深入原理、公式推导；
   - 认知风格为「视觉型」多用图示化描述，「实践型」多给代码/动手示例，「文本型」用清晰的分点文字。
4. 尽量围绕学生当前课程展开；学生问课程外问题时也友好解答，并酌情提示当前课程。
5. 用中文回答，结构清晰，适当使用 Markdown（标题/列表/代码块/公式）。

【输出要求】
直接输出回答正文，不要寒暄（如"好的""收到"），不要重复问题。
"""


def _build_prompt(
    question: str,
    chat_history: List[dict],
    student_profile: Dict,
    course: str,
    rag_context: str,
) -> str:
    """构建本轮用户提示词：画像 + 课程 + 讲义参考 + 历史 + 提问"""
    profile_desc = (
        f"知识基础：{student_profile.get('base_level', 3)}/5\n"
        f"认知风格：{student_profile.get('cognitive_style', '文本型')}\n"
        f"资源偏好：{student_profile.get('learn_preference', '综合')}\n"
        f"易错类型：{student_profile.get('error_type', '概念混淆')}\n"
        f"学习目标：{student_profile.get('learn_goal', '全面掌握')}\n"
        f"当前课程：{course or '未选择'}"
    )

    history_txt = ""
    for m in chat_history[-10:]:
        role = "学生" if m["role"] == "user" else "助教"
        history_txt += f"{role}：{m['content'].strip()}\n"

    return (
        f"【学习画像】\n{profile_desc}\n\n"
        f"【讲义参考】\n{rag_context or '（未检索到相关讲义内容）'}\n\n"
        f"【对话历史】\n{history_txt or '（无）'}\n"
        f"【学生本轮提问】\n{question.strip()}"
    )


async def run_tutor_stream(
    student_id: str,
    question: str,
    chat_history: List[dict],
    student_profile: Dict,
    course: str,
) -> AsyncGenerator[str, None]:
    """流式答疑，逐条 yield 原始 JSON 事件字符串（不含 "data: " 前缀）

    Yields:
        {"type":"start"}
        {"type":"chunk","content":"..."}
        {"type":"done","reply":"...","sources":[...],"status":"success"}
        {"type":"error","message":"..."}
    """
    from agents.llm_adapter import chat_completion_stream
    from rag.chroma_client import ensure_rag_ready, chroma_client

    # 1) RAG 检索讲义/习题/代码
    sources = []
    rag_context = ""
    try:
        await ensure_rag_ready()
        docs = chroma_client.query(question, n_results=3)
        if docs:
            parts = []
            for i, d in enumerate(docs):
                meta = d.get("metadata") or {}
                parts.append(
                    f"[{i + 1}]（{meta.get('type', '')} / {meta.get('source', '')}）\n"
                    f"{d.get('content', '')}"
                )
                sources.append({
                    "type": meta.get("type", ""),
                    "source": str(meta.get("source", "")),
                    "distance": d.get("distance", 0),
                })
            rag_context = "\n\n".join(parts)
    except Exception as e:
        print(f"[TutorAgent] RAG检索失败: {str(e)[:100]}")

    prompt = _build_prompt(question, chat_history, student_profile, course, rag_context)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]

    yield json.dumps({"type": "start"}, ensure_ascii=False)

    full_reply = ""
    try:
        async for chunk in chat_completion_stream(messages, model="standard"):
            full_reply += chunk
            yield json.dumps({"type": "chunk", "content": chunk}, ensure_ascii=False)
    except Exception as e:
        yield json.dumps({"type": "error", "message": f"答疑服务异常: {str(e)[:100]}"}, ensure_ascii=False)
        return

    reply = full_reply.strip() or "抱歉，暂时无法回答，请稍后再试。"
    yield json.dumps({
        "type": "done",
        "reply": reply,
        "sources": sources,
        "status": "success",
    }, ensure_ascii=False)
