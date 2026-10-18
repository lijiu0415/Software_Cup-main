"""
数据库CRUD操作
"""
import json
from typing import Optional, List
from sqlalchemy import select, update, and_
from sqlalchemy.ext.asyncio import AsyncSession
from db.models import (
    StudentProfile, KnowledgePoint, KpDependency,
    StudentMastery, LearningResource, ChatRecord, ProfileHistory,
    User, AnswerRecord, QuestionnaireResult, QaMessage, EvaluationRecord,
    ChapterTest, ChapterTestHistory, StudySetting, PomodoroSession, ReviewRecord,
    Textbook, CourseProfile
)


# ==================== 学生画像 CRUD ====================

async def create_student(db: AsyncSession, **kwargs) -> StudentProfile:
    student = StudentProfile(**kwargs)
    db.add(student)
    await db.flush()
    return student


async def get_student(db: AsyncSession, student_id: str) -> Optional[StudentProfile]:
    result = await db.execute(
        select(StudentProfile).where(StudentProfile.id == student_id)
    )
    return result.scalar_one_or_none()


async def update_student(db: AsyncSession, student_id: str, **kwargs) -> Optional[StudentProfile]:
    await db.execute(
        update(StudentProfile)
        .where(StudentProfile.id == student_id)
        .values(**kwargs)
    )
    return await get_student(db, student_id)


# ==================== 课程画像快照 CRUD ====================

def _course_profile_fields(profile: dict) -> dict:
    """从画像 dict 中抽取 6 维字段（仅保留 course_profile 表存在的列）"""
    valid = {c.name for c in CourseProfile.__table__.columns}
    fields = ("base_level", "cognitive_style", "learn_preference",
              "error_type", "learn_speed", "learn_goal")
    return {k: v for k, v in (profile or {}).items() if k in fields and k in valid}


async def get_course_profile(db: AsyncSession, student_id: str, course: str) -> Optional[CourseProfile]:
    """获取某生某课程的画像快照"""
    result = await db.execute(
        select(CourseProfile).where(and_(
            CourseProfile.student_id == student_id,
            CourseProfile.course == course,
        ))
    )
    return result.scalar_one_or_none()


async def upsert_course_profile(db: AsyncSession, student_id: str, course: str, profile: dict) -> CourseProfile:
    """写入或更新某生某课程的画像快照（每生每课程一条）"""
    data = _course_profile_fields(profile)
    existing = await get_course_profile(db, student_id, course)
    if existing:
        for k, v in data.items():
            setattr(existing, k, v)
        await db.flush()
        return existing
    record = CourseProfile(student_id=student_id, course=course, **data)
    db.add(record)
    await db.flush()
    return record


# ==================== 知识点 CRUD ====================

async def get_knowledge_points(db: AsyncSession, course: str = None) -> List[KnowledgePoint]:
    if course:
        result = await db.execute(
            select(KnowledgePoint).where(KnowledgePoint.course == course).order_by(KnowledgePoint.kp_id)
        )
    else:
        result = await db.execute(select(KnowledgePoint).order_by(KnowledgePoint.kp_id))
    return result.scalars().all()


async def get_knowledge_point(db: AsyncSession, kp_id: str) -> Optional[KnowledgePoint]:
    result = await db.execute(
        select(KnowledgePoint).where(KnowledgePoint.kp_id == kp_id)
    )
    return result.scalar_one_or_none()


async def get_kps_by_chapter(db: AsyncSession, chapter_id: str) -> List[KnowledgePoint]:
    result = await db.execute(
        select(KnowledgePoint)
        .where(KnowledgePoint.chapter_id == chapter_id)
        .order_by(KnowledgePoint.kp_id)
    )
    return result.scalars().all()


async def bulk_create_kps(db: AsyncSession, kps: list):
    """批量创建知识点"""
    valid_fields = {c.name for c in KnowledgePoint.__table__.columns}
    for kp_data in kps:
        filtered = {k: v for k, v in kp_data.items() if k in valid_fields}
        kp = KnowledgePoint(**filtered)
        db.add(kp)
    await db.flush()


# ==================== 依赖关系 CRUD ====================

