"""GLM-4.7 异步客户端模块"""

import asyncio
import json
import time
from typing import Any, AsyncIterator, List, Optional, Dict
from aiohttp import ClientSession, ClientError, ClientTimeout
from loguru import logger

from ..config import get_config
from ..models.message import Message, ChatResponse, ToolCall
from .stream_handler import StreamHandler, stream_to_chunks, StreamChunk


class GLMClientError(Exception):
    """GLM客户端错误"""

    def __init__(self, message: str, code: Optional[str] = None):
        self.message = message
        self.code = code
        super().__init__(message)


class GLMRateLimitError(GLMClientError):
    """速率限制错误"""
    pass


class GLMAsyncClient:
    """GLM-4.7 异步客户端"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        api_base: Optional[str] = None
    ):
        """
        初始化客户端

        Args:
            api_key: API密钥，不传则从配置读取
            model: 模型ID，不传则从配置读取
            api_base: API端点，不传则使用默认端点
        """
        config = get_config()

        self.api_key = api_key or config.zhipuai_api_key
        self.model = model or config.zhipuai_model
        self.api_base = (
            api_base or
            config.zhipuai_api_base or
            "https://open.bigmodel.cn/api/paas/v4/"
        )

        # 确保API base以/结尾
        if not self.api_base.endswith("/"):
            self.api_base += "/"

        self.timeout = config.request_timeout
        self.max_retries = config.max_retries

        self._session: Optional[ClientSession] = None
        self._stream_handler = StreamHandler()

    async def _get_session(self) -> ClientSession:
        """获取或创建HTTP会话"""
        if self._session is None or self._session.closed:
            timeout = ClientTimeout(total=self.timeout)
            self._session = ClientSession(timeout=timeout)
        return self._session

    async def close(self) -> None:
        """关闭客户端"""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    async def __aenter__(self):
        """异步上下文管理器入口"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.close()

    def _build_headers(self) -> Dict[str, str]:
        """构建请求头"""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    async def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.7,
        top_p: float = 0.9,
        max_tokens: Optional[int] = None,
        stream: bool = False
    ) -> AsyncIterator[StreamChunk]:
        """
        聊天对话

        Args:
            messages: 消息列表
            tools: 工具列表
            temperature: 温度参数
            top_p: top_p采样参数
            max_tokens: 最大生成token数
            stream: 是否流式输出

        Yields:
            StreamChunk: 流式数据块
        """
        url = self.api_base + "chat/completions"

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "top_p": top_p,
            "stream": stream
        }

        if max_tokens:
            payload["max_tokens"] = max_tokens

        if tools:
            payload["tools"] = tools

        # 带重试的请求
        for attempt in range(self.max_retries + 1):
            try:
                if stream:
                    async for chunk in self._stream_request(url, payload):
                        yield chunk
                else:
                    response = await self._request(url, payload)
                    yield StreamChunk(
                        event="end",
                        content=response.get("content", ""),
                        finish_reason="stop"
                    )
                return

            except GLMRateLimitError as e:
                if attempt < self.max_retries:
                    wait_time = 2 ** attempt  # 指数退避
                    logger.warning(f"速率限制，{wait_time}秒后重试 (尝试 {attempt + 1}/{self.max_retries})")
                    await asyncio.sleep(wait_time)
                else:
                    raise

            except (GLMClientError, ClientError) as e:
                if attempt < self.max_retries:
                    logger.warning(f"请求失败，重试中 (尝试 {attempt + 1}/{self.max_retries}): {e}")
                    await asyncio.sleep(1)
                else:
                    raise GLMClientError(f"请求失败: {e}") from e

            except Exception as e:
                logger.error(f"未知错误: {e}")
                raise GLMClientError(f"请求失败: {e}") from e

    async def _request(self, url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        发送非流式请求

        Args:
            url: 请求URL
            payload: 请求体

        Returns:
            Dict[str, Any]: 响应数据
        """
        session = await self._get_session()

        logger.debug(f"发送请求到 {url}")

        async with session.post(
            url,
            headers=self._build_headers(),
            json=payload
        ) as response:
            await self._check_response(response)

            data = await response.json()

            choices = data.get("choices", [])
            if not choices:
                raise GLMClientError("响应中没有choices")

            choice = choices[0]
            message = choice.get("message", {})

            # 处理工具调用
            tool_calls = message.get("tool_calls")
            tool_calls_list = None
            if tool_calls:
                tool_calls_list = [
                    ToolCall(
                        id=tc.get("id", ""),
                        type=tc.get("type", "function"),
                        function=tc.get("function", {})
                    )
                    for tc in tool_calls
                ]

            return {
                "content": message.get("content", ""),
                "tool_calls": [tc.model_dump() for tc in tool_calls_list] if tool_calls_list else None,
                "finish_reason": choice.get("finish_reason", "stop"),
                "usage": data.get("usage"),
                "model": data.get("model", self.model)
            }

    async def _stream_request(
        self,
        url: str,
        payload: Dict[str, Any]
    ) -> AsyncIterator[StreamChunk]:
        """
        发送流式请求

        Args:
            url: 请求URL
            payload: 请求体

        Yields:
            StreamChunk: 流式数据块
        """
        session = await self._get_session()
        self._stream_handler.reset()

        logger.debug(f"发送流式请求到 {url}")

        async with session.post(
            url,
            headers=self._build_headers(),
            json=payload
        ) as response:
            await self._check_response(response)

            async for line in response.content:
                line_str = line.decode('utf-8', errors='ignore')
                chunk = await self._stream_handler.process_sse(line_str)
                if chunk:
                    yield chunk

            # 检查是否有未返回的工具调用
            tool_calls = self._stream_handler.get_tool_calls()
            if tool_calls:
                yield StreamChunk(
                    event="tool_call",
                    tool_call=tool_calls[0] if tool_calls else None
                )

    async def _check_response(self, response) -> None:
        """
        检查响应状态

        Args:
            response: aiohttp响应对象

        Raises:
            GLMClientError: 响应错误
            GLMRateLimitError: 速率限制
        """
        if response.status == 200:
            return

        # 尝试解析错误信息
        try:
            error_data = await response.json()
            error_msg = error_data.get("error", {}).get("message", "未知错误")
            error_code = error_data.get("error", {}).get("code", "")
        except Exception:
            error_msg = await response.text()
            error_code = str(response.status)

        if response.status == 429:
            raise GLMRateLimitError(error_msg, error_code)

        raise GLMClientError(
            f"API请求失败 (HTTP {response.status}): {error_msg}",
            error_code
        )


# 默认客户端实例
_default_client: Optional[GLMAsyncClient] = None


async def get_client(
    api_key: Optional[str] = None,
    model: Optional[str] = None
) -> GLMAsyncClient:
    """
    获取默认客户端实例

    Args:
        api_key: API密钥
        model: 模型ID

    Returns:
        GLMAsyncClient: 客户端实例
    """
    global _default_client

    if _default_client is None:
        _default_client = GLMAsyncClient(api_key=api_key, model=model)

    return _default_client


async def close_client() -> None:
    """关闭默认客户端"""
    global _default_client

    if _default_client:
        await _default_client.close()
        _default_client = None
