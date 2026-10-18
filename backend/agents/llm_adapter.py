"""
统一 LLM 调用适配器
==================

支持多提供商切换，只需修改 .env 中的 LLM_PROVIDER 配置。

提供商:
  - deepseek : DeepSeek API（默认，OpenAI 兼容，走硅基流动 SiliconFlow）
  - longcat  : Longcat API（备用）
  - spark    : 讯飞星火 API（备用）

环境变量:
  LLM_PROVIDER       : 提供商选择（deepseek / longcat / spark）
  DEEPSEEK_API_KEY   : DeepSeek API 密钥
  DEEPSEEK_BASE_URL  : DeepSeek API 基础 URL
  MODEL_FAST         : 快档模型（对话/思维导图/视频）
  MODEL_STANDARD     : 标准档模型（教案/习题/阅读）
  MODEL_CODE         : 代码专用模型
  MODEL_STRONG       : 强推理模型（可选，慢）
  LONGCAT_API_KEY    : Longcat API 密钥
  LONGCAT_BASE_URL   : Longcat API 基础 URL
  LONGCAT_MODEL      : Longcat 模型名称
  USE_LOCAL_EMBEDDING: 使用本地 Embedding 模型（true / false）
"""

import os
import json
import asyncio
import httpx
from typing import List, Optional, AsyncGenerator
from enum import Enum

from config import settings


class LLMProvider(str, Enum):
    """LLM 提供商枚举"""
    DEEPSEEK = "deepseek"
    LONGCAT = "longcat"
    SPARK = "spark"


# ============================================================
# 逻辑档位 -> 实际模型 ID 解析
# ============================================================

_MODEL_TIERS = {
    "fast": settings.MODEL_FAST,
    "standard": settings.MODEL_STANDARD,
    "code": settings.MODEL_CODE,
    "strong": settings.MODEL_STRONG,
}


def _resolve_model(model: str) -> str:
    """把逻辑档位名（fast/standard/code/strong）解析成实际模型 ID"""
    return _MODEL_TIERS.get(model, settings.MODEL_STANDARD)


# ============================================================
# 统一对话生成接口
# ============================================================

async def chat_completion(
    messages: List[dict],
    system_prompt: str = "",
    model: str = "default",
    max_tokens: int = 4096,
    temperature: float = 0.7,
) -> str:
    """
    统一的对话生成接口

    Args:
        messages: 消息列表 [{"role": "user", "content": "..."}]
        system_prompt: 系统提示词
        model: 模型名称（lite / pro / ultra）
        max_tokens: 最大输出 token 数
        temperature: 温度参数

    Returns:
        生成的文本内容
    """
    provider = settings.LLM_PROVIDER

    if system_prompt:
        messages = [{"role": "system", "content": system_prompt}] + messages

    if provider == LLMProvider.DEEPSEEK:
        return await _call_deepseek(messages, model, max_tokens, temperature)
    elif provider == LLMProvider.LONGCAT:
        return await _call_longcat(messages, model, max_tokens, temperature)
    elif provider == LLMProvider.SPARK:
        from agents.spark_client import _call_spark
        return await _call_spark(model, messages, system_prompt="", stream=False)
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")


async def chat_completion_stream(
    messages: List[dict],
    system_prompt: str = "",
    model: str = "default",
    max_tokens: int = 4096,
    temperature: float = 0.7,
) -> AsyncGenerator[str, None]:
    """
    统一的流式对话生成接口（AsyncGenerator）

    用法:
        async for chunk in chat_completion_stream(messages, system_prompt="...", model="lite"):
            print(chunk, end="")
    """
    provider = settings.LLM_PROVIDER

    if system_prompt:
        messages = [{"role": "system", "content": system_prompt}] + messages

    if provider == LLMProvider.SPARK:
        from agents.spark_client import _call_spark_stream
        async for chunk in _call_spark_stream(model, messages, system_prompt=""):
            yield chunk
    elif provider == LLMProvider.DEEPSEEK:
        async for chunk in _call_deepseek_stream(messages, model, max_tokens, temperature):
            yield chunk
    elif provider == LLMProvider.LONGCAT:
        result = await _call_longcat(messages, model, max_tokens, temperature)
        yield result
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")


# ============================================================
# 统一 Embedding 接口
# ============================================================

async def get_embedding(text: str) -> List[float]:
    """
    统一的文本向量化接口

    Args:
        text: 输入文本

    Returns:
        向量列表（768维）
    """
    use_local = os.getenv("USE_LOCAL_EMBEDDING", "true").lower() == "true"

    if use_local:
        return await _call_local_embedding(text)
    else:
        return await _call_longcat_embedding(text)


