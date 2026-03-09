"""CLI 主界面模块"""

import asyncio
import signal
from typing import Optional, List
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.styles import Style
from loguru import logger

from ..config import get_config
from ..models.message import Message, MessageRole, Conversation, ToolCall
from ..client.async_client import GLMAsyncClient, get_client
from ..tools.registry import ToolRegistry, get_registry
from ..tools.executor import ToolExecutor, get_executor
from ..tools.builtin.file_ops import register_builtin_tools
from ..tools.builtin.search import register_builtin_search_tools
from .formatter import StreamingFormatter


class CLI:
    """CLI 主界面"""

    def __init__(
        self,
        client: Optional[GLMAsyncClient] = None,
        registry: Optional[ToolRegistry] = None,
        executor: Optional[ToolExecutor] = None
    ):
        """
        初始化 CLI

        Args:
            client: GLM客户端
            registry: 工具注册表
            executor: 工具执行器
        """
        self.client = client
        self.registry = registry
        self.executor = executor
        self.formatter = StreamingFormatter()
        self.conversation = Conversation()
        self.running = False

        # 设置系统提示
        self.conversation.system_prompt = """你是 Esther，一个智能编程助手。你的任务是帮助用户进行编程相关的任务。

你具备以下能力：
1. 代码编写和解释
2. 调试和优化代码
3. 文件操作（读取、写入、搜索）
4. 代码理解和重构

在回答时：
- 尽量简洁明了
- 代码使用markdown代码块格式
- 遵循最佳实践
- 提供实际可运行的代码

你可以使用工具来操作文件系统。当需要读取或写入文件时，请主动调用相应的工具。"""

        # 初始化提示会话
        self.session = PromptSession(
            history=FileHistory(".esther_history"),
            auto_suggest=True
        )

        # 设置样式
        self.style = Style.from_dict({
            "prompt": "ansiblue bold",
            "assistant": "ansigreen",
            "user": "ansicyan",
        })

        # 设置键绑定
        self._setup_key_bindings()

    def _setup_key_bindings(self):
        """设置键绑定"""
        kb = KeyBindings()

        @kb.add("c-c")
        def _(event):
            """Ctrl+C 退出"""
            event.app.exit(exception=KeyboardInterrupt, style="class:aborting")

        self.key_bindings = kb

    async def initialize(self) -> None:
        """初始化 CLI"""
        config = get_config()

        # 初始化客户端
        if self.client is None:
            self.client = await get_client()

        # 初始化注册表
        if self.registry is None:
            self.registry = get_registry()
            # 注册内置工具
            register_builtin_tools(self.registry)
            register_builtin_search_tools(self.registry)

        # 初始化执行器
        if self.executor is None:
            self.executor = get_executor()

        logger.info("CLI 初始化完成")

    async def run(self) -> None:
        """运行 CLI 主循环"""
        await self.initialize()

        # 显示欢迎信息
        self._show_welcome()

        self.running = True

        # 设置信号处理
        self._setup_signal_handlers()

        try:
            while self.running:
                # 获取用户输入
                user_input = await self._get_input()

                if not user_input:
                    continue

                # 处理命令
                if user_input.startswith("/"):
                    await self._handle_command(user_input)
                    continue

                # 处理对话
                await self._handle_conversation(user_input)

        except KeyboardInterrupt:
            print("\n\n[bold yellow]正在退出...[/]")
        except Exception as e:
            logger.error(f"CLI 错误: {e}")
        finally:
            await self.cleanup()

    def _show_welcome(self) -> None:
        """显示欢迎信息"""
        self.formatter.header("Esther Code v0.1.0")
        self.formatter.separator()
        self.formatter.format_info("输入 /help 查看帮助，输入 /exit 退出")
        self.formatter.separator()

    async def _get_input(self) -> str:
        """
        获取用户输入

        Returns:
            str: 用户输入
        """
        try:
            result = await self.session.prompt_async(
                "user: ",
                style=self.style,
                key_bindings=self.key_bindings
            )
            return result.strip()
        except (EOFError, KeyboardInterrupt):
            self.running = False
            return "/exit"

    async def _handle_command(self, command: str) -> None:
        """
        处理命令

        Args:
            command: 命令字符串
        """
        parts = command.split()
        cmd = parts[0].lower()

        if cmd == "/exit" or cmd == "/quit":
            self.running = False
        elif cmd == "/help":
            self.formatter.help()
        elif cmd == "/clear":
            self.conversation.clear()
            self.formatter.format_success("对话历史已清空")
        elif cmd == "/tools":
            await self._list_tools()
        elif cmd == "/config":
            self._show_config()
        else:
            self.formatter.format_warning(f"未知命令: {command}")

    async def _list_tools(self) -> None:
        """列出可用工具"""
        tools = self.registry.get_enabled()

        if not tools:
            self.formatter.format_info("没有可用工具")
            return

        table_data = []
        for tool in tools:
            table_data.append({
                "Name": tool.metadata.name,
                "Category": tool.metadata.category,
                "Description": tool.metadata.description
            })

        self.formatter.format_table(table_data, title="可用工具")

    def _show_config(self) -> None:
        """显示当前配置"""
        config = get_config()
        self.formatter.format_json({
            "model": config.zhipuai_model,
            "log_level": config.log_level,
            "max_retries": config.max_retries,
            "timeout": config.request_timeout
        })

    async def _handle_conversation(self, user_input: str) -> None:
        """
        处理对话

        Args:
            user_input: 用户输入
        """
        # 添加用户消息
        self.conversation.add_user_message(user_input)

        # 显示用户消息
        self.formatter.format_message("user", user_input)

        try:
            # 准备 API 调用
            messages = self.conversation.get_messages_for_api()
            tools = self.registry.get_definitions(enabled_only=True)

            # 调用 API
            full_response = ""
            tool_calls: Optional[List[ToolCall]] = None

            async for chunk in self.client.chat(
                messages=messages,
                tools=tools,
                stream=True
            ):
                # 处理不同类型的块
                if chunk.event == "delta" and chunk.content:
                    # 流式输出内容
                    full_response += chunk.content
                    self.formatter.format_stream_chunk(chunk.content)

                elif chunk.event == "tool_call" and chunk.tool_call:
                    # 工具调用
                    if tool_calls is None:
                        tool_calls = []

                    # 处理工具调用
                    tool_call = chunk.tool_call
                    call = ToolCall(
                        id=tool_call.get("id", ""),
                        type=tool_call.get("type", "function"),
                        function=tool_call.get("function", {})
                    )

                    # 检查是否已有同名工具调用
                    existing = next(
                        (tc for tc in tool_calls if tc.id == call.id),
                        None
                    )
                    if existing:
                        # 追加参数
                        if call.function.get("arguments"):
                            existing.function["arguments"] += call.function["arguments"]
                        if call.function.get("name"):
                            existing.function["name"] = call.function["name"]
                    else:
                        tool_calls.append(call)

            # 换行
            self.formatter.separator()

            # 处理工具调用
            if tool_calls:
                await self._execute_tool_calls(tool_calls)

            # 添加助手响应到对话
            if full_response:
                self.conversation.add_assistant_message(
                    full_response,
                    tool_calls=[tc.model_dump() for tc in tool_calls] if tool_calls else None
                )

        except Exception as e:
            logger.error(f"对话处理错误: {e}")
            self.formatter.format_error(f"发生错误: {e}")

    async def _execute_tool_calls(self, tool_calls: List[ToolCall]) -> None:
        """
        执行工具调用

        Args:
            tool_calls: 工具调用列表
        """
        self.formatter.format_info(f"执行 {len(tool_calls)} 个工具调用...")

        # 逐个执行工具
        for tool_call in tool_calls:
            tool_name = tool_call.function.get("name", "")
            arguments = tool_call.function.get("arguments", "{}")

            # 显示工具调用
            self.formatter.format_tool_call(
                tool_name,
                arguments
            )

            # 执行工具
            result = await self.executor.execute(
                tool_name,
                arguments
            )

            # 显示结果
            if result.success:
                self.formatter.format_tool_result(
                    tool_name,
                    result.data,
                    success=True
                )
            else:
                self.formatter.format_tool_result(
                    tool_name,
                    {"error": result.error},
                    success=False
                )

            # 添加工具结果到对话
            self.conversation.add_tool_result(
                tool_call.id,
                result.model_dump_json()
            )

        # 使用工具结果继续对话
        await self._continue_conversation()

    async def _continue_conversation(self) -> None:
        """使用工具结果继续对话"""
        messages = self.conversation.get_messages_for_api()

        try:
            full_response = ""

            async for chunk in self.client.chat(
                messages=messages,
                stream=True
            ):
                if chunk.event == "delta" and chunk.content:
                    full_response += chunk.content
                    self.formatter.format_stream_chunk(chunk.content)

            self.formatter.separator()

            if full_response:
                self.conversation.add_assistant_message(full_response)

        except Exception as e:
            logger.error(f"继续对话错误: {e}")

    def _setup_signal_handlers(self):
        """设置信号处理器"""
        try:
            signal.signal(signal.SIGINT, self._signal_handler)
        except ValueError:
            # Windows 不支持 SIGINT
            pass

    def _signal_handler(self, signum, frame):
        """信号处理器"""
        self.running = False

    async def cleanup(self) -> None:
        """清理资源"""
        logger.info("正在清理资源...")

        if self.client:
            await self.client.close()

        logger.info("清理完成")


async def run_cli() -> None:
    """运行 CLI 的入口函数"""
    cli = CLI()
    await cli.run()
