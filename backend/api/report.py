"""
学习档案报告接口 - GET /api/report/overview
基于真实学习数据（掌握度 / 章节完成度 / 画像历史）聚合生成
"""
import re
from collections import defaultdict
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import get_db
from db import crud
from utils.security import AuthUser, get_current_user, resolve_student_id

router = APIRouter(prefix="/api/report", tags=["学习报告"])

# 能力雷达 5 维（与前端 DashboardPage.buildAbility 保持一致）
ABILITY_DIMENSIONS = ["理论基础", "实践能力", "算法思维", "工程应用", "知识迁移"]


def _build_ability(profile: dict) -> list:
    """由学生画像推导 5 维能力雷达（无画像数据时为 0）"""
    if not profile:
        return [0, 0, 0, 0, 0]

    base = profile.get("base_level") or 0
    speed = profile.get("learn_speed") or 0
    pref = (profile.get("learn_preference") or "") + (profile.get("cognitive_style") or "")
    goal = profile.get("learn_goal") or ""

    def clamp(n):
        return max(0, min(5, int(n)))

    practice = max(base, 4) if any(k in pref for k in ("实践", "代码", "习题")) else base
    algo = max(speed, 4) if any(k in goal for k in ("竞赛", "算法")) else speed
    eng = max(base, 4) if any(k in goal for k in ("就业", "项目", "工程")) else base

    return [clamp(base), clamp(practice), clamp(algo), clamp(eng), clamp(speed)]


def _profile_to_dict(p) -> dict:
    return {
        "base_level": p.base_level,
        "learn_speed": p.learn_speed,
        "learn_preference": p.learn_preference,
        "cognitive_style": p.cognitive_style,
        "learn_goal": p.learn_goal,
    }


def _chapter_label(chapter_id: str) -> str:
    """把 'ai_ch03' / 'sc_ch05' 之类转成 '第3章' 的可读标签"""
    m = re.search(r"ch(\d+)", chapter_id or "")
    if m:
        return f"第{int(m.group(1))}章"
    return chapter_id or "未分类"


