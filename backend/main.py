"""
A3 个性化学习多智能体系统 - FastAPI入口
"""
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from db.database import init_db
from kg.kg_data import init_kg_data
from rag.chroma_client import init_rag_data, chroma_client
from utils.exceptions import global_exception_handler
from api import chat, resource, path, kg_api, auth, report, exercise, questionnaire, qa, profile


async def _init_rag_background():
    """后台初始化RAG，避免ONNX下载阻塞启动"""
    try:
        await init_rag_data()
        count = chroma_client.count()
        print(f"[OK] RAG知识库初始化完成: {count} 篇文档")
    except Exception as e:
        print(f"[WARN] RAG后台初始化失败: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用启动时初始化"""
    print("=" * 60)
    print("  A3 个性化学习多智能体系统 启动中...")
    print("=" * 60)

    # 初始化数据库
    await init_db()
    print("[OK] 数据库表初始化完成")

    # 初始化知识图谱数据
    from db.database import async_session_factory
    async with async_session_factory() as db:
        await init_kg_data(db)

    # RAG知识库延迟初始化（首次查询时加载，避免ONNX模型下载阻塞启动）
    print("[OK] RAG知识库将在首次查询时初始化")

    print("=" * 60)
    print("  系统启动完成！")
    print("  API文档: http://localhost:8000/docs")
    print("=" * 60)
    yield


app = FastAPI(
    title="A3 个性化学习多智能体系统",
    description="第十五届软件杯A3赛题 - 基于讯飞星火大模型+Astron+知识图谱",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 异常处理
app.add_exception_handler(Exception, global_exception_handler)

# 注册路由
app.include_router(chat.router)
app.include_router(resource.router)
app.include_router(path.router)
app.include_router(kg_api.router)
app.include_router(auth.router)
app.include_router(report.router)
app.include_router(exercise.router)
app.include_router(questionnaire.router)
app.include_router(qa.router)
app.include_router(profile.router)


@app.get("/")
async def root():
    return {
        "name": "A3 个性化学习多智能体系统",
        "version": "1.0.0",
        "docs": "/docs",
        "status": "running",
    }


@app.get("/health")
async def health():
    return {"status": "ok"}
