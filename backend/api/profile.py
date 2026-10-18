"""
个人资料接口 - 学习设置 / 每日目标 / 番茄钟 / 遗忘曲线复习提醒
"""
import math
import re
import uuid
from datetime import datetime, timedelta
from pathlib import Path

import aiofiles
from fastapi import APIRouter, Depends, Query, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import get_db
from db import crud
from utils import files
from utils.security import AuthUser, get_current_user, resolve_student_id
from agents.diagnose_agent import DEFAULTS

router = APIRouter(prefix="/api/profile", tags=["个人资料"])

# 艾宾浩斯遗忘曲线复习间隔（天），第 N 次复习后按第 N 档间隔再提醒
REVIEW_INTERVALS = [1, 2, 4, 7, 15, 30]

DEFAULT_SETTINGS = {"daily_goal": 3, "focus_min": 25, "break_min": 5}


def _chapter_label(chapter_id: str) -> str:
    """把 'ai_ch03' 之类转成 '第3章' 的可读标签"""
    m = re.search(r"ch(\d+)", chapter_id or "")
    if m:
        return f"第{int(m.group(1))}章"
    return chapter_id or "未分类"


def _retention(days_since: int, interval_days: int) -> int:
    """按指数衰减估算记忆保持度（%），interval_days 为当前目标复习间隔"""
    stability = max(1, interval_days)
    return max(0, round(100 * math.exp(-days_since / stability)))


async def _build_due_reviews(db: AsyncSession, student_id: str, course: str = None) -> list:
    """计算待复习知识点（遗忘曲线到期），可按课程过滤"""
    masteries = await crud.get_all_student_masteries(db, student_id)
    kps = await crud.get_knowledge_points(db, course=course)
    kp_map = {kp.kp_id: kp for kp in kps}
    reviews = {r.kp_id: r for r in await crud.get_review_records(db, student_id)}

    now = datetime.now()
    due = []
    for m in masteries:
        kp = kp_map.get(m.kp_id)
        if course and kp is None:
            continue  # 非当前课程知识点，跳过
        if not m.completed:
            continue
        base = None
        rr = reviews.get(m.kp_id)
        if rr and rr.last_reviewed_at:
            base = rr.last_reviewed_at
        elif m.completed_time:
            base = m.completed_time
        elif m.last_learn_time:
            base = m.last_learn_time
        if not base:
            continue

        review_count = rr.review_count if rr else 0
        interval = REVIEW_INTERVALS[min(review_count, len(REVIEW_INTERVALS) - 1)]
        due_at = base + timedelta(days=interval)
        if now < due_at:
            continue

        days_since = (now - base).days
        kp = kp_map.get(m.kp_id)
        due.append({
            "kp_id": m.kp_id,
            "name": kp.name if kp else m.kp_id,
            "chapter": _chapter_label(kp.chapter_id) if kp else "未分类",
            "review_count": review_count,
            "days_since": days_since,
            "retention": _retention(days_since, interval),
            "next_interval": interval,
        })

    due.sort(key=lambda x: -x["days_since"])  # 逾期最久的排前
    return due