async def get_prerequisites(db: AsyncSession, kp_id: str) -> List[str]:
    """获取知识点的前置依赖"""
    result = await db.execute(
        select(KpDependency.from_kp_id)
        .where(and_(
            KpDependency.to_kp_id == kp_id,
            KpDependency.dependency_type == "strong"
        ))
    )
    return result.scalars().all()


async def get_all_dependencies(db: AsyncSession) -> List[KpDependency]:
    result = await db.execute(select(KpDependency))
    return result.scalars().all()


async def bulk_create_dependencies(db: AsyncSession, deps: list):
    """批量创建依赖关系"""
    valid_fields = {c.name for c in KpDependency.__table__.columns}
    for dep_data in deps:
        filtered = {k: v for k, v in dep_data.items() if k in valid_fields}
        dep = KpDependency(**filtered)
        db.add(dep)
    await db.flush()


# ==================== 掌握度 CRUD ====================

async def get_student_mastery(db: AsyncSession, student_id: str, kp_id: str) -> Optional[StudentMastery]:
    result = await db.execute(
        select(StudentMastery)
        .where(and_(
            StudentMastery.student_id == student_id,
            StudentMastery.kp_id == kp_id
        ))
    )
    return result.scalar_one_or_none()


async def get_all_student_masteries(db: AsyncSession, student_id: str) -> List[StudentMastery]:
    result = await db.execute(
        select(StudentMastery).where(StudentMastery.student_id == student_id)
    )
    return result.scalars().all()


async def upsert_mastery(db: AsyncSession, student_id: str, kp_id: str, mastery: float, completed: bool = False):
    """更新或插入掌握度"""
    from datetime import datetime
    now = datetime.now()
    existing = await get_student_mastery(db, student_id, kp_id)
    if existing:
        existing.mastery = mastery
        if completed:
            if not existing.completed:
                existing.completed_time = now  # 首次完成时记录时间点
            existing.completed = True
        existing.last_learn_time = now
    else:
        record = StudentMastery(
            student_id=student_id,
            kp_id=kp_id,
            mastery=mastery,
            completed=completed,
            completed_time=now if completed else None,
        )
        db.add(record)
    await db.flush()


# ==================== 学习资源 CRUD ====================

async def create_resource(db: AsyncSession, kp_id: str, student_id: str, res_type: str, content: str) -> LearningResource:
    resource = LearningResource(kp_id=kp_id, student_id=student_id, res_type=res_type, content=content)
    db.add(resource)
    await db.flush()
    return resource


async def get_resources_by_kp(db: AsyncSession, kp_id: str, student_id: str) -> List[LearningResource]:
    result = await db.execute(
        select(LearningResource).where(and_(
            LearningResource.kp_id == kp_id,
            LearningResource.student_id == student_id,
        ))
    )
    return result.scalars().all()


# ==================== 对话记录 CRUD ====================

async def add_chat_record(db: AsyncSession, student_id: str, role: str, content: str) -> ChatRecord:
    record = ChatRecord(student_id=student_id, role=role, content=content)
    db.add(record)
    await db.flush()
    return record


async def get_chat_history(db: AsyncSession, student_id: str, limit: int = 20) -> List[ChatRecord]:
    result = await db.execute(
        select(ChatRecord)
        .where(ChatRecord.student_id == student_id)
        .order_by(ChatRecord.create_time.desc())
        .limit(limit)
    )
    return list(reversed(result.scalars().all()))


# ==================== 画像历史 CRUD ====================

async def create_profile_history(db: AsyncSession, student_id: str, chat_round: int, **kwargs) -> ProfileHistory:
    """保存画像历史记录（过滤掉 ProfileHistory 表不存在的字段，如 course）"""
    valid_fields = {c.name for c in ProfileHistory.__table__.columns}
    filtered = {k: v for k, v in kwargs.items() if k in valid_fields}
    record = ProfileHistory(
        student_id=student_id,
        chat_round=chat_round,
        **filtered
    )
    db.add(record)
    await db.flush()
    return record


async def get_profile_history(db: AsyncSession, student_id: str) -> List[ProfileHistory]:
    """获取学生的画像历史"""
    result = await db.execute(
        select(ProfileHistory)
        .where(ProfileHistory.student_id == student_id)
        .order_by(ProfileHistory.chat_round.asc())
    )
    return result.scalars().all()


