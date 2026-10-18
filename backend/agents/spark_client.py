"""
大模型客户端封装（统一适配器模式）
====================================

通过 llm_adapter 统一调用，支持多提供商切换。
保留原有函数签名，确保现有 Agent 代码无需修改。

提供商切换:
  - LLM_PROVIDER=longcat  → 调用 Longcat API
  - LLM_PROVIDER=spark    → 调用讯飞星火 API（原始实现）
"""

import json
import hashlib
import base64
import time
import hmac
import asyncio
from typing import List, Optional, AsyncGenerator
import httpx
from config import SPARK_APP_ID, SPARK_API_KEY, SPARK_API_SECRET, SPARK_URLS

# 导入统一适配器
from agents.llm_adapter import chat_completion, get_embedding as get_adapter_embedding

# 全局信号量：限制同时进行的 Spark WebSocket 连接数（避免并发导致 AppIdNoAuthError）
_SPARK_SEMAPHORE = asyncio.Semaphore(3)  # 允许3路并发，控制而非完全串行


# ============================================================
# 保留原有函数签名，内部改为调用适配器
# ============================================================

async def call_spark_lite(
    messages: List[dict],
    system_prompt: str = "",
    stream: bool = False,
) -> str:
    """快模型（对话诊断 / 思维导图 / 视频推荐）"""
    return await chat_completion(
        messages=messages,
        system_prompt=system_prompt,
        model="fast",
    )


async def call_spark_pro(
    messages: List[dict],
    system_prompt: str = "",
    stream: bool = False,
) -> str:
    """标准模型（教案 / 习题 / 拓展阅读）"""
    return await chat_completion(
        messages=messages,
        system_prompt=system_prompt,
        model="standard",
    )


async def call_spark_ultra(
    messages: List[dict],
    system_prompt: str = "",
    stream: bool = False,
) -> str:
    """标准模型（兼容旧调用）"""
    return await chat_completion(
        messages=messages,
        system_prompt=system_prompt,
        model="standard",
    )


async def call_spark_code(
    messages: List[dict],
    system_prompt: str = "",
    stream: bool = False,
) -> str:
    """代码专用模型"""
    return await chat_completion(
        messages=messages,
        system_prompt=system_prompt,
        model="code",
    )


async def call_spark_x15(
    messages: List[dict],
    system_prompt: str = "",
    stream: bool = False,
) -> str:
    """标准模型（兼容旧调用）"""
    return await chat_completion(
        messages=messages,
        system_prompt=system_prompt,
        model="standard",
    )


async def get_embedding(text: str) -> List[float]:
    """获取文本向量（优先本地 Embedding）"""
    return await get_adapter_embedding(text)


# ============================================================
# 以下为星火专用实现（当 LLM_PROVIDER=spark 时使用）
# ============================================================

def _build_auth_url(url: str) -> str:
    """构建带认证参数的 WebSocket URL（星火专用）"""
    from urllib.parse import urlparse, urlunparse
    parsed = urlparse(url)
    host = parsed.hostname
    path = parsed.path

    # 生成 RFC1123 格式时间戳
    gmt_time = time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime())

    # 构建签名字符串
    string_to_sign = f"host: {host}\npath: {path}\ndate: {gmt_time}"

    # HMAC-SHA256 签名
    sign = hmac.new(
        SPARK_API_SECRET.encode("utf-8"),
        string_to_sign.encode("utf-8"),
        hashlib.sha256
    ).digest()
    sign_b64 = base64.b64encode(sign).decode("utf-8")

    # 构建 Authorization
    auth_origin = f"api_key=\"{SPARK_API_KEY}\", algorithm=\"hmac-sha256\""
    auth = base64.b64encode(auth_origin.encode("utf-8")).decode("utf-8")

    # 拼接完整 URL
    auth_params = (
        f"?authorization={auth}"
        f"&date={gmt_time}"
        f"&host={host}"
    )
    return f"{url}{auth_params}"


