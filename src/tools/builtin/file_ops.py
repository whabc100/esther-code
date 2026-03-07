"""文件操作工具模块"""

import os
import json
from pathlib import Path
from typing import Optional, List
from loguru import logger

from ...models.tools import AsyncTool, ToolParameter, ToolParameterType, ToolResult


class ReadFileTool(AsyncTool):
    """文件读取工具"""

    def __init__(self):
        super().__init__(
            name="read_file",
            description="读取文件内容",
            parameters=[
                ToolParameter(
                    name="file_path",
                    type=ToolParameterType.STRING,
                    description="要读取的文件路径",
                    required=True
                ),
                ToolParameter(
                    name="encoding",
                    type=ToolParameterType.STRING,
                    description="文件编码，默认为utf-8",
                    required=False,
                    default="utf-8"
                )
            ],
            category="file"
        )

    async def _execute_impl(self, **kwargs) -> ToolResult:
        """实现文件读取"""
        file_path = kwargs.get("file_path")
        encoding = kwargs.get("encoding", "utf-8")

        if not file_path:
            return ToolResult(
                success=False,
                error="缺少必需参数: file_path",
                tool_name=self.metadata.name
            )

        try:
            path = Path(file_path).expanduser().resolve()

            if not path.exists():
                return ToolResult(
                    success=False,
                    error=f"文件不存在: {file_path}",
                    tool_name=self.metadata.name
                )

            if not path.is_file():
                return ToolResult(
                    success=False,
                    error=f"路径不是文件: {file_path}",
                    tool_name=self.metadata.name
                )

            # 检查文件大小（限制10MB）
            file_size = path.stat().st_size
            if file_size > 10 * 1024 * 1024:
                return ToolResult(
                    success=False,
                    error=f"文件过大: {file_size} bytes (最大支持10MB)",
                    tool_name=self.metadata.name
                )

            content = path.read_text(encoding=encoding)

            # 尝试检测文件类型
            lines = content.count('\n') + 1

            return ToolResult(
                success=True,
                data={
                    "content": content,
                    "path": str(path),
                    "size": file_size,
                    "lines": lines
                },
                tool_name=self.metadata.name
            )

        except PermissionError:
            return ToolResult(
                success=False,
                error=f"没有读取权限: {file_path}",
                tool_name=self.metadata.name
            )

        except UnicodeDecodeError as e:
            return ToolResult(
                success=False,
                error=f"编码错误: {e}",
                tool_name=self.metadata.name
            )

        except Exception as e:
            logger.error(f"读取文件错误: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                tool_name=self.metadata.name
            )


class WriteFileTool(AsyncTool):
    """文件写入工具"""

    def __init__(self):
        super().__init__(
            name="write_file",
            description="写入文件内容，会覆盖现有文件",
            parameters=[
                ToolParameter(
                    name="file_path",
                    type=ToolParameterType.STRING,
                    description="要写入的文件路径",
                    required=True
                ),
                ToolParameter(
                    name="content",
                    type=ToolParameterType.STRING,
                    description="要写入的内容",
                    required=True
                ),
                ToolParameter(
                    name="encoding",
                    type=ToolParameterType.STRING,
                    description="文件编码，默认为utf-8",
                    required=False,
                    default="utf-8"
                )
            ],
            category="file"
        )

    async def _execute_impl(self, **kwargs) -> ToolResult:
        """实现文件写入"""
        file_path = kwargs.get("file_path")
        content = kwargs.get("content", "")
        encoding = kwargs.get("encoding", "utf-8")

        if not file_path:
            return ToolResult(
                success=False,
                error="缺少必需参数: file_path",
                tool_name=self.metadata.name
            )

        try:
            path = Path(file_path).expanduser().resolve()

            # 创建父目录
            path.parent.mkdir(parents=True, exist_ok=True)

            # 检查文件是否存在
            existed = path.exists()
            old_size = path.stat().st_size if existed else 0

            # 写入文件
            path.write_text(content, encoding=encoding)

            new_size = path.stat().st_size

            action = "覆盖" if existed else "创建"

            return ToolResult(
                success=True,
                data={
                    "path": str(path),
                    "action": action,
                    "size": new_size,
                    "old_size": old_size if existed else None
                },
                tool_name=self.metadata.name
            )

        except PermissionError:
            return ToolResult(
                success=False,
                error=f"没有写入权限: {file_path}",
                tool_name=self.metadata.name
            )

        except Exception as e:
            logger.error(f"写入文件错误: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                tool_name=self.metadata.name
            )


