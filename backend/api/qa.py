"""
课程答疑接口 - POST /api/qa/chat/stream (流式 SSE)
支持答疑历史记录（独立于画像对话的 ChatRecord）
"""
import asyncio
import json
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from db.database import get_db, async_session_factory
from db import crud
from agents.tutor_agent import run_tutor_stream
from agents.evaluation_agent import maybe_evaluate
from utils.sensitive_filter import check_sensitive_async
from utils.security import AuthUser, get_current_user, resolve_student_id

router = APIRouter(prefix="/api/qa", tags=["答疑"])


class QaRequest(BaseModel):
    student_id: str
    content: str


class EvaluateRequest(BaseModel):
    student_id: str


def _loads(s):
    try:
        return json.loads(s) if s else None
    except (json.JSONDecodeError, TypeError):
        return None


def _serialize_evaluation(rec):
    """把 EvaluationRecord 序列化为前端可读的 dict"""
    return {
        "id": rec.id,
        "create_time": rec.create_time.strftime("%Y-%m-%d %H:%M:%S") if rec.create_time else "",
        "before_profile": _loads(rec.before_profile),
        "after_profile": _loads(rec.after_profile),
        "questions": _loads(rec.questions),
        "changes": _loads(rec.changes),
        "summary": rec.summary,
        "applied": rec.applied,
    }


def _profile_dict(student) -> dict:
    if not student:
        return {}
    return {
        "base_level": student.base_level,
        "cognitive_style": student.cognitive_style,
        "learn_preference": student.learn_preference,
        "error_type": student.error_type,
        "learn_speed": student.learn_speed,
        "learn_goal": student.learn_goal,
        "course": student.course,
    }


async def _background_evaluate(student_id: str):
    """答疑结束后后台评估画像（不阻塞流式响应）"""
    try:
        async with async_session_factory() as eval_db:
            record = await maybe_evaluate(eval_db, student_id)
            if record is not None:
                await eval_db.commit()
    except Exception as e:
        print(f"[评估Agent] 后台评估失败: {e}")


@router.post("/chat/stream")
async def qa_chat_stream(
    req: QaRequest,
    db: AsyncSession = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    """流式课程答疑（SSE）"""
    student_id = resolve_student_id(req.student_id, current_user)

    # 敏感词检测
    has_sensitive, _ = await check_sensitive_async(req.content)
    if has_sensitive:
        async def _sensitive():
            yield f"data: {json.dumps({'type': 'error', 'message': '您的消息包含不当内容，请重新输入。'}, ensure_ascii=False)}\n\n"
        return StreamingResponse(_sensitive(), media_type="text/event-stream")

    # 获取或创建学生
    student = await crud.get_student(db, student_id)
    if not student:
        student = await crud.create_student(db, id=student_id, student_name="新同学")
        await db.commit()

    # 获取答疑历史（最近 20 条，时间正序）
    history = await crud.get_qa_history(db, student_id, limit=20)
    chat_history = [{"role": h.role, "content": h.content} for h in history]

    student_profile = {
        "base_level": student.base_level,
        "cognitive_style": student.cognitive_style,
        "learn_preference": student.learn_preference,
        "error_type": student.error_type,
        "learn_speed": student.learn_speed,
        "learn_goal": student.learn_goal,
    }
    course = student.course

    # 保存用户问句
    await crud.add_qa_message(db, student_id, "user", req.content, "")
    await db.commit()

    # 后台触发动态画像评估（自动，不阻塞响应）
    asyncio.create_task(_background_evaluate(student_id))

    async def _stream():
        agent_reply = ""
        sources = []

        async for event_json in run_tutor_stream(
            student_id=student_id,
            question=req.content,
            chat_history=chat_history,
            student_profile=student_profile,
            course=course,
        ):
            yield f"data: {event_json}\n\n"
            try:
                data = json.loads(event_json)
                if data.get("type") == "done":
                    agent_reply = data.get("reply", "")
                    sources = data.get("sources", [])
            except (json.JSONDecodeError, KeyError):
                pass

        # 流结束后保存 assistant 回答
        if agent_reply:
            async with async_session_factory() as save_db:
                await crud.add_qa_message(
                    save_db, student_id, "assistant", agent_reply,
                    json.dumps(sources, ensure_ascii=False),
                )
                await save_db.commit()

    return StreamingResponse(_stream(), media_type="text/event-stream")


@router.get("/history/{student_id}")
async def get_history(
    student_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    """获取该生全部答疑历史（时间正序）"""
    student_id = resolve_student_id(student_id, current_user)
    history = await crud.get_qa_history(db, student_id, limit=200)
    return {
        "student_id": student_id,
        "messages": [
            {
                "role": m.role,
                "content": m.content,
                "sources": json.loads(m.sources) if m.sources else [],
                "create_time": m.create_time.strftime("%Y-%m-%d %H:%M:%S") if m.create_time else "",
            }
            for m in history
        ],
        "total": len(history),
    }


@router.delete("/history/{student_id}")
async def clear_history(
    student_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    """清空该生答疑历史"""
    student_id = resolve_student_id(student_id, current_user)
    await crud.delete_qa_history(db, student_id)
    await db.commit()
    return {"message": "清空成功"}


@router.post("/evaluate")
async def manual_evaluate(
    req: EvaluateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    """手动触发动态画像评估（force=True 跳过提问数阈值）"""
    student_id = resolve_student_id(req.student_id, current_user)
    record = await maybe_evaluate(db, student_id, force=True)
    await db.commit()
    student = await crud.get_student(db, student_id)
    if record is not None:
        return {"evaluated": True, "record": _serialize_evaluation(record), "profile": _profile_dict(student)}
    return {"evaluated": False, "reason": "近期答疑提问不足，暂无法评估", "profile": _profile_dict(student)}


@router.get("/evaluation/history/{student_id}")
async def get_evaluation_history(
    student_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    """获取该生动态画像评估历史（新→旧）"""
    student_id = resolve_student_id(student_id, current_user)
    records = await crud.get_evaluation_history(db, student_id, limit=20)
    return {"student_id": student_id, "history": [_serialize_evaluation(r) for r in records]}


@router.get("/evaluation/latest/{student_id}")
async def get_latest_evaluation(
    student_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    """获取该生最近一次动态画像评估"""
    student_id = resolve_student_id(student_id, current_user)
    record = await crud.get_latest_evaluation(db, student_id)
    return {"student_id": student_id, "record": _serialize_evaluation(record) if record else None}
