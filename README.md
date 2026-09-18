# Personal AI Toolkit (个人 AI 工具库)

> 这是一个长期维护的个人 AI 工具库与能力库，旨在聚合各类独立自治的自动化脚本、AI 增强工具与效率插件。

---

## 1. 项目介绍

**Personal AI Toolkit** 是一个面向未来的**个人 AI 能力库**，而非单一的封闭产品。

随着日常工作与生活对 AI 辅助需求的不断增长，我们常常需要针对不同场景开发轻量、高效的独立工具（例如 Steam 折扣猎人、AI 新闻助手、股票分析器、学习笔记助手、Notion 辅助插件、GitHub 工作流增强等）。

### 核心设计原则

- **个人能力库属性**：每个工具都是一个原子化的能力单元，彼此解耦、独立演进。
- **高扩展性**：采用插拔式架构，新增工具只需套用模板，无需改动全局架构或其它工具代码。
- **AI 友好（AI-Native）**：提供规范化的文档格式与上下文结构，使得人类开发者与各类 AI Coding 助手（GPT、Claude、Gemini、OpenClaw、Cursor 等）都能在秒级完成上下文理解与协作开发。
- **统一结构规范**：每个工具自包含（Self-contained），自带依赖定义、环境配置样例、入口脚本以及专属输出空间。
- **零全局污染**：工具间环境相互隔离，杜绝跨工具隐式依赖。

---

## 2. 目录结构说明

```text
personal-ai-tools/
├── README.md                # 项目主说明文档与总索引
├── .gitignore               # 统一 Git 忽略配置（包含环境、密钥与输出产物过滤）
├── dashboard/               # [未来规划] 基于 Vue 3 的统一可视化管理看板
│   ├── README.md
│   └── placeholder.md
├── tools/                   # 核心工具集目录（按应用领域分类）
│   ├── gaming/              # 游戏娱乐相关工具（如 Steam 折扣监控、游戏数据分析）
│   ├── finance/             # 金融理财工具（如 股票分析、资产看板、财报提取）
│   ├── study/               # 学习助手（如 论文速读、记忆卡片生成、背单词助手）
│   ├── productivity/        # 生产力提升（如 Notion 联动、GitHub 批处理、文档转换）
│   ├── life/                # 日常生活助手（如 天气提醒、健康管理、信息汇总）
│   └── README.md
├── prompts/                 # 优质提示词与系统 Prompt 库
│   ├── README.md
│   └── examples/            # 常用场景 Prompt 示例与模板
├── templates/               # 工具脚手架模板
│   ├── tool-template/       # 标准 Python 工具模板
│   │   ├── README.md        # 工具说明模板
│   │   ├── config.example.json # 配置文件模板
│   │   ├── requirements.txt # 依赖列表
│   │   ├── main.py          # 入口执行文件与首次配置向导
│   │   ├── data/            # 缓存数据存储目录
│   │   ├── logs/            # 运行日志存储目录
│   │   └── output/          # 输出结果产物目录
│   └── README.md
└── docs/                    # 仓库规范与系统开发指南
    ├── AI_GUIDE.md          # 专为各类 AI 编程助手编写的协作规范
    └── CONVENTIONS.md       # 全仓库编码与工程化统一约定
```

---

## 3. 已收录工具矩阵 (Tool Catalog)

| 领域分类 | 工具名称 | 目录路径 | 状态 | 核心功能简介 |
| :--- | :--- | :--- | :--- | :--- |
| 🎮 游戏娱乐 | **Steam 折扣挖掘器** | [steam-discount-finder](file:///tools/gaming/steam-discount-finder) | 🟢 生产可用 | 基于 $V=Q^2 \times H/P$ 模型量化性价比，自动同步/排除已拥有游戏并生成多维折扣日报 |

---

## 4. 新增工具流程

新增一个工具非常简单，只需以下步骤：

1. **复制模板**：复制 `templates/tool-template` 目录到 `tools/<分类>/<工具名称>`，例如 `tools/gaming/steam-discount-hunter`。
2. **修改说明**：按照统一规范修改该工具目录下的 `README.md`，写明功能、输入输出及配置说明。
3. **调整配置模板**：在 `config.example.json` 中定义该工具所需的配置字段（首次运行会自动触发交互式配置向导生成 `config.json`，**禁止要求用户配置系统环境变量**）。
4. **编写逻辑**：在 `main.py` 中实现核心业务逻辑（缓存写至 `data/`，日志写至 `logs/`，导出结果写至 `output/`）。
5. **补充依赖**：在 `requirements.txt` 中登记本工具所需的第三方依赖库。
6. **提交代码**：自测通过后，将新工具代码与 `config.example.json` 提交到 Git（`config.json` 已被自动忽略）。

> 💡 规范约定详见 [docs/CONVENTIONS.md](file:///docs/CONVENTIONS.md)。

---

## 5. AI 助手使用说明

# For AI Assistants

如果你是参与本项目开发的 AI 助手（包括但不限于 GPT, Claude, Gemini, OpenClaw, Cursor 等），请严格遵循以下执行准则：

1. **阅读本 README**：理解项目愿景、模块化设计原则及通用流程。
2. **浏览 tools 目录**：确定要新建或修改的工具归属的分类领域（`gaming`, `finance`, `study`, `productivity`, `life`）。
3. **阅读对应工具 README**：在执行、测试或扩展任何工具之前，先阅读目标工具目录下的 `README.md` 了解其上下文。
4. **配置规范（强制）**：
   - 优先且必须使用 `config.json`，**禁止要求用户配置系统环境变量**。
   - 检查 `config.example.json` 获知所需字段。
   - 若 `config.json` 不存在，必须具备首次运行自动检测、启动配置向导询问并生成 `config.json`，随后提示重新运行的机制。
5. **目录职责规范**：
   - `data/`：仅用于存放缓存数据。
   - `logs/`：仅用于存放运行日志。
   - `output/`：仅用于存放输出结果文件。
6. **安装 requirements.txt**：明确运行该工具所需的最小依赖集。
7. **执行 main.py**：每个工具的统一执行入口均为 `main.py`。
8. **路径规范（关键）**：
   - **严禁依赖绝对路径**。
   - 所有文件读写、模块导入、脚本调用均必须采用**相对路径**（以工具所在目录或项目根目录为基准）。
   - 保证代码在不同开发者机器与不同操作系统环境（Windows / macOS / Linux）下即开即用。

详细的 AI 交互规则与工程准则请参见 [docs/AI_GUIDE.md](file:///docs/AI_GUIDE.md)。
