# CONVENTIONS.md — Personal AI Toolkit 全仓库开发规范

本文档定义本仓库内所有代码、工具及文档必须遵循的统一工程约定。

---

## 1. 核心设计原则

- **高扩展性**：新增工具与组件应以原子化插件方式接入，不修改既有公共架构。
- **自包含与解耦**：每个工具独立维护依赖、配置、执行逻辑与输出，禁止工具间相互耦合。
- **环境无关**：拒绝硬编码操作系统路径，保证在跨平台（Windows, Linux, macOS）环境下行为一致。

---

## 2. 工具结构规范（必须包含 5 要素）

在 `tools/<分类>/<工具名称>/` 下，每个工具**必须包含**以下五个基本要素：

```text
tools/<category>/<tool-name>/
├── README.md        # 工具统一说明文档
├── requirements.txt # 独立第三方 Python 依赖清单
├── .env.example     # 环境变量配置模板
├── main.py          # 工具主运行入口
└── output/          # 产物输出目录（附带 .gitkeep）
```

缺少以上任何一项均视为不符合仓库规范。

---

## 3. 工具 README.md 统一格式

所有工具的 `README.md` 必须严格包含以下 7 个二级标题：

```markdown
# 工具名称

## 功能

## 输入

## 输出

## 环境配置

## 安装依赖

## 运行方式

## 示例
```

各章节内容定义：
- **`# 工具名称`**：工具中文名称及简明概述。
- **`## 功能`**：工具的核心特性清单。
- **`## 输入`**：工具需要的命令行输入、输入文件或外部 API 依赖。
- **`## 输出`**：工具输出的日志格式及在 `output/` 目录下生成的文件格式。
- **`## 环境配置`**：说明所需配置的 `.env` 变量列表、默认值与获取方式。
- **`## 安装依赖`**：执行 `pip install -r requirements.txt`。
- **`## 运行方式`**：说明如何启动工具（如 `python main.py` 或附带的 CLI 参数）。
- **`## 示例`**：提供真实可行的执行命令及预期控制台/产物示例。

---

## 4. 环境变量与安全规范

1. **禁止提交私密配置**：
   - 包含真实凭证的 `.env` 严禁提交至 Git 仓库（已由根目录 `.gitignore` 忽略）。
2. **强制提供 `.env.example`**：
   - 工具所需的全部环境变量必须在 `.env.example` 中清晰列出。
   - 命名格式统一采用全大写蛇形命名法（如 `OPENAI_API_KEY`, `FEISHU_WEBHOOK_URL`）。
3. **配置加载约定**：
   - 统一使用 `python-dotenv` 加载当前工具目录下的 `.env` 文件。

---

## 5. 代码与路径约定

1. **相对路径解析**：
   - 脚本内部涉及文件读写操作时，必须基于脚本所在目录进行相对解析：
     ```python
     from pathlib import Path

     BASE_DIR = Path(__file__).resolve().parent
     OUTPUT_DIR = BASE_DIR / "output"
     OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
     ```
2. **编码规范**：
   - Python 代码遵循 PEP 8 规范。
   - 所有 Python 文件开头指定 UTF-8 编码或使用标准 Python 3 语法。
   - 函数和核心流程需附带清晰的注释与类型提示（Type Hints）。

---

## 6. Git 提交规范

建议遵循约定式提交（Conventional Commits）：

- `feat(tools/<category>): add <tool-name>` — 新增工具
- `fix(tools/<tool-name>): fix issue description` — 修复工具 bug
- `docs: update documentation` — 更新说明文档或规范
- `chore: repository maintenance` — 维护与配置调整
