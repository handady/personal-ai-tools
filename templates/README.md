# Templates (工具脚手架模板)

本目录包含新增工具时所用的标准模版。

---

## 目录说明

- `tool-template/`：标准的独立 Python 工具模板工程。所有新工具均基于此模板进行复制与扩展。

---

## 使用模板新建工具指南

只需通过终端执行复制命令即可完成新工具的脚手架初始化：

### Windows PowerShell

```powershell
# 复制模板到目标分类下（以 gaming/steam-discount-hunter 为例）
Copy-Item -Recurse -Path "templates/tool-template" -Destination "tools/gaming/steam-discount-hunter"
```

### Bash / Zsh (Linux / macOS / Git Bash)

```bash
# 复制模板到目标分类下
cp -r templates/tool-template tools/gaming/steam-discount-hunter
```

复制完成后：
1. 编辑目标目录下的 `README.md`，补全工具名称、功能、输入输出及配置。
2. 依据需求调整 `config.example.json` 中的字段项（首次运行 `python main.py` 会自动启动配置向导生成 `config.json`）。
3. 在 `requirements.txt` 中添加依赖包。
4. 编写 `main.py` 完成工具开发。