class ListDirectoryTool(AsyncTool):
    """目录列表工具"""

    def __init__(self):
        super().__init__(
            name="list_directory",
            description="列出目录内容",
            parameters=[
                ToolParameter(
                    name="directory",
                    type=ToolParameterType.STRING,
                    description="要列出的目录路径，默认为当前目录",
                    required=False,
                    default="."
                ),
                ToolParameter(
                    name="recursive",
                    type=ToolParameterType.BOOLEAN,
                    description="是否递归列出子目录",
                    required=False,
                    default=False
                ),
                ToolParameter(
                    name="pattern",
                    type=ToolParameterType.STRING,
                    description="文件名匹配模式(如 *.py)",
                    required=False,
                    default=None
                )
            ],
            category="file"
        )

    async def _execute_impl(self, **kwargs) -> ToolResult:
        """实现目录列表"""
        directory = kwargs.get("directory", ".")
        recursive = kwargs.get("recursive", False)
        pattern = kwargs.get("pattern")

        try:
            path = Path(directory).expanduser().resolve()

            if not path.exists():
                return ToolResult(
                    success=False,
                    error=f"目录不存在: {directory}",
                    tool_name=self.metadata.name
                )

            if not path.is_dir():
                return ToolResult(
                    success=False,
                    error=f"路径不是目录: {directory}",
                    tool_name=self.metadata.name
                )

            items = []

            if recursive:
                # 递归列出
                for item in path.rglob("*") if not pattern else path.rglob(pattern):
                    if item.is_file():
                        items.append({
                            "name": item.name,
                            "path": str(item),
                            "size": item.stat().st_size,
                            "type": "file"
                        })
                    elif item.is_dir():
                        items.append({
                            "name": item.name + "/",
                            "path": str(item),
                            "type": "directory"
                        })
            else:
                # 只列出当前目录
                for item in path.iterdir():
                    if pattern and not item.match(pattern):
                        continue

                    info = {
                        "name": item.name,
                        "path": str(item),
                        "type": "directory" if item.is_dir() else "file"
                    }

                    if item.is_file():
                        info["size"] = item.stat().st_size

                    items.append(info)

            return ToolResult(
                success=True,
                data={
                    "directory": str(path),
                    "items": sorted(items, key=lambda x: (x["type"], x["name"])),
                    "count": len(items)
                },
                tool_name=self.metadata.name
            )

        except PermissionError:
            return ToolResult(
                success=False,
                error=f"没有访问权限: {directory}",
                tool_name=self.metadata.name
            )

        except Exception as e:
            logger.error(f"列出目录错误: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                tool_name=self.metadata.name
            )


class DeleteFileTool(AsyncTool):
    """文件删除工具"""

    def __init__(self):
        super().__init__(
            name="delete_file",
            description="删除文件或空目录",
            parameters=[
                ToolParameter(
                    name="file_path",
                    type=ToolParameterType.STRING,
                    description="要删除的文件路径",
                    required=True
                )
            ],
            category="file"
        )

    async def _execute_impl(self, **kwargs) -> ToolResult:
        """实现文件删除"""
        file_path = kwargs.get("file_path")

        if not file_path:
            return ToolResult(
                success=False,
                error="缺少必需参数: file_path",
                tool_name=self.metadata.name
            )

        try:
            path = Path(file_path).expanduser().resolve()

            if not path.exists():
                return ToolResult(
                    success=False,
                    error=f"文件不存在: {file_path}",
                    tool_name=self.metadata.name
                )

            if path.is_dir() and any(path.iterdir()):
                return ToolResult(
                    success=False,
                    error="目录不为空，无法删除",
                    tool_name=self.metadata.name
                )

            if path.is_file():
                size = path.stat().st_size
                path.unlink()
                item_type = "file"
            else:
                path.rmdir()
                size = None
                item_type = "directory"

            return ToolResult(
                success=True,
                data={
                    "path": str(path),
                    "type": item_type,
                    "size": size
                },
                tool_name=self.metadata.name
            )

        except PermissionError:
            return ToolResult(
                success=False,
                error=f"没有删除权限: {file_path}",
                tool_name=self.metadata.name
            )

        except Exception as e:
            logger.error(f"删除文件错误: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                tool_name=self.metadata.name
            )


def register_builtin_tools(registry) -> None:
    """
    注册所有内置文件操作工具

    Args:
        registry: 工具注册表
    """
    registry.register(ReadFileTool())
    registry.register(WriteFileTool())
    registry.register(ListDirectoryTool())
    registry.register(DeleteFileTool())
