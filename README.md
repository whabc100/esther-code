# Esther Code - 终端 AI 编程工具

基于 GLM-4.7 模型的智能终端编程助手，提供对话、代码生成、文件操作和工具调用等功能。

## 功能特性

- 🤖 **智能对话**: 基于 GLM-4.7 的高质量 AI 对话
- 💻 **代码生成**: 支持多种编程语言的代码编写和优化
- 📁 **文件操作**: 智能文件读写、创建和修改
- 🔍 **代码搜索**: 快速搜索和理解代码库
- 🎨 **美化界面**: 基于 Rich 的终端美化显示
- 🚀 **流式输出**: 实时响应，流畅体验
- 🛠️ **工具系统**: 可扩展的工具调用机制

## 安装

### 1. 克隆或下载项目

```bash
cd esther-code
```

### 2. 创建虚拟环境 (推荐)

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 配置环境变量

复制 `.env.example` 为 `.env` 并设置你的 API Key:

```bash
cp .env.example .env
```

编辑 `.env` 文件，设置 `ZHIPUAI_API_KEY`:

```
ZHIPUAI_API_KEY=your_actual_api_key_here
```

获取 API Key: https://open.bigmodel.cn/

## 使用方法

### 启动程序

```bash
python -m src.main
```

### 交互示例

```bash
# 基础对话
> 你好

# 代码生成
> 用 Python 写一个快速排序算法

# 文件操作
> 创建一个包含 Hello World 的 test.py 文件

# 代码理解
> 帮我分析当前目录下的代码结构
```

### 退出

按 `Ctrl+C` 或输入 `/exit` 退出程序。

## 项目结构

```
esther-code/
├── src/
│   ├── main.py                 # CLI入口点
│   ├── config.py               # 配置管理
│   ├── models/                 # 数据模型
│   ├── client/                 # GLM-4.7客户端
│   ├── tools/                  # 工具系统
│   └── ui/                     # 用户界面
├── requirements.txt            # 依赖清单
├── .env.example               # 环境变量示例
└── README.md
```

## 技术栈

- **GLM-4.7**: 智谱AI 大语言模型
- **Python 3.10+**: 主要编程语言
- **Rich**: 终端美化
- **Prompt Toolkit**: 交互式输入
- **Pydantic**: 数据验证

## 开发计划

- [ ] 支持多轮对话历史
- [ ] 代码执行功能
- [ ] Git 集成
- [ ] 自定义工具开发
- [ ] 配置文件支持

## 许可证

MIT License
