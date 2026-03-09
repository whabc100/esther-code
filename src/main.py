"""Esther Code - 终端 AI 编程工具主入口"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger
from src.config import init_config
from src.ui.cli import run_cli


def setup_logging(level: str) -> None:
    """
    配置日志系统

    Args:
        level: 日志级别
    """
    logger.remove()  # 移除默认处理器

    # 控制台输出
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=level,
        colorize=True
    )

    # 文件输出
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    logger.add(
        log_dir / "esther_{time:YYYY-MM-DD}.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level=level,
        rotation="00:00",  # 每天午夜轮换
        retention="7 days",  # 保留7天
        compression="zip"  # 压缩旧日志
    )


def print_banner() -> None:
    """打印欢迎横幅"""
    banner = """
╔══════════════════════════════════════════════════════════╗
║                                                          ║
║    ██████╗  █████╗ ██╗   ██╗ █████╗ ███████╗ ███████╗    ║
║    ██╔══██╗██╔══██╗██║   ██║██╔══██╗██╔════╝██╔════╝    ║
║    ██████╔╝██║  ██║██║   ██║██████╔╝██║     ███████╗    ║
║    ██╔══██╗██║  ██║██║   ██║██╔══██╗██║     ╚════██║    ║
║    ██║  ╚██║██████╔╝╚██████╔╝██║  ██║     ███████║    ║
║    ╚═╝   ╚═╝╚═════╝  ╚═════╝ ╚═╝   ╚═╝     ╚═════╝    ║
║                                                          ║
║                    ESTHER CODE v0.1.0              ║
║              终端 AI 编程助手                         ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
"""
    print(banner)


def check_env() -> None:
    """检查环境配置"""
    import os

    if not os.path.exists(".env"):
        print("[bold yellow]警告: .env 文件不存在[/]")
        print("[yellow]请复制 .env.example 为 .env 并设置 ZHIPUAI_API_KEY[/]")
        print()

        # 尝试从环境变量读取
        api_key = os.environ.get("ZHIPUAI_API_KEY")
        if api_key:
            print("[green]✓[/] 已从环境变量读取 ZHIPUAI_API_KEY")
        else:
            print("[red]✗[/] 未找到 ZHIPUAI_API_KEY 配置")
            print("[yellow]程序可能无法正常运行[/]")
            print()


def main() -> None:
    """主函数"""
    print_banner()
    check_env()

    try:
        # 初始化配置
        config = init_config()

        # 设置日志
        setup_logging(config.log_level)

        logger.info("Esther Code 启动")

        # 运行 CLI
        asyncio.run(run_cli())

    except KeyboardInterrupt:
        logger.info("用户中断")
        print("\n[bold yellow]再见![/]")
    except Exception as e:
        logger.error(f"程序错误: {e}")
        print(f"[bold red]发生错误:[/] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
