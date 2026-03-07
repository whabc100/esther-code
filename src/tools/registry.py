"""工具注册表模块"""

from typing import Dict, List, Optional, Set
from loguru import logger

from ..models.tools import Tool, ToolDefinition


class ToolRegistry:
    """工具注册表"""

    def __init__(self):
        self._tools: Dict[str, Tool] = {}
        self._categories: Dict[str, Set[str]] = {}
        self._disabled: Set[str] = set()

    def register(self, tool: Tool) -> None:
        """
        注册工具

        Args:
            tool: 工具实例

        Raises:
            ValueError: 工具名称已存在
        """
        name = tool.metadata.name

        if name in self._tools:
            raise ValueError(f"工具 '{name}' 已存在")

        self._tools[name] = tool

        # 添加到分类
        category = tool.metadata.category
        if category not in self._categories:
            self._categories[category] = set()
        self._categories[category].add(name)

        logger.debug(f"注册工具: {name} (分类: {category})")

    def unregister(self, name: str) -> bool:
        """
        注销工具

        Args:
            name: 工具名称

        Returns:
            bool: 是否成功注销
        """
        if name not in self._tools:
            return False

        tool = self._tools[name]
        category = tool.metadata.category

        # 从分类中移除
        if category in self._categories:
            self._categories[category].discard(name)
            if not self._categories[category]:
                del self._categories[category]

        del self._tools[name]
        self._disabled.discard(name)

        logger.debug(f"注销工具: {name}")
        return True

    def get(self, name: str) -> Optional[Tool]:
        """
        获取工具

        Args:
            name: 工具名称

        Returns:
            Optional[Tool]: 工具实例，不存在则返回None
        """
        return self._tools.get(name)

    def get_all(self) -> List[Tool]:
        """获取所有已注册的工具"""
        return list(self._tools.values())

    def get_enabled(self) -> List[Tool]:
        """获取所有启用的工具"""
        return [
            tool for tool in self._tools.values()
            if tool.metadata.name not in self._disabled
        ]

    def get_by_category(self, category: str) -> List[Tool]:
        """
        获取指定分类的工具

        Args:
            category: 分类名称

        Returns:
            List[Tool]: 工具列表
        """
        names = self._categories.get(category, set())
        return [
            self._tools[name] for name in names
            if name in self._tools and name not in self._disabled
        ]

    def get_categories(self) -> List[str]:
        """获取所有分类"""
        return list(self._categories.keys())

    def enable(self, name: str) -> bool:
        """
        启用工具

        Args:
            name: 工具名称

        Returns:
            bool: 是否成功启用
        """
        if name not in self._tools:
            return False

        self._disabled.discard(name)
        logger.debug(f"启用工具: {name}")
        return True

    def disable(self, name: str) -> bool:
        """
        禁用工具

        Args:
            name: 工具名称

        Returns:
            bool: 是否成功禁用
        """
        if name not in self._tools:
            return False

        self._disabled.add(name)
        logger.debug(f"禁用工具: {name}")
        return True

    def is_enabled(self, name: str) -> bool:
        """
        检查工具是否启用

        Args:
            name: 工具名称

        Returns:
            bool: 是否启用
        """
        return name in self._tools and name not in self._disabled

    def get_definitions(self, enabled_only: bool = True) -> List[Dict[str, Any]]:
        """
        获取工具定义列表，用于API调用

        Args:
            enabled_only: 是否只返回启用的工具

        Returns:
            List[Dict[str, Any]]: 工具定义列表
        """
        tools = self.get_enabled() if enabled_only else self.get_all()
        return [tool.to_definition().model_dump() for tool in tools]

    def has_tool(self, name: str) -> bool:
        """
        检查工具是否存在

        Args:
            name: 工具名称

        Returns:
            bool: 是否存在
        """
        return name in self._tools

    def clear(self) -> None:
        """清空所有工具"""
        self._tools.clear()
        self._categories.clear()
        self._disabled.clear()
        logger.debug("清空工具注册表")


# 全局注册表实例
_global_registry: Optional[ToolRegistry] = None


def get_registry() -> ToolRegistry:
    """
    获取全局工具注册表

    Returns:
        ToolRegistry: 工具注册表实例
    """
    global _global_registry

    if _global_registry is None:
        _global_registry = ToolRegistry()

    return _global_registry