async def get_embeddings_batch(texts: List[str]) -> List[List[float]]:
    """
    批量文本向量化

    Args:
        texts: 文本列表

    Returns:
        向量列表
    """
    use_local = os.getenv("USE_LOCAL_EMBEDDING", "true").lower() == "true"

    if use_local:
        return await _call_local_embedding_batch(texts)
    else:
        # Longcat 暂无批量接口，逐个调用
        return [await _call_longcat_embedding(t) for t in texts]


# ============================================================
# Longcat API 实现
# ============================================================

async def _call_openai_compatible(
    api_key: str,
    base_url: str,
    model_name: str,
    provider_label: str,
    messages: List[dict],
    max_tokens: int = 4096,
    temperature: float = 0.7,
    stream: bool = False,
) -> str:
    """调用任意 OpenAI 兼容的 Chat Completions API（DeepSeek / Longcat 等）"""
    if not api_key:
        raise ValueError(f"{provider_label} API key is not set in config/.env")

    url = f"{base_url}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model_name,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }

    if stream:
        payload["stream"] = True
        return await _stream_openai_compatible(url, headers, payload, provider_label, model_name)

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload, headers=headers, timeout=120.0)

            # 记录详细错误信息
            if resp.status_code != 200:
                print(f"[{provider_label} API Error] Status: {resp.status_code}")
                print(f"[{provider_label} API Error] Response: {resp.text[:500]}")
                print(f"[{provider_label} API Error] URL: {url}")
                print(f"[{provider_label} API Error] Model: {model_name}")

            resp.raise_for_status()
            data = resp.json()

        # 适配 OpenAI 兼容格式
        if "choices" in data:
            return data["choices"][0]["message"]["content"]
        # 适配其他格式
        elif "content" in data:
            return data["content"]
        elif "response" in data:
            return data["response"]
        else:
            raise ValueError(f"Unexpected {provider_label} response format: {data}")
    except httpx.HTTPStatusError as e:
        print(f"[{provider_label} API HTTP Error] {e}")
        raise
    except Exception as e:
        print(f"[{provider_label} API Exception] {e}")
        raise


async def _stream_openai_compatible(
    url: str,
    headers: dict,
    payload: dict,
    provider_label: str,
    model_name: str,
    max_retries: int = 5,
) -> str:
    """流式调用 OpenAI 兼容 API，累加 delta.content（跳过 reasoning_content 思考内容）

    带自动重试：对 DNS 解析失败、连接中断、429 限流、5xx 等瞬时错误重试，
    避免偶发网络抖动导致「对话画像」这类单次调用直接失败。
    """
    last_err = None
    for attempt in range(max_retries):
        parts = []
        try:
            async with httpx.AsyncClient() as client:
                async with client.stream(
                    "POST", url, json=payload, headers=headers,
                    timeout=httpx.Timeout(connect=10.0, read=120.0, write=30.0, pool=10.0),
                ) as resp:
                    if resp.status_code == 429 or resp.status_code >= 500:
                        body = await resp.aread()
                        print(f"[{provider_label} API Error] Status: {resp.status_code}: {body[:200]}")
                        raise httpx.HTTPStatusError(
                            f"status={resp.status_code}", request=resp.request, response=resp
                        )
                    if resp.status_code != 200:
                        body = await resp.aread()
                        print(f"[{provider_label} API Error] Status: {resp.status_code}")
                        print(f"[{provider_label} API Error] Response: {body[:500]}")
                        print(f"[{provider_label} API Error] Model: {model_name}")
                        resp.raise_for_status()

                    async for line in resp.aiter_lines():
                        if not line.startswith("data:"):
                            continue
                        data_str = line[5:].strip()
                        if data_str == "[DONE]":
                            break
                        try:
                            delta = json.loads(data_str)["choices"][0].get("delta", {})
                            content = delta.get("content")
                            if content:
                                parts.append(content)
                        except (json.JSONDecodeError, KeyError, IndexError):
                            continue

            result = "".join(parts)
            if not result:
                raise ValueError(f"{provider_label} 流式返回为空")
            return result
        except Exception as e:
            last_err = e
            if attempt < max_retries - 1:
                wait = (2, 5, 10, 15)[min(attempt, 3)]
                print(f"[{provider_label}] 调用失败({str(e)[:80]})，{wait}s 后重试({attempt + 1}/{max_retries - 1})")
                await asyncio.sleep(wait)
                continue
            print(f"[{provider_label} API Exception] {e}")
            raise

    raise last_err


