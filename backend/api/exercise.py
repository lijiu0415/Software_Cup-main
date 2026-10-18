"""
习题接口 - 题库、作答提交、错题本
"""
import json
import random
from typing import Any

from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import get_db
from db import crud
from data.exercise_bank import EXERCISE_BANK
from data.chapter_bank import CHAPTER_NAMES, CHAPTER_BANK
from data.sc_exercise_bank import SC_EXERCISE_BANK
from data.sc_chapter_bank import SC_CHAPTER_NAMES, SC_CHAPTER_BANK
from agents.program_test_agent import generate_program_question, grade_program_answer
from agents.evaluation_agent import _normalize_changes
from utils.security import AuthUser, get_current_user, resolve_student_id

router = APIRouter(prefix="/api/exercise", tags=["习题"])


def _is_sc(chapter_id: str) -> bool:
    """根据章节/题目 ID 前缀判断是否软件安全技术（sc_）"""
    return (chapter_id or "").startswith("sc_")


def _exercise_bank(course: str = None) -> list:
    """按课程返回客观题题库"""
    if course == "软件安全技术":
        return SC_EXERCISE_BANK
    return EXERCISE_BANK


def _find_question(ex_id: str):
    for bank in (EXERCISE_BANK, SC_EXERCISE_BANK):
        for q in bank:
            if q["ex_id"] == ex_id:
                return q
    return None


def _chapter_names(chapter_id: str) -> dict:
    """按章节 ID 前缀返回对应课程的章节名映射"""
    return SC_CHAPTER_NAMES if _is_sc(chapter_id) else CHAPTER_NAMES


def _chapter_bank(chapter_id: str) -> list:
    """按章节 ID 前缀返回对应课程的章节题库"""
    return SC_CHAPTER_BANK if _is_sc(chapter_id) else CHAPTER_BANK


def _course_of_question(q: dict) -> str:
    """由题目 ex_id 前缀判断所属课程"""
    return "软件安全技术" if _is_sc(q.get("ex_id") or "") else "人工智能导论"


def _format_answer(question: dict, answer: Any) -> str:
    """把答案索引/列表转成展示文本"""
    qtype = question["type"]
    options = question.get("options") or []
    if qtype == "多选题":
        if not answer:
            return ""
        return "、".join(options[i] for i in answer if isinstance(i, int) and i < len(options))
    if qtype == "编程题":
        return "（编程题不判分）"
    if answer is None or not isinstance(answer, int) or answer >= len(options):
        return ""
    return options[answer]


def _serialize_question(q: dict) -> dict:
    """取题时不返回答案与解析，但返回编程题参考解答（自评用）"""
    return {
        "ex_id": q["ex_id"],
        "kp_id": q.get("kp_id"),
        "type": q["type"],
        "difficulty": q.get("difficulty", 3),
        "question": q["question"],
        "options": q.get("options") or [],
        "reference_answer": q.get("reference_answer", ""),
    }


async def _chapter_course(db: AsyncSession, student_id: str) -> str:
    """返回学生当前课程（用于章节测试结果落库）"""
    student = await crud.get_student(db, student_id)
    return (student.course or "人工智能导论") if student else "人工智能导论"


async def _chapter_progress(db: AsyncSession, student_id: str, chapter_id: str) -> tuple:
    """返回 (total_kp, completed_kp)，口径同 report.get_chapter_analysis：该章全部知识点数与已完成数"""
    kps = await crud.get_kps_by_chapter(db, chapter_id)
    total = len(kps)
    if total == 0:
        return 0, 0
    kp_ids = {kp.kp_id for kp in kps}
    masteries = await crud.get_all_student_masteries(db, student_id)
    completed = sum(1 for m in masteries if m.kp_id in kp_ids and m.completed)
    return total, completed


def _judge(question: dict, student_answer: Any) -> bool:
    """整章测试判分：多选排序比较；其余索引相等（编程题由调用方跳过）"""
    qtype = question["type"]
    if qtype == "多选题":
        a = sorted([int(x) for x in (question["answer"] or [])])
        b = sorted([int(x) for x in (student_answer or [])])
        return a == b
    return student_answer == question["answer"]


