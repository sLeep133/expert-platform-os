"""
Wiki LLM 调用模块

使用 open-webui 已配置的大模型连接，为 Wiki 编译器提供 LLM 调用能力。
"""

import logging
from typing import Optional

log = logging.getLogger(__name__)


async def call_llm(
    messages: list[dict],
    model: Optional[str] = None,
) -> str:
    """
    调用 open-webui 已配置的大模型

    Args:
        messages: 消息列表 [{"role": "user", "content": "..."}]
        model: 模型名称（可选，默认使用系统配置的模型）

    Returns:
        LLM 生成的文本内容
    """
    try:
        from open_webui.utils.chat import generate_chat_completion
        from starlette.datastructures import State
        from dataclasses import dataclass
        from starlette.requests import Request
        from unittest.mock import MagicMock

        # 获取默认模型
        if not model:
            from open_webui.config import DEFAULT_MODEL
            model = DEFAULT_MODEL.value if hasattr(DEFAULT_MODEL, 'value') else DEFAULT_MODEL

        # 构造 form_data
        form_data = {
            "model": model,
            "messages": messages,
            "stream": False,
        }

        # 创建一个模拟的 Request 对象
        # 由于 generate_chat_completion 内部主要读取 app.state.config 和 app.state.MODELS
        # 我们需要直接使用 Ollama 的原始 API 调用
        raise NotImplementedError("需要使用其他方式调用")

    except NotImplementedError:
        # 降级方案：直接调用 Ollama API
        return await _call_ollama_direct(messages, model)


async def _call_ollama_direct(
    messages: list[dict],
    model: Optional[str] = None,
) -> str:
    """
    直接调用 Ollama API（使用 open-webui 的 OLLAMA_BASE_URL 配置）
    """
    import os
    import aiohttp
    from open_webui.config import OLLAMA_BASE_URL

    if not model:
        model = os.getenv("OLLAMA_MODEL", "deepseek-r1:14b")

    # 获取 Ollama URL
    base_url = OLLAMA_BASE_URL.value if hasattr(OLLAMA_BASE_URL, 'value') else OLLAMA_BASE_URL
    if not base_url:
        base_url = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")

    # 特殊处理 Docker 网络主机名
    if base_url == "/ollama":
        base_url = "http://ollama:11434"
    elif base_url and not base_url.startswith("http"):
        base_url = f"http://{base_url}:11434"

    url = f"{base_url}/api/chat"
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
    }

    timeout = aiohttp.ClientTimeout(total=120)
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(url, json=payload) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Ollama API error: {response.status} - {error_text}")

                result = await response.json()
                return result.get("message", {}).get("content", "")
    except Exception as e:
        log.error(f"Ollama call failed: {e}")
        raise


async def call_llm_simple(
    prompt: str,
    system: Optional[str] = None,
    model: Optional[str] = None,
) -> str:
    """
    简单的 LLM 调用接口

    Args:
        prompt: 用户 prompt
        system: 系统提示词（可选）
        model: 模型名称（可选）

    Returns:
        LLM 生成的文本内容
    """
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    return await _call_ollama_direct(messages, model)