async def _call_longcat(
    messages: List[dict],
    model: str = "default",
    max_tokens: int = 4096,
    temperature: float = 0.7,
) -> str:
    """调用 Longcat Chat API"""
    return await _call_openai_compatible(
        api_key=settings.LONGCAT_API_KEY,
        base_url=settings.LONGCAT_BASE_URL,
        # 始终使用配置的模型名（lite/pro/ultra 只是兼容性参数）
        model_name=settings.LONGCAT_MODEL,
        provider_label="Longcat",
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
    )


async def _call_deepseek(
    messages: List[dict],
    model: str = "standard",
    max_tokens: int = 4096,
    temperature: float = 0.7,
) -> str:
    """调用 DeepSeek / 硅基流动 OpenAI 兼容 API（按逻辑档位选模型，走流式）"""
    return await _call_openai_compatible(
        api_key=settings.DEEPSEEK_API_KEY,
        base_url=settings.DEEPSEEK_BASE_URL,
        model_name=_resolve_model(model),
        provider_label="DeepSeek",
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
        stream=True,
    )


async def _call_deepseek_stream(
    messages: List[dict],
    model: str = "standard",
    max_tokens: int = 4096,
    temperature: float = 0.7,
) -> AsyncGenerator[str, None]:
    """DeepSeek / 硅基流动 真·流式调用：逐 token yield delta.content（跳过 reasoning_content）

    仅在「尚未输出任何内容」时重试（连接/DNS/429/5xx 等阶段错误）；
    已开始输出后中断则直接终止，避免重试造成内容重复。
    """
    if not settings.DEEPSEEK_API_KEY:
        raise ValueError("DEEPSEEK_API_KEY is not set in config/.env")

    url = f"{settings.DEEPSEEK_BASE_URL}/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": _resolve_model(model),
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": True,
    }

    last_err = None
    for attempt in range(5):
        yielded_any = False
        try:
            async with httpx.AsyncClient() as client:
                async with client.stream(
                    "POST", url, json=payload, headers=headers,
                    timeout=httpx.Timeout(connect=10.0, read=120.0, write=30.0, pool=10.0),
                ) as resp:
                    if resp.status_code != 200:
                        body = await resp.aread()
                        print(f"[DeepSeek API Error] Status: {resp.status_code}: {body[:500]}")
                        resp.raise_for_status()

                    async for line in resp.aiter_lines():
                        if not line.startswith("data:"):
                            continue
                        data_str = line[5:].strip()
                        if data_str == "[DONE]":
                            break
                        try:
                            delta = json.loads(data_str)["choices"][0].get("delta", {})
                            content = delta.get("content")
                            if content:
                                yielded_any = True
                                yield content
                        except (json.JSONDecodeError, KeyError, IndexError):
                            continue

            if not yielded_any:
                raise ValueError("DeepSeek 流式返回为空")
            return
        except Exception as e:
            if yielded_any:
                print(f"[DeepSeek] 流中断（已输出部分内容），终止: {str(e)[:80]}")
                raise
            last_err = e
            if attempt < 4:
                wait = (2, 5, 10, 15)[min(attempt, 3)]
                print(f"[DeepSeek] 流式调用失败({str(e)[:80]})，{wait}s 后重试({attempt + 1}/4)")
                await asyncio.sleep(wait)
                continue
            print(f"[DeepSeek API Exception] {e}")
            raise

    raise last_err


async def _call_longcat_embedding(text: str) -> List[float]:
    """调用 Longcat Embedding API（如果支持）"""
    api_key = settings.LONGCAT_API_KEY
    base_url = settings.LONGCAT_BASE_URL

    if not api_key:
        raise ValueError("LONGCAT_API_KEY is not set")

    url = f"{base_url}/embeddings"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "longcat-embedding",
        "input": text,
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(url, json=payload, headers=headers, timeout=120.0)
        resp.raise_for_status()
        data = resp.json()

    if "data" in data:
        return data["data"][0]["embedding"]
    elif "embedding" in data:
        return data["embedding"]
    else:
        raise ValueError(f"Unexpected Longcat embedding format: {data}")


# ============================================================
# 本地 Embedding 实现（免费，无需 API Key）
# ============================================================

async def _call_local_embedding(text: str) -> List[float]:
    """调用本地 Embedding 模型"""
    from agents.local_embedding import embed_text
    return await embed_text(text)


async def _call_local_embedding_batch(texts: List[str]) -> List[List[float]]:
    """调用本地 Embedding 模型（批量）"""
    from agents.local_embedding import embed_batch
    return await embed_batch(texts)