def _get_model_config(model_type: str) -> dict:
    """
    根据model_type返回对应的配置

    Returns:
        {
            "url": "wss://...",
            "domain": "lite",
            "max_tokens": 4096,
            "supports_system": False  # 是否支持system角色
        }
    """
    configs = {
        "lite": {
            "url": SPARK_URLS["lite"],
            "domain": "lite",
            "max_tokens": 4096,
            "supports_system": False,  # Lite 不支持 system 角色
        },
        "x1.5": {
            "url": SPARK_URLS["x1.5"],
            "domain": "spark-x",
            "max_tokens": 4096,
            "supports_system": True,
        },
        "pro": {
            "url": SPARK_URLS["pro"],
            "domain": "generalv3",
            "max_tokens": 4096,
            "supports_system": True,
        },
        "ultra": {
            "url": SPARK_URLS["ultra"],
            "domain": "generalv3.5",
            "max_tokens": 8192,
            "supports_system": True,
        },
    }
    return configs.get(model_type, configs["ultra"])


def _build_spark_request(model_type: str, messages: List[dict], system_prompt: str = "") -> tuple:
    """构建星火 WebSocket 请求的 URL 和请求体"""
    from urllib.parse import urlencode, urlparse

    config = _get_model_config(model_type)
    url = config["url"]
    domain = config["domain"]
    max_tokens = config["max_tokens"]
    supports_system = config["supports_system"]

    parsed = urlparse(url)
    host = parsed.hostname
    path = parsed.path

    cur_time = time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime())
    signature_origin = f"host: {host}\ndate: {cur_time}\nGET {path} HTTP/1.1"

    signature_sha = hmac.new(
        SPARK_API_SECRET.encode("utf-8"),
        signature_origin.encode("utf-8"),
        hashlib.sha256
    ).digest()
    signature_sha_base64 = base64.b64encode(signature_sha).decode(encoding="utf-8")

    authorization_origin = f'api_key="{SPARK_API_KEY}", algorithm="hmac-sha256", headers="host date request-line", signature="{signature_sha_base64}"'
    authorization = base64.b64encode(authorization_origin.encode("utf-8")).decode(encoding="utf-8")

    params = {"authorization": authorization, "date": cur_time, "host": host}
    ws_url = f"{url}?{urlencode(params)}"

    # 构建消息，处理 system 角色兼容
    text_messages = []
    system_contents = []
    for msg in messages:
        if msg["role"] == "system":
            system_contents.append(msg["content"])
    if system_prompt:
        system_contents.insert(0, system_prompt)

    if supports_system and system_contents:
        combined_system = "\n".join(system_contents)
        text_messages.append({"role": "system", "content": combined_system})

    for msg in messages:
        if msg["role"] != "system":
            if not supports_system and system_contents and msg["role"] == "user" and len(text_messages) == 0:
                combined_system = "\n".join(system_contents)
                text_messages.append({"role": "user", "content": combined_system + "\n\n" + msg["content"]})
            else:
                text_messages.append({"role": msg["role"], "content": msg["content"]})

    if not supports_system and system_contents and not any(msg["role"] == "user" for msg in messages):
        combined_system = "\n".join(system_contents)
        text_messages.append({"role": "user", "content": combined_system})

    if not text_messages:
        text_messages.append({"role": "user", "content": "请继续"})

    request_data = {
        "header": {"app_id": SPARK_APP_ID, "uid": "user_" + str(hash(str(messages)))[:8]},
        "parameter": {"chat": {"domain": domain, "temperature": 0.5, "max_tokens": max_tokens, "top_k": 4}},
        "payload": {"message": {"text": text_messages}},
    }

    return ws_url, request_data