async def get_next_profile_round(db: AsyncSession, student_id: str) -> int:
    """获取下一次画像记录的序号（基于已有画像历史）"""
    from sqlalchemy import func
    result = await db.execute(
        select(func.max(ProfileHistory.chat_round))
        .where(ProfileHistory.student_id == student_id)
    )
    max_round = result.scalar()
    return (max_round or 0) + 1


async def reset_student_data(db: AsyncSession, student_id: str):
    """重置学生全部学习数据：画像回默认、历史清空、掌握度归零、答题/学习资源/对话记录删除"""
    from sqlalchemy import delete, update as sql_update

    await db.execute(delete(AnswerRecord).where(AnswerRecord.student_id == student_id))
    await db.execute(delete(LearningResource).where(LearningResource.student_id == student_id))
    await db.execute(delete(QuestionnaireResult).where(QuestionnaireResult.student_id == student_id))
    await db.execute(delete(ChatRecord).where(ChatRecord.student_id == student_id))
    await db.execute(delete(QaMessage).where(QaMessage.student_id == student_id))
    await db.execute(delete(EvaluationRecord).where(EvaluationRecord.student_id == student_id))
    await db.execute(delete(ChapterTest).where(ChapterTest.student_id == student_id))
    await db.execute(delete(ChapterTestHistory).where(ChapterTestHistory.student_id == student_id))
    await db.execute(delete(StudySetting).where(StudySetting.student_id == student_id))
    await db.execute(delete(PomodoroSession).where(PomodoroSession.student_id == student_id))
    await db.execute(delete(ReviewRecord).where(ReviewRecord.student_id == student_id))
    await db.execute(delete(Textbook).where(Textbook.student_id == student_id))
    await db.execute(delete(CourseProfile).where(CourseProfile.student_id == student_id))
    await db.execute(delete(ProfileHistory).where(ProfileHistory.student_id == student_id))
    await db.execute(delete(StudentMastery).where(StudentMastery.student_id == student_id))
    await db.execute(
        sql_update(StudentProfile)
        .where(StudentProfile.id == student_id)
        .values(
            base_level=3, cognitive_style="文本型", learn_preference="综合",
            error_type="概念混淆", learn_speed=3, learn_goal="全面掌握",
            course="",
        )
    )
    await db.flush()


# ==================== 问卷 CRUD ====================

async def get_questionnaire(db: AsyncSession, student_id: str, course: str = None) -> Optional[QuestionnaireResult]:
    """获取学生某课程问卷结果（course 为空时不按课程过滤，兼容旧调用）"""
    q = select(QuestionnaireResult).where(QuestionnaireResult.student_id == student_id)
    if course:
        q = q.where(QuestionnaireResult.course == course)
    result = await db.execute(q)
    return result.scalar_one_or_none()


async def upsert_questionnaire(
    db: AsyncSession,
    student_id: str,
    answers: str,
    derived: str = "",
    summary: str = "",
    course: str = "",
) -> QuestionnaireResult:
    """写入或更新学生某课程问卷结果（每生每课程一条）"""
    existing = await get_questionnaire(db, student_id, course=course)
    if existing:
        existing.answers = answers
        existing.derived = derived
        existing.summary = summary
        if course:
            existing.course = course
        await db.flush()
        return existing
    record = QuestionnaireResult(
        student_id=student_id, answers=answers, derived=derived, summary=summary, course=course
    )
    db.add(record)
    await db.flush()
    return record


# ==================== 答疑记录 CRUD ====================

async def add_qa_message(db: AsyncSession, student_id: str, role: str, content: str, sources: str = "") -> QaMessage:
    """新增一条答疑记录"""
    record = QaMessage(student_id=student_id, role=role, content=content, sources=sources)
    db.add(record)
    await db.flush()
    return record


async def get_qa_history(db: AsyncSession, student_id: str, limit: int = 20) -> List[QaMessage]:
    """获取答疑历史：最新 limit 条按时间正序返回"""
    result = await db.execute(
        select(QaMessage)
        .where(QaMessage.student_id == student_id)
        .order_by(QaMessage.create_time.desc())
        .limit(limit)
    )
    return list(reversed(result.scalars().all()))


