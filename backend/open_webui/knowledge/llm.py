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
    system = messages[0]["content"] if messages and messages[0]["role"] == "system" else None
    user_prompt = messages[-1]["content"] if messages else ""
    return await call_llm_api(user_prompt, system=system, model=model)


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
        model = DEFAULT_MODELS.value if hasattr(DEFAULT_MODELS, 'value') else DEFAULT_MODELS
        if not model:
            model = os.getenv("OLLAMA_MODEL")

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


def _get_model_from_config() -> Optional[str]:
    """
    从 Open WebUI 配置数据库中读取已启用的大模型
    """
    try:
        import json
        import os
        import sqlite3

        db_path = os.getenv("WEBUI_DB_PATH", "/app/backend/data/webui.db")
        if not os.path.exists(db_path):
            return None

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT data FROM config ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        conn.close()

        if not row or not row[0]:
            return None

        config = json.loads(row[0])

        # 1. 尝试从 openai 配置中读取启用的模型
        openai_cfg = config.get("openai", {})
        if openai_cfg.get("enable"):
            api_configs = openai_cfg.get("api_configs", {})
            for cfg in api_configs.values():
                if cfg.get("enable"):
                    model_ids = cfg.get("model_ids", [])
                    if model_ids:
                        return model_ids[0]

        # 2. 尝试从 direct 配置中读取
        direct_cfg = config.get("direct", {})
        if direct_cfg.get("enable"):
            api_configs = direct_cfg.get("api_configs", {})
            for cfg in api_configs.values():
                if cfg.get("enable"):
                    model_ids = cfg.get("model_ids", [])
                    if model_ids:
                        return model_ids[0]

        # 3. 尝试从 ollama 配置中读取
        ollama_cfg = config.get("ollama", {})
        if ollama_cfg.get("enable"):
            api_configs = ollama_cfg.get("api_configs", {})
            for cfg in api_configs.values():
                if cfg.get("enable"):
                    model_ids = cfg.get("model_ids", [])
                    if model_ids:
                        return model_ids[0]

        return None
    except Exception as e:
        log.warning(f"Failed to read model from config db: {e}")
        return None


def _get_openai_credentials_from_config() -> tuple[Optional[str], Optional[str]]:
    """
    从 Open WebUI 配置数据库中读取 OpenAI 兼容 API 的 key 和 base_url
    """
    try:
        import json
        import os
        import sqlite3

        db_path = os.getenv("WEBUI_DB_PATH", "/app/backend/data/webui.db")
        if not os.path.exists(db_path):
            return None, None

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT data FROM config ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        conn.close()

        if not row or not row[0]:
            return None, None

        config = json.loads(row[0])
        openai_cfg = config.get("openai", {})

        if openai_cfg.get("enable"):
            api_keys = openai_cfg.get("api_keys", [])
            api_base_urls = openai_cfg.get("api_base_urls", [])
            key = api_keys[0] if api_keys else None
            base_url = api_base_urls[0] if api_base_urls else None
            return key, base_url

        return None, None
    except Exception as e:
        log.warning(f"Failed to read openai credentials from config db: {e}")
        return None, None


async def call_llm_api(
    prompt: str,
    system: Optional[str] = None,
    model: Optional[str] = None,
) -> str:
    """
    调用用户配置的默认模型（支持 Ollama / OpenAI 兼容 API / Anthropic）
    """
    import os
    import aiohttp
    from open_webui.config import OLLAMA_BASE_URL, DEFAULT_MODELS

    if not model:
        model = DEFAULT_MODELS.value if hasattr(DEFAULT_MODELS, 'value') else DEFAULT_MODELS
        if not model:
            model = os.getenv("OLLAMA_MODEL")
        if not model:
            # 尝试从 Open WebUI 配置数据库中读取已配置的模型
            model = _get_model_from_config()

    if not model:
        raise ValueError(
            "未配置默认模型。请在 Open WebUI 设置中配置 DEFAULT_MODELS，"
            "或设置 OLLAMA_MODEL 环境变量。"
        )

    log.info(f"call_llm_api using model={model}")

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    # 判断模型类型
    is_ollama = any(prefix in model.lower() for prefix in ["llama", "mistral", "deepseek", "qwen", "phi", "gemma", "codellama", "nomic"])

    if is_ollama:
        # Ollama 模型
        base_url = OLLAMA_BASE_URL.value if hasattr(OLLAMA_BASE_URL, 'value') else OLLAMA_BASE_URL
        if not base_url:
            base_url = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
        if base_url == "/ollama":
            base_url = "http://ollama:11434"
        elif base_url and not base_url.startswith("http"):
            base_url = f"http://{base_url}:11434"

        url = f"{base_url}/api/chat"
        payload = {"model": model, "messages": messages, "stream": False}
        timeout = aiohttp.ClientTimeout(total=120)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(url, json=payload) as response:
                result = await response.json()
                return result.get("message", {}).get("content", "")
    else:
        # OpenAI 兼容 API（支持 GPT、Claude 等）
        api_key = os.getenv("OPENAI_API_KEY", "")
        base_url = os.getenv("OPENAI_API_BASE_URL", "https://api.openai.com/v1")

        # 尝试从配置数据库读取
        cfg_key, cfg_base_url = _get_openai_credentials_from_config()
        if cfg_key:
            api_key = cfg_key
        if cfg_base_url:
            base_url = cfg_base_url

        url = f"{base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": messages,
        }
        timeout = aiohttp.ClientTimeout(total=120)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(url, json=payload, headers=headers) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"OpenAI API error: {response.status} - {error_text}")
                result = await response.json()
                return result.get("choices", [{}])[0].get("message", {}).get("content", "")


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
    return await call_llm_api(prompt, system=system, model=model)