@router.get("/overview")
async def get_report_overview(
    student_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    """学习档案总览：掌握度 / 章节完成度 / 学习活跃趋势 / 能力成长 / 总结建议"""
    student_id = resolve_student_id(student_id, current_user)
    student = await crud.get_student(db, student_id)
    course = (student.course if student and student.course else "人工智能导论")

    kps = await crud.get_knowledge_points(db, course=course)
    masteries = await crud.get_all_student_masteries(db, student_id)
    kp_ids = {kp.kp_id for kp in kps}

    # 已掌握 / 未掌握（按 completed 计；无学习记录时天然为 0）
    completed_ids = {m.kp_id for m in masteries if m.completed}
    total = len(kps)
    mastered = sum(1 for kp in kps if kp.kp_id in completed_ids)
    unmastered = total - mastered

    # 章节完成度（按 chapter_id 分组统计）
    chapter_total = defaultdict(int)
    chapter_done = defaultdict(int)
    for kp in kps:
        ch = kp.chapter_id or "未分类"
        chapter_total[ch] += 1
        if kp.kp_id in completed_ids:
            chapter_done[ch] += 1
    chapters = [
        {
            "name": _chapter_label(ch),
            "progress": round(chapter_done[ch] / chapter_total[ch] * 100),
        }
        for ch in sorted(chapter_total.keys())
    ]

    # 学习活跃趋势：近 7 天每日学习（更新掌握度）的知识点数
    today = datetime.now().date()
    day_list = [today - timedelta(days=i) for i in range(6, -1, -1)]
    day_labels = [d.strftime("%m-%d") for d in day_list]
    day_counts = {d: 0 for d in day_list}
    for m in masteries:
        if m.kp_id not in kp_ids:
            continue
        if m.last_learn_time and m.last_learn_time.date() in day_counts:
            day_counts[m.last_learn_time.date()] += 1
    counts = [day_counts[d] for d in day_list]

    # 能力成长对比：期初 = 首次画像快照，当前 = 实时画像
    history = await crud.get_profile_history(db, student_id)
    initial_profile = _profile_to_dict(history[0]) if history else {}
    current_profile = _profile_to_dict(student) if student else {}
    ability_growth = {
        "dimensions": ABILITY_DIMENSIONS,
        "initial": _build_ability(initial_profile),
        "current": _build_ability(current_profile),
    }

    summary, suggestions = _build_summary_suggestions(
        student, total, mastered, unmastered, chapters
    )

    return {
        "study_trend": {"days": day_labels, "counts": counts},
        "mastery": {"mastered": mastered, "unmastered": unmastered},
        "chapters": chapters,
        "ability_growth": ability_growth,
        "summary": summary,
        "suggestions": suggestions,
    }


@router.get("/chapter_analysis")
async def get_chapter_analysis(
    student_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    """章节分析：各章节完成度 / 平均掌握度 + 章节内知识点明细"""
    student_id = resolve_student_id(student_id, current_user)
    student = await crud.get_student(db, student_id)
    course = student.course if student and student.course else "人工智能导论"

    kps = await crud.get_knowledge_points(db, course=course)
    masteries = await crud.get_all_student_masteries(db, student_id)
    mastery_map = {m.kp_id: m for m in masteries}

    chapter_map = defaultdict(list)
    for kp in kps:
        chapter_map[kp.chapter_id or "未分类"].append(kp)

    chapters = []
    for ch_id in sorted(chapter_map.keys()):
        ch_kps = chapter_map[ch_id]
        total = len(ch_kps)
        completed = sum(
            1 for kp in ch_kps
            if kp.kp_id in mastery_map and mastery_map[kp.kp_id].completed
        )
        avg_mastery = round(
            sum(mastery_map[kp.kp_id].mastery if kp.kp_id in mastery_map else 0.0 for kp in ch_kps) / total,
            2,
        ) if total else 0.0

        chapters.append({
            "chapter_id": ch_id,
            "name": _chapter_label(ch_id),
            "total": total,
            "completed": completed,
            "progress": round(completed / total * 100) if total else 0,
            "avg_mastery": avg_mastery,
            "kps": [
                {
                    "kp_id": kp.kp_id,
                    "name": kp.name,
                    "difficulty": kp.difficulty,
                    "mastery": mastery_map[kp.kp_id].mastery if kp.kp_id in mastery_map else 0.0,
                    "completed": bool(mastery_map[kp.kp_id].completed) if kp.kp_id in mastery_map else False,
                }
                for kp in ch_kps
            ],
        })

    return {"course": course, "chapters": chapters}


@router.get("/ability_growth")
async def get_ability_growth(
    student_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    """能力成长：期初 vs 当前能力雷达 + 各维度成长 + 累计掌握成长曲线"""
    student_id = resolve_student_id(student_id, current_user)
    student = await crud.get_student(db, student_id)
    course = (student.course if student and student.course else "人工智能导论")

    # 能力雷达：期初 = 首次画像快照，当前 = 实时画像
    history = await crud.get_profile_history(db, student_id)
    initial_profile = _profile_to_dict(history[0]) if history else {}
    current_profile = _profile_to_dict(student) if student else {}
    initial = _build_ability(initial_profile)
    current = _build_ability(current_profile)
    growth = [round(current[i] - initial[i], 1) for i in range(len(ABILITY_DIMENSIONS))]

    # 累计掌握成长曲线：按 completed_time（回退 last_learn_time）累计（仅当前课程）
    kps = await crud.get_knowledge_points(db, course=course)
    kp_ids = {kp.kp_id for kp in kps}
    masteries = await crud.get_all_student_masteries(db, student_id)
    times = []
    for m in masteries:
        if m.kp_id not in kp_ids:
            continue
        if not m.completed:
            continue
        t = m.completed_time or m.last_learn_time
        if t:
            times.append(t)

    timeline = {"days": [], "mastered": []}
    if times:
        times.sort()
        end = datetime.now().date()
        start = times[0].date()
        if (end - start).days > 60:  # 跨度过长时只看最近 60 天，避免图表拥挤
            start = end - timedelta(days=59)
        day_list = []
        d = start
        while d <= end:
            day_list.append(d)
            d += timedelta(days=1)

        # 累计计数（含 start 之前已完成的历史基数）
        cum = sum(1 for t in times if t.date() < start)
        ti = 0
        counts = []
        for day in day_list:
            while ti < len(times) and times[ti].date() <= day:
                cum += 1
                ti += 1
            counts.append(cum)
        timeline = {"days": [d.strftime("%m-%d") for d in day_list], "mastered": counts}

    # 画像更新时间线（重新画像记录）
    profile_rounds = [
        {
            "round": h.chat_round,
            "time": h.create_time.strftime("%Y-%m-%d %H:%M") if h.create_time else "",
            "base_level": h.base_level,
            "learn_speed": h.learn_speed,
            "learn_goal": h.learn_goal,
            "cognitive_style": h.cognitive_style,
        }
        for h in history
    ]

    return {
        "dimensions": ABILITY_DIMENSIONS,
        "initial": initial,
        "current": current,
        "growth": growth,
        "timeline": timeline,
        "profile_rounds": profile_rounds,
    }


@router.get("/wrong_analysis")
async def get_wrong_analysis(
    student_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    """错题分析：错题总数/正确率/题型分布/章节分布/易错知识点排行/趋势（按课程隔离）"""
    student_id = resolve_student_id(student_id, current_user)
    student = await crud.get_student(db, student_id)
    course = (student.course if student and student.course else "人工智能导论")
    records = await crud.get_answer_records(db, student_id, course=course)

    total = len(records)
    correct = sum(1 for r in records if r.is_correct)
    wrong = total - correct
    accuracy = round(correct / total * 100, 1) if total else 0.0

    # 知识点元信息（名称 + 章节）
    kps = await crud.get_knowledge_points(db)
    kp_meta = {kp.kp_id: kp for kp in kps}

    # 题型分布
    by_type_map = defaultdict(lambda: {"type": "", "wrong": 0, "total": 0})
    for r in records:
        by_type_map[r.type]["type"] = r.type
        by_type_map[r.type]["total"] += 1
        if not r.is_correct:
            by_type_map[r.type]["wrong"] += 1
    by_type = sorted(by_type_map.values(), key=lambda x: -x["wrong"])

    # 章节 / 知识点分布（只统计错题）
    chapter_wrong = defaultdict(int)
    kp_wrong = defaultdict(int)
    for r in records:
        if r.is_correct or not r.kp_id:
            continue
        kp = kp_meta.get(r.kp_id)
        if kp:
            chapter_wrong[_chapter_label(kp.chapter_id)] += 1
            kp_wrong[r.kp_id] += 1

    by_chapter = [
        {"chapter": ch, "wrong": n}
        for ch, n in sorted(chapter_wrong.items(), key=lambda x: -x[1])
    ]
    by_kp = [
        {
            "kp_id": kp_id,
            "name": kp_meta[kp_id].name if kp_id in kp_meta else kp_id,
            "wrong_count": n,
        }
        for kp_id, n in sorted(kp_wrong.items(), key=lambda x: -x[1])
    ]

    # 错题时间趋势（近 7 天）
    today = datetime.now().date()
    day_list = [today - timedelta(days=i) for i in range(6, -1, -1)]
    day_labels = [d.strftime("%m-%d") for d in day_list]
    day_counts = {d: 0 for d in day_list}
    for r in records:
        if not r.is_correct and r.create_time and r.create_time.date() in day_counts:
            day_counts[r.create_time.date()] += 1
    trend = {"days": day_labels, "wrong": [day_counts[d] for d in day_list]}

    # 错题明细
    wrong_list = [
        {
            "ex_id": r.ex_id,
            "type": r.type,
            "question": r.question,
            "student_answer": r.student_answer,
            "correct_answer": r.correct_answer,
            "analysis": r.analysis,
            "kp_id": r.kp_id,
            "kp_name": kp_meta[r.kp_id].name if r.kp_id in kp_meta else "",
            "chapter": _chapter_label(kp_meta[r.kp_id].chapter_id) if r.kp_id in kp_meta else "未分类",
            "time": r.create_time.strftime("%Y-%m-%d %H:%M") if r.create_time else "",
        }
        for r in records
        if not r.is_correct
    ]

    return {
        "total": total,
        "correct": correct,
        "wrong": wrong,
        "accuracy": accuracy,
        "by_type": by_type,
        "by_chapter": by_chapter,
        "by_kp": by_kp,
        "trend": trend,
        "wrong_list": wrong_list,
    }


def _build_summary_suggestions(student, total, mastered, unmastered, chapters):
    """规则生成学习总结与提升建议（真实数据驱动，无数据时给出引导）"""
    name = (student.student_name if student else None) or "同学"
    course = (student.course if student and student.course else "课程")

    if total == 0:
        return (
            f"{name}，当前课程「{course}」暂无知识点，请先完成画像或选择其他课程。",
            ["完成对话画像，生成个性化学习路径", "切换课程后开始第一节学习"],
        )

    progress = round(mastered / total * 100) if total else 0

    if mastered == 0:
        summary = f"{name}，你已开启「{course}」的学习，尚未完成任何知识点（共 {total} 个）。建议从首个知识点开始，建立稳定的学习节奏。"
    else:
        summary = f"{name}，你在「{course}」中已完成 {mastered}/{total} 个知识点（{progress}%）。"

    weak_chapters = [c for c in chapters if c["progress"] < 60]

    suggestions = []
    if mastered == 0:
        suggestions.append(f"课程共 {total} 个知识点，建议从第 1 章循序渐进开始学习。")
    elif unmastered > 0:
        suggestions.append(f"仍有 {unmastered} 个知识点待掌握，建议按个性化学习路径继续推进。")
    else:
        suggestions.append("本课程知识点已全部掌握，可以挑战更高难度或开启新课程。")

    if weak_chapters:
        names = "、".join(c["name"] for c in weak_chapters[:3])
        suggestions.append(f"章节「{names}」完成度偏低，建议重点复习与巩固。")

    if student and student.error_type:
        suggestions.append(f"你的易错类型为「{student.error_type}」，建议多做针对性练习。")
    if student and student.learn_preference:
        suggestions.append(f"你偏好「{student.learn_preference}」类资源，可优先选用对应资源进行学习。")
    if student and student.learn_goal:
        suggestions.append(f"你的学习目标是「{student.learn_goal}」，建议据此调整学习侧重。")

    return summary, suggestions[:5]
