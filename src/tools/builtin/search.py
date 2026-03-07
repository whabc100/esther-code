"""文件搜索工具模块"""

import re
from pathlib import Path
from typing import Optional, List, Pattern
from loguru import logger

from ...models.tools import AsyncTool, ToolParameter, ToolParameterType, ToolResult
import pathspec


class SearchFilesTool(AsyncTool):
    """文件搜索工具 - 按名称搜索"""

    def __init__(self):
        super().__init__(
            name="search_files",
            description="搜索文件，支持通配符模式匹配",
            parameters=[
                ToolParameter(
                    name="pattern",
                    type=ToolParameterType.STRING,
                    description="搜索模式，支持通配符(如 *.py, test*.txt)",
                    required=True
                ),
                ToolParameter(
                    name="directory",
                    type=ToolParameterType.STRING,
                    description="搜索目录，默认为当前目录",
                    required=False,
                    default="."
                ),
                ToolParameter(
                    name="recursive",
                    type=ToolParameterType.BOOLEAN,
                    description="是否递归搜索子目录",
                    required=False,
                    default=True
                ),
                ToolParameter(
                    name="max_results",
                    type=ToolParameterType.INTEGER,
                    description="最大结果数量",
                    required=False,
                    default=100
                )
            ],
            category="search"
        )

    async def _execute_impl(self, **kwargs) -> ToolResult:
        """实现文件搜索"""
        pattern = kwargs.get("pattern")
        directory = kwargs.get("directory", ".")
        recursive = kwargs.get("recursive", True)
        max_results = kwargs.get("max_results", 100)

        if not pattern:
            return ToolResult(
                success=False,
                error="缺少必需参数: pattern",
                tool_name=self.metadata.name
            )

        try:
            path = Path(directory).expanduser().resolve()

            if not path.exists():
                return ToolResult(
                    success=False,
                    error=f"目录不存在: {directory}",
                    tool_name=self.metadata.name
                )

            results = []

            if recursive:
                # 使用 glob 递归搜索
                # **/* 表示递归所有子目录
                search_pattern = f"**/{pattern}"
                for item in path.glob(search_pattern):
                    if item.is_file():
                        results.append({
                            "path": str(item.relative_to(path)) if path != item else item.name,
                            "full_path": str(item),
                            "size": item.stat().st_size
                        })
                        if len(results) >= max_results:
                            break
            else:
                # 只搜索当前目录
                for item in path.glob(pattern):
                    if item.is_file():
                        results.append({
                            "path": item.name,
                            "full_path": str(item),
                            "size": item.stat().st_size
                        })
                        if len(results) >= max_results:
                            break

            return ToolResult(
                success=True,
                data={
                    "pattern": pattern,
                    "directory": str(path),
                    "results": results,
                    "count": len(results)
                },
                tool_name=self.metadata.name
            )

        except Exception as e:
            logger.error(f"搜索文件错误: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                tool_name=self.metadata.name
            )


