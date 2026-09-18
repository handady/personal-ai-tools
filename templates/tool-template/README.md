# 工具名称

简要描述本工具的核心定位与设计目标（例如：一句话概述本工具解决什么痛点）。

---

## 功能

- [功能点 1]：描述主要功能特性与自动化能力
- [功能点 2]：描述扩展功能或辅助特性
- [功能点 3]：描述数据处理或通知机制

---

## 输入

- **命令行参数**：说明是否支持 CLI 传参（例如 `--limit 10`, `--query keyword`）
- **配置文件**：说明依赖的配置文件或参数项
- **外部数据源**：说明读取的文件（如 `input.json`）或调用的外部 API 数据源

---

## 输出

- **控制台输出**：关键执行步骤日志、摘要信息
- **缓存数据**：运行时产生的本地缓存数据存放在 `data/` 目录
- **运行日志**：详细操作记录与调试日志存放在 `logs/` 目录
- **产物结果**：最终导出的报表、分析文件保存在 `output/` 目录（例如 `output/report.json`, `output/summary.md`）

---

## 环境配置

本工具优先使用 `config.json` 进行配置（**严禁要求用户配置系统环境变量**）。

### 首次运行配置向导

若当前目录下不存在 `config.json`，直接运行入口脚本：

```bash
python main.py
```

程序会自动启动**交互式配置向导**，引导填写所需配置并自动生成 `config.json`，随后按提示重新运行即可。

也可手动复制参考配置模板后填写：

```bash
cp config.example.json config.json
```

配置项说明：

| 配置键名 | 是否必填 | 默认值 | 说明 |
| :--- | :--- | :--- | :--- |
| `api_key` | 是 | `""` | 第三方平台 API 访问密钥 |
| `user_id` | 否 | `""` | 目标用户标识或系统 ID |

> ⚠️ 注意：`config.json` 已被 Git 忽略，切勿将包含真实密钥的文件提交至仓库。

---

## 安装依赖

建议在工具目录下或全局虚拟环境中安装依赖包：

```bash
pip install -r requirements.txt
```

---

## 运行方式

在工具根目录下通过相对路径执行入口脚本：

```bash
python main.py
```

或从项目根目录执行：

```bash
python tools/<分类>/<工具名称>/main.py
```

---

## 示例

### 运行指令

```bash
python main.py
```

### 预期输出

```text
Tool template running...
[INFO] Task completed successfully. Results saved to output/result.json.
```