def _apply_test_rules(profile: dict, acc: float, wrong_by_type: dict) -> dict:
    """确定性画像规则：base_level 按正确率增减；error_type 按错题题型主导项调整"""
    changes = []
    updates = {}

    base_level = int(profile.get("base_level") or 3)
    if acc >= 80:
        new_base = min(5, base_level + 1)
    elif acc < 40:
        new_base = max(1, base_level - 1)
    else:
        new_base = base_level
    if new_base != base_level:
        updates["base_level"] = new_base
        changes.append({"field": "base_level", "old": base_level, "new": new_base})

    wrong_total = sum(wrong_by_type.values())
    if wrong_total >= 2:
        concept = wrong_by_type.get("单选题", 0) + wrong_by_type.get("判断题", 0)
        logic = wrong_by_type.get("多选题", 0)
        if concept > logic and concept > 0:
            new_error = "概念混淆"
        elif logic > concept and logic > 0:
            new_error = "逻辑漏洞"
        else:
            new_error = None
        if new_error and new_error != profile.get("error_type"):
            updates["error_type"] = new_error
            changes.append({"field": "error_type", "old": profile.get("error_type"), "new": new_error})

    return {"changes": changes, "updates": updates}


@router.get("/list")
async def list_exercises(course: str = Query(None)):
    """获取题库（不含答案与解析，判分在服务端；按课程隔离）"""
    items = [
        {
            "ex_id": q["ex_id"],
            "kp_id": q.get("kp_id"),
            "type": q["type"],
            "difficulty": q.get("difficulty", 3),
            "question": q["question"],
            "options": q.get("options") or [],
        }
        for q in _exercise_bank(course)
    ]
    return {"total": len(items), "items": items}


class SubmitRequest(BaseModel):
    student_id: str
    ex_id: str
    student_answer: Any = None  # int（单选/判断索引）/ list[int]（多选）/ str（编程题）


