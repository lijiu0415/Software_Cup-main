"""
自适应学习路径接口 - GET /api/path/get_path
"""
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from db.database import get_db
from db import crud
from kg.kg_engine import kg_engine
from agents.path_agent import plan_learning_path
from utils.security import AuthUser, get_current_user, resolve_student_id

router = APIRouter(prefix="/api/path", tags=["学习路径"])


class PathItem(BaseModel):
    kp_id: str
    name: str
    description: str
    chapter_id: str
    difficulty: int
    mastery: float
    priority_score: float


class LearningPathResponse(BaseModel):
    student_id: str
    path: list
    completed: list = []
    total: int


async def _build_completed_list(db: AsyncSession, student, all_masteries) -> list:
    """按学生课程过滤，构建已完成知识点列表（get_path 与 /plan 复用）"""
    completed_kps = []
    for m in all_masteries:
        if m.completed:
            kp = await crud.get_knowledge_point(db, m.kp_id)
            if kp and (not student.course or kp.course == student.course):
                completed_kps.append({
                    "kp_id": m.kp_id,
                    "name": kp.name,
                    "description": kp.description,
                    "chapter_id": kp.chapter_id,
                    "difficulty": kp.difficulty,
                    "mastery": m.mastery,
                    "completed": True,
                    "priority_score": 0,
                })
    return completed_kps


@router.get("/get_path", response_model=LearningPathResponse)
async def get_learning_path(
    student_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    """获取自适应学习路径"""
    student_id = resolve_student_id(student_id, current_user)
    student = await crud.get_student(db, student_id)
    if not student:
        student = await crud.create_student(db, id=student_id, student_name="新同学")
        await db.commit()

    # 获取学生画像用于路径个性化
    student_profile = {
        "learn_speed": student.learn_speed,
        "base_level": student.base_level,
        "learn_goal": student.learn_goal,
        "cognitive_style": student.cognitive_style,
    }
    path = await kg_engine.compute_learning_path(db, student_id, student_profile, course=student.course)

    # 获取已完成的知识点列表
    all_masteries = await crud.get_all_student_masteries(db, student_id)
    completed_kps = await _build_completed_list(db, student, all_masteries)

    return LearningPathResponse(
        student_id=student_id,
        path=path,
        completed=completed_kps,
        total=len(path),
    )


class PlanRequest(BaseModel):
    student_id: str


@router.post("/plan")
async def plan_path(
    req: PlanRequest,
    db: AsyncSession = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    """AI 规划个性化学习路径（规则算法兜底）"""
    student_id = resolve_student_id(req.student_id, current_user)
    student = await crud.get_student(db, student_id)
    if not student:
        student = await crud.create_student(db, id=student_id, student_name="新同学")
        await db.commit()

    # 完整画像（AI 规划用，含 course 及 6 维特征）
    student_profile = {
        "course": student.course,
        "base_level": student.base_level,
        "learn_goal": student.learn_goal,
        "learn_preference": student.learn_preference,
        "cognitive_style": student.cognitive_style,
        "error_type": student.error_type,
        "learn_speed": student.learn_speed,
    }

    # 候选池 = 规则算法产出（前置满足、未完成），同时作为回退结果
    candidates = await kg_engine.compute_learning_path(
        db, student_id, student_profile, course=student.course
    )

    # 已完成知识点列表
    all_masteries = await crud.get_all_student_masteries(db, student_id)
    completed_kps = await _build_completed_list(db, student, all_masteries)

    # AI 规划（失败/结果为空时回退规则结果）
    summary = ""
    plan = await plan_learning_path(student_profile, candidates)
    if plan and plan.get("path"):
        summary = plan.get("summary") or ""
        reason_map = {p["kp_id"]: p["reason"] for p in plan["path"]}
        by_id = {c["kp_id"]: c for c in candidates}
        path = []
        covered = set()
        for p in plan["path"]:
            c = by_id.get(p["kp_id"])
            if not c:
                continue
            covered.add(p["kp_id"])
            path.append({**c, "reason": reason_map.get(p["kp_id"], "")})
        # 补充 AI 未覆盖的候选（如超出候选上限者），按规则顺序追加到末尾
        for c in candidates:
            if c["kp_id"] not in covered:
                path.append({**c, "reason": ""})
        source = "ai"
    else:
        path = [{**c, "reason": ""} for c in candidates]
        source = "rule"

    return {
        "student_id": student_id,
        "summary": summary,
        "path": path,
        "completed": completed_kps,
        "total": len(path),
        "source": source,
    }


@router.get("/course_progress")
async def get_course_progress(
    student_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    """获取各科目的学习完成度（真实统计）"""
    student_id = resolve_student_id(student_id, current_user)
    kps = await crud.get_knowledge_points(db)
    masteries = await crud.get_all_student_masteries(db, student_id)
    completed_ids = {m.kp_id for m in masteries if m.completed}

    course_total = {}
    course_done = {}
    for kp in kps:
        c = kp.course or "未分类"
        course_total[c] = course_total.get(c, 0) + 1
        if kp.kp_id in completed_ids:
            course_done[c] = course_done.get(c, 0) + 1

    courses = []
    for c, total in course_total.items():
        done = course_done.get(c, 0)
        courses.append({
            "course": c,
            "total": total,
            "completed": done,
            "progress": round(done / total * 100) if total else 0,
        })

    return {"courses": courses}


class MasteryUpdateRequest(BaseModel):
    student_id: str
    kp_id: str
    new_mastery: float


@router.put("/update_mastery")
async def update_mastery(
    req: MasteryUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    """更新知识点掌握度"""
    student_id = resolve_student_id(req.student_id, current_user)
    await kg_engine.update_mastery_after_learning(
        db, student_id, req.kp_id, req.new_mastery
    )
    return {"message": "掌握度已更新", "kp_id": req.kp_id, "new_mastery": req.new_mastery}


class CompleteRequest(BaseModel):
    student_id: str
    kp_id: str


@router.post("/complete_kp")
async def complete_kp(
    req: CompleteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    """标记知识点已完成学习（mastery=1.0, completed=True）"""
    student_id = resolve_student_id(req.student_id, current_user)
    await kg_engine.update_mastery_after_learning(
        db, student_id, req.kp_id, score=1.0, completed=True
    )
    return {"message": "已完成学习", "kp_id": req.kp_id}
