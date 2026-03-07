#!/usr/bin/env python3
"""
Esther Code 项目测试脚本
验证项目结构和基本功能
"""

import ast
import os
import sys
from pathlib import Path
from typing import List, Tuple


class ProjectTester:
    """项目测试器"""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.results = []
        self.passed = 0
        self.failed = 0

    def test_file_exists(self, relative_path: str, description: str) -> bool:
        """
        测试文件是否存在

        Args:
            relative_path: 相对路径
            description: 描述

        Returns:
            bool: 测试是否通过
        """
        file_path = self.project_root / relative_path
        exists = file_path.exists()

        self.results.append({
            "test": description,
            "status": "PASS" if exists else "FAIL",
            "expected": relative_path,
            "found": str(file_path) if exists else "Not found"
        })

        if exists:
            self.passed += 1
        else:
            self.failed += 1

        return exists

    def test_python_syntax(self, relative_path: str) -> bool:
        """
        测试 Python 文件语法

        Args:
            relative_path: 相对路径

        Returns:
            bool: 语法是否正确
        """
        file_path = self.project_root / relative_path

        if not file_path.exists():
            self.failed += 1
            return False

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                ast.parse(f.read())

            self.results.append({
                "test": f"Syntax check: {relative_path}",
                "status": "PASS",
                "expected": "Valid Python syntax",
                "found": "Valid"
            })
            self.passed += 1
            return True

        except SyntaxError as e:
            self.results.append({
                "test": f"Syntax check: {relative_path}",
                "status": "FAIL",
                "expected": "Valid Python syntax",
                "found": f"Line {e.lineno}: {e.msg}"
            })
            self.failed += 1
            return False

    def test_file_has_content(self, relative_path: str, min_lines: int = 1) -> bool:
        """
        测试文件是否有内容

        Args:
            relative_path: 相对路径
            min_lines: 最小行数

        Returns:
            bool: 是否有足够内容
        """
        file_path = self.project_root / relative_path

        if not file_path.exists():
            return False

        lines = file_path.read_text(encoding='utf-8').split('\n')
        actual_lines = len([l for l in lines if l.strip()])

        has_content = actual_lines >= min_lines

        self.results.append({
            "test": f"Content check: {relative_path}",
            "status": "PASS" if has_content else "FAIL",
            "expected": f"At least {min_lines} lines",
            "found": f"{actual_lines} lines"
        })

        if has_content:
            self.passed += 1
        else:
            self.failed += 1

        return has_content

    def test_module_import(self, relative_path: str, module_path: str) -> bool:
        """
        测试模块是否可以导入（语法层面）

        Args:
            relative_path: 文件相对路径
            module_path: 模块路径

        Returns:
            bool: 模块结构是否正确
        """
        file_path = self.project_root / relative_path

        if not file_path.exists():
            self.failed += 1
            return False

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 检查基本的 Python 结构
            ast.parse(content)

            self.results.append({
                "test": f"Module structure: {module_path}",
                "status": "PASS",
                "expected": "Valid module",
                "found": "Valid"
            })
            self.passed += 1
            return True

        except Exception as e:
            self.results.append({
                "test": f"Module structure: {module_path}",
                "status": "FAIL",
                "expected": "Valid module",
                "found": str(e)
            })
            self.failed += 1
            return False

    def run_all_tests(self) -> None:
        """运行所有测试"""
        print("=" * 60)
        print("Esther Code 项目测试")
        print("=" * 60)
        print()

        # 测试文件结构
        print("测试文件结构...")
        print("-" * 40)

        required_files = {
            "src/main.py": "CLI 入口点",
            "src/config.py": "配置管理",
            "src/models/message.py": "消息模型",
            "src/models/tools.py": "工具定义",
            "src/client/async_client.py": "异步客户端",
            "src/client/stream_handler.py": "流式处理器",
            "src/tools/registry.py": "工具注册表",
            "src/tools/executor.py": "工具执行器",
            "src/tools/builtin/file_ops.py": "文件操作工具",
            "src/tools/builtin/search.py": "搜索工具",
            "src/ui/cli.py": "CLI 主界面",
            "src/ui/formatter.py": "输出格式化",
            "requirements.txt": "依赖清单",
            ".env.example": "环境变量示例",
            ".gitignore": "Git 忽略配置",
            "README.md": "项目说明"
        }

        for file_path, description in required_files.items():
            self.test_file_exists(file_path, description)

        # 测试 Python 语法
        print("\n测试 Python 语法...")
        print("-" * 40)

        python_files = list(self.project_root.rglob("*.py"))
        for py_file in python_files:
            rel_path = py_file.relative_to(self.project_root)
            self.test_python_syntax(str(rel_path))

        # 测试文件内容
        print("\n测试文件内容...")
        print("-" * 40)

        content_tests = [
            ("src/main.py", 50, "main.py 内容"),
            ("src/config.py", 30, "config.py 内容"),
            ("src/client/async_client.py", 80, "async_client.py 内容"),
            ("src/tools/registry.py", 30, "registry.py 内容"),
            ("src/ui/cli.py", 80, "cli.py 内容")
        ]

        for file_path, min_lines, description in content_tests:
            self.test_file_has_content(file_path, min_lines)

        # 测试模块结构
        print("\n测试模块结构...")
        print("-" * 40)

        module_tests = [
            ("src/config.py", "src.config"),
            ("src/models/message.py", "src.models.message"),
            ("src/models/tools.py", "src.models.tools"),
            ("src/client/async_client.py", "src.client.async_client"),
            ("src/tools/registry.py", "src.tools.registry"),
            ("src/tools/executor.py", "src.tools.executor"),
            ("src/ui/cli.py", "src.ui.cli"),
        ]

        for file_path, module_path in module_tests:
            self.test_module_import(file_path, module_path)

        # 打印结果
        self.print_results()

    def print_results(self) -> None:
        """打印测试结果"""
        print()
        print("=" * 60)
        print("测试结果汇总")
        print("=" * 60)

        total = self.passed + self.failed
        percentage = (self.passed / total * 100) if total > 0 else 0

        print(f"总计: {total}")
        print(f"通过: {self.passed} ({percentage:.1f}%)")
        print(f"失败: {self.failed}")

        if self.failed > 0:
            print("\n失败的测试:")
            print("-" * 40)
            for result in self.results:
                if result["status"] == "FAIL":
                    print(f"  - {result['test']}")
                    print(f"    Expected: {result['expected']}")
                    print(f"    Found: {result['found']}")
            print()

        print("=" * 60)

        if self.failed == 0:
            print("所有测试通过!")
            return 0
        else:
            print(f"有 {self.failed} 个测试失败")
            return 1


def main():
    """主函数"""
    project_root = Path(__file__).parent

    tester = ProjectTester(project_root)
    exit_code = tester.run_all_tests()

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