async def delete_qa_history(db: AsyncSession, student_id: str):
    """清空该生全部答疑记录"""
    from sqlalchemy import delete
    await db.execute(delete(QaMessage).where(QaMessage.student_id == student_id))
    await db.flush()


# ==================== 动态画像评估 CRUD ====================

async def add_evaluation(
    db: AsyncSession,
    student_id: str,
    before_profile: dict,
    after_profile: dict,
    questions: List[str],
    changes: List[dict],
    summary: str,
    applied: bool,
) -> EvaluationRecord:
    """新增一条动态画像评估记录"""
    record = EvaluationRecord(
        student_id=student_id,
        before_profile=json.dumps(before_profile, ensure_ascii=False),
        after_profile=json.dumps(after_profile, ensure_ascii=False),
        questions=json.dumps(questions, ensure_ascii=False),
        changes=json.dumps(changes, ensure_ascii=False),
        summary=summary,
        applied=applied,
    )
    db.add(record)
    await db.flush()
    return record


async def get_evaluation_history(db: AsyncSession, student_id: str, limit: int = 20) -> List[EvaluationRecord]:
    """获取该生动态画像评估历史（新→旧）"""
    result = await db.execute(
        select(EvaluationRecord)
        .where(EvaluationRecord.student_id == student_id)
        .order_by(EvaluationRecord.create_time.desc())
        .limit(limit)
    )
    return result.scalars().all()


