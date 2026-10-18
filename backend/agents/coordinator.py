"""
协调Agent - 总调度
接收前端请求 → 任务分发 → 并行调用执行Agent → 结果聚合
（基于 asyncio.gather 并行调度，满足赛题多智能体并行要求）
"""
import asyncio
import json
from typing import Dict, List, Optional, AsyncGenerator
from agents.diagnose_agent import run_diagnose
from agents.lesson_agent import generate_lesson
from agents.exercise_agent import generate_exercise
from agents.code_agent import generate_code
from agents.mindmap_agent import generate_mindmap
from agents.reading_agent import generate_reading
from agents.video_agent import generate_video
from agents.agent_msg import AgentMessage, create_message


class CoordinatorAgent:
    """协调Agent - 多智能体编排核心

    模型分工（赛题要求）：
    - 诊断Agent  → Spark Lite（降级 Ultra）
    - 教案Agent  → Spark 4.0 Ultra
    - 习题Agent  → Spark Pro（降级 Ultra）
    - 代码Agent  → Spark Pro（降级 Ultra）
    - 思维导图   → 本地引擎
    """

    def __init__(self):
        self.name = "Coordinator"
        self.agents = {
            "diagnose": run_diagnose,
            "lesson": generate_lesson,
            "exercise": generate_exercise,
            "code": generate_code,
            "mindmap": generate_mindmap,
        }

    async def handle_chat(
        self,
        student_id: str,
        content: str,
        chat_history: List[dict],
        student_profile: Dict,
    ) -> Dict:
        """
        处理对话请求 → 调用诊断Agent

        Returns:
            {reply, profile_update, break_points}
        """
        msg = create_message(
            sender="frontend",
            receiver="Coordinator",
            task_type="diagnose",
            payload={
                "student_id": student_id,
                "content": content,
            }
        )

        for attempt in range(3):
            try:
                reply, profile_update, core_complete = await run_diagnose(
                    student_id=student_id,
                    chat_history=chat_history,
                    student_profile=student_profile,
                    content=content,
                )
                return {
                    "reply": reply,
                    "profile_update": profile_update,
                    "break_points": [],
                    "core_complete": core_complete,
                    "status": "success",
                }
            except Exception as e:
                if attempt == 2:
                    return {
                        "reply": f"抱歉，系统暂时无法响应，请稍后重试。(错误: {str(e)[:100]})",
                        "profile_update": {},
                        "break_points": [],
                        "status": "fail",
                    }
                await asyncio.sleep(3)

    async def handle_chat_stream(
        self,
        student_id: str,
        content: str,
        chat_history: List[dict],
        student_profile: Dict,
    ) -> AsyncGenerator[str, None]:
        """
        处理流式对话请求 → 调用诊断Agent流式版

        Yields:
            SSE事件字符串 (data: {...}\n\n)
        """
        from agents.diagnose_agent import run_diagnose_stream

        try:
            async for event_json in run_diagnose_stream(
                student_id=student_id,
                chat_history=chat_history,
                student_profile=student_profile,
                content=content,
            ):
                yield f"data: {event_json}\n\n"
                await asyncio.sleep(0)
        except Exception as e:
            error_event = json.dumps({
                "type": "error",
                "message": f"诊断服务异常: {str(e)[:100]}",
            }, ensure_ascii=False)
            yield f"data: {error_event}\n\n"

    async def _call_with_retry(self, agent_name: str, agent_func, *args, max_retries: int = 3) -> str:
        """带重试的Agent调用"""
        for attempt in range(max_retries):
            try:
                result = await agent_func(*args)
                return result
            except Exception as e:
                error_msg = str(e)
                if "QpsOverFlow" in error_msg or "11202" in error_msg:
                    wait_time = 5 * (attempt + 1)
                    print(f"[Coordinator] {agent_name} QPS限流，等待{wait_time}秒后重试...")
                    await asyncio.sleep(wait_time)
                elif attempt < max_retries - 1:
                    print(f"[Coordinator] {agent_name} 调用失败: {error_msg[:50]}，重试中...")
                    await asyncio.sleep(3)
                else:
                    raise e

    async def _run_single_agent(
        self, agent_name: str, agent_func, delay: float, *args
    ) -> tuple:
        """执行单个Agent并捕获结果，返回 (agent_name, result_dict)

        delay: 启动延迟（秒），用于错开并发请求避免 QPS 限流
        """
        try:
            if delay > 0:
                await asyncio.sleep(delay)
            print(f"[Coordinator] 并行生成 {agent_name}: 启动 (延迟{delay}s)")
            result = await self._call_with_retry(agent_name, agent_func, *args)
            print(f"[Coordinator] 并行生成 {agent_name}: 完成 ({len(result)} 字)")
            return (agent_name, {"content": result, "status": "success"})
        except Exception as e:
            print(f"[Coordinator] 并行生成 {agent_name}: 失败 ({str(e)[:50]})")
            return (agent_name, {"content": f"生成失败: {str(e)[:200]}", "status": "fail"})

    async def generate_resources(
        self,
        student_id: str,
        kp_id: str,
        kp_name: str,
        kp_description: str,
        student_profile: Dict,
        mastery_data: List[Dict],
        rag_context: str = "",
        related_kps: List[Dict] = None,
    ) -> Dict:
        """
        并行生成4类个性化学习资源

        赛题要求：协调Agent「并行」调度5个执行Agent。
        使用 asyncio.gather 同时启动，综合耗时 ≈ 单次API调用时间。

        Returns:
            {lesson, exercise, code, mindmap}
        """
        # 6个生成任务并发执行（错开启动避免 QPS 限流）
        STAGGER = 0.0  # 信号量已控并发
        tasks = [
            self._run_single_agent("教案Agent", generate_lesson, 0 * STAGGER,
                kp_id, kp_name, kp_description,
                student_profile, mastery_data, rag_context, related_kps),
            self._run_single_agent("习题Agent", generate_exercise, 1 * STAGGER,
                kp_id, kp_name, student_profile, rag_context, related_kps),
            self._run_single_agent("代码Agent", generate_code, 2 * STAGGER,
                kp_id, kp_name, kp_description,
                student_profile, rag_context, related_kps),
            self._run_single_agent("思维导图Agent", generate_mindmap, 3 * STAGGER,
                kp_id, kp_name, student_profile, mastery_data, related_kps),
            self._run_single_agent("拓展阅读Agent", generate_reading, 4 * STAGGER,
                kp_id, kp_name, kp_description,
                student_profile, rag_context, related_kps),
            self._run_single_agent("视频推荐Agent", generate_video, 5 * STAGGER,
                kp_id, kp_name, kp_description,
                student_profile, rag_context, related_kps),
        ]

        agent_results = await asyncio.gather(*tasks, return_exceptions=True)

        name_map = {
            "教案Agent": "lesson",
            "习题Agent": "exercise",
            "代码Agent": "code",
            "思维导图Agent": "mindmap",
            "拓展阅读Agent": "reading",
            "视频推荐Agent": "video",
        }

        results = {}
        for item in agent_results:
            if isinstance(item, tuple):
                agent_name, result_dict = item
                key = name_map.get(agent_name, agent_name)
                results[key] = result_dict["content"]
            else:
                print(f"[Coordinator] 异常结果: {item}")

        return results

    async def generate_resources_stream(
        self,
        student_id: str,
        kp_id: str,
        kp_name: str,
        kp_description: str,
        student_profile: Dict,
        mastery_data: List[Dict],
        rag_context: str = "",
        related_kps: List[Dict] = None,
    ) -> AsyncGenerator[str, None]:
        """
        流式并行生成资源（SSE 进度事件）

        Yields:
            data: {"type":"progress","agent":"教案Agent","status":"running"}
            data: {"type":"progress","agent":"教案Agent","status":"done","chars":1234}
            ...
            data: {"type":"done","results":{...}}
        """
        from collections import OrderedDict

        agent_configs = OrderedDict([
            ("教案Agent", (generate_lesson, [kp_id, kp_name, kp_description,
                student_profile, mastery_data, rag_context, related_kps])),
            ("习题Agent", (generate_exercise, [kp_id, kp_name,
                student_profile, rag_context, related_kps])),
            ("代码Agent", (generate_code, [kp_id, kp_name, kp_description,
                student_profile, rag_context, related_kps])),
            ("思维导图Agent", (generate_mindmap, [kp_id, kp_name,
                student_profile, mastery_data, related_kps])),
            ("拓展阅读Agent", (generate_reading, [kp_id, kp_name, kp_description,
                student_profile, rag_context, related_kps])),
            ("视频推荐Agent", (generate_video, [kp_id, kp_name, kp_description,
                student_profile, rag_context, related_kps])),
        ])

        total = len(agent_configs)
        name_map = {
            "教案Agent": "lesson",
            "习题Agent": "exercise",
            "代码Agent": "code",
            "思维导图Agent": "mindmap",
            "拓展阅读Agent": "reading",
            "视频推荐Agent": "video",
        }

        async def _run_and_report(agent_name: str, delay: float):
            """执行单个Agent并通过队列报告进度

            delay: 启动延迟（秒），用于错开并发请求避免 QPS 限流
            """
            func, args = agent_configs[agent_name]
            q = progress_queue

            if delay > 0:
                await asyncio.sleep(delay)

            await q.put(json.dumps({
                "type": "progress", "agent": agent_name,
                "key": name_map[agent_name], "status": "running",
            }))

            try:
                print(f"[Coordinator] 并行流式 {agent_name}: 启动 (延迟{delay}s)")
                content = await self._call_with_retry(agent_name, func, *args)
                print(f"[Coordinator] 并行流式 {agent_name}: 完成 ({len(content)} 字)")
                await q.put(json.dumps({
                    "type": "progress", "agent": agent_name,
                    "key": name_map[agent_name], "status": "done",
                    "chars": len(content),
                }))
                return (agent_name, content)
            except Exception as e:
                print(f"[Coordinator] 并行流式 {agent_name}: 失败 ({str(e)[:50]})")
                await q.put(json.dumps({
                    "type": "progress", "agent": agent_name,
                    "key": name_map[agent_name], "status": "fail",
                    "error": str(e)[:100],
                }))
                return (agent_name, f"生成失败: {str(e)[:200]}")

        STAGGER = 0.0  # 信号量已控并发
        progress_queue = asyncio.Queue()
        agent_tasks = [
            asyncio.create_task(_run_and_report(name, i * STAGGER))
            for i, name in enumerate(agent_configs)
        ]

        # 初始进度事件
        yield f"data: {json.dumps({'type': 'start', 'total': total, 'agents': list(agent_configs.keys())})}\n\n"
        await asyncio.sleep(0)

        completed = 0
        while completed < total:
            event = await progress_queue.get()
            yield f"data: {event}\n\n"
            await asyncio.sleep(0)

            data = json.loads(event)
            if data["type"] == "progress" and data["status"] in ("done", "fail"):
                completed += 1

        # 收集结果
        results = {}
        gathered = await asyncio.gather(*agent_tasks, return_exceptions=True)
        for item in gathered:
            if isinstance(item, tuple):
                agent_name, content = item
                results[name_map.get(agent_name, agent_name)] = content

        # 最终结果
        done_event = json.dumps({"type": "done", "results": results}, ensure_ascii=False)
        yield f"data: {done_event}\n\n"


# 全局协调Agent实例
coordinator = CoordinatorAgent()
