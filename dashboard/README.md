# Personal AI Toolkit · 控制台看板 (Dashboard)

基于 **Vue 3 + Vite + TypeScript + Vanilla CSS Design System** 构建的轻量级现代化个人 AI 能力库可视化看板。

---

## 核心特性

1. **零后端轻量自治**：
   - 采用纯前端 SPA 架构，通过 `scripts/scan-tools.mjs` 自动扫描 `tools/` 目录；
   - 自动提取各工具的 `README.md`、`config.example.json` 及 `output/` 产物状态，生成统一清单，开箱即用。
2. **高定现代视觉体系**：
   - 原生 Vanilla CSS 变量系统，原生毛玻璃质感 (Glassmorphism) 与平滑微动画；
   - 完美支持 **暗黑 (Dark) / 明亮 (Light)** 双模式一键无缝切换。
3. **一体化多维卡片看板**：
   - **领域色彩分类**：游戏娱乐 (Gaming)、金融理财 (Finance)、学习辅助 (Study)、生产力工具 (Productivity)、日常助手 (Life)；
   - **状态感应**：自动显示各个工具的配置就绪度与产物状态；
   - **一键快捷复制**：卡片直接提供终端执行命令一键复制；
   - **即时搜索与过滤**：支持按工具中文名、功能关键词及领域胶囊即时筛选。
4. **沉浸式交互抽屉与实时产物看板**：
   - 内置 Markdown 渲染引擎，直接在看板内查阅各工具的高保真完整使用手册；
   - 集成专属产物预览器（例如直接在网页看板中查看 **Steam 折扣挖掘器** 抓取的最优性价比榜与深度折扣游戏卡片）。

---

## 本地启动与开发

在 `dashboard/` 目录下执行：

```bash
# 1. 安装依赖
npm install

# 2. 启动本地开发服务（会自动先触发 npm run scan 刷新工具列表）
npm run dev

# 3. 仅手动更新工具清单
npm run scan

# 4. 构建生产产物
npm run build
```

---

## 目录结构

```text
dashboard/
├── scripts/
│   └── scan-tools.mjs        # 工具库静态扫描与元数据提取脚本
├── src/
│   ├── components/
│   │   ├── ToolCard.vue          # 工具卡片组件
│   │   ├── ToolDetailModal.vue   # 工具说明与产物沉浸式弹窗
│   │   └── SteamDealsPreview.vue # Steam 折扣榜产物专属预览组件
│   ├── data/
│   │   └── tools-manifest.json   # 扫描生成的工具清单元数据
│   ├── App.vue                   # 主页面与指标统计
│   ├── main.ts                   # 前端应用主入口
│   └── style.css                 # 现代化设计系统与双模 CSS 变量
├── index.html                    # 页面骨架与字体
├── package.json
└── vite.config.ts
```
