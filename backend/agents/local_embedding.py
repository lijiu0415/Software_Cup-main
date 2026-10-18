"""
本地 Embedding 模型封装
======================

使用开源 sentence-transformers 模型，完全免费，无需 API Key。
用于替代讯飞星火 Embedding，支持 RAG 向量检索。

模型:
  - shibing624/text2vec-base-chinese (默认，中文优化，约 400MB)
  - sentence-transformers/all-MiniLM-L6-v2 (英文优化，约 80MB)

环境变量:
  LOCAL_EMBEDDING_MODEL: 模型名称（默认: shibing624/text2vec-base-chinese）
  TRANSFORMERS_CACHE   : 模型缓存目录（默认: ~/.cache/huggingface/）
"""

import os
import asyncio
from typing import List
from functools import lru_cache


# 全局模型实例（懒加载）
_model = None


def _get_model():
    """
    获取或初始化本地 Embedding 模型（单例模式）

    Returns:
        SentenceTransformer 模型实例
    """
    global _model

    if _model is None:
        from sentence_transformers import SentenceTransformer

        model_name = os.getenv(
            "LOCAL_EMBEDDING_MODEL",
            "shibing624/text2vec-base-chinese"
        )
        cache_dir = os.getenv(
            "TRANSFORMERS_CACHE",
            os.path.expanduser("~/.cache/huggingface/")
        )

        print(f"[LocalEmbedding] Loading model: {model_name}")
        print(f"[LocalEmbedding] Cache dir: {cache_dir}")
        _model = SentenceTransformer(model_name, cache_folder=cache_dir)
        print(f"[LocalEmbedding] Model loaded successfully")

    return _model


async def embed_text(text: str) -> List[float]:
    """
    将单条文本转为向量

    Args:
        text: 输入文本

    Returns:
        向量列表（384维或768维，取决于模型）
    """
    # 在线程池中运行，避免阻塞事件循环
    loop = asyncio.get_event_loop()
    model = _get_model()
    embedding = await loop.run_in_executor(None, model.encode, text)
    return embedding.tolist()


async def embed_batch(texts: List[str]) -> List[List[float]]:
    """
    批量文本向量化

    Args:
        texts: 文本列表

    Returns:
        向量列表
    """
    loop = asyncio.get_event_loop()
    model = _get_model()
    embeddings = await loop.run_in_executor(None, model.encode, texts)
    return embeddings.tolist()


def get_model_dimension() -> int:
    """
    获取当前模型的输出维度

    Returns:
        向量维度数
    """
    model = _get_model()
    return model.get_sentence_embedding_dimension()
