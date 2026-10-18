"""
全局异常处理
"""
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse


class AppException(Exception):
    """应用自定义异常"""
    def __init__(self, code: int = 500, message: str = "服务器内部错误"):
        self.code = code
        self.message = message


class AgentException(AppException):
    """智能体调用异常"""
    def __init__(self, agent_name: str, message: str):
        super().__init__(code=502, message=f"智能体[{agent_name}]调用失败: {message}")


class KnowledgePointNotFoundException(AppException):
    """知识点不存在"""
    def __init__(self, kp_id: str):
        super().__init__(code=404, message=f"知识点[{kp_id}]不存在")


class StudentNotFoundException(AppException):
    """学生不存在"""
    def __init__(self, student_id: str):
        super().__init__(code=404, message=f"学生[{student_id}]不存在")


class PrerequisiteNotMetException(AppException):
    """前置知识点未满足"""
    def __init__(self, lack_kps: list):
        super().__init__(code=400, message=f"前置知识点未满足: {lack_kps}")


async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理器"""
    if isinstance(exc, AppException):
        return JSONResponse(
            status_code=exc.code,
            content={"code": exc.code, "message": exc.message},
        )
    return JSONResponse(
        status_code=500,
        content={"code": 500, "message": f"服务器内部错误: {str(exc)[:200]}"},
    )
