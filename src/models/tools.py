"""工具定义模块"""

from typing import Any, Dict, List, Optional, Callable, Awaitable
from enum import Enum
from pydantic import BaseModel, Field


class ToolParameterType(str, Enum):
    """工具参数类型"""

    STRING = "string"
    INTEGER = "integer"
    NUMBER = "number"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"


class ToolParameter(BaseModel):
    """工具参数定义"""

    name: str = Field(description="参数名称")
    type: ToolParameterType = Field(description="参数类型")
    description: str = Field(description="参数描述")
    required: bool = Field(default=False, description="是否必需")
    default: Optional[Any] = Field(default=None, description="默认值")
    enum: Optional[List[Any]] = Field(
        default=None, description="枚举值列表"
    )


class ToolFunction(BaseModel):
    """工具函数定义"""

    name: str = Field(description="函数名称")
    description: str = Field(description="函数描述")
    parameters: Dict[str, Any] = Field(description="参数定义(JSON Schema格式)")


class ToolDefinition(BaseModel):
    """工具定义"""

    name: str = Field(description="工具名称")
    type: str = Field(default="function", description="工具类型")
    function: ToolFunction = Field(description="函数定义")


class ToolResult(BaseModel):
    """工具执行结果"""

    success: bool = Field(description="是否成功")
    data: Any = Field(default=None, description="返回数据")
    error: Optional[str] = Field(default=None, description="错误信息")
    tool_name: str = Field(description="工具名称")


class ToolMetadata(BaseModel):
    """工具元数据"""

    name: str = Field(description="工具名称")
    category: str = Field(description="工具分类")
    version: str = Field(default="1.0.0", description="版本")
    description: str = Field(description="描述")
    enabled: bool = Field(default=True, description="是否启用")


class Tool:
    """工具基类"""

    def __init__(
        self,
        name: str,
        description: str,
        parameters: List[ToolParameter],
        category: str = "general",
        version: str = "1.0.0"
    ):
        self.metadata = ToolMetadata(
            name=name,
            category=category,
            version=version,
            description=description
        )
        self.parameters = parameters

    def to_definition(self) -> ToolDefinition:
        """转换为工具定义格式"""
        properties = {}
        required = []

        for param in self.parameters:
            prop: Dict[str, Any] = {
                "type": param.type.value,
                "description": param.description
            }

            if param.enum:
                prop["enum"] = param.enum

            if param.default is not None:
                prop["default"] = param.default

            properties[param.name] = prop

            if param.required:
                required.append(param.name)

        return ToolDefinition(
            name=self.metadata.name,
            function=ToolFunction(
                name=self.metadata.name,
                description=self.metadata.description,
                parameters={
                    "type": "object",
                    "properties": properties,
                    "required": required
                }
            )
        )

    async def execute(self, **kwargs) -> ToolResult:
        """执行工具

        Args:
            **kwargs: 工具参数

        Returns:
            ToolResult: 执行结果

        Raises:
            NotImplementedError: 子类必须实现此方法
        """
        raise NotImplementedError(
            f"{self.__class__.__name__}.execute() must be implemented"
        )


class AsyncTool(Tool):
    """异步工具基类"""

    async def execute(self, **kwargs) -> ToolResult:
        """异步执行工具

        Args:
            **kwargs: 工具参数

        Returns:
            ToolResult: 执行结果
        """
        return await self._execute_impl(**kwargs)

    async def _execute_impl(self, **kwargs) -> ToolResult:
        """实际执行实现，由子类覆盖"""
        raise NotImplementedError(
            f"{self.__class__.__name__}._execute_impl() must be implemented"
        )


class SyncTool(Tool):
    """同步工具基类"""

    async def execute(self, **kwargs) -> ToolResult:
        """执行工具(同步包装)"""
        return self._execute_sync(**kwargs)

    def _execute_sync(self, **kwargs) -> ToolResult:
        """同步执行实现，由子类覆盖"""
        raise NotImplementedError(
            f"{self.__class__.__name__}._execute_sync() must be implemented"
        )
