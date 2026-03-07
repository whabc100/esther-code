"""流式输出处理器模块"""

import json
from typing import Any, AsyncIterator, Optional
from loguru import logger


class StreamEvent:
    """流式事件"""

    START = "start"
    DELTA = "delta"
    TOOL_CALL = "tool_call"
    TOOL_CALL_END = "tool_call_end"
    END = "end"
    ERROR = "error"


class StreamChunk:
    """流式数据块"""

    def __init__(
        self,
        event: str,
        content: Optional[str] = None,
        tool_call: Optional[dict] = None,
        error: Optional[str] = None,
        finish_reason: Optional[str] = None
    ):
        self.event = event
        self.content = content
        self.tool_call = tool_call
        self.error = error
        self.finish_reason = finish_reason


class StreamHandler:
    """流式输出处理器"""

    def __init__(self):
        self.buffer: str = ""
        self.current_tool_calls: list = []
        self.current_tool_index: Optional[int] = None

    async def process_sse(
        self,
        line: str
    ) -> Optional[StreamChunk]:
        """
        处理 SSE (Server-Sent Events) 行

        Args:
            line: SSE 行内容

        Returns:
            StreamChunk: 解析出的数据块，如果未完成则返回None
        """
        if not line or line.strip() == "":
            return None

        # SSE 格式: data: {...}
        if line.startswith("data:"):
            data_str = line[5:].strip()

            # 检查结束标记
            if data_str == "[DONE]":
                return StreamChunk(
                    event=StreamEvent.END,
                    finish_reason="stop"
                )

            try:
                data = json.loads(data_str)
                return self._process_delta(data)
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse SSE data: {e}")
                return StreamChunk(
                    event=StreamEvent.ERROR,
                    error=f"JSON解析错误: {e}"
                )

        return None

    def _process_delta(self, data: dict) -> Optional[StreamChunk]:
        """
        处理 delta 数据

        Args:
            data: 解析后的数据字典

        Returns:
            StreamChunk: 数据块
        """
        choices = data.get("choices", [])
        if not choices:
            return None

        choice = choices[0]
        delta = choice.get("delta", {})

        # 处理工具调用
        tool_calls = delta.get("tool_calls")
        if tool_calls:
            return self._process_tool_calls(tool_calls)

        # 处理普通内容
        content = delta.get("content", "")
        if content:
            return StreamChunk(
                event=StreamEvent.DELTA,
                content=content
            )

        # 检查结束原因
        finish_reason = choice.get("finish_reason")
        if finish_reason:
            if self.current_tool_calls:
                # 有未完成的工具调用
                return StreamChunk(
                    event=StreamEvent.TOOL_CALL_END,
                    finish_reason=finish_reason
                )
            return StreamChunk(
                event=StreamEvent.END,
                finish_reason=finish_reason
            )

        return None

    def _process_tool_calls(self, tool_calls: list) -> StreamChunk:
        """
        处理工具调用数据

        Args:
            tool_calls: 工具调用列表

        Returns:
            StreamChunk: 工具调用数据块
        """
        for tool_call in tool_calls:
            index = tool_call.get("index", 0)
            function = tool_call.get("function", {})

            # 确保工具调用列表有足够的空间
            while index >= len(self.current_tool_calls):
                self.current_tool_calls.append({
                    "id": "",
                    "type": "function",
                    "function": {"name": "", "arguments": ""}
                })

            current = self.current_tool_calls[index]

            # 更新工具调用ID
            tool_id = tool_call.get("id")
            if tool_id:
                current["id"] = tool_id

            # 更新函数名
            if "name" in function:
                current["function"]["name"] = function["name"]

            # 追加参数
            if "arguments" in function:
                current["function"]["arguments"] += function["arguments"]

        return StreamChunk(
            event=StreamEvent.TOOL_CALL,
            tool_call=tool_calls[0] if tool_calls else None
        )

    def get_tool_calls(self) -> list:
        """
        获取完整的工具调用列表

        Returns:
            list: 工具调用列表
        """
        return self.current_tool_calls.copy()

    def reset(self) -> None:
        """重置处理器状态"""
        self.buffer = ""
        self.current_tool_calls = []
        self.current_tool_index = None


async def stream_to_chunks(
    stream: AsyncIterator[str],
    handler: StreamHandler
) -> AsyncIterator[StreamChunk]:
    """
    将流式响应转换为数据块

    Args:
        stream: 异步流
        handler: 流处理器

    Yields:
        StreamChunk: 数据块
    """
    handler.reset()

    async for line in stream:
        chunk = await handler.process_sse(line)
        if chunk:
            yield chunk
