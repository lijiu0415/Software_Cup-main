"""
用户认证接口 - POST /api/auth/register  注册
              POST /api/auth/login     登录

- 用户名在数据库中唯一
- 密码使用 bcrypt 哈希存储，不保存明文
- 登录时区分「未注册」与「密码错误」两种失败原因
"""
import bcrypt
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import get_db
from db import crud
from utils import files
from utils.security import AuthUser, create_access_token, get_current_user

router = APIRouter(prefix="/api/auth", tags=["认证"])

# bcrypt 单次最多处理 72 字节，超出会抛错
_MAX_PASSWORD_BYTES = 72


class RegisterRequest(BaseModel):
    username: str
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str


class DeleteRequest(BaseModel):
    username: str


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


@router.post("/register")
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """注册新用户：校验用户名唯一，创建用户账号 + 学生画像"""
    username = req.username.strip()
    password = req.password or ""

    if not username or not password:
        return {"success": False, "error_code": "invalid_input", "message": "用户名和密码不能为空"}

    if len(password) < 6:
        return {"success": False, "error_code": "weak_password", "message": "密码至少需要 6 位"}

    if len(password.encode("utf-8")) > _MAX_PASSWORD_BYTES:
        return {"success": False, "error_code": "password_too_long", "message": "密码过长，请使用更短的密码"}

    existing = await crud.get_user_by_username(db, username)
    if existing:
        return {"success": False, "error_code": "username_exists", "message": "该用户名已被注册"}

    student_id = f"student_{username}"
    await crud.create_user(db, username, _hash_password(password), student_id)

    # 同步创建学生画像，保证后续学习功能可直接使用该 student_id
    student = await crud.get_student(db, student_id)
    if not student:
        await crud.create_student(db, id=student_id, student_name=username)

    await db.commit()
    return {
        "success": True,
        "username": username,
        "student_id": student_id,
        "access_token": create_access_token(username, student_id),
        "token_type": "bearer",
        "message": "注册成功",
    }


@router.post("/login")
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    """登录：先校验用户名是否存在，再校验密码是否匹配"""
    username = req.username.strip()
    password = req.password or ""

    if not username or not password:
        return {"success": False, "error_code": "invalid_input", "message": "请输入用户名和密码"}

    user = await crud.get_user_by_username(db, username)
    if not user:
        return {"success": False, "error_code": "not_registered", "message": "该用户尚未注册，请先注册"}

    if not _verify_password(password, user.password_hash):
        return {"success": False, "error_code": "wrong_password", "message": "密码错误，请重试"}

    return {
        "success": True,
        "username": username,
        "student_id": user.student_id,
        "access_token": create_access_token(username, user.student_id),
        "token_type": "bearer",
        "message": "登录成功",
    }


@router.post("/delete")
async def delete_account(
    req: DeleteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    """注销用户账号：删除账号及该用户的全部学习数据（不可撤回）"""
    # token 中的身份优先（防止伪造越权注销他人账号），关闭鉴权时回退请求体
    username = (current_user.username or req.username).strip()

    if not username:
        return {"success": False, "error_code": "invalid_input", "message": "无法确定用户身份"}

    user = await crud.get_user_by_username(db, username)
    if not user:
        return {"success": False, "error_code": "not_registered", "message": "该用户不存在"}

    # 清理该用户上传的教材文件（磁盘）
    textbooks = await crud.get_textbooks(db, user.student_id)
    files.delete_textbook_files([t.stored_name for t in textbooks])

    await crud.delete_user_account(db, username, user.student_id)
    await db.commit()
    return {"success": True, "message": "用户已注销"}
