"""
数据库连接管理
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from config import settings
from db.models import Base

# 根据 DATABASE_URL 自动适配数据库驱动：
# - SQLite (sqlite+aiosqlite) 本地开发：无连接池，只保留 busy timeout
# - PostgreSQL (postgresql+asyncpg) Docker 部署：连接池 + asyncpg 专有参数
_is_sqlite = (settings.DATABASE_URL or "").startswith("sqlite")

if _is_sqlite:
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=False,
        connect_args={"timeout": 30},  # SQLite busy timeout（秒）
    )
else:
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=False,
        pool_size=20,
        max_overflow=10,
        pool_pre_ping=True,
        pool_recycle=1800,
        connect_args={
            "timeout": 30,
            "command_timeout": 60,
        },
    )

async_session_factory = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


async def init_db():
    """初始化数据库表"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_migrate_schema)


def _migrate_schema(sync_conn):
    """轻量迁移：为旧库补充新增字段（无 Alembic 时的兼容处理）"""
    from sqlalchemy import inspect, text
    insp = inspect(sync_conn)
    if "learning_resource" in insp.get_table_names():
        cols = {c["name"] for c in insp.get_columns("learning_resource")}
        if "student_id" not in cols:
            sync_conn.execute(text("ALTER TABLE learning_resource ADD COLUMN student_id VARCHAR(100)"))
            sync_conn.execute(text(
                "CREATE INDEX IF NOT EXISTS ix_learning_resource_student_id "
                "ON learning_resource (student_id)"
            ))

    # student_mastery 新增 completed_time（能力成长曲线用）
    if "student_mastery" in insp.get_table_names():
        cols = {c["name"] for c in insp.get_columns("student_mastery")}
        if "completed_time" not in cols:
            sync_conn.execute(text("ALTER TABLE student_mastery ADD COLUMN completed_time DATETIME"))

    # 课程强隔离：为若干表补充 course 列（旧库升级用；新库由 create_all 直接建出）
    _add_course_col(sync_conn, insp, "questionnaire_result")
    _add_course_col(sync_conn, insp, "study_setting")
    _add_course_col(sync_conn, insp, "pomodoro_session")
    _add_course_col(sync_conn, insp, "answer_record")

    # study_setting 唯一约束由 (student_id) 升级为 (student_id, course)：
    # 表级 UNIQUE(student_id) 约束在 SQLite 中是不可 DROP 的 autoindex，只能重建表。
    if "study_setting" in insp.get_table_names():
        old_uc = [
            c for c in insp.get_unique_constraints("study_setting")
            if sorted(c.get("column_names") or []) == ["student_id"]
        ]
        if old_uc:
            _rebuild_study_setting(sync_conn)


def _rebuild_study_setting(sync_conn):
    """重建 study_setting 表：去掉旧的 UNIQUE(student_id) 约束，改为 (student_id, course)"""
    from sqlalchemy import text
    sync_conn.execute(text(
        """
        CREATE TABLE study_setting_new (
            id VARCHAR NOT NULL,
            student_id VARCHAR NOT NULL,
            course VARCHAR(50) DEFAULT '',
            daily_goal INTEGER,
            focus_min INTEGER,
            break_min INTEGER,
            create_time DATETIME,
            update_time DATETIME,
            PRIMARY KEY (id),
            CONSTRAINT uq_study_setting_student_course UNIQUE (student_id, course),
            FOREIGN KEY(student_id) REFERENCES student_profile (id)
        )
        """
    ))
    # 旧数据 course 回填为学生当前课程，保证唯一约束不冲突
    sync_conn.execute(text(
        """
        INSERT INTO study_setting_new
            (id, student_id, course, daily_goal, focus_min, break_min, create_time, update_time)
        SELECT
            id, student_id,
            COALESCE(NULLIF(course, ''), (
                SELECT course FROM student_profile
                WHERE student_profile.id = study_setting.student_id
            ), '人工智能导论'),
            daily_goal, focus_min, break_min, create_time, update_time
        FROM study_setting
        """
    ))
    sync_conn.execute(text("DROP TABLE study_setting"))
    sync_conn.execute(text("ALTER TABLE study_setting_new RENAME TO study_setting"))
    sync_conn.execute(text(
        "CREATE INDEX IF NOT EXISTS ix_study_setting_student_id ON study_setting (student_id)"
    ))


def _add_course_col(sync_conn, insp, table_name):
    """为指定表补充 course 列（若缺失），并尽量按学生当前课程回填旧数据"""
    from sqlalchemy import text
    if table_name not in insp.get_table_names():
        return
    cols = {c["name"] for c in insp.get_columns(table_name)}
    if "course" in cols:
        return
    sync_conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN course VARCHAR(50) DEFAULT ''"))
    # 回填：旧数据归属该生当前课程
    if table_name in ("questionnaire_result", "study_setting", "pomodoro_session", "answer_record"):
        sync_conn.execute(text(
            f"UPDATE {table_name} SET course = COALESCE(("
            "SELECT course FROM student_profile WHERE student_profile.id = "
            f"{table_name}.student_id), '人工智能导论') WHERE course IS NULL OR course = ''"
        ))


async def get_db() -> AsyncSession:
    """获取数据库会话"""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
