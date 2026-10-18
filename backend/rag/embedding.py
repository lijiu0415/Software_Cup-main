"""
文本向量化封装
=============

统一接口，支持多提供商切换：
  - 本地 Embedding（sentence-transformers，免费）
  - Longcat Embedding API
  - 讯飞星火 Embedding API（备用）

由 agents/llm_adapter.py 统一调度，本模块保留兼容接口。
"""

from typing import List, Optional
from agents.llm_adapter import get_embedding, get_embeddings_batch


async def embed_text(text: str) -> List[float]:
    """
    将文本转为向量

    Args:
        text: 输入文本

    Returns:
        向量列表
    """
    try:
        return await get_embedding(text)
    except Exception as e:
        # 降级：返回空向量（不影响系统运行，但会降低 RAG 精度）
        import logging
        logging.warning(f"Embedding failed: {e}")
        return []


async def embed_query(query: str) -> Optional[List[float]]:
    """
    将查询文本转为向量

    Args:
        query: 查询文本

    Returns:
        向量列表，失败返回 None
    """
    result = await embed_text(query)
    return result if result else None


async def embed_batch(texts: List[str]) -> List[List[float]]:
    """
    批量文本向量化

    Args:
        texts: 文本列表

    Returns:
        向量列表
    """
    try:
        return await get_embeddings_batch(texts)
    except Exception as e:
        import logging
        logging.warning(f"Batch embedding failed: {e}")
        return []