async def _call_spark(
    model_type: str,
    messages: List[dict],
    system_prompt: str = "",
    stream: bool = False,
) -> str:
    """通用星火模型调用（使用WebSocket接口，非流式返回完整文本）"""
    import websockets

    ws_url, request_data = _build_spark_request(model_type, messages, system_prompt)

    try:
        async with _SPARK_SEMAPHORE:  # 防止并发连接导致认证失败
            async with websockets.connect(
                ws_url, ping_timeout=120, close_timeout=60, open_timeout=30,
            ) as websocket:
                await websocket.send(json.dumps(request_data))
                content_parts = []

                while True:
                    response = await asyncio.wait_for(websocket.recv(), timeout=120)
                    data = json.loads(response)

                    if data["header"]["code"] != 0:
                        error_code = data["header"]["code"]
                        error_msg = data["header"].get("message", "Unknown error")
                        raise Exception(f"Spark API error: code={error_code}, message={error_msg}")

                    text_item = data["payload"]["choices"]["text"][0]
                    chunk_content = text_item.get("content", "")
                    if chunk_content:
                        content_parts.append(chunk_content)

                    if data["payload"]["choices"].get("status", 0) == 2:
                        break

                final_content = "".join(content_parts)
                return final_content if final_content else "(模型返回为空，请重试)"

    except websockets.exceptions.ConnectionClosed as e:
        raise Exception(f"Spark WebSocket connection closed: {str(e)}")
    except asyncio.TimeoutError:
        raise Exception("Spark WebSocket timeout: 接收响应超时")
    except Exception as e:
        raise Exception(f"Spark WebSocket error: {str(e)}")


async def _call_spark_stream(
    model_type: str,
    messages: List[dict],
    system_prompt: str = "",
) -> AsyncGenerator[str, None]:
    """星火流式调用 - 逐块 yield 响应内容"""
    import websockets

    ws_url, request_data = _build_spark_request(model_type, messages, system_prompt)

    try:
        async with _SPARK_SEMAPHORE:  # 防止并发连接导致认证失败
            async with websockets.connect(
                ws_url, ping_timeout=120, close_timeout=60, open_timeout=30,
            ) as websocket:
                await websocket.send(json.dumps(request_data))

                while True:
                    response = await asyncio.wait_for(websocket.recv(), timeout=120)
                    data = json.loads(response)

                    if data["header"]["code"] != 0:
                        error_code = data["header"]["code"]
                        error_msg = data["header"].get("message", "Unknown error")
                        raise Exception(f"Spark API error: code={error_code}, message={error_msg}")

                    text_item = data["payload"]["choices"]["text"][0]
                    chunk_content = text_item.get("content", "")
                    if chunk_content:
                        yield chunk_content

                    if data["payload"]["choices"].get("status", 0) == 2:
                        break

    except websockets.exceptions.ConnectionClosed as e:
        raise Exception(f"Spark WebSocket connection closed: {str(e)}")
    except asyncio.TimeoutError:
        raise Exception("Spark WebSocket timeout: 接收响应超时")
    except Exception as e:
        raise Exception(f"Spark WebSocket error: {str(e)}")


def _get_model_name(model_type: str) -> str:
    """根据model_type返回对应的domain（兼容旧代码）"""
    mapping = {
        "lite": "lite",
        "x1.5": "spark-x",
        "pro": "spark-x",
        "ultra": "spark-x",
    }
    return mapping.get(model_type, "lite")


async def _normal_call(url: str, payload: dict, headers: dict = None) -> str:
    """非流式调用"""
    async with httpx.AsyncClient() as client:
        resp = await client.post(url, json=payload, headers=headers, timeout=30.0)
        data = resp.json()
        if "choices" in data:
            return data["choices"][0]["message"]["content"]
        elif data.get("code") == 0:
            return data["choices"][0]["message"]["content"]
        else:
            raise Exception(f"Spark API error: {data}")


async def _stream_call(url: str, payload: dict, headers: dict = None) -> str:
    """流式调用，拼接完整结果"""
    result = []
    async with httpx.AsyncClient() as client:
        async with client.stream("POST", url, json=payload, headers=headers, timeout=60.0) as resp:
            async for line in resp.aiter_lines():
                if line.startswith("data:"):
                    data_str = line[5:].strip()
                    if data_str == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data_str)
                        content = chunk["choices"][0].get("delta", {}).get("content", "")
                        if content:
                            result.append(content)
                    except json.JSONDecodeError:
                        continue
    return "".join(result)
