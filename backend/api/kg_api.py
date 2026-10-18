"""
知识图谱接口 - 前置校验、知识点查询、课程切换
"""
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from db.database import get_db
from db import crud
from kg.kg_engine import kg_engine
from utils.security import AuthUser, get_current_user, resolve_student_id

router = APIRouter(prefix="/api/kg", tags=["知识图谱"])


class PrereqCheckResponse(BaseModel):
    is_ok: bool
    lack_kp: list


@router.get("/check_pre/{kp_id}/{student_id}", response_model=PrereqCheckResponse)
async def check_prerequisites(
    kp_id: str,
    student_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    """前置知识点校验"""
    student_id = resolve_student_id(student_id, current_user)
    is_ok, lack_kps = await kg_engine.check_prerequisites(db, kp_id, student_id)
    return PrereqCheckResponse(is_ok=is_ok, lack_kp=lack_kps)


class KPResponse(BaseModel):
    kp_id: str
    name: str
    description: str
    chapter_id: str
    difficulty: int


@router.get("/courses")
async def list_courses(db: AsyncSession = Depends(get_db)):
    """获取所有可用课程列表"""
    kps = await crud.get_knowledge_points(db)
    courses = list(set(kp.course for kp in kps if kp.course))
    # 统计每门课的知识点数量
    result = []
    for c in sorted(courses):
        count = sum(1 for kp in kps if kp.course == c)
        result.append({"course": c, "kp_count": count})
    return {"courses": result}


@router.get("/knowledge_points")
async def list_knowledge_points(
    chapter_id: str = Query(None),
    course: str = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """获取知识点列表（支持按课程过滤）"""
    if chapter_id:
        kps = await crud.get_kps_by_chapter(db, chapter_id)
    else:
        kps = await crud.get_knowledge_points(db, course=course)

    return {
        "total": len(kps),
        "items": [
            {
                "kp_id": kp.kp_id,
                "name": kp.name,
                "description": kp.description,
                "chapter_id": kp.chapter_id,
                "difficulty": kp.difficulty,
                "course": kp.course,
            }
            for kp in kps
        ],
    }


@router.get("/knowledge_point/{kp_id}")
async def get_kp_detail(kp_id: str, db: AsyncSession = Depends(get_db)):
    """获取知识点详情"""
    kp = await crud.get_knowledge_point(db, kp_id)
    if not kp:
        return {"error": "知识点不存在"}

    prereqs = await crud.get_prerequisites(db, kp_id)
    related = await kg_engine.get_related_knowledge_points(db, kp_id)

    return {
        "kp_id": kp.kp_id,
        "name": kp.name,
        "description": kp.description,
        "chapter_id": kp.chapter_id,
        "course": kp.course,
        "difficulty": kp.difficulty,
        "prerequisites": prereqs,
        "related": related,
    }


@router.get("/graph")
async def get_kg_graph(
    course: str = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """获取知识图谱结构（支持按课程过滤）"""
    kps = await crud.get_knowledge_points(db, course=course)
    deps = await crud.get_all_dependencies(db)

    # 过滤依赖：只保留当前课程内的边
    kp_ids = {kp.kp_id for kp in kps}
    filtered_deps = [d for d in deps if d.from_kp_id in kp_ids and d.to_kp_id in kp_ids]

    return {
        "nodes": [
            {"id": kp.kp_id, "name": kp.name, "chapter_id": kp.chapter_id,
             "difficulty": kp.difficulty, "course": kp.course}
            for kp in kps
        ],
        "edges": [
            {"from": d.from_kp_id, "to": d.to_kp_id, "weight": d.weight}
            for d in filtered_deps
        ],
    }
