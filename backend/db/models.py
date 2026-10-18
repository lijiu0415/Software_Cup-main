"""
数据库模型定义 - 6张核心表
"""
import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, Text, DateTime,
    ForeignKey, UniqueConstraint
)
from sqlalchemy.orm import relationship, DeclarativeBase


class Base(DeclarativeBase):
    pass


def gen_uuid():
    return str(uuid.uuid4())


class StudentProfile(Base):
    """学生画像表 - 6维特征"""
    __tablename__ = "student_profile"

    id = Column(String, primary_key=True, default=gen_uuid)
    student_name = Column(String(100), default="匿名学生")
    base_level = Column(Integer, default=3)          # 知识基础 1-5
    cognitive_style = Column(String(50), default="文本型")  # 视觉型/文本型/实践型
    learn_preference = Column(String(50), default="综合")    # 偏好资源类型
    error_type = Column(String(50), default="概念混淆")      # 易错类型
    learn_speed = Column(Integer, default=3)          # 学习速度 1-5
    learn_goal = Column(String(200), default="全面掌握")     # 学习目标
    course = Column(String(50), default="")               # 当前学习课程
    create_time = Column(DateTime, default=datetime.now)
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # 关系
    masteries = relationship("StudentMastery", back_populates="student", cascade="all, delete-orphan")
    chat_records = relationship("ChatRecord", back_populates="student", cascade="all, delete-orphan")


class CourseProfile(Base):
    """课程画像快照表 - 每生每课程一份独立 6 维画像（课程切换时快照/恢复）"""
    __tablename__ = "course_profile"
    __table_args__ = (
        UniqueConstraint("student_id", "course", name="uq_course_profile_student_course"),
    )

    id = Column(String, primary_key=True, default=gen_uuid)
    student_id = Column(String, ForeignKey("student_profile.id"), nullable=False, index=True)
    course = Column(String(50), nullable=False)
    base_level = Column(Integer, default=3)
    cognitive_style = Column(String(50), default="文本型")
    learn_preference = Column(String(50), default="综合")
    error_type = Column(String(50), default="概念混淆")
    learn_speed = Column(Integer, default=3)
    learn_goal = Column(String(200), default="全面掌握")
    create_time = Column(DateTime, default=datetime.now)
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class KnowledgePoint(Base):
    """知识点节点表"""
    __tablename__ = "knowledge_point"

    kp_id = Column(String, primary_key=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, default="")
    chapter_id = Column(String(50), nullable=False, index=True)
    course = Column(String(50), default="", index=True)   # 所属课程
    difficulty = Column(Integer, default=3)          # 难度 1-5
    mastery_threshold = Column(Float, default=0.6)   # 掌握阈值
    create_time = Column(DateTime, default=datetime.now)
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # 关系
    dependencies_as_from = relationship("KpDependency", foreign_keys="KpDependency.from_kp_id", cascade="all, delete-orphan")
    dependencies_as_to = relationship("KpDependency", foreign_keys="KpDependency.to_kp_id", cascade="all, delete-orphan")
    masteries = relationship("StudentMastery", back_populates="knowledge_point", cascade="all, delete-orphan")
    resources = relationship("LearningResource", back_populates="knowledge_point", cascade="all, delete-orphan")


class KpDependency(Base):
    """知识点依赖边表 - DAG强依赖"""
    __tablename__ = "kp_dependency"

    edge_id = Column(String, primary_key=True, default=gen_uuid)
    from_kp_id = Column(String, ForeignKey("knowledge_point.kp_id"), nullable=False, index=True)
    to_kp_id = Column(String, ForeignKey("knowledge_point.kp_id"), nullable=False, index=True)
    dependency_type = Column(String(20), default="strong")  # 固定值: strong
    weight = Column(Float, default=0.8)                       # 依赖权重 0-1
    create_time = Column(DateTime, default=datetime.now)


class StudentMastery(Base):
    """学生知识点掌握度表"""
    __tablename__ = "student_mastery"
    __table_args__ = (
        UniqueConstraint("student_id", "kp_id", name="uq_student_kp"),
    )

    id = Column(String, primary_key=True, default=gen_uuid)
    student_id = Column(String, ForeignKey("student_profile.id"), nullable=False, index=True)
    kp_id = Column(String, ForeignKey("knowledge_point.kp_id"), nullable=False, index=True)
    mastery = Column(Float, default=0.0)              # 掌握度 0-1
    completed = Column(Boolean, default=False)         # 是否已完成学习
    last_learn_time = Column(DateTime, default=datetime.now)
    completed_time = Column(DateTime, nullable=True)   # 完成学习的时间点（能力成长曲线用）

    # 关系
    student = relationship("StudentProfile", back_populates="masteries")
    knowledge_point = relationship("KnowledgePoint", back_populates="masteries")


