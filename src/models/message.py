"""消息模型模块"""

from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field


class MessageRole(str, Enum):
    """消息角色枚举"""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class MessageContent(BaseModel):
    """消息内容基类"""

    type: str


class TextContent(MessageContent):
    """文本内容"""

    type: str = Field(default="text", description="内容类型")
    text: str = Field(default="", description="文本内容")


class ToolCall(BaseModel):
    """工具调用"""

    id: str = Field(description="工具调用ID")
    type: str = Field(default="function", description="调用类型")
    function: Dict[str, str] = Field(description="函数信息")
    # function 包含:
    # - name: 函数名
    # - arguments: JSON字符串格式的参数


class ToolResult(BaseModel):
    """工具执行结果"""

    tool_call_id: str = Field(description="工具调用ID")
    role: str = Field(default="tool", description="角色")
    content: str = Field(description="执行结果内容")


class Message(BaseModel):
    """消息模型"""

    role: MessageRole = Field(description="消息角色")
    content: Union[str, List[MessageContent]] = Field(
        description="消息内容，可以是字符串或内容列表"
    )
    tool_calls: Optional[List[ToolCall]] = Field(
        default=None, description="工具调用列表"
    )
    tool_call_id: Optional[str] = Field(
        default=None, description="工具调用ID(用于tool消息)"
    )
    name: Optional[str] = Field(default=None, description="消息名称")

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式，用于API调用"""
        result: Dict[str, Any] = {"role": self.role.value}

        if isinstance(self.content, str):
            result["content"] = self.content
        else:
            result["content"] = [item.model_dump() for item in self.content]

        if self.tool_calls:
            result["tool_calls"] = [tc.model_dump() for tc in self.tool_calls]

        if self.tool_call_id:
            result["tool_call_id"] = self.tool_call_id

        if self.name:
            result["name"] = self.name

        return result


class Conversation(BaseModel):
    """对话会话"""

    messages: List[Message] = Field(default_factory=list, description="消息列表")
    system_prompt: Optional[str] = Field(
        default=None, description="系统提示词"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="元数据"
    )

    def add_message(self, message: Message) -> None:
        """添加消息"""
        self.messages.append(message)

    def add_user_message(self, content: str) -> None:
        """添加用户消息"""
        self.messages.append(Message(role=MessageRole.USER, content=content))

    def add_assistant_message(
        self,
        content: str,
        tool_calls: Optional[List[ToolCall]] = None
    ) -> None:
        """添加助手消息"""
        self.messages.append(
            Message(
                role=MessageRole.ASSISTANT,
                content=content,
                tool_calls=tool_calls
            )
        )

    def add_tool_result(self, tool_call_id: str, content: str) -> None:
        """添加工具结果消息"""
        self.messages.append(
            Message(
                role=MessageRole.TOOL,
                content=content,
                tool_call_id=tool_call_id
            )
        )

    def get_messages_for_api(self) -> List[Dict[str, Any]]:
        """获取用于API调用的消息列表"""
        messages = []

        if self.system_prompt:
            messages.append({
                "role": "system",
                "content": self.system_prompt
            })

        messages.extend([msg.to_dict() for msg in self.messages])

        return messages

    def clear(self) -> None:
        """清空对话"""
        self.messages.clear()


class ChatResponse(BaseModel):
    """聊天响应模型"""

    content: str = Field(description="响应内容")
    tool_calls: Optional[List[ToolCall]] = Field(
        default=None, description="工具调用列表"
    )
    finish_reason: str = Field(description="结束原因")
    usage: Optional[Dict[str, int]] = Field(
        default=None, description="使用量统计"
    )
    model: str = Field(description="使用的模型")
    stream: bool = Field(default=False, description="是否为流式响应")
