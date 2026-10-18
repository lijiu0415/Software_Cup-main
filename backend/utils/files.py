"""
文件存储辅助 - 教材上传目录与文件删除
"""
from pathlib import Path

# backend/ 目录（utils/files.py 的上级的上级）
BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / "uploads"

# 允许上传的教材文件类型（扩展名，小写、不含点）
ALLOWED_EXTENSIONS = {
    "pdf", "doc", "docx", "ppt", "pptx", "xls", "xlsx",
    "txt", "md", "markdown", "png", "jpg", "jpeg", "gif",
}

# 单文件大小上限（字节）
MAX_UPLOAD_BYTES = 50 * 1024 * 1024


def ensure_upload_dir() -> None:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def textbook_path(stored_name: str) -> Path:
    return UPLOAD_DIR / stored_name


def delete_textbook_file(stored_name: str) -> None:
    """删除单个教材文件（不存在/失败时静默）"""
    try:
        p = textbook_path(stored_name)
        if p.exists():
            p.unlink()
    except OSError:
        pass


def delete_textbook_files(stored_names) -> None:
    """批量删除教材文件"""
    for name in stored_names:
        delete_textbook_file(name)
