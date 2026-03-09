"""网络搜索工具模块"""

import json
from typing import Any, Dict, Optional
from loguru import logger

from ...models.tools import AsyncTool, ToolParameter, ToolParameterType, ToolResult


class WebSearchTool(AsyncTool):
    """网络搜索工具 - 调用 GLM-4.7 内置的 web_search 功能"""

    def __init__(self):
        super().__init__(
            name="web_search",
            description="使用 GLM-4.7 内置的网络搜索功能搜索网页内容",
            parameters=[
                ToolParameter(
                    name="query",
                    type=ToolParameterType.STRING,
                    description="搜索关键词或问题",
                    required=True
                ),
                ToolParameter(
                    name="top_k",
                    type=ToolParameterType.INTEGER,
                    description="返回结果的最大数量，默认为 6",
                    required=False,
                    default=6
                )
            ],
            category="search"
        )

    async def _execute_impl(self, **kwargs) -> ToolResult:
        """实现网络搜索

        Args:
            **kwargs: 搜索参数

        Returns:
            ToolResult: 搜索结果
        """
        query = kwargs.get("query", "")
        top_k = kwargs.get("top_k", 6)

        if not query:
            return ToolResult(
                success=False,
                error="搜索关键词不能为空",
                tool_name=self.metadata.name
            )

        try:
            # 调用智谱AI API 进行网络搜索
            from ...client.async_client import get_client

            client = await get_client()

            # 构造搜索消息
            messages = [
                {
                    "role": "user",
                    "content": f"请帮我搜索：{query}，返回最多 {top_k} 个相关结果，包含标题、链接和简要描述。"
                }
            ]

            # 发送搜索请求
            full_response = ""

            async for chunk in client.chat(
                messages=messages,
                stream=True
            ):
                if chunk.content:
                    full_response += chunk.content

            # 解析搜索结果
            # 模型返回的格式通常是:
            # 1. 标题: xxx
            # 链接: xxx
            # 描述: xxx

            results = self._parse_search_results(full_response, top_k)

            return ToolResult(
                success=True,
                data={
                    "query": query,
                    "results": results,
                    "count": len(results)
                },
                tool_name=self.metadata.name
            )

        except Exception as e:
            logger.error(f"网络搜索错误: {e}")
            return ToolResult(
                success=False,
                error=f"搜索失败: {str(e)}",
                tool_name=self.metadata.name
            )

    def _parse_search_results(self, response: str, max_count: int) -> list:
        """
        解析搜索结果

        Args:
            response: 模型响应文本
            max_count: 最大结果数

        Returns:
            list: 解析后的结果列表
        """
        results = []

        # 尝试解析为 JSON
        try:
            # 如果响应是 JSON 格式
            if response.strip().startswith("{") or response.strip().startswith("["):
                parsed = json.loads(response)

                # 如果是数组
                if isinstance(parsed, list):
                    for i, item in enumerate(parsed[:max_count]):
                        if isinstance(item, dict):
                            results.append({
                                "title": item.get("title", ""),
                                "url": item.get("url", item.get("link", "")),
                                "description": item.get("description", item.get("snippet", ""))
                            })
                # 如果是包含结果的字典
                elif isinstance(parsed, dict):
                    items = parsed.get("results", parsed.get("items", []))
                    for i, item in enumerate(items[:max_count]):
                        if isinstance(item, dict):
                            results.append({
                                "title": item.get("title", ""),
                                "url": item.get("url", item.get("link", "")),
                                "description": item.get("description", item.get("snippet", ""))
                            })
        except json.JSONDecodeError:
            # 尝试解析文本格式
            lines = response.split("\n")

            current_result = {}
            for line in lines:
                line = line.strip()

                # 尝试提取 URL
                if line.startswith("http") or line.startswith("https"):
                    current_result["url"] = line
                    if len(results) < max_count:
                        results.append(current_result)
                    current_result = {}

                # 尝试提取标题 (通常在链接前)
                elif line and not line.startswith("-") and not line.startswith("*"):
                    if "url" in current_result:
                        current_result["title"] = line
                    else:
                        current_result["title"] = line

                # 尝试提取描述 (通常在标题后)
                elif "title" in current_result and "description" not in current_result:
                    current_result["description"] = line
                    if len(results) < max_count:
                        results.append(current_result)

        return results


class WebSearchToolMock(AsyncTool):
    """网络搜索工具 - 模拟版本（用于测试）"""

    def __init__(self):
        super().__init__(
            name="web_search",
            description="使用 GLM-4.7 内置的网络搜索功能搜索网页内容",
            parameters=[
                ToolParameter(
                    name="query",
                    type=ToolParameterType.STRING,
                    description="搜索关键词或问题",
                    required=True
                )
            ],
            category="search"
        )

    async def _execute_impl(self, **kwargs) -> ToolResult:
        """实现网络搜索（模拟）

        Args:
            **kwargs: 搜索参数

        Returns:
            ToolResult: 搜索结果
        """
        query = kwargs.get("query", "")

        if not query:
            return ToolResult(
                success=False,
                error="搜索关键词不能为空",
                tool_name=self.metadata.name
            )

        # 模拟搜索结果
        mock_results = [
            {
                "title": f"关于 {query} 的搜索结果 1",
                "url": f"https://example.com/search?q={query}",
                "description": f"这是关于 {query} 的第一个搜索结果的简要描述。"
            },
            {
                "title": f"关于 {query} 的搜索结果 2",
                "url": f"https://example.com/search?q={query}&page=2",
                "description": f"这是关于 {query} 的第二个搜索结果的简要描述。"
            },
            {
                "title": f"关于 {query} 的搜索结果 3",
                "url": f"https://example.com/search?q={query}&page=3",
                "description": f"这是关于 {query} 的第三个搜索结果的简要描述。"
            }
        ]

        return ToolResult(
            success=True,
            data={
                "query": query,
                "results": mock_results,
                "count": len(mock_results)
            },
            tool_name=self.metadata.name
        )


def register_web_search_tools(registry) -> None:
    """
    注册网络搜索工具

    Args:
        registry: 工具注册表
    """
    # 注册实际的网络搜索工具（需要 API 支持）
    # registry.register(WebSearchTool())

    # 注册模拟版本用于测试
    registry.register(WebSearchToolMock())
