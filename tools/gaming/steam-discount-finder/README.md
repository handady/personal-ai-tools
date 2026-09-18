# Steam 每日高性价比折扣挖掘器 (Steam Discount Finder)

一个基于量化性价比算法的自动化 Steam 折扣游戏挖掘工具。解决传统打折列表「只看折扣百分比不看质量」、「只看绝对低价不看内容时长」的痛点，帮助玩家用最少的预算买到最值得玩的优质游戏。

---

## 功能介绍

1. **量化性价比模型 ($V = Q^2 \times H \div P$)**：
   - **$Q$ (综合质量分)**：$0.75 \times \text{贝叶斯平滑好评率} + 0.25 \times (\text{Metacritic} \div 100)$。惩罚小样本刷分游戏，重视真实口碑。
   - **$H$ (中位游玩小时数)**：依据游戏类型基准（开放世界/模拟/策略/RPG等）+ 成就数量加成 + 原价档位系数综合估算内容体量。
   - **$P$ (折后价格)**：抓取 Steam 国区实时人民币现价。
   - 核心指标 $V$ 代表**每 1 元人民币能买到的优质游戏时间**。
2. **全免费数据链路**：无需购买第三方数据接口，直连 Steam 官方搜索与详情 API。
3. **已拥有游戏自适应排除**：
   - 支持 Steam Web API 自动同步个人游戏库或本地手动清单过滤；
   - 采用**自适应动态扩扫**算法，即便库内游戏极多，也会自动扩大扫描深度补足候选池，绝不让榜单清空。
4. **本地历史低价沉淀**：
   - 逐日累积记录历史价格，自动判定并标记「🔥观测新低」、「🆕首次记录」、「⬇降价」等标签。
5. **多端多格式报表输出**：
   - 自动生成交互式 HTML（支持即时关键词搜索与按列点击动态排序）；
   - 生成精美 GitHub 风格 Markdown 研报；
   - 生成面向 AI Agent 与下游流程的结构化 JSON 数据集。

---

## 输入内容

- **配置文件**：当前目录下的 `config.json`（Steam API Key 与 SteamID）。
- **命令行参数**（可选覆盖）：
  - `--max-price 60`：折后价上限（元，默认 200.0）
  - `--min-discount 70`：最低折扣百分比（默认 35）
  - `--top-n 30`：榜单显示数量（默认 20）
  - `--pages-per-sort 10`：初始扫描深度（默认 6）
  - `--sync-owned`：强制重新调用 Steam API 刷新个人游戏库
- **手动清单**（可选）：`data/owned.txt`，支持按行配置 AppID 或游戏名称，用于不使用 API 时的兜底排除。

---

## 输出内容

- **终端标准输出**：运行进度阶段日志（`[1/6]` ~ `[6/6]`）及 Markdown 格式的精选简报。
- **本地日志**：写入 `logs/run.log`，包含详细时间戳、网络重试与系统事件。
- **持久化缓存**：
  - `data/history.json`：历史价格沉淀记录；
  - `data/appinfo_cache.json`：游戏分类、评分与成就缓存；
  - `data/owned.json`：个人游戏库同步缓存（默认 7 天刷新）。
- **最终产物文件**（全部保存在 `output/` 目录）：
  - `output/deals-YYYY-MM-DD.html`：当日完整交互式前端报表；
  - `output/latest.html`：最新一份 HTML 报表；
  - `output/deals-YYYY-MM-DD.md`：当日 Markdown 完整分析报告；
  - `output/deals-latest.json`：全量结构化排序游戏数据（供 AI Agent 消费）。

---

## 配置方法

本项目优先且唯一读取当前目录下的 `config.json`（**严禁使用或要求系统环境变量**）。

参考模板 `config.example.json`：

```json
{
  "_comment": "Steam Web API 配置",
  "steam_api_key": "",
  "steam_id": "",
  "vanity": "",
  "owned_extra": []
}
```

配置项说明：