@router.get("/summary/{student_id}")
async def get_profile_summary(
    student_id: str,
    course: str = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    """个人资料总览：设置 + 今日新完成 + 番茄钟今日统计 + 待复习列表（按课程隔离）"""
    student_id = resolve_student_id(student_id, current_user)

    # course 未传时回退到学生当前课程
    if not course:
        student = await crud.get_student(db, student_id)
        course = (student.course if student and student.course else "人工智能导论")

    setting = await crud.get_study_setting(db, student_id, course=course)
    settings = {
        "daily_goal": setting.daily_goal if setting else DEFAULT_SETTINGS["daily_goal"],
        "focus_min": setting.focus_min if setting else DEFAULT_SETTINGS["focus_min"],
        "break_min": setting.break_min if setting else DEFAULT_SETTINGS["break_min"],
    }

    # 今日新完成的知识点数（completed_time 为今天，且属于当前课程）
    today = datetime.now().date()
    kps = await crud.get_knowledge_points(db, course=course)
    kp_ids = {kp.kp_id for kp in kps}
    masteries = await crud.get_all_student_masteries(db, student_id)
    today_completed = 0
    for m in masteries:
        if m.kp_id not in kp_ids:
            continue
        if not m.completed:
            continue
        t = m.completed_time or m.last_learn_time
        if t and t.date() == today:
            today_completed += 1

    # 今日番茄钟统计
    today_start = datetime.combine(today, datetime.min.time())
    sessions = await crud.get_pomodoro_sessions_since(db, student_id, today_start, course=course)
    pomodoro_today = {
        "count": len(sessions),
        "focus_minutes": sum(s.focus_min for s in sessions),
    }

    due_reviews = await _build_due_reviews(db, student_id, course=course)

    return {
        "course": course,
        "settings": settings,
        "today_completed": today_completed,
        "pomodoro_today": pomodoro_today,
        "due_reviews": due_reviews,
        "due_count": len(due_reviews),
    }


@router.get("/settings/{student_id}")
async def get_settings(
    student_id: str,
    course: str = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    """获取学习设置（不存在时返回默认值，按课程隔离）"""
    student_id = resolve_student_id(student_id, current_user)
    if not course:
        student = await crud.get_student(db, student_id)
        course = (student.course if student and student.course else "人工智能导论")
    setting = await crud.get_study_setting(db, student_id, course=course)
    if setting:
        return {"daily_goal": setting.daily_goal, "focus_min": setting.focus_min, "break_min": setting.break_min}
    return dict(DEFAULT_SETTINGS)


class SettingsRequest(BaseModel):
    student_id: str
    daily_goal: int = 3
    focus_min: int = 25
    break_min: int = 5
    course: str = "人工智能导论"


@router.put("/settings")
async def update_settings(
    req: SettingsRequest,
    db: AsyncSession = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    """更新学习设置（每日目标 / 番茄钟时长，按课程隔离）"""
    student_id = resolve_student_id(req.student_id, current_user)
    daily_goal = max(1, min(50, int(req.daily_goal)))
    focus_min = max(1, min(180, int(req.focus_min)))
    break_min = max(0, min(60, int(req.break_min)))
    course = req.course or "人工智能导论"
    await crud.upsert_study_setting(db, student_id, daily_goal, focus_min, break_min, course=course)
    return {"daily_goal": daily_goal, "focus_min": focus_min, "break_min": break_min}


class PomodoroRequest(BaseModel):
    student_id: str
    focus_min: int = 25
    break_min: int = 5
    course: str = "人工智能导论"


@router.post("/pomodoro")
async def complete_pomodoro(
    req: PomodoroRequest,
    db: AsyncSession = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    """记录一次完成的番茄钟专注时段，返回今日累计统计（按课程隔离）"""
    student_id = resolve_student_id(req.student_id, current_user)
    course = req.course or "人工智能导论"
    await crud.create_pomodoro_session(db, student_id, req.focus_min, req.break_min, course=course)

    today = datetime.now().date()
    today_start = datetime.combine(today, datetime.min.time())
    sessions = await crud.get_pomodoro_sessions_since(db, student_id, today_start, course=course)
    return {
        "count": len(sessions),
        "focus_minutes": sum(s.focus_min for s in sessions),
    }


class ReviewRequest(BaseModel):
    student_id: str


@router.post("/review/{kp_id}")
async def mark_reviewed(
    kp_id: str,
    req: ReviewRequest,
    db: AsyncSession = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    """标记知识点已复习：复习次数 +1，更新最近复习时间与学习时间"""
    student_id = resolve_student_id(req.student_id, current_user)
    record = await crud.mark_reviewed(db, student_id, kp_id)

    # 复习行为同步刷新掌握度时间（不影响 completed_time，故不计入每日目标）
    mastery = await crud.get_student_mastery(db, student_id, kp_id)
    if mastery:
        mastery.last_learn_time = datetime.now()

    return {"ok": True, "kp_id": kp_id, "review_count": record.review_count}


# ==================== 课程切换（学习数据按课程强隔离） ====================

def _profile_of(student) -> dict:
    """从 StudentProfile 抽取 6 维画像（供课程快照/切换返回）"""
    return {
        "base_level": student.base_level,
        "cognitive_style": student.cognitive_style,
        "learn_preference": student.learn_preference,
        "error_type": student.error_type,
        "learn_speed": student.learn_speed,
        "learn_goal": student.learn_goal,
    }


class CourseSwitchRequest(BaseModel):
    student_id: str
    course: str


@router.post("/course/switch")
async def switch_course(
    req: CourseSwitchRequest,
    db: AsyncSession = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    """切换当前课程：快照旧课程画像，载入新课程画像（或默认），刷新课程完成态与设置"""
    student_id = resolve_student_id(req.student_id, current_user)
    course = req.course or "人工智能导论"

    student = await crud.get_student(db, student_id)
    if not student:
        student = await crud.create_student(db, id=student_id, student_name="新同学")
        await db.commit()
        student = await crud.get_student(db, student_id)

    old_course = student.course or "人工智能导论"

    # 1) 把当前活动画像快照到旧课程
    await crud.upsert_course_profile(db, student_id, old_course, _profile_of(student))

    # 2) 载入新课程画像快照；不存在则用默认画像
    snap = await crud.get_course_profile(db, student_id, course)
    if snap:
        new_profile = {
            "base_level": snap.base_level,
            "cognitive_style": snap.cognitive_style,
            "learn_preference": snap.learn_preference,
            "error_type": snap.error_type,
            "learn_speed": snap.learn_speed,
            "learn_goal": snap.learn_goal,
        }
    else:
        new_profile = {
            "base_level": DEFAULTS["base_level"],
            "cognitive_style": DEFAULTS["cognitive_style"],
            "learn_preference": DEFAULTS["learn_preference"],
            "error_type": DEFAULTS["error_type"],
            "learn_speed": DEFAULTS["learn_speed"],
            "learn_goal": DEFAULTS["learn_goal"],
        }

    # 3) 更新活动画像并切换课程
    await crud.update_student(db, student_id, course=course, **new_profile)
    await db.commit()

    # 4) 组装返回：新课程画像 + 问卷完成态 + 学习设置
    student = await crud.get_student(db, student_id)
    questionnaire = await crud.get_questionnaire(db, student_id, course=course)
    setting = await crud.get_study_setting(db, student_id, course=course)

    profile = {
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
        "questionnaire_complete": questionnaire is not None,
    }
    settings = {
        "daily_goal": setting.daily_goal if setting else DEFAULT_SETTINGS["daily_goal"],
        "focus_min": setting.focus_min if setting else DEFAULT_SETTINGS["focus_min"],
        "break_min": setting.break_min if setting else DEFAULT_SETTINGS["break_min"],
    }

    return {
        "course": course,
        "profile": profile,
        "questionnaire_complete": questionnaire is not None,
        "settings": settings,
    }


# ==================== 书架（教材上传 / 列表 / 下载 / 删除） ====================

def _serialize_textbook(t) -> dict:
    return {
        "id": t.id,
        "title": t.title,
        "file_size": t.file_size,
        "file_type": t.file_type,
        "create_time": t.create_time.strftime("%Y-%m-%d %H:%M") if t.create_time else "",
    }


@router.post("/textbooks")
async def upload_textbook(
    student_id: str = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    """上传教材到书架（支持 pdf/docx/ppt/txt/md/图片等）"""
    student_id = resolve_student_id(student_id, current_user)
    title = Path(file.filename or "教材").name.strip() or "教材"
    ext = Path(title).suffix.lstrip(".").lower()
    if not ext or ext not in files.ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"不支持的文件类型：{ext or '未知'}")

    files.ensure_upload_dir()
    stored_name = f"{uuid.uuid4().hex}.{ext}"
    dest = files.textbook_path(stored_name)
    size = 0
    try:
        async with aiofiles.open(dest, "wb") as out:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                if size > files.MAX_UPLOAD_BYTES:
                    raise HTTPException(status_code=413, detail="文件过大（上限 50MB）")
                await out.write(chunk)
    except Exception:
        files.delete_textbook_file(stored_name)
        raise

    record = await crud.create_textbook(db, student_id, title, stored_name, size, ext)
    return _serialize_textbook(record)


@router.get("/textbooks/{student_id}")
async def list_textbooks(
    student_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    """获取某生书架上的全部教材（新→旧）"""
    student_id = resolve_student_id(student_id, current_user)
    textbooks = await crud.get_textbooks(db, student_id)
    return {"items": [_serialize_textbook(t) for t in textbooks]}


@router.get("/textbooks/{textbook_id}/download")
async def download_textbook(
    textbook_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    """下载 / 预览教材文件"""
    tb = await crud.get_textbook(db, textbook_id)
    if not tb:
        raise HTTPException(status_code=404, detail="教材不存在")
    path = files.textbook_path(tb.stored_name)
    if not path.exists():
        raise HTTPException(status_code=404, detail="文件已丢失")
    return FileResponse(path, filename=tb.title, content_disposition_type="inline")


@router.delete("/textbooks/{textbook_id}")
async def delete_textbook_endpoint(
    textbook_id: str,
    student_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    """从书架删除教材（同时删除磁盘文件）"""
    student_id = resolve_student_id(student_id, current_user)
    tb = await crud.get_textbook(db, textbook_id)
    if not tb or tb.student_id != student_id:
        raise HTTPException(status_code=404, detail="教材不存在")
    files.delete_textbook_file(tb.stored_name)
    await crud.delete_textbook(db, textbook_id)
    return {"ok": True}
