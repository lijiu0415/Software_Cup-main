"""
问卷接口 - POST /api/questionnaire/submit   提交并分析问卷
          GET  /api/questionnaire/status/{id}  查询问卷完成状态
"""
import json
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from db.database import get_db
from db import crud
from agents.questionnaire_rules import derive_profile
from agents.questionnaire_agent import analyze_open
from utils.security import AuthUser, get_current_user, resolve_student_id

router = APIRouter(prefix="/api/questionnaire", tags=["问卷"])


class SubmitRequest(BaseModel):
    student_id: str
    answers: dict = {}
    course: str = "人工智能导论"


@router.post("/submit")
async def submit_questionnaire(
    req: SubmitRequest,
    db: AsyncSession = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    """提交问卷：规则映射 + LLM 开放题分析 → 写入画像与问卷结果（按课程隔离）"""
    student_id = resolve_student_id(req.student_id, current_user)
    answers = req.answers if isinstance(req.answers, dict) else {}
    course = req.course or "人工智能导论"

    student = await crud.get_student(db, student_id)
    if not student:
        student = await crud.create_student(db, id=student_id, student_name="新同学")
        await db.commit()

    # 规则映射 → LLM 精修（失败回退规则结果）；course 决定画像归属课程
    rule_profile = derive_profile(answers, course)
    profile, summary = await analyze_open(answers, rule_profile, course)

    # 写入画像（profile 含 course，会把学生当前课程切到该课程）
    await crud.update_student(db, student_id, **profile)
    # 同步一份课程画像快照（课程切换时恢复）
    await crud.upsert_course_profile(db, student_id, course, profile)

    # 持久化问卷结果
    answers_json = json.dumps(answers, ensure_ascii=False)
    derived_json = json.dumps(profile, ensure_ascii=False)
    await crud.upsert_questionnaire(db, student_id, answers_json, derived_json, summary, course=course)
    await db.commit()

    return {
        "student_id": student_id,
        "course": course,
        "profile": profile,
        "summary": summary,
        "completed": True,
    }


@router.get("/status/{student_id}")
async def get_questionnaire_status(
    student_id: str,
    course: str = Query("人工智能导论"),
    db: AsyncSession = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    """查询问卷完成状态（页面刷新后恢复，按课程隔离）"""
    student_id = resolve_student_id(student_id, current_user)
    record = await crud.get_questionnaire(db, student_id, course=course)

    if not record:
        return {
            "student_id": student_id,
            "course": course,
            "completed": False,
            "answers": {},
            "profile": {},
            "summary": "",
        }

    def _load(text):
        try:
            return json.loads(text) if text else {}
        except (json.JSONDecodeError, TypeError):
            return {}

    return {
        "student_id": student_id,
        "course": course,
        "completed": True,
        "answers": _load(record.answers),
        "profile": _load(record.derived),
        "summary": record.summary or "",
    }