class LearningResource(Base):
    """学习资源表"""
    __tablename__ = "learning_resource"

    res_id = Column(String, primary_key=True, default=gen_uuid)
    kp_id = Column(String, ForeignKey("knowledge_point.kp_id"), nullable=False, index=True)
    student_id = Column(String(100), nullable=False, index=True)  # 资源归属学生
    res_type = Column(String(20), nullable=False)     # lesson/exercise/code/mindmap
    content = Column(Text, nullable=False)
    create_time = Column(DateTime, default=datetime.now)

    # 关系
    knowledge_point = relationship("KnowledgePoint", back_populates="resources")


class ChatRecord(Base):
    """对话记录表"""
    __tablename__ = "chat_record"

    id = Column(String, primary_key=True, default=gen_uuid)
    student_id = Column(String, ForeignKey("student_profile.id"), nullable=False, index=True)
    role = Column(String(20), nullable=False)         # user/agent/system
    content = Column(Text, nullable=False)
    create_time = Column(DateTime, default=datetime.now)

    # 关系
    student = relationship("StudentProfile", back_populates="chat_records")


class ProfileHistory(Base):
    """画像历史表 - 记录画像变化过程"""
    __tablename__ = "profile_history"

    id = Column(String, primary_key=True, default=gen_uuid)
    student_id = Column(String, ForeignKey("student_profile.id"), nullable=False, index=True)
    base_level = Column(Integer, default=3)
    cognitive_style = Column(String(50), default="文本型")
    learn_preference = Column(String(50), default="综合")
    error_type = Column(String(50), default="概念混淆")
    learn_speed = Column(Integer, default=3)
    learn_goal = Column(String(200), default="全面掌握")
    chat_round = Column(Integer, default=0)  # 第几轮对话
    create_time = Column(DateTime, default=datetime.now)

    # 关系
    student = relationship("StudentProfile")


class User(Base):
    """用户账号表 - 登录认证（用户名唯一）"""
    __tablename__ = "user"

    id = Column(String, primary_key=True, default=gen_uuid)
    username = Column(String(100), nullable=False, unique=True, index=True)
    password_hash = Column(String(200), nullable=False)
    student_id = Column(String(100), nullable=False, index=True)  # 关联 student_profile.id
    create_time = Column(DateTime, default=datetime.now)


class AnswerRecord(Base):
    """学生答题记录表 - 错题分析数据源"""
    __tablename__ = "answer_record"

    id = Column(String, primary_key=True, default=gen_uuid)
    student_id = Column(String, ForeignKey("student_profile.id"), nullable=False, index=True)
    kp_id = Column(String, ForeignKey("knowledge_point.kp_id"), nullable=True, index=True)
    ex_id = Column(String(50), nullable=True)
    course = Column(String(50), default="")              # 所属课程（错题本按课程隔离）
    type = Column(String(20), default="单选题")           # 单选题/多选题/判断题
    question = Column(Text, nullable=False)               # 题干
    options = Column(Text, nullable=True)                 # 选项（JSON 字符串）
    student_answer = Column(Text, nullable=True)          # 学生作答（展示文本）
    correct_answer = Column(Text, nullable=True)          # 正确答案（展示文本）
    is_correct = Column(Boolean, default=False)
    analysis = Column(Text, default="")                   # 解析
    create_time = Column(DateTime, default=datetime.now)


class QuestionnaireResult(Base):
    """问卷结果表 - 用户评估问卷作答 + 推导画像"""
    __tablename__ = "questionnaire_result"

    id = Column(String, primary_key=True, default=gen_uuid)
    student_id = Column(String, ForeignKey("student_profile.id"), nullable=False, index=True)
    course = Column(String(50), default="")              # 所属课程（每生每课程一份问卷）
    answers = Column(Text, nullable=False)               # 原始作答 JSON 字符串
    derived = Column(Text, default="")                    # 推导画像 JSON 字符串
    summary = Column(Text, default="")                    # LLM 画像摘要
    create_time = Column(DateTime, default=datetime.now)


class QaMessage(Base):
    """答疑记录表 - 学习过程中的课程答疑（独立于画像对话的 ChatRecord）"""
    __tablename__ = "qa_message"

    id = Column(String, primary_key=True, default=gen_uuid)
    student_id = Column(String, ForeignKey("student_profile.id"), nullable=False, index=True)
    role = Column(String(20), nullable=False)         # user / assistant
    content = Column(Text, nullable=False)
    sources = Column(Text, default="")                # assistant 消息的 RAG 出处 JSON
    create_time = Column(DateTime, default=datetime.now)


