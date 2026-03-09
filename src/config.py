"""配置管理模块"""

import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置类"""

    # GLM-4.7 API 配置
    zhipuai_api_key: str = Field(default="", description="智谱AI API密钥")
    zhipuai_model: str = Field(default="glm-4.7", description="使用的模型ID")
    zhipuai_api_base: Optional[str] = Field(
        default=None,
        description="自定义API端点"
    )

    # 日志配置
    log_level: str = Field(default="INFO", description="日志级别")
    log_dir: Path = Field(default=Path("logs"), description="日志目录")

    # 请求配置
    max_retries: int = Field(default=3, description="最大重试次数", ge=0, le=10)
    request_timeout: int = Field(default=120, description="请求超时时间(秒)", ge=10)
    stream_chunk_size: int = Field(default=4, description="流式响应块大小", ge=1)

    # UI 配置
    max_display_width: int = Field(default=120, description="最大显示宽度", ge=40)
    show_thinking: bool = Field(default=True, description="是否显示思考过程")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """验证日志级别"""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v = v.upper()
        if v not in valid_levels:
            raise ValueError(f"日志级别必须是: {', '.join(valid_levels)}")
        return v

    @field_validator("zhipuai_api_key")
    @classmethod
    def validate_api_key(cls, v: str) -> str:
        """验证API密钥"""
        if not v:
            raise ValueError(
                "ZHIPUAI_API_KEY 未设置，请在 .env 文件中配置或设置环境变量"
            )
        return v


# 全局配置实例
_settings: Optional[Settings] = None


def init_config(env_file: Optional[str] = None) -> Settings:
    """
    初始化配置

    Args:
        env_file: 环境变量文件路径

    Returns:
        Settings: 配置实例
    """
    if env_file:
        load_dotenv(env_file)
    else:
        # 尝试加载 .env 文件
        load_dotenv()

    return Settings()


def get_config() -> Settings:
    """
    获取配置实例

    Returns:
        Settings: 配置实例

    Raises:
        RuntimeError: 如果配置未初始化
    """
    global _settings
    if _settings is None:
        _settings = init_config()
    return _settings


def reload_config() -> Settings:
    """
    重新加载配置

    Returns:
        Settings: 新的配置实例
    """
    global _settings
    settings = init_config()
    _settings = settings
    return settings
