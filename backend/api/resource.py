"""
个性化资源生成接口
- POST /api/resource/generate         标准模式
- POST /api/resource/generate/stream  流式模式（SSE 进度条）
支持缓存：同一知识点只生成一次，后续请求返回缓存
"""
import asyncio
import json
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from db.database import get_db, async_session_factory
from db import crud
from agents.coordinator import coordinator
from rag.chroma_client import chroma_client
from utils.sensitive_filter import check_sensitive_async
from utils.security import AuthUser, get_current_user, resolve_student_id

router = APIRouter(prefix="/api/resource", tags=["资源生成"])


class ResourceRequest(BaseModel):
    student_id: str
    kp_id: str


class ResourceResponse(BaseModel):
    lesson: str = ""
    exercise: str = ""
    code: str = ""
    mindmap: str = ""
    reading: str = ""
    video: str = ""


async def _prepare_generation(db: AsyncSession, student_id: str, kp_id: str) -> dict:
    """准备资源生成所需的全部上下文数据"""
    kp = await crud.get_knowledge_point(db, kp_id)
    if not kp:
        from utils.exceptions import KnowledgePointNotFoundException
        raise KnowledgePointNotFoundException(kp_id)

    student = await crud.get_student(db, student_id)
    if not student:
        from utils.exceptions import StudentNotFoundException
        raise StudentNotFoundException(student_id)

    student_profile = {
        "base_level": student.base_level,
        "cognitive_style": student.cognitive_style,
        "learn_preference": student.learn_preference,
        "error_type": student.error_type,
        "learn_speed": student.learn_speed,
        "learn_goal": student.learn_goal,
        "course": kp.course,
    }

    masteries = await crud.get_all_student_masteries(db, student_id)
    mastery_data = [{m.kp_id: m.mastery} for m in masteries]

    rag_context = ""
    try:
        from rag.chroma_client import ensure_rag_ready
        await ensure_rag_ready()
        rag_results = chroma_client.query(kp.name, n_results=3)
        if rag_results:
            rag_context = "\n".join([r["content"] for r in rag_results])
    except Exception:
        pass

    from kg.kg_engine import kg_engine
    related_kps = await kg_engine.get_related_knowledge_points(db, kp_id)

    return {
        "kp": kp,
        "student_profile": student_profile,
        "mastery_data": mastery_data,
        "rag_context": rag_context,
        "related_kps": related_kps,
    }


@router.post("/generate", response_model=ResourceResponse)
async def generate_resource(
    req: ResourceRequest,
    db: AsyncSession = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    """多智能体并行生成个性化学习资源（支持缓存）"""
    student_id = resolve_student_id(req.student_id, current_user)
    ctx = await _prepare_generation(db, student_id, req.kp_id)
    kp = ctx["kp"]

    # 检查缓存
    existing_resources = await crud.get_resources_by_kp(db, req.kp_id, student_id)
    if existing_resources and len(existing_resources) >= 3:
        cached_results = {}
        for res in existing_resources:
            cached_results[res.res_type] = res.content
        if all(key in cached_results for key in ["lesson", "exercise", "code", "mindmap", "reading", "video"]):
            print(f"[缓存] 命中缓存: {kp.name} ({req.kp_id})")
            return ResourceResponse(**cached_results)

    print(f"[生成] 并行调度多智能体: {kp.name} ({req.kp_id})")
    results = await coordinator.generate_resources(
        student_id=student_id,
        kp_id=req.kp_id,
        kp_name=kp.name,
        kp_description=kp.description,
        student_profile=ctx["student_profile"],
        mastery_data=ctx["mastery_data"],
        rag_context=ctx["rag_context"],
        related_kps=ctx["related_kps"],
    )

    # 保存缓存
    for res_type, content in results.items():
        if content and not content.startswith("生成失败"):
            await crud.create_resource(db, req.kp_id, student_id, res_type, content)
    await db.commit()

    return ResourceResponse(**results)


@router.post("/generate/stream")
async def generate_resource_stream(
    req: ResourceRequest,
    db: AsyncSession = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    """流式并行生成资源（SSE 进度事件）"""
    student_id = resolve_student_id(req.student_id, current_user)
    ctx = await _prepare_generation(db, student_id, req.kp_id)
    kp = ctx["kp"]

    # 检查缓存 - 缓存命中也走流式返回
    existing_resources = await crud.get_resources_by_kp(db, req.kp_id, student_id)
    if existing_resources and len(existing_resources) >= 3:
        cached_results = {}
        for res in existing_resources:
            cached_results[res.res_type] = res.content
        if all(key in cached_results for key in ["lesson", "exercise", "code", "mindmap", "reading", "video"]):
            print(f"[缓存] 流式命中缓存: {kp.name} ({req.kp_id})")

            async def _cached_stream():
                agents = ["教案Agent", "习题Agent", "代码Agent", "思维导图Agent", "拓展阅读Agent", "视频推荐Agent"]
                key_map = {"教案Agent": "lesson", "习题Agent": "exercise",
                           "代码Agent": "code", "思维导图Agent": "mindmap",
                           "拓展阅读Agent": "reading", "视频推荐Agent": "video"}
                yield f"data: {json.dumps({'type': 'start', 'total': 4, 'agents': agents})}\n\n"
                await asyncio.sleep(0.1)
                for a in agents:
                    yield f"data: {json.dumps({'type': 'progress', 'agent': a, 'key': key_map[a], 'status': 'done', 'chars': len(cached_results.get(key_map[a], '')), 'cached': True})}\n\n"
                    await asyncio.sleep(0.1)
                yield f"data: {json.dumps({'type': 'done', 'results': cached_results}, ensure_ascii=False)}\n\n"

            return StreamingResponse(_cached_stream(), media_type="text/event-stream")

    print(f"[生成] 并行流式生成: {kp.name} ({req.kp_id})")

    async def _stream():
        async for sse_line in coordinator.generate_resources_stream(
            student_id=student_id,
            kp_id=req.kp_id,
            kp_name=kp.name,
            kp_description=kp.description,
            student_profile=ctx["student_profile"],
            mastery_data=ctx["mastery_data"],
            rag_context=ctx["rag_context"],
            related_kps=ctx["related_kps"],
        ):
            yield sse_line
            await asyncio.sleep(0)

        # 提取结果并保存缓存
        # （在流结束后保存）
        async with async_session_factory() as save_db:
            try:
                # 重新从流数据中提取结果（下一个 yield 已经是 done 格式）
                # 这里我们需要实际等待 gather 完成
                pass
            finally:
                await save_db.close()

    # 用内存队列桥接流式生成器和缓存保存
    async def _bridge_stream():
        results = {}
        async for sse_line in coordinator.generate_resources_stream(
            student_id=student_id,
            kp_id=req.kp_id,
            kp_name=kp.name,
            kp_description=kp.description,
            student_profile=ctx["student_profile"],
            mastery_data=ctx["mastery_data"],
            rag_context=ctx["rag_context"],
            related_kps=ctx["related_kps"],
        ):
            yield sse_line
            await asyncio.sleep(0)

            # 捕获 done 事件
            line = sse_line.removeprefix("data: ").strip()
            try:
                data = json.loads(line)
                if data.get("type") == "done":
                    results = data.get("results", {})
            except (json.JSONDecodeError, KeyError):
                pass

        # 保存到数据库
        if results:
            async with async_session_factory() as save_db:
                for res_type, content in results.items():
                    if content and not content.startswith("生成失败"):
                        await crud.create_resource(save_db, req.kp_id, student_id, res_type, content)
                await save_db.commit()

    return StreamingResponse(_bridge_stream(), media_type="text/event-stream")