async def get_latest_evaluation(db: AsyncSession, student_id: str) -> Optional[EvaluationRecord]:
    """获取该生最近一次动态画像评估"""
    result = await db.execute(
        select(EvaluationRecord)
        .where(EvaluationRecord.student_id == student_id)
        .order_by(EvaluationRecord.create_time.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def count_user_questions_since(db: AsyncSession, student_id: str, since_time=None) -> int:
    """统计该生自某时间点以来的答疑提问数（role=user）"""
    from sqlalchemy import func
    q = select(func.count(QaMessage.id)).where(
        QaMessage.student_id == student_id,
        QaMessage.role == "user",
    )
    if since_time is not None:
        q = q.where(QaMessage.create_time > since_time)
    result = await db.execute(q)
    return result.scalar() or 0


async def get_user_questions(db: AsyncSession, student_id: str, limit: int = 10) -> List[str]:
    """获取该生最近的答疑提问文本（时间正序）"""
    result = await db.execute(
        select(QaMessage.content)
        .where(
            QaMessage.student_id == student_id,
            QaMessage.role == "user",
        )
        .order_by(QaMessage.create_time.desc())
        .limit(limit)
    )
    return list(reversed(result.scalars().all()))


# ==================== 用户认证 CRUD ====================

async def get_user_by_username(db: AsyncSession, username: str) -> Optional[User]:
    """按用户名查询用户（用户名唯一）"""
    result = await db.execute(
        select(User).where(User.username == username)
    )
    return result.scalar_one_or_none()


async def create_user(db: AsyncSession, username: str, password_hash: str, student_id: str) -> User:
    """创建用户账号"""
    user = User(username=username, password_hash=password_hash, student_id=student_id)
    db.add(user)
    await db.flush()
    return user


async def delete_user_account(db: AsyncSession, username: str, student_id: str):
    """注销用户账号：删除用户 + 学生画像 + 全部关联学习数据"""
    from sqlalchemy import delete

    await db.execute(delete(AnswerRecord).where(AnswerRecord.student_id == student_id))
    await db.execute(delete(LearningResource).where(LearningResource.student_id == student_id))
    await db.execute(delete(ProfileHistory).where(ProfileHistory.student_id == student_id))
    await db.execute(delete(StudentMastery).where(StudentMastery.student_id == student_id))
    await db.execute(delete(ChatRecord).where(ChatRecord.student_id == student_id))
    await db.execute(delete(QaMessage).where(QaMessage.student_id == student_id))
    await db.execute(delete(EvaluationRecord).where(EvaluationRecord.student_id == student_id))
    await db.execute(delete(ChapterTest).where(ChapterTest.student_id == student_id))
    await db.execute(delete(ChapterTestHistory).where(ChapterTestHistory.student_id == student_id))
    await db.execute(delete(StudySetting).where(StudySetting.student_id == student_id))
    await db.execute(delete(PomodoroSession).where(PomodoroSession.student_id == student_id))
    await db.execute(delete(ReviewRecord).where(ReviewRecord.student_id == student_id))
    await db.execute(delete(Textbook).where(Textbook.student_id == student_id))
    await db.execute(delete(CourseProfile).where(CourseProfile.student_id == student_id))
    await db.execute(delete(QuestionnaireResult).where(QuestionnaireResult.student_id == student_id))
    await db.execute(delete(User).where(User.username == username))
    await db.execute(delete(StudentProfile).where(StudentProfile.id == student_id))
    await db.flush()


# ==================== 答题记录 CRUD ====================

async def create_answer_record(db: AsyncSession, **kwargs) -> AnswerRecord:
    """新增答题记录"""
    record = AnswerRecord(**kwargs)
    db.add(record)
    await db.flush()
    return record


async def get_answer_records(db: AsyncSession, student_id: str, course: str = None) -> List[AnswerRecord]:
    """获取学生答题记录（新→旧），可按课程过滤"""
    q = select(AnswerRecord).where(AnswerRecord.student_id == student_id)
    if course:
        q = q.where(AnswerRecord.course == course)
    result = await db.execute(q.order_by(AnswerRecord.create_time.desc()))
    return result.scalars().all()


# ==================== 章节测试 CRUD ====================

async def get_chapter_test(db: AsyncSession, student_id: str, chapter_id: str) -> Optional[ChapterTest]:
    """获取该生某章节最新一次整章测试结果"""
    result = await db.execute(
        select(ChapterTest).where(and_(
            ChapterTest.student_id == student_id,
            ChapterTest.chapter_id == chapter_id,
        ))
    )
    return result.scalar_one_or_none()


async def upsert_chapter_test(
    db: AsyncSession,
    student_id: str,
    chapter_id: str,
    course: str,
    correct_count: int,
    wrong_count: int,
    total_count: int,
    accuracy: float,
    detail: str,
    profile_changes: str,
) -> ChapterTest:
    """写入或更新整章测试结果（每生每章仅保留最新，覆盖旧记录）"""
    from datetime import datetime
    existing = await get_chapter_test(db, student_id, chapter_id)
    if existing:
        existing.course = course
        existing.correct_count = correct_count
        existing.wrong_count = wrong_count
        existing.total_count = total_count
        existing.accuracy = accuracy
        existing.detail = detail
        existing.profile_changes = profile_changes
        existing.create_time = datetime.now()
        await db.flush()
        return existing
    record = ChapterTest(
        student_id=student_id,
        chapter_id=chapter_id,
        course=course,
        correct_count=correct_count,
        wrong_count=wrong_count,
        total_count=total_count,
        accuracy=accuracy,
        detail=detail,
        profile_changes=profile_changes,
    )
    db.add(record)
    await db.flush()
    return record


async def add_chapter_test_history(
    db: AsyncSession,
    student_id: str,
    chapter_id: str,
    course: str,
    correct_count: int,
    wrong_count: int,
    total_count: int,
    accuracy: float,
) -> ChapterTestHistory:
    """追加一次测试历史（append-only，往期按正确率存储）"""
    record = ChapterTestHistory(
        student_id=student_id,
        chapter_id=chapter_id,
        course=course,
        correct_count=correct_count,
        wrong_count=wrong_count,
        total_count=total_count,
        accuracy=accuracy,
    )
    db.add(record)
    await db.flush()
    return record


async def get_chapter_test_history(db: AsyncSession, student_id: str, chapter_id: str) -> List[ChapterTestHistory]:
    """获取该生某章节的测试历史（新→旧）"""
    result = await db.execute(
        select(ChapterTestHistory).where(and_(
            ChapterTestHistory.student_id == student_id,
            ChapterTestHistory.chapter_id == chapter_id,
        )).order_by(ChapterTestHistory.create_time.desc())
    )
    return result.scalars().all()


# ==================== 学习设置（每日目标 + 番茄钟） CRUD ====================

async def get_study_setting(db: AsyncSession, student_id: str, course: str = "") -> Optional[StudySetting]:
    """获取学生某课程学习设置（不存在返回 None）"""
    q = select(StudySetting).where(StudySetting.student_id == student_id)
    if course:
        q = q.where(StudySetting.course == course)
    result = await db.execute(q)
    return result.scalar_one_or_none()


async def upsert_study_setting(
    db: AsyncSession,
    student_id: str,
    daily_goal: int,
    focus_min: int,
    break_min: int,
    course: str = "",
) -> StudySetting:
    """写入或更新学习设置（每生每课程一条）"""
    existing = await get_study_setting(db, student_id, course=course)
    if existing:
        existing.daily_goal = daily_goal
        existing.focus_min = focus_min
        existing.break_min = break_min
        if course:
            existing.course = course
        await db.flush()
        return existing
    record = StudySetting(
        student_id=student_id,
        daily_goal=daily_goal,
        focus_min=focus_min,
        break_min=break_min,
        course=course,
    )
    db.add(record)
    await db.flush()
    return record


# ==================== 番茄钟 CRUD ====================

async def create_pomodoro_session(db: AsyncSession, student_id: str, focus_min: int, break_min: int, course: str = "") -> PomodoroSession:
    """新增一次已完成的番茄钟专注记录"""
    record = PomodoroSession(student_id=student_id, focus_min=focus_min, break_min=break_min, course=course)
    db.add(record)
    await db.flush()
    return record


async def get_pomodoro_sessions_since(db: AsyncSession, student_id: str, since, course: str = "") -> List[PomodoroSession]:
    """获取某时间点以来的番茄钟记录（since 为 datetime，可按课程过滤）"""
    q = select(PomodoroSession).where(and_(
        PomodoroSession.student_id == student_id,
        PomodoroSession.create_time >= since,
    ))
    if course:
        q = q.where(PomodoroSession.course == course)
    result = await db.execute(q.order_by(PomodoroSession.create_time.desc()))
    return result.scalars().all()


# ==================== 复习记录（遗忘曲线） CRUD ====================

async def get_review_record(db: AsyncSession, student_id: str, kp_id: str) -> Optional[ReviewRecord]:
    """获取某生某知识点的复习记录"""
    result = await db.execute(
        select(ReviewRecord).where(and_(
            ReviewRecord.student_id == student_id,
            ReviewRecord.kp_id == kp_id,
        ))
    )
    return result.scalar_one_or_none()


async def get_review_records(db: AsyncSession, student_id: str) -> List[ReviewRecord]:
    """获取某生全部复习记录"""
    result = await db.execute(
        select(ReviewRecord).where(ReviewRecord.student_id == student_id)
    )
    return result.scalars().all()


async def mark_reviewed(db: AsyncSession, student_id: str, kp_id: str) -> ReviewRecord:
    """标记知识点已复习：复习次数 +1 并更新最近复习时间"""
    from datetime import datetime
    existing = await get_review_record(db, student_id, kp_id)
    if existing:
        existing.review_count += 1
        existing.last_reviewed_at = datetime.now()
        await db.flush()
        return existing
    record = ReviewRecord(
        student_id=student_id,
        kp_id=kp_id,
        review_count=1,
        last_reviewed_at=datetime.now(),
    )
    db.add(record)
    await db.flush()
    return record


# ==================== 教材（书架） CRUD ====================

async def create_textbook(
    db: AsyncSession,
    student_id: str,
    title: str,
    stored_name: str,
    file_size: int,
    file_type: str,
) -> Textbook:
    """新增一条教材记录"""
    record = Textbook(
        student_id=student_id,
        title=title,
        stored_name=stored_name,
        file_size=file_size,
        file_type=file_type,
    )
    db.add(record)
    await db.flush()
    return record


async def get_textbooks(db: AsyncSession, student_id: str) -> List[Textbook]:
    """获取某生的全部教材（新→旧）"""
    result = await db.execute(
        select(Textbook)
        .where(Textbook.student_id == student_id)
        .order_by(Textbook.create_time.desc())
    )
    return result.scalars().all()


async def get_textbook(db: AsyncSession, textbook_id: str) -> Optional[Textbook]:
    """按 id 获取教材"""
    result = await db.execute(
        select(Textbook).where(Textbook.id == textbook_id)
    )
    return result.scalar_one_or_none()


async def delete_textbook(db: AsyncSession, textbook_id: str) -> None:
    """删除教材记录"""
    from sqlalchemy import delete
    await db.execute(delete(Textbook).where(Textbook.id == textbook_id))
    await db.flush()
