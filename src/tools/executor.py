"""工具执行器模块"""

import json
import asyncio
from typing import Any, Dict, List, Optional
from loguru import logger

from ..models.tools import Tool, ToolResult
from ..models.message import ToolCall
from .registry import ToolRegistry


class ToolExecutionError(Exception):
    """工具执行错误"""
    pass


class ToolExecutor:
    """工具执行器"""

    def __init__(self, registry: Optional[ToolRegistry] = None):
        """
        初始化执行器

        Args:
            registry: 工具注册表，不传则使用全局注册表
        """
        self.registry = registry

    def _get_registry(self) -> ToolRegistry:
        """获取工具注册表"""
        if self.registry is None:
            from .registry import get_registry
            return get_registry()
        return self.registry

    async def execute(
        self,
        tool_name: str,
        arguments: str
    ) -> ToolResult:
        """
        执行单个工具

        Args:
            tool_name: 工具名称
            arguments: JSON字符串格式的参数

        Returns:
            ToolResult: 执行结果

        Raises:
            ToolExecutionError: 执行失败
        """
        registry = self._get_registry()
        tool = registry.get(tool_name)

        if tool is None:
            return ToolResult(
                success=False,
                error=f"工具 '{tool_name}' 不存在",
                tool_name=tool_name
            )

        if not registry.is_enabled(tool_name):
            return ToolResult(
                success=False,
                error=f"工具 '{tool_name}' 已禁用",
                tool_name=tool_name
            )

        try:
            # 解析参数
            kwargs = json.loads(arguments) if arguments else {}
            logger.info(f"执行工具: {tool_name} 参数: {kwargs}")

            # 执行工具
            result = await tool.execute(**kwargs)
            result.tool_name = tool_name

            return result

        except json.JSONDecodeError as e:
            return ToolResult(
                success=False,
                error=f"参数解析失败: {e}",
                tool_name=tool_name
            )

        except Exception as e:
            logger.error(f"工具执行错误: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                tool_name=tool_name
            )

    async def execute_all(
        self,
        tool_calls: List[ToolCall],
        parallel: bool = False
    ) -> List[ToolResult]:
        """
        执行多个工具调用

        Args:
            tool_calls: 工具调用列表
            parallel: 是否并行执行

        Returns:
            List[ToolResult]: 执行结果列表
        """
        if not tool_calls:
            return []

        if parallel:
            # 并行执行
            tasks = [
                self.execute(
                    tc.function.get("name", ""),
                    tc.function.get("arguments", "{}")
                )
                for tc in tool_calls
            ]
            return await asyncio.gather(*tasks)

        else:
            # 串行执行
            results = []
            for tc in tool_calls:
                result = await self.execute(
                    tc.function.get("name", ""),
                    tc.function.get("arguments", "{}")
                )
                results.append(result)

                # 如果失败，可以选择停止后续执行
                if not result.success:
                    logger.warning(f"工具 {tc.function.get('name')} 执行失败")

            return results

    def format_result_for_api(
        self,
        tool_call_id: str,
        result: ToolResult
    ) -> Dict[str, Any]:
        """
        格式化结果为API消息格式

        Args:
            tool_call_id: 工具调用ID
            result: 执行结果

        Returns:
            Dict[str, Any]: API格式消息
        """
        content = json.dumps(result.model_dump(), ensure_ascii=False)

        return {
            "tool_call_id": tool_call_id,
            "role": "tool",
            "content": content
        }


class ParallelToolExecutor(ToolExecutor):
    """并行工具执行器"""

    def __init__(self, max_concurrent: int = 5, registry: ToolRegistry = None):
        """
        初始化并行执行器

        Args:
            max_concurrent: 最大并发数
            registry: 工具注册表
        """
        super().__init__(registry)
        self.semaphore = asyncio.Semaphore(max_concurrent)

    async def execute(
        self,
        tool_name: str,
        arguments: str
    ) -> ToolResult:
        """
        执行单个工具(带并发控制)

        Args:
            tool_name: 工具名称
            arguments: JSON字符串格式的参数

        Returns:
            ToolResult: 执行结果
        """
        async with self.semaphore:
            return await super().execute(tool_name, arguments)


# 默认执行器实例
_default_executor: Optional[ToolExecutor] = None


def get_executor() -> ToolExecutor:
    """
    获取默认工具执行器

    Returns:
        ToolExecutor: 工具执行器实例
    """
    global _default_executor

    if _default_executor is None:
        _default_executor = ToolExecutor()

    return _default_executor
