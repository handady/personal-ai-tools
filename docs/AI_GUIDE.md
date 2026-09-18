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

每一个工具都是一个**完全独立自治的微型工程**。每个工具目录内部必须严格包含以下结构（缺一不可）：

```text
tools/<category>/<tool-name>/
├── README.md        # 工具说明文档（严格遵循指定 7 个二级标题）
├── requirements.txt # 工具独立依赖列表（即使为空也必须存在）
├── .env.example     # 环境变量配置模板
├── main.py          # 工具主入口文件
└── output/          # 该工具专属输出与产物目录（包含 .gitkeep）
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
- 输出产物说明（保存在 output/ 目录中的文件）

## 环境配置
- 说明依赖的 .env 变量及其用途

## 安装依赖
- pip install -r requirements.txt

## 运行方式
- python main.py

## 示例
- 提供具体的运行指令与预期输出日志
```

---

## 5. 环境变量规范

1. **零密钥提交**：严禁在代码、注释或 Git 历史中硬编码任何真实 API 密钥或敏感凭据。
2. **模板对应**：所有通过 `os.getenv()` 或 `python-dotenv` 读取的环境变量，必须在 `.env.example` 中列出空值或占位符示例。
3. **防御性校验**：在 `main.py` 启动时，如关键环境变量缺失，应抛出易读的错误提示，指引用户配置 `.env`。

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

## 7. 输出规范

1. **产物隔离**：
   - 工具运行产生的数据缓存、JSON 报表、下载文件或 Markdown 摘要必须统一保存在工具自身的 `output/` 目录下。
   - 禁止向项目根目录或其他工具的目录中乱写临时文件。
2. **忽略控制**：
   - `output/` 下的动态生成内容已被全局 `.gitignore` 忽略，确保 Git 仓库洁净。
3. **控制台输出规范**：
   - 打印清晰的状态日志（推荐带上 `[INFO]`, `[WARN]`, `[ERROR]` 前缀），便于自动化脚本与用户观察执行进度。

---

## 8. AI 协作检查清单 (AI Checklist)

当用户要求 AI 新建或修改工具时，AI 必须自检以下各项：

- [ ] 是否已从 `templates/tool-template` 派生？
- [ ] 目录名是否符合小写 kebab-case 规范，且归入正确分类？
- [ ] 是否完整保留了 `README.md`, `requirements.txt`, `.env.example`, `main.py`, `output/`？
- [ ] `README.md` 是否包含了标准的 7 个二级标题？
- [ ] 代码中的文件路径读写是否全部基于相对路径？
- [ ] 是否有任何敏感密钥泄漏风险？
- [ ] 运行完毕后，是否已执行 `git diff` / `git status` 自检确认变更无误？
