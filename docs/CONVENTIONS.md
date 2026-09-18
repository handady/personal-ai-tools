# CONVENTIONS.md — Personal AI Toolkit 全仓库开发规范

本文档定义本仓库内所有代码、工具及文档必须遵循的统一工程约定。

---

## 1. 核心设计原则

- **高扩展性**：新增工具与组件应以原子化插件方式接入，不修改既有公共架构。
- **自包含与解耦**：每个工具独立维护依赖、配置、执行逻辑与输出，禁止工具间相互耦合。
- **环境无关**：拒绝硬编码操作系统路径，保证在跨平台（Windows, Linux, macOS）环境下行为一致。

---

## 2. 工具结构规范（必须包含 7 要素）

在 `tools/<分类>/<工具名称>/` 下，每个工具**必须包含**以下七个基本要素：

```text
tools/<category>/<tool-name>/
├── README.md           # 工具统一说明文档
├── requirements.txt    # 独立第三方 Python 依赖清单
├── config.example.json # 配置文件参考模板（提交至 Git）
├── main.py             # 工具主运行入口（集成首次运行配置向导）
├── data/               # 缓存数据存储目录（附带 .gitkeep）
├── logs/               # 运行日志存储目录（附带 .gitkeep）
└── output/             # 产物输出目录（附带 .gitkeep）
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
- **`## 输出`**：明确说明 `data/`（缓存数据）、`logs/`（运行日志）与 `output/`（结果产物）各自记录的内容。
- **`## 环境配置`**：说明 `config.json` 各配置项含义、默认值及首次运行交互式引导流程（**禁止要求用户配置系统环境变量**）。
- **`## 安装依赖`**：执行 `pip install -r requirements.txt`。
- **`## 运行方式`**：说明如何启动工具（如 `python main.py` 或附带的 CLI 参数）。
- **`## 示例`**：提供真实可行的执行命令及预期控制台/产物示例。

---

## 4. 配置管理与首次运行规则

1. **配置优先原则**：
   - 优先且必须使用当前工具目录下的 `config.json`。
   - **禁止要求用户配置系统环境变量**。
2. **Git 版本控制规则**：
   - **提交**：`config.example.json`。
   - **忽略**：`config.json`（严禁将私密配置提交到版本库）。
3. **首次运行规则（强制）**：
   当用户或 AI 首次在工具目录下运行 `python main.py` 且 `config.json` 尚未存在时：
   1. **自动检测**：检测到 `config.json` 缺失；
   2. **自动创建配置向导**：自动进入终端配置向导流程；
   3. **询问用户所需配置**：依据 `config.example.json` 的字段逐一提示用户输入；
   4. **自动生成 `config.json`**：将输入或默认值格式化写入 `config.json`；
   5. **提示重新运行**：提示用户配置已完成，引导重新执行 `python main.py` 并正常退出。

---

## 5. 目录职责规范 (Data / Logs / Output)

- **`data/`**：仅用于存放本地持久化缓存、离线数据源、临时快照等中间数据。
- **`logs/`**：仅用于存放工具运行日志（如 debug.log、error.log），便于复盘回溯。
- **`output/`**：仅用于存放最终面向用户的结果报表、分析文件、导出数据或图表。
- 上述三个目录均由全局 `.gitignore` 自动忽略其动态内容，并在模板中保留 `.gitkeep`。

---

## 6. 代码与路径约定

1. **相对路径解析**：
   - 脚本内部涉及文件读写操作时，必须基于脚本所在目录进行相对解析：
     ```python
     from pathlib import Path

     BASE_DIR = Path(__file__).resolve().parent
     CONFIG_FILE = BASE_DIR / "config.json"
     DATA_DIR = BASE_DIR / "data"
     LOGS_DIR = BASE_DIR / "logs"
     OUTPUT_DIR = BASE_DIR / "output"
     ```
2. **编码规范**：
   - Python 代码遵循 PEP 8 规范。
   - 所有 Python 文件开头指定 UTF-8 编码或使用标准 Python 3 语法。
   - 函数和核心流程需附带清晰的注释与类型提示（Type Hints）。

---

## 7. Git 提交规范

建议遵循约定式提交（Conventional Commits）：

- `feat(tools/<category>): add <tool-name>` — 新增工具
- `fix(tools/<tool-name>): fix issue description` — 修复工具 bug
- `docs: update documentation` — 更新说明文档或规范
- `chore: repository maintenance` — 维护与配置调整