| 配置键名 | 是否必填 | 默认值 | 获取与说明 |
| :--- | :--- | :--- | :--- |
| `steam_api_key` | 否 | `""` | 在 [Steam API Key 申请页](https://steamcommunity.com/dev/apikey) 登录获取（域名可任意填写如 localhost） |
| `steam_id` | 否 | `""` | 17 位 SteamID64（可在个人主页 URL 或 SteamDB 查到） |
| `vanity` | 否 | `""` | 若不知道 17 位数字，可在此填写个人主页个性化后缀昵称，程序会自动解析转换 |
| `owned_extra` | 否 | `[]` | 额外需要强制排除的游戏 AppID 数组 |

> 💡 提示：若不配置 API Key，程序将自动回退为仅读取 `data/owned.txt` 手动清单，核心折扣挖掘功能不受任何影响。

---

## 安装依赖

本项目完全基于 Python 3.8+ 标准库开发，无需安装任何外部第三方依赖：

```bash
pip install -r requirements.txt
```

---

## 首次运行

当首次克隆或在新环境下运行时，如果尚未存在 `config.json`：

直接启动入口程序：

```bash
python main.py
```

1. 程序会自动检测到 `config.json` 缺失；
2. 自动启动控制台**交互式配置向导**；
3. 提示输入 `Steam Web API Key`、`SteamID` 或个性化昵称（如无需 API 可直接连续回车跳过）；
4. 自动生成标准 `config.json` 并安全保存在本地（已被 Git 自动忽略）；
5. 提示用户配置完成，随后重新执行 `python main.py` 即可正常工作。

---

## 使用方式

在工具目录下执行：

```bash
# 1. 默认参数运行
python main.py

# 2. 覆盖参数运行（只看 60 元以内、7 折以上的高性价比游戏）
python main.py --max-price 60 --min-discount 70

# 3. 强制刷新 Steam 个人库存缓存
python main.py --sync-owned
```

也可从项目根目录下执行：

```bash
python tools/gaming/steam-discount-finder/main.py
```

---

## 输出位置

所有生成物均保存在本工具的 `output/` 目录下：

```text
tools/gaming/steam-discount-finder/output/
├── deals-2026-09-18.html  # 完整交互报表
├── deals-2026-09-18.md    # Markdown 研报
├── latest.html            # 最新报表链接
└── deals-latest.json      # 结构化数据导出
```

---

## 示例

### 运行输出

```text
============================================================
🎮 启动 Steam 高性价比折扣挖掘任务...
============================================================
[1/6] 加载你的游戏库...
      已登记游戏 412 款（来源：Steam Web API）
[2/6] 抓取在售折扣并排除已拥有...
      第 1 轮扫描 1200 个折扣位 → 符合质量门槛 92 款（排除已拥有 31 款）
      最终可用 92 款（排除 31 款已拥有），精算前 92 款
[3/6] 抓取 Steam 游戏详情（类型/媒体分/成就）...
[4/6] 计算综合性价比 Q, H, V...
      完成精算评分，进榜候选 63 款
[5/6] 更新本地历史价格数据...
[6/6] 生成 Markdown, HTML 与 JSON 输出产物...
[SUCCESS] 任务执行完毕！产物已输出至：
  - Markdown: deals-2026-09-18.md
  - HTML:     deals-2026-09-18.html / latest.html
  - JSON:     deals-latest.json
```

### 实际精选榜单切片 (Markdown 样例)

| # | 游戏 | 原价→现价 | 折扣 | 好评 | 时长 | ¥/小时 | 性价比 | 历史 |
|---|---|---|---|---|---|---|---|---|
| 1 | [Terraria](https://store.steampowered.com/app/105600/?cc=cn) | ¥42→¥21 | -50% | 97% (1124890) | 60.0h | ¥0.35 | **2.682** | 🔥新低 |
| 2 | [Hollow Knight](https://store.steampowered.com/app/367520/?cc=cn) | ¥58→¥29 | -50% | 97% (321450) | 35.0h | ¥0.83 | **1.141** | ⬇降价 |
| 3 | [Portal 2](https://store.steampowered.com/app/620/?cc=cn) | ¥42→¥4 | -90% | 98% (385120) | 12.0h | ¥0.33 | **2.825** | — |
