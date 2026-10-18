"""
JWT 鉴权工具

- create_access_token / decode_access_token：签发与校验 token
- get_current_user：FastAPI 依赖，读取 Authorization: Bearer <token>
- resolve_student_id：AUTH_ENABLED=true 时以 token 中的 student_id 为准，否则回退请求体
"""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from fastapi import Header, HTTPException
from jose import JWTError, jwt

from config import settings


@dataclass
class AuthUser:
    """鉴权后的当前用户身份"""
    username: str = ""
    student_id: str = ""


def create_access_token(username: str, student_id: str) -> str:
    """签发 JWT，携带 sub=username、student_id、exp"""
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    payload = {"sub": username, "student_id": student_id, "exp": expire}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    """校验并解码 JWT，失败返回 None"""
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        return None


def get_current_user(authorization: str = Header(default="")) -> AuthUser:
    """当前用户身份依赖。

    AUTH_ENABLED=false 时直接放行（返回空身份），保证开发/演示流程不受影响；
    AUTH_ENABLED=true 时强制校验 Bearer token，失败抛 401。
    """
    if not settings.AUTH_ENABLED:
        return AuthUser()

    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未登录或凭证缺失")

    token = authorization[len("Bearer "):].strip()
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="凭证无效或已过期")

    return AuthUser(
        username=payload.get("sub", ""),
        student_id=payload.get("student_id", ""),
    )


def resolve_student_id(req_student_id: str, current_user: AuthUser) -> str:
    """确定生效的 student_id：token 优先（防止伪造越权），关闭鉴权时回退请求体。"""
    return current_user.student_id or req_student_id
