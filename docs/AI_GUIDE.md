# AI_GUIDE.md — 专为 AI 助手定制的协作与开发指南

> **适用对象**：GPT, Claude, Gemini, OpenClaw, Cursor 以及所有参与本仓库构建与维护的 AI 编程助手。  
> **核心宗旨**：保障 Personal AI Toolkit 的高自治性、高一致性与即插即用体验。

---

## 1. 项目目标

- **定位**：这是一个面向长期维护的**个人 AI 能力库（Personal AI Toolkit）**，而非单一封闭产品。
- **架构哲学**：原子化能力、高扩展性、零全局污染。后续新增任何工具，**绝对无需改动仓库核心架构**。
- **目标场景**：游戏辅助、金融分析、学习助手、效率工具、日常助手等。

---

## 2. 目录规范

仓库根目录层级遵循严格的职责划分：

```text
personal-ai-tools/
├── README.md                # 根索引文档
├── .gitignore               # 忽略环境配置与中间输出
├── dashboard/               # [占位] 前端可视化看板（未开发前切勿修改）
├── tools/                   # 所有工具的实体目录（按领域子目录划分）
│   ├── gaming/              # 游戏娱乐
│   ├── finance/             # 投资理财与资产分析
│   ├── study/               # 学习与研究
│   ├── productivity/        # 效率提升与自动化
│   └── life/                # 生活日常
├── prompts/                 # Prompt 资产库（通用系统角色与指令模板）
├── templates/               # 标准工具模板（tool-template）
└── docs/                    # 规范文档库（AI_GUIDE.md & CONVENTIONS.md）
```

**AI 准则**：
- 新增工具时，必须归入 `tools/<分类>/<工具名称>`，不得直接在 `tools/` 根目录下平铺。
- 工具目录名称必须全部小写，多个单词用中划线连接（kebab-case），如 `steam-discount-hunter`。

---

## 3. 工具规范 (Tool Specification)

每一个工具都是一个**完全独立自治的微型工程**。每个工具目录内部必须严格包含以下 7 个核心要素（缺一不可）：

```text
tools/<category>/<tool-name>/
├── README.md           # 工具说明文档（严格遵循指定 7 个二级标题）
├── requirements.txt    # 工具独立依赖列表（即使为空也必须存在）
├── config.example.json # 配置文件参考模板（提交至 Git）
├── main.py             # 工具主入口文件（必须集成首次运行向导）
├── data/               # 存放缓存数据（包含 .gitkeep）
├── logs/               # 存放运行日志（包含 .gitkeep）
└── output/             # 存放输出结果文件（包含 .gitkeep）
```

---

## 4. README 规范

工具目录下的 `README.md` 是人类与 AI 快速了解其功能的唯一真相源（Single Source of Truth）。必须严格包含以下 7 个二级标题结构：

```markdown
# 工具名称

## 功能
- 核心能力与特性点

## 输入
- 参数输入说明（CLI 参数、输入文件等）

## 输出
- 输出产物说明（data/ 缓存、logs/ 日志、output/ 结果）

## 环境配置
- 说明 config.json 配置项、默认值与首次交互向导机制（严禁要求配置系统环境变量）

## 安装依赖
- pip install -r requirements.txt

## 运行方式
- python main.py

## 示例
- 提供具体的运行指令与预期输出日志
```

---

## 5. 配置规范 (Configuration Specification)

1. **统一使用 `config.json`**：
   - 工具所有的配置项必须优先且统一通过本地 `config.json` 管理。
   - **严禁要求用户配置系统环境变量**。
2. **Git 版本控制规则**：
   - 提交：`config.example.json`（提供空值或默认值样例）。
   - 忽略：`config.json`（真实配置严禁提交至代码仓库）。
3. **首次运行规则（必须严格遵守）**：
   若 `config.json` 不存在，`main.py` 必须实现以下闭环流程：
   1. **自动检测**：启动时检测目标目录下是否存在 `config.json`；
   2. **创建向导**：不存在时自动开启终端交互式配置向导；
   3. **询问用户**：依据 `config.example.json` 逐项询问用户所需配置；
   4. **自动生成**：将用户输入写入格式化的 `config.json`；
   5. **提示重启**：输出清晰提示告知用户配置文件已生成，指引重新运行 `python main.py` 并退出进程。

---

## 6. 执行规范

1. **相对路径优先（强制）**：
   - 严禁硬编码绝对路径（如 `C:\Users\...` 或 `/home/...`）。
   - 代码内解析路径推荐使用 `pathlib.Path(__file__).resolve().parent` 作为当前工具的基准路径。
2. **独立虚拟环境兼容**：
   - 依赖项必须全部记录在当前工具的 `requirements.txt` 中。
   - 工具之间不得相互跨目录 import 代码，保持解耦。
3. **跨平台兼容**：
   - 代码与路径处理必须兼容 Windows, macOS 与 Linux。

---

## 7. 目录职责规范 (Data / Logs / Output)

各工具目录下的子目录具有明确且单一的职责边界：

1. **`data/`（存缓存数据）**：
   - 存放持久化缓存、本地数据库文件（如 SQLite）、离线抓取的数据包等中间缓存。
2. **`logs/`（存运行日志）**：
   - 存放运行过程中的滚动日志文件（如 `app.log`），便于调试与回溯。
3. **`output/`（存输出结果）**：
   - 仅存放面向用户的最终产出物，如生成的 Markdown 研报、CSV 报表、导出的图片或汇总 JSON。
4. **Git 忽略控制**：
   - `data/*`, `logs/*`, `output/*` 内的动态生成内容已被根目录 `.gitignore` 自动忽略，通过 `.gitkeep` 保留骨架。

---

## 8. AI 协作检查清单 (AI Checklist)

当用户要求 AI 新建或修改工具时，AI 必须自检以下各项：

- [ ] 是否已从 `templates/tool-template` 派生？
- [ ] 目录名是否符合小写 kebab-case 规范，且归入正确分类？
- [ ] 是否完整包含 7 要素：`README.md`, `requirements.txt`, `config.example.json`, `main.py`, `data/`, `logs/`, `output/`？
- [ ] 是否严格采用 `config.json` 管理配置，且**未要求用户配置系统环境变量**？
- [ ] `main.py` 是否实现了首次运行自动检测缺失、启动向导、生成 `config.json` 并提示重新运行？
- [ ] `README.md` 是否包含了标准的 7 个二级标题？
- [ ] 数据、日志与输出是否分别存入 `data/`, `logs/`, `output/`？
- [ ] 代码中的文件路径读写是否全部基于相对路径？
- [ ] 运行完毕后，是否已执行 `git diff` / `git status` 自检确认变更无误？
