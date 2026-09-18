#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Standard Tool Template Entry Point.
"""

import json
import sys
from pathlib import Path

# 统一相对路径基准
BASE_DIR = Path(__file__).resolve().parent
CONFIG_FILE = BASE_DIR / "config.json"
CONFIG_EXAMPLE_FILE = BASE_DIR / "config.example.json"
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"
OUTPUT_DIR = BASE_DIR / "output"


def init_directories():
    """初始化标准数据、日志与输出目录。"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def setup_wizard():
    """首次运行交互式配置向导：检测缺失、询问配置、生成 config.json 并提示重新运行。"""
    print("=" * 60)
    print("[配置向导] 检测到未找到 config.json，正在启动首次配置向导...")
    print("=" * 60)

    template_config = {}
    if CONFIG_EXAMPLE_FILE.exists():
        try:
            with open(CONFIG_EXAMPLE_FILE, "r", encoding="utf-8") as f:
                template_config = json.load(f)
        except Exception as e:
            print(f"[WARN] 读取 config.example.json 失败: {e}")

    if not template_config:
        template_config = {"api_key": "", "user_id": ""}

    user_config = {}
    print("请根据提示输入对应配置项（直接回车使用默认值）：")
    for key, default_val in template_config.items():
        prompt = f"- 请输入 {key}"
        if default_val:
            prompt += f" [默认: {default_val}]"
        prompt += ": "

        try:
            val = input(prompt).strip()
            user_config[key] = val if val else default_val
        except (KeyboardInterrupt, EOFError):
            print("\n[INFO] 已取消配置向导。")
            sys.exit(1)

    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(user_config, f, ensure_ascii=False, indent=2)
        print("=" * 60)
        print(f"[SUCCESS] 配置文件已成功生成: {CONFIG_FILE.name}")
        print("首次配置已完成，请重新运行本程序以启动工具：")
        print("  python main.py")
        print("=" * 60)
    except Exception as e:
        print(f"[ERROR] 写入 config.json 失败: {e}")
        sys.exit(1)

    # 首次运行完成向导后提示重新运行并退出
    sys.exit(0)


def load_config():
    """读取 config.json，若不存在则触发首次配置向导。"""
    if not CONFIG_FILE.exists():
        setup_wizard()

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[ERROR] 读取 config.json 失败: {e}")
        sys.exit(1)


def main():
    init_directories()
    config = load_config()

    print("Tool template running...")
    # TODO: 在此处编写工具主要业务逻辑，使用 config 字典访问所需配置


if __name__ == "__main__":
    main()
