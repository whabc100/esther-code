"""输出格式化模块"""

import re
import textwrap
from typing import Any, Dict, List, Optional
from rich.console import Console
from rich.syntax import Syntax
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich.json import JSON
from rich import box


class OutputFormatter:
    """输出格式化器"""

    def __init__(self, console: Optional[Console] = None):
        """
        初始化格式化器

        Args:
            console: Rich Console 实例
        """
        self.console = console or Console()

    def format_markdown(self, content: str) -> None:
        """
        格式化并显示 Markdown 内容

        Args:
            content: Markdown 内容
        """
        if not content or not content.strip():
            return

        markdown = Markdown(content)
        self.console.print(markdown)

    def format_code(self, code: str, language: str = "python") -> None:
        """
        格式化并显示代码

        Args:
            code: 代码内容
            language: 编程语言
        """
        if not code or not code.strip():
            return

        syntax = Syntax(code, language, theme="monokai", line_numbers=True)
        self.console.print(syntax)

    def format_json(self, data: Any) -> None:
        """
        格式化并显示 JSON 数据

        Args:
            data: 要显示的数据
        """
        self.console.print(JSON.from_data(data))

    def format_table(self, data: List[Dict[str, Any]], title: Optional[str] = None) -> None:
        """
        格式化并显示表格

        Args:
            data: 表格数据列表
            title: 表格标题
        """
        if not data:
            return

        table = Table(title=title, box=box.ROUNDED)

        # 添加列
        columns = list(data[0].keys())
        for col in columns:
            table.add_column(col, style="cyan")

        # 添加行
        for row in data:
            values = [str(row.get(col, "")) for col in columns]
            table.add_row(*values)

        self.console.print(table)

    def format_message(self, role: str, content: str) -> None:
        """
        格式化并显示消息

        Args:
            role: 消息角色 (user, assistant, system, tool)
            content: 消息内容
        """
        styles = {
            "user": "bold blue",
            "assistant": "bold green",
            "system": "bold yellow",
            "tool": "bold magenta"
        }

        role_style = styles.get(role, "bold white")

        if role == "user":
            self.console.print(f"[{role_style}]User:[/] {content}")
        elif role == "assistant":
            self.console.print()
            self.format_markdown(content)
        elif role == "tool":
            panel = Panel(content, title=f"[{role_style}]Tool Result[/]", style="dim")
            self.console.print(panel)

    def format_error(self, message: str) -> None:
        """
        格式化并显示错误信息

        Args:
            message: 错误消息
        """
        self.console.print(f"[bold red]Error:[/] {message}")

    def format_warning(self, message: str) -> None:
        """
        格式化并显示警告信息

        Args:
            message: 警告消息
        """
        self.console.print(f"[bold yellow]Warning:[/] {message}")

    def format_info(self, message: str) -> None:
        """
        格式化并显示信息

        Args:
            message: 信息消息
        """
        self.console.print(f"[bold cyan]Info:[/] {message}")

    def format_success(self, message: str) -> None:
        """
        格式化并显示成功信息

        Args:
            message: 成功消息
        """
        self.console.print(f"[bold green]Success:[/] {message}")

    def format_tool_call(self, tool_name: str, arguments: Dict[str, Any]) -> None:
        """
        格式化并显示工具调用

        Args:
            tool_name: 工具名称
            arguments: 工具参数
        """
        panel = Panel(
            JSON.from_data(arguments),
            title=f"[bold magenta]Calling:[/] {tool_name}",
            style="dim"
        )
        self.console.print(panel)

    def format_tool_result(
        self,
        tool_name: str,
        result: Dict[str, Any],
        success: bool = True
    ) -> None:
        """
        格式化并显示工具执行结果

        Args:
            tool_name: 工具名称
            result: 执行结果
            success: 是否成功
        """
        status = "[bold green]Success[/]" if success else "[bold red]Failed[/]"
        panel = Panel(
            JSON.from_data(result),
            title=f"{status} [bold magenta]{tool_name}[/]",
            style="green" if success else "red"
        )
        self.console.print(panel)

    def format_stream_chunk(self, chunk: str) -> None:
        """
        格式化并显示流式输出块

        Args:
            chunk: 输出内容块
        """
        # 直接输出，不换行
        self.console.print(chunk, end="")

    def clear_line(self) -> None:
        """清除当前行"""
        self.console.print("\r\033[K", end="")

    def separator(self) -> None:
        """打印分隔线"""
        self.console.print()

    def header(self, title: str) -> None:
        """
        打印标题头

        Args:
            title: 标题
        """
        panel = Panel(
            Text(title, justify="center"),
            style="bold blue"
        )
        self.console.print(panel)

    def help(self) -> None:
        """显示帮助信息"""
        help_text = """
[bold cyan]Esther Code - 终端 AI 编程助手[/]

[bold]命令:[/]
  /help      显示此帮助信息
  /exit      退出程序
  /clear     清空对话历史
  /tools     列出可用工具
  /config    显示当前配置

[bold]使用提示:[/]
  - 直接输入问题与AI对话
  - 可以请求AI执行文件操作
  - 支持多轮对话上下文
"""
        self.console.print(help_text)


class StreamingFormatter(OutputFormatter):
    """支持流式输出的格式化器"""

    def __init__(self, console: Optional[Console] = None):
        super().__init__(console)
        self._buffer = ""
        self._code_block = False
        self._code_language = ""
        self._code_buffer = ""

    def process_stream_chunk(self, chunk: str) -> Optional[str]:
        """
        处理流式输出块，返回需要显示的内容

        Args:
            chunk: 新的输出块

        Returns:
            Optional[str]: 需要显示的内容
        """
        if not chunk:
            return None

        self._buffer += chunk

        # 检测代码块
        code_start = re.search(r'```(\w+)?', chunk)
        code_end = re.search(r'```', chunk)

        if code_start and not self._code_block:
            # 代码块开始
            self._code_block = True
            self._code_language = code_start.group(1) or "text"
            return chunk[:code_start.start()]  # 返回代码块之前的内容
        elif code_end and self._code_block:
            # 代码块结束
            self._code_block = False
            # 格式化并显示代码块
            self.format_code(self._code_buffer, self._code_language)
            self._code_buffer = ""
            return chunk[code_end.end():]  # 返回代码块之后的内容
        elif self._code_block:
            # 在代码块中，缓存内容
            self._code_buffer += chunk
            return None

        # 普通文本，返回显示
        return chunk

    def flush(self) -> None:
        """刷新缓冲区，显示剩余内容"""
        if self._code_buffer:
            self.format_code(self._code_buffer, self._code_language)
            self._code_buffer = ""

        if self._buffer and not self._code_block:
            self.format_markdown(self._buffer)

        self._buffer = ""
