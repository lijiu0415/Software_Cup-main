"""清空知识图谱数据，强制重新加载双课程"""
import asyncio
from db.database import async_session_factory
from db.models import KnowledgePoint, KpDependency, StudentMastery, LearningResource
from sqlalchemy import delete

async def clear_and_reload():
    async with async_session_factory() as db:
        await db.execute(delete(LearningResource))
        await db.execute(delete(StudentMastery))
        await db.execute(delete(KpDependency))
        await db.execute(delete(KnowledgePoint))
        await db.commit()
        print("旧数据已清除")
    print("请重启后端以加载双课程知识图谱")

if __name__ == "__main__":
    asyncio.run(clear_and_reload())