class SearchContentTool(AsyncTool):
    """内容搜索工具 - 搜索文件内容"""

    def __init__(self):
        super().__init__(
            name="search_content",
            description="在文件中搜索内容",
            parameters=[
                ToolParameter(
                    name="query",
                    type=ToolParameterType.STRING,
                    description="要搜索的内容(支持正则表达式)",
                    required=True
                ),
                ToolParameter(
                    name="directory",
                    type=ToolParameterType.STRING,
                    description="搜索目录，默认为当前目录",
                    required=False,
                    default="."
                ),
                ToolParameter(
                    name="file_pattern",
                    type=ToolParameterType.STRING,
                    description="文件名模式(如 *.py)，只搜索匹配的文件",
                    required=False,
                    default=None
                ),
                ToolParameter(
                    name="case_sensitive",
                    type=ToolParameterType.BOOLEAN,
                    description="是否区分大小写",
                    required=False,
                    default=False
                ),
                ToolParameter(
                    name="max_results",
                    type=ToolParameterType.INTEGER,
                    description="最大匹配结果数",
                    required=False,
                    default=50
                )
            ],
            category="search"
        )

    async def _execute_impl(self, **kwargs) -> ToolResult:
        """实现内容搜索"""
        query = kwargs.get("query")
        directory = kwargs.get("directory", ".")
        file_pattern = kwargs.get("file_pattern")
        case_sensitive = kwargs.get("case_sensitive", False)
        max_results = kwargs.get("max_results", 50)

        if not query:
            return ToolResult(
                success=False,
                error="缺少必需参数: query",
                tool_name=self.metadata.name
            )

        try:
            path = Path(directory).expanduser().resolve()

            if not path.exists():
                return ToolResult(
                    success=False,
                    error=f"目录不存在: {directory}",
                    tool_name=self.metadata.name
                )

            # 编译正则表达式
            flags = 0 if case_sensitive else re.IGNORECASE
            regex = re.compile(query, flags)

            results = []
            total_matches = 0

            # 确定要搜索的文件
            if file_pattern:
                files = list(path.glob(f"**/{file_pattern}"))
            else:
                files = [f for f in path.rglob("*") if f.is_file()]

            # 排除二进制文件
            binary_extensions = {
                '.pyc', '.pyo', '.so', '.dll', '.exe', '.bin',
                '.zip', '.tar', '.gz', '.pdf', '.png', '.jpg', '.jpeg',
                '.gif', '.mp3', '.mp4', '.wav', '.ogg'
            }

            for file_path in files:
                if file_path.suffix in binary_extensions:
                    continue

                try:
                    content = file_path.read_text(encoding='utf-8', errors='ignore')
                    lines = content.split('\n')

                    file_matches = []
                    for line_num, line in enumerate(lines, 1):
                        if regex.search(line):
                            file_matches.append({
                                "line_number": line_num,
                                "line": line.strip(),
                                "match": regex.search(line).group(0) if regex.search(line) else ""
                            })

                    if file_matches:
                        results.append({
                            "path": str(file_path.relative_to(path)) if path != file_path else file_path.name,
                            "matches": file_matches[:10],  # 限制每个文件的匹配数
                            "match_count": len(file_matches)
                        })
                        total_matches += len(file_matches)

                        if total_matches >= max_results:
                            break

                except Exception:
                    # 跳过无法读取的文件
                    continue

            return ToolResult(
                success=True,
                data={
                    "query": query,
                    "directory": str(path),
                    "results": results,
                    "total_matches": total_matches,
                    "file_count": len(results)
                },
                tool_name=self.metadata.name
            )

        except re.error as e:
            return ToolResult(
                success=False,
                error=f"正则表达式错误: {e}",
                tool_name=self.metadata.name
            )

        except Exception as e:
            logger.error(f"搜索内容错误: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                tool_name=self.metadata.name
            )


class GetFileStatsTool(AsyncTool):
    """文件统计工具"""

    def __init__(self):
        super().__init__(
            name="get_file_stats",
            description="获取文件或目录的统计信息",
            parameters=[
                ToolParameter(
                    name="path",
                    type=ToolParameterType.STRING,
                    description="文件或目录路径",
                    required=True
                )
            ],
            category="search"
        )

    async def _execute_impl(self, **kwargs) -> ToolResult:
        """实现文件统计"""
        path_str = kwargs.get("path")

        if not path_str:
            return ToolResult(
                success=False,
                error="缺少必需参数: path",
                tool_name=self.metadata.name
            )

        try:
            path = Path(path_str).expanduser().resolve()

            if not path.exists():
                return ToolResult(
                    success=False,
                    error=f"路径不存在: {path_str}",
                    tool_name=self.metadata.name
                )

            stat = path.stat()

            info = {
                "path": str(path),
                "name": path.name,
                "type": "directory" if path.is_dir() else "file",
                "size": stat.st_size,
                "modified": stat.st_mtime,
                "created": stat.st_ctime
            }

            if path.is_file():
                try:
                    content = path.read_text(encoding='utf-8', errors='ignore')
                    info["lines"] = content.count('\n') + 1
                    info["characters"] = len(content)
                    info["words"] = len(content.split())
                except Exception:
                    pass

            return ToolResult(
                success=True,
                data=info,
                tool_name=self.metadata.name
            )

        except Exception as e:
            logger.error(f"获取文件统计错误: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                tool_name=self.metadata.name
            )


def register_builtin_search_tools(registry) -> None:
    """
    注册所有内置搜索工具

    Args:
        registry: 工具注册表
    """
    registry.register(SearchFilesTool())
    registry.register(SearchContentTool())
    registry.register(GetFileStatsTool())
