#!/bin/bash
# Esther Code 依赖安装脚本

echo "=========================================="
echo "Esther Code - 依赖安装"
echo "=========================================="
echo ""

# 检查 Python 版本
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "Python 版本: $PYTHON_VERSION"

# 检查 pip
if command -v pip3 &> /dev/null; then
    echo "✓ pip3 已安装"
    PIP_CMD="pip3"
elif command -v pip &> /dev/null; then
    echo "✓ pip 已安装"
    PIP_CMD="pip"
else
    echo "✗ pip 未安装，正在安装..."
    curl -sS https://bootstrap.pypa.io/get-pip.py | python3
    if [ $? -eq 0 ]; then
        echo "✓ pip 安装成功"
        PIP_CMD="python3 -m pip"
    else
        echo "✗ pip 安装失败"
        echo "请手动安装 pip: https://pip.pypa.io/en/stable/installation/"
        exit 1
    fi
fi

echo ""
echo "安装依赖包..."
echo "------------------------------------------"

# 尝试普通安装
$PIP_CMD install -r requirements.txt

if [ $? -ne 0 ]; then
    echo ""
    echo "普通安装失败，尝试使用用户目录安装..."
    $PIP_CMD install --user -r requirements.txt

    if [ $? -ne 0 ]; then
        echo ""
        echo "✗ 依赖安装失败"
        echo ""
        echo "建议使用虚拟环境："
        echo "  python3 -m venv venv"
        echo "  source venv/bin/activate"
        echo "  pip install -r requirements.txt"
        echo "  python -m src.main"
        exit 1
    fi
fi

echo ""
echo "=========================================="
echo "✓ 依赖安装完成！"
echo "=========================================="
echo ""
echo "运行程序："
echo "  python -m src.main"
echo ""
