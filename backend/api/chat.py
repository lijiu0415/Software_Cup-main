"""
对话画像接口 - POST /api/chat/diagnose  (非流式)
              POST /api/chat/diagnose/stream (流式 SSE)
支持画像历史记录
"""
import asyncio
import json
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from db.database import get_db, async_session_factory
from db import crud
from agents.coordinator import coordinator
from utils import files
from utils.sensitive_filter import check_sensitive_async
from utils.security import AuthUser, get_current_user, resolve_student_id

router = APIRouter(prefix="/api/chat", tags=["对话"])


class ChatRequest(BaseModel):
    student_id: str
    content: str


class ChatResponse(BaseModel):
    reply: str
    profile_update: dict
    break_points: list


@router.post("/diagnose", response_model=ChatResponse)
async def chat_diagnose(
    req: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    """对话式学生画像构建"""
    student_id = resolve_student_id(req.student_id, current_user)

    # 敏感词检测
    has_sensitive, word = await check_sensitive_async(req.content)
    if has_sensitive:
        return ChatResponse(
            reply=f"您的消息包含不当内容，请重新输入。",
            profile_update={},
            break_points=[],
        )

    # 获取学生信息
    student = await crud.get_student(db, student_id)
    if not student:
        # 自动创建学生
        student = await crud.create_student(db, id=student_id, student_name="新同学")
        await db.commit()

    # 获取对话历史
    history = await crud.get_chat_history(db, student_id, limit=10)
    chat_history = [{"role": h.role, "content": h.content} for h in history]

    # 构建学生画像
    student_profile = {
        "base_level": student.base_level,
        "cognitive_style": student.cognitive_style,
        "learn_preference": student.learn_preference,
        "error_type": student.error_type,
        "learn_speed": student.learn_speed,
        "learn_goal": student.learn_goal,
    }

    # 调用协调Agent → 诊断Agent
    result = await coordinator.handle_chat(
        student_id=student_id,
        content=req.content,
        chat_history=chat_history,
        student_profile=student_profile,
    )

    # 保存对话记录
    await crud.add_chat_record(db, student_id, "user", req.content)
    await crud.add_chat_record(db, student_id, "agent", result["reply"])

    # 更新画像并保存历史记录
    if result.get("profile_update"):
        pu = result["profile_update"]
        # 提取 course_name，单独写入 course 字段
        course_name = pu.pop("course_name", None)
        if course_name:
            pu["course"] = course_name
        await crud.update_student(db, student_id, **pu)

        chat_round = await crud.get_next_profile_round(db, student_id)

        # 保存画像历史记录
        await crud.create_profile_history(
            db,
            student_id=student_id,
            chat_round=chat_round,
            **pu
        )

    await db.commit()

    return ChatResponse(
        reply=result["reply"],
        profile_update=result.get("profile_update", {}),
        break_points=result.get("break_points", []),
    )


@router.post("/diagnose/stream")
async def chat_diagnose_stream(
    req: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    """流式对话画像构建（SSE）"""
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

    # 获取对话历史
    history = await crud.get_chat_history(db, student_id, limit=10)
    chat_history = [{"role": h.role, "content": h.content} for h in history]

    student_profile = {
        "base_level": student.base_level,
        "cognitive_style": student.cognitive_style,
        "learn_preference": student.learn_preference,
        "error_type": student.error_type,
        "learn_speed": student.learn_speed,
        "learn_goal": student.learn_goal,
    }

    # 保存用户消息
    await crud.add_chat_record(db, student_id, "user", req.content)
    await db.commit()

    async def _stream():
        agent_reply = ""
        profile_update = {}

        async for sse_line in coordinator.handle_chat_stream(
            student_id=student_id,
            content=req.content,
            chat_history=chat_history,
            student_profile=student_profile,
        ):
            if '"type": "done"' in sse_line:
                try:
                    raw = sse_line.removeprefix("data: ").strip()
                    data = json.loads(raw)
                    agent_reply = data.get("reply", "")
                    profile_update = data.get("profile_update", {})
                except (json.JSONDecodeError, KeyError):
                    pass
            yield sse_line
            await asyncio.sleep(0)

        if agent_reply:
            async with async_session_factory() as save_db:
                await crud.add_chat_record(save_db, student_id, "agent", agent_reply)
                if profile_update:
                    pu = dict(profile_update)
                    course_name = pu.pop("course_name", None)
                    if course_name:
                        pu["course"] = course_name
                    await crud.update_student(save_db, student_id, **pu)
                    chat_round = await crud.get_next_profile_round(save_db, student_id)
                    await crud.create_profile_history(
                        save_db, student_id=student_id,
                        chat_round=chat_round, **pu,
                    )
                await save_db.commit()

    return StreamingResponse(_stream(), media_type="text/event-stream")


class ResetRequest(BaseModel):
    student_id: str


@router.post("/reset")
async def reset_student(
    req: ResetRequest,
    db: AsyncSession = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    """重置学生全部学习数据"""
    student_id = resolve_student_id(req.student_id, current_user)
    student = await crud.get_student(db, student_id)
    if not student:
        return {"error": "学生不存在"}

    # 清理该生上传的教材文件（磁盘）
    textbooks = await crud.get_textbooks(db, student_id)
    files.delete_textbook_files([t.stored_name for t in textbooks])

    await crud.reset_student_data(db, student_id)
    await db.commit()
    return {"message": "重置成功"}


@router.get("/profile_history/{student_id}")
async def get_profile_history(
    student_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    """获取学生的画像历史"""
    student_id = resolve_student_id(student_id, current_user)
    # 获取学生信息
    student = await crud.get_student(db, student_id)
    if not student:
        return {"error": "学生不存在"}

    # 获取画像历史
    history = await crud.get_profile_history(db, student_id)

    # 格式化历史记录
    history_list = []
    for record in history:
        history_list.append({
            "id": record.id,
            "chat_round": record.chat_round,
            "base_level": record.base_level,
            "cognitive_style": record.cognitive_style,
            "learn_preference": record.learn_preference,
            "error_type": record.error_type,
            "learn_speed": record.learn_speed,
            "learn_goal": record.learn_goal,
            "create_time": record.create_time.strftime("%Y-%m-%d %H:%M:%S"),
        })

    return {
        "student_id": student_id,
        "student_name": student.student_name,
        "history": history_list,
        "total": len(history_list),
    }


@router.get("/profile/{student_id}")
async def get_student_profile(
    student_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    """获取学生当前画像（页面刷新后恢复画像用）"""
    student_id = resolve_student_id(student_id, current_user)
    student = await crud.get_student(db, student_id)
    if not student:
        return {"error": "学生不存在"}

    history = await crud.get_profile_history(db, student_id)
    questionnaire = await crud.get_questionnaire(db, student_id, course=student.course)

    return {
        "student_id": student.id,
        "student_name": student.student_name,
        "course": student.course,
        "base_level": student.base_level,
        "learn_goal": student.learn_goal,
        "learn_preference": student.learn_preference,
        "cognitive_style": student.cognitive_style,
        "error_type": student.error_type,
        "learn_speed": student.learn_speed,
        "register_date": student.create_time.strftime("%Y-%m-%d") if student.create_time else "",
        "profiled": len(history) > 0,
        "questionnaire_complete": questionnaire is not None,
    }


@router.post("/seed_virtual_students")
async def seed_virtual_students(db: AsyncSession = Depends(get_db)):
    """导入10组虚拟学生画像（赛题演示用）"""
    from db.virtual_students import VIRTUAL_STUDENTS

    created = []
    for vs in VIRTUAL_STUDENTS:
        student_id = f"student_{vs['student_name']}"
        existing = await crud.get_student(db, student_id)
        if existing:
            continue  # 已存在则跳过
        student = await crud.create_student(db, id=student_id, **vs)
        created.append({
            "student_id": student_id,
            "student_name": vs["student_name"],
            "profile": vs,
        })
    await db.commit()

    return {
        "message": f"已创建 {len(created)} 名虚拟学生",
        "total_available": len(VIRTUAL_STUDENTS),
        "students": created,
    }