class EvaluationRecord(Base):
    """动态画像评估记录表 - 评估Agent 分析答疑提问后调整画像的过程"""
    __tablename__ = "evaluation_record"

    id = Column(String, primary_key=True, default=gen_uuid)
    student_id = Column(String, ForeignKey("student_profile.id"), nullable=False, index=True)
    before_profile = Column(Text, default="")         # 评估前画像 JSON
    after_profile = Column(Text, default="")          # 评估后画像 JSON
    questions = Column(Text, default="")              # 参与分析的用户提问 JSON 数组
    changes = Column(Text, default="")                # 逐维变更 JSON [{field,value,confidence,reason}]
    summary = Column(Text, default="")                # LLM 评估结论摘要
    applied = Column(Boolean, default=False)          # 是否实际调整了画像
    create_time = Column(DateTime, default=datetime.now)


class ChapterTest(Base):
    """章节整章测试结果表 - 每生每章仅保留最新一次"""
    __tablename__ = "chapter_test"
    __table_args__ = (
        UniqueConstraint("student_id", "chapter_id", name="uq_student_chapter"),
    )

    id = Column(String, primary_key=True, default=gen_uuid)
    student_id = Column(String, ForeignKey("student_profile.id"), nullable=False, index=True)
    chapter_id = Column(String, nullable=False, index=True)
    course = Column(String(50), default="")
    correct_count = Column(Integer, default=0)
    wrong_count = Column(Integer, default=0)
    total_count = Column(Integer, default=0)
    accuracy = Column(Float, default=0.0)
    detail = Column(Text, default="")
    profile_changes = Column(Text, default="")
    create_time = Column(DateTime, default=datetime.now)


class ChapterTestHistory(Base):
    """章节测试历史表 - append-only，往期正确率"""
    __tablename__ = "chapter_test_history"

    id = Column(String, primary_key=True, default=gen_uuid)
    student_id = Column(String, ForeignKey("student_profile.id"), nullable=False, index=True)
    chapter_id = Column(String, nullable=False, index=True)
    course = Column(String(50), default="")
    correct_count = Column(Integer, default=0)
    wrong_count = Column(Integer, default=0)
    total_count = Column(Integer, default=0)
    accuracy = Column(Float, default=0.0)
    create_time = Column(DateTime, default=datetime.now)


class StudySetting(Base):
    """学习设置表 - 每日目标 + 番茄钟时长（每生每课程一条）"""
    __tablename__ = "study_setting"
    __table_args__ = (
        UniqueConstraint("student_id", "course", name="uq_study_setting_student_course"),
    )

    id = Column(String, primary_key=True, default=gen_uuid)
    student_id = Column(String, ForeignKey("student_profile.id"), nullable=False, index=True)
    course = Column(String(50), default="")      # 所属课程（每日目标/番茄钟按课程隔离）
    daily_goal = Column(Integer, default=3)      # 每日学习目标（知识点数）
    focus_min = Column(Integer, default=25)      # 番茄钟专注时长（分钟）
    break_min = Column(Integer, default=5)       # 番茄钟休息时长（分钟）
    create_time = Column(DateTime, default=datetime.now)
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class PomodoroSession(Base):
    """番茄钟记录表 - 每次完成的专注时段（append-only，供统计）"""
    __tablename__ = "pomodoro_session"

    id = Column(String, primary_key=True, default=gen_uuid)
    student_id = Column(String, ForeignKey("student_profile.id"), nullable=False, index=True)
    course = Column(String(50), default="")      # 所属课程（番茄钟统计按课程隔离）
    focus_min = Column(Integer, default=25)
    break_min = Column(Integer, default=5)
    create_time = Column(DateTime, default=datetime.now)


class ReviewRecord(Base):
    """复习记录表 - 遗忘曲线复习次数与最近复习时间（每生每知识点一条）"""
    __tablename__ = "review_record"
    __table_args__ = (
        UniqueConstraint("student_id", "kp_id", name="uq_review_student_kp"),
    )

    id = Column(String, primary_key=True, default=gen_uuid)
    student_id = Column(String, ForeignKey("student_profile.id"), nullable=False, index=True)
    kp_id = Column(String, ForeignKey("knowledge_point.kp_id"), nullable=False, index=True)
    review_count = Column(Integer, default=0)        # 已完成复习次数
    last_reviewed_at = Column(DateTime, nullable=True)  # 最近一次复习时间
    create_time = Column(DateTime, default=datetime.now)


class Textbook(Base):
    """教材表 - 用户自定义上传的教材（书架）"""
    __tablename__ = "textbook"

    id = Column(String, primary_key=True, default=gen_uuid)
    student_id = Column(String, ForeignKey("student_profile.id"), nullable=False, index=True)
    title = Column(String(255), nullable=False)        # 原文件名（展示用）
    stored_name = Column(String(255), nullable=False)  # 磁盘存储文件名（uuid.扩展名）
    file_size = Column(Integer, default=0)             # 字节数
    file_type = Column(String(20), default="")         # 扩展名（小写、不含点）
    create_time = Column(DateTime, default=datetime.now)