@router.post("/submit")
async def submit_answer(
    req: SubmitRequest,
    db: AsyncSession = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    """提交作答：服务端判分并记录"""
    student_id = resolve_student_id(req.student_id, current_user)
    question = _find_question(req.ex_id)
    if not question:
        return {"error": "题目不存在"}

    qtype = question["type"]
    if qtype == "多选题":
        a = sorted([int(x) for x in (question["answer"] or [])])
        b = sorted([int(x) for x in (req.student_answer or [])])
        is_correct = a == b
    elif qtype == "编程题":
        is_correct = True  # 编程题不判分
    else:
        is_correct = req.student_answer == question["answer"]

    correct_text = _format_answer(question, question["answer"])
    student_text = _format_answer(question, req.student_answer)

    # 编程题不记录（不判分，不计入错题统计）
    if qtype != "编程题":
        await crud.create_answer_record(
            db,
            student_id=student_id,
            kp_id=question.get("kp_id"),
            ex_id=question["ex_id"],
            course=_course_of_question(question),
            type=qtype,
            question=question["question"],
            options=json.dumps(question.get("options") or [], ensure_ascii=False),
            student_answer=student_text,
            correct_answer=correct_text,
            is_correct=is_correct,
            analysis=question.get("analysis", ""),
        )

    return {
        "is_correct": is_correct,
        "correct_answer": correct_text,
        "analysis": question.get("analysis", ""),
        "type": qtype,
    }


@router.get("/wrong_book")
async def get_wrong_book(
    student_id: str = Query(...),
    course: str = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    """错题本：做题统计 + 错题明细（按课程隔离）"""
    student_id = resolve_student_id(student_id, current_user)
    records = await crud.get_answer_records(db, student_id, course=course)

    total = len(records)
    correct = sum(1 for r in records if r.is_correct)
    wrong = total - correct
    stats = {"done": total, "correct": correct, "wrong": wrong}

    items = [
        {
            "id": r.id,
            "ex_id": r.ex_id,
            "kp_id": r.kp_id,
            "type": r.type,
            "question": r.question,
            "options": json.loads(r.options) if r.options else [],
            "student_answer": r.student_answer,
            "correct_answer": r.correct_answer,
            "analysis": r.analysis,
            "create_time": r.create_time.strftime("%Y-%m-%d %H:%M") if r.create_time else "",
        }
        for r in records
        if not r.is_correct
    ]

    return {"stats": stats, "items": items}


@router.get("/chapters")
async def list_chapters(
    student_id: str = Query(...),
    course: str = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    """章节列表：解锁状态 + 题目分布（未解锁章节不可测试，按课程隔离）"""
    student_id = resolve_student_id(student_id, current_user)
    if not course:
        course = await _chapter_course(db, student_id)

    bank = SC_CHAPTER_BANK if course == "软件安全技术" else CHAPTER_BANK
    names = SC_CHAPTER_NAMES if course == "软件安全技术" else CHAPTER_NAMES

    chapter_ids = []
    for q in bank:
        if q["chapter_id"] not in chapter_ids:
            chapter_ids.append(q["chapter_id"])

    chapters = []
    for cid in chapter_ids:
        total_kp, completed_kp = await _chapter_progress(db, student_id, cid)
        counts = {}
        for q in bank:
            if q["chapter_id"] == cid:
                counts[q["type"]] = counts.get(q["type"], 0) + 1
        chapters.append({
            "chapter_id": cid,
            "name": names.get(cid, cid),
            "total_kp": total_kp,
            "completed_kp": completed_kp,
            "unlocked": total_kp > 0 and completed_kp == total_kp,
            "question_counts": counts,
        })

    return {"course": course, "chapters": chapters}


@router.get("/test/{chapter_id}")
async def get_chapter_test_questions(
    chapter_id: str,
    student_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    """取整章题目（不含答案与解析）；未解锁返回 403"""
    student_id = resolve_student_id(student_id, current_user)

    questions = [q for q in _chapter_bank(chapter_id) if q["chapter_id"] == chapter_id]
    if not questions:
        raise HTTPException(status_code=404, detail="章节不存在")

    total_kp, completed_kp = await _chapter_progress(db, student_id, chapter_id)
    if not (total_kp > 0 and completed_kp == total_kp):
        raise HTTPException(status_code=403, detail="该章节尚未学完全部知识点，暂无法测试")

    return {
        "chapter_id": chapter_id,
        "name": _chapter_names(chapter_id).get(chapter_id, chapter_id),
        "questions": [_serialize_question(q) for q in questions],
    }


class SubmitTestRequest(BaseModel):
    student_id: str
    chapter_id: str
    answers: list  # [{"ex_id": str, "student_answer": Any}]


@router.post("/submit_test")
async def submit_chapter_test(
    req: SubmitTestRequest,
    db: AsyncSession = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    """提交整章测试：统一判分 + 写入答题记录 + 更新画像 + 落库结果"""
    student_id = resolve_student_id(req.student_id, current_user)
    chapter_id = req.chapter_id

    questions = [q for q in _chapter_bank(chapter_id) if q["chapter_id"] == chapter_id]
    if not questions:
        raise HTTPException(status_code=404, detail="章节不存在")

    total_kp, completed_kp = await _chapter_progress(db, student_id, chapter_id)
    if not (total_kp > 0 and completed_kp == total_kp):
        raise HTTPException(status_code=403, detail="该章节尚未学完全部知识点，暂无法测试")

    course = "软件安全技术" if _is_sc(chapter_id) else "人工智能导论"

    answer_map = {a.get("ex_id"): a.get("student_answer") for a in req.answers}

    judged = [q for q in questions if q["type"] != "编程题"]

    def _has_answer(v) -> bool:
        return v is not None and v != "" and v != []

    missing = [q["ex_id"] for q in judged if not _has_answer(answer_map.get(q["ex_id"]))]
    if missing:
        raise HTTPException(status_code=400, detail="还有题目未作答，请完成全部判分题目后再提交")

    correct = 0
    wrong = 0
    wrong_by_type = {}
    detail = []
    for q in judged:
        student_answer = answer_map.get(q["ex_id"])
        is_correct = _judge(q, student_answer)
        if is_correct:
            correct += 1
        else:
            wrong += 1
            wrong_by_type[q["type"]] = wrong_by_type.get(q["type"], 0) + 1
        correct_text = _format_answer(q, q["answer"])
        student_text = _format_answer(q, student_answer)
        detail.append({
            "ex_id": q["ex_id"],
            "type": q["type"],
            "is_correct": is_correct,
            "student_answer": student_text,
            "correct_answer": correct_text,
            "analysis": q.get("analysis", ""),
            "kp_id": q.get("kp_id"),
        })
        # 全部判分题（对+错）写入 AnswerRecord，实现错题本 + 易错知识点累计
        await crud.create_answer_record(
            db,
            student_id=student_id,
            kp_id=q.get("kp_id"),
            ex_id=q["ex_id"],
            course=course,
            type=q["type"],
            question=q["question"],
            options=json.dumps(q.get("options") or [], ensure_ascii=False),
            student_answer=student_text,
            correct_answer=correct_text,
            is_correct=is_correct,
            analysis=q.get("analysis", ""),
        )

    total = len(judged)
    accuracy = round(correct / total * 100, 1) if total else 0.0

    student = await crud.get_student(db, student_id)
    profile = {
        "base_level": student.base_level if student else 3,
        "error_type": student.error_type if student else "概念混淆",
    }
    rule_result = _apply_test_rules(profile, accuracy, wrong_by_type)
    profile_changes = rule_result["changes"]
    if rule_result["updates"]:
        await crud.update_student(db, student_id, **rule_result["updates"])

    await crud.upsert_chapter_test(
        db,
        student_id=student_id,
        chapter_id=chapter_id,
        course=course,
        correct_count=correct,
        wrong_count=wrong,
        total_count=total,
        accuracy=accuracy,
        detail=json.dumps(detail, ensure_ascii=False),
        profile_changes=json.dumps(profile_changes, ensure_ascii=False),
    )
    await crud.add_chapter_test_history(
        db,
        student_id=student_id,
        chapter_id=chapter_id,
        course=course,
        correct_count=correct,
        wrong_count=wrong,
        total_count=total,
        accuracy=accuracy,
    )

    return {
        "accuracy": accuracy,
        "correct": correct,
        "wrong": wrong,
        "total": total,
        "profile_changes": profile_changes,
        "detail": detail,
    }


class ProgramStartRequest(BaseModel):
    student_id: str
    chapter_id: str


@router.post("/program/start")
async def start_program_test(
    req: ProgramStartRequest,
    db: AsyncSession = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    """编程测试Agent：为该章随机生成一道编程题（不计分，供对话式作答）"""
    student_id = resolve_student_id(req.student_id, current_user)

    if req.chapter_id not in _chapter_names(req.chapter_id):
        raise HTTPException(status_code=404, detail="章节不存在")

    total_kp, completed_kp = await _chapter_progress(db, student_id, req.chapter_id)
    if not (total_kp > 0 and completed_kp == total_kp):
        raise HTTPException(status_code=403, detail="该章节尚未学完全部知识点，暂无法测试")

    student = await crud.get_student(db, student_id)
    profile = {
        "base_level": student.base_level if student else 3,
        "cognitive_style": student.cognitive_style if student else "文本型",
        "learn_preference": student.learn_preference if student else "综合",
        "error_type": student.error_type if student else "概念混淆",
    }
    chapter_name = _chapter_names(req.chapter_id)[req.chapter_id]

    kps = await crud.get_kps_by_chapter(db, req.chapter_id)
    kp_list = [{"kp_id": kp.kp_id, "name": kp.name, "difficulty": kp.difficulty} for kp in kps]

    # 优先 Agent 生成；失败回退到题库静态编程题
    result = None
    try:
        result = await generate_program_question(chapter_name, kp_list, profile)
    except Exception as e:
        print(f"[编程测试Agent] 出题失败: {e}")

    if not result or not result.get("question"):
        bank = [q for q in _chapter_bank(req.chapter_id) if q["chapter_id"] == req.chapter_id and q["type"] == "编程题"]
        if bank:
            q = random.choice(bank)
            kp_name = next((kp["name"] for kp in kp_list if kp["kp_id"] == q.get("kp_id")), "")
            result = {
                "question": q["question"],
                "kp_id": q.get("kp_id"),
                "kp_name": kp_name,
                "difficulty": q.get("difficulty", 3),
            }
        else:
            result = {
                "question": f"请围绕「{chapter_name}」核心算法编写一段 Python 代码并说明思路。",
                "kp_id": None,
                "kp_name": "",
                "difficulty": 3,
            }

    return {
        "chapter_id": req.chapter_id,
        "chapter_name": chapter_name,
        "question": result.get("question"),
        "kp_id": result.get("kp_id"),
        "kp_name": result.get("kp_name"),
        "difficulty": result.get("difficulty", 3),
    }


class ProgramGradeRequest(BaseModel):
    student_id: str
    chapter_id: str
    question: str
    kp_id: str = None
    kp_name: str = None
    student_answer: str


@router.post("/program/grade")
async def grade_program_answer_endpoint(
    req: ProgramGradeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    """编程测试Agent：实时批改编程作答，给出知识点与标准答案；结果不计分，但更新画像"""
    student_id = resolve_student_id(req.student_id, current_user)
    if not (req.question or "").strip() or not (req.student_answer or "").strip():
        raise HTTPException(status_code=400, detail="题目或作答不能为空")

    student = await crud.get_student(db, student_id)
    current_profile = {
        "base_level": student.base_level if student else 3,
        "learn_speed": student.learn_speed if student else 3,
        "cognitive_style": student.cognitive_style if student else "文本型",
        "learn_preference": student.learn_preference if student else "综合",
        "error_type": student.error_type if student else "概念混淆",
    }

    try:
        result = await grade_program_answer(
            req.question, req.kp_id, req.kp_name, req.student_answer, current_profile,
        )
    except Exception as e:
        print(f"[编程测试Agent] 批改失败: {e}")
        result = {
            "correctness": "无法判定",
            "feedback": "批改服务暂时不可用，请稍后再试。",
            "kp_id": req.kp_id,
            "kp_name": req.kp_name,
            "standard_answer": "",
            "profile_changes": [],
        }

    # 受约束画像调整（复用评估Agent的规范化规则）
    changes = _normalize_changes(result.get("profile_changes") or [], current_profile)
    display_changes = []
    if changes:
        updates = {}
        for c in changes:
            updates[c["field"]] = c["value"]
            display_changes.append({
                "field": c["field"],
                "old": current_profile.get(c["field"]),
                "new": c["value"],
            })
        await crud.update_student(db, student_id, **updates)

    return {
        "correctness": result.get("correctness"),
        "feedback": result.get("feedback"),
        "kp_id": result.get("kp_id"),
        "kp_name": result.get("kp_name"),
        "standard_answer": result.get("standard_answer"),
        "profile_changes": display_changes,
    }


@router.get("/result/{chapter_id}")
async def get_chapter_test_result(
    chapter_id: str,
    student_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    """该章最新一次测试结果 + 往期正确率历史"""
    student_id = resolve_student_id(student_id, current_user)

    latest_rec = await crud.get_chapter_test(db, student_id, chapter_id)
    history_recs = await crud.get_chapter_test_history(db, student_id, chapter_id)

    latest = None
    if latest_rec:
        latest = {
            "accuracy": latest_rec.accuracy,
            "correct": latest_rec.correct_count,
            "wrong": latest_rec.wrong_count,
            "total": latest_rec.total_count,
            "detail": json.loads(latest_rec.detail) if latest_rec.detail else [],
            "profile_changes": json.loads(latest_rec.profile_changes) if latest_rec.profile_changes else [],
            "create_time": latest_rec.create_time.strftime("%Y-%m-%d %H:%M:%S") if latest_rec.create_time else "",
        }

    history = [
        {
            "accuracy": r.accuracy,
            "correct": r.correct_count,
            "wrong": r.wrong_count,
            "total": r.total_count,
            "create_time": r.create_time.strftime("%Y-%m-%d %H:%M:%S") if r.create_time else "",
        }
        for r in history_recs
    ]

    return {"latest": latest, "history": history}
