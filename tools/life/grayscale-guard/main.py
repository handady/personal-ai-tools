#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
灰度守护 (Grayscale Guard) - 防熬夜屏幕作息守卫
Personal AI Toolkit - Life (日常生活) 领域自动化工具

功能概述：
  1. 到点自动变灰、到点自动恢复彩色，掐断深夜打游戏与刷视频的心流冲动；
  2. 依赖 Windows 自带颜色滤镜 (Win+Ctrl+C) 与计划任务，零常驻进程、零外部依赖；
  3. 提供 Python 统一管理入口、首次运行配置向导与实时状态产物生成；
  4. 支持 CLI 命令行自动化与终端交互式菜单双模操作。
"""

import argparse
import datetime
import json
import os
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Optional

# ==================== 1. 路径与常量定义 ====================
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"
OUTPUT_DIR = BASE_DIR / "output"
SCRIPTS_DIR = BASE_DIR / "scripts"

CONFIG_FILE = BASE_DIR / "config.json"
CONFIG_EXAMPLE_FILE = BASE_DIR / "config.example.json"
PAUSE_FLAG = BASE_DIR / ".paused"

GUARD_PS1 = SCRIPTS_DIR / "guard.ps1"
INSTALL_PS1 = SCRIPTS_DIR / "install.ps1"
UNINSTALL_PS1 = SCRIPTS_DIR / "uninstall.ps1"

STATUS_JSON = OUTPUT_DIR / "guard-status.json"
STATUS_MD = OUTPUT_DIR / "status.md"

# 兼容 Windows 终端控制台编码
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


# ==================== 2. 基础环境与目录初始化 ====================
def init_directories():
    """初始化标准数据、日志与输出目录。"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def check_platform_support() -> bool:
    """检查操作系统是否为 Windows。"""
    if platform.system() != "Windows":
        print("[警告] 灰度守护基于 Windows 系统的颜色滤镜与计划任务开发。")
        print(f"当前系统为 {platform.system()}，部分原生功能将受限。")
        return False
    return True


# ==================== 3. 首次配置向导 ====================
def setup_wizard():
    """首次运行交互式配置向导：检测缺失、询问配置、生成 config.json 并提示重新运行。"""
    print("=" * 65)
    print("【灰度守护 · 首次配置向导】")
    print("未检测到 config.json，让我们用 10 秒时间完成基础作息配置：")
    print("=" * 65)

    default_config = {
        "nightStart": "23:00",
        "morningEnd": "07:30",
        "recheckMinutes": 10,
        "enabled": True,
    }

    if CONFIG_EXAMPLE_FILE.exists():
        try:
            with open(CONFIG_EXAMPLE_FILE, "r", encoding="utf-8-sig") as f:
                loaded = json.load(f)
                for k, v in loaded.items():
                    if not k.startswith("_"):
                        default_config[k] = v
        except Exception as e:
            print(f"[提示] 读取配置模板警告: {e}")

    user_config: Dict[str, Any] = {}

    try:
        print("\n1. 夜间屏幕变灰时间点 (24小时制 HH:MM)")
        start_input = input(f"   请输入夜间开始时间 [默认: {default_config['nightStart']}]: ").strip()
        user_config["nightStart"] = start_input if start_input else default_config["nightStart"]

        print("\n2. 早晨屏幕恢复彩色时间点 (24小时制 HH:MM)")
        end_input = input(f"   请输入早晨结束时间 [默认: {default_config['morningEnd']}]: ").strip()
        user_config["morningEnd"] = end_input if end_input else default_config["morningEnd"]

        print("\n3. 定时对表复查频率 (分钟，0为仅边界/解锁时检查)")
        recheck_input = input(f"   请输入检查间隔 [默认: {default_config['recheckMinutes']}]: ").strip()
        if recheck_input:
            try:
                user_config["recheckMinutes"] = int(recheck_input)
            except ValueError:
                user_config["recheckMinutes"] = default_config["recheckMinutes"]
        else:
            user_config["recheckMinutes"] = default_config["recheckMinutes"]

        user_config["enabled"] = True

        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(user_config, f, ensure_ascii=False, indent=2)

        print("\n" + "=" * 65)
        print(f"✓ 配置文件已生成: {CONFIG_FILE.name}")
        print("  夜间灰度时段: " + f"{user_config['nightStart']} ~ {user_config['morningEnd']}")
        print("  复查检查频率: 每 " + f"{user_config['recheckMinutes']} 分钟")
        print("\n首次配置已完成！请重新运行本程序以启动或安装灰度守护：")
        print("  python main.py")
        print("=" * 65)
    except (KeyboardInterrupt, EOFError):
        print("\n[INFO] 已取消配置向导。")
        sys.exit(1)

    sys.exit(0)


def load_config() -> Dict[str, Any]:
    """读取 config.json，若缺失则自动触发配置向导。"""
    if not CONFIG_FILE.exists():
        setup_wizard()

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8-sig") as f:
            return json.load(f)
    except Exception as e:
        print(f"[错误] 读取配置文件失败: {e}")
        sys.exit(1)


# ==================== 4. PowerShell 子进程执行引擎 ====================
def run_powershell(script_path: Path, action_arg: Optional[str] = None, wait: bool = True):
    """以 Bypass 执行策略运行 PowerShell 脚本，实时流式输出，杜绝弹窗闪现。"""
    cmd = [
        "powershell.exe",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        f"$OutputEncoding = [Console]::OutputEncoding = [System.Text.Encoding]::UTF8; & '{script_path}'" + (f" -Action '{action_arg}'" if action_arg else ""),
    ]

    startupinfo = None
    if platform.system() == "Windows":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = 0  # SW_HIDE (避免弹出系统黑框)

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
        startupinfo=startupinfo,
    )

    if proc.stdout:
        for line in proc.stdout:
            sys.stdout.write(line)
            sys.stdout.flush()

    proc.wait()
    return proc


def run_powershell_capture(script_path: Path, action_arg: Optional[str] = None) -> str:
    """运行 PowerShell 脚本并捕获标准输出内容。"""
    cmd = [
        "powershell.exe",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(script_path),
    ]
    if action_arg:
        cmd.extend(["-Action", action_arg])

    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=False, encoding="utf-8", errors="replace")
        return res.stdout or ""
    except Exception as e:
        return f"[执行异常] {e}"


# ==================== 5. 核心动作逻辑 ====================
def get_system_diagnostic() -> Dict[str, Any]:
    """收集 Windows 注册表颜色滤镜状态与计划任务健康信息。"""
    cfg = load_config()
    is_paused = PAUSE_FLAG.exists()

    diag: Dict[str, Any] = {
        "tool": "GrayscaleGuard",
        "nightStart": cfg.get("nightStart", "23:00"),
        "morningEnd": cfg.get("morningEnd", "07:30"),
        "recheckMinutes": cfg.get("recheckMinutes", 10),
        "enabled": cfg.get("enabled", True),
        "isPaused": is_paused,
        "currentColorState": "未知",
        "colorStateCode": -1,
        "hotkeyEnabled": False,
        "taskInstalled": False,
        "taskState": "NotInstalled",
        "lastRunTime": "-",
        "nextRunTime": "-",
        "updatedAt": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    if platform.system() != "Windows":
        return diag

    # 通过 PowerShell 一次性安全拉取注册表与任务计划数据
    query_cmd = """
    $reg = Get-ItemProperty -Path 'HKCU:\\SOFTWARE\\Microsoft\\ColorFiltering' -ErrorAction SilentlyContinue
    $task = Get-ScheduledTask -TaskName 'GrayscaleGuard' -ErrorAction SilentlyContinue
    $taskInfo = if ($task) { Get-ScheduledTaskInfo -TaskName 'GrayscaleGuard' -ErrorAction SilentlyContinue } else { $null }

    [PSCustomObject]@{
        Active = if ($reg -and $null -ne $reg.Active) { [int]$reg.Active } else { -1 }
        HotkeyEnabled = if ($reg -and $null -ne $reg.HotkeyEnabled) { [int]$reg.HotkeyEnabled } else { 0 }
        TaskExists = if ($task) { $true } else { $false }
        TaskState = if ($task) { [string]$task.State } else { 'NotInstalled' }
        LastRunTime = if ($taskInfo -and $taskInfo.LastRunTime) { $taskInfo.LastRunTime.ToString('yyyy-MM-dd HH:mm:ss') } else { '-' }
        NextRunTime = if ($taskInfo -and $taskInfo.NextRunTime) { $taskInfo.NextRunTime.ToString('yyyy-MM-dd HH:mm:ss') } else { '-' }
    } | ConvertTo-Json -Compress
    """
    try:
        res = subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command", query_cmd],
            capture_output=True,
            text=True,
            check=False,
            encoding="utf-8",
            errors="replace",
        )
        if res.stdout.strip():
            info = json.loads(res.stdout.strip())
            diag["colorStateCode"] = info.get("Active", -1)
            diag["currentColorState"] = "灰度 (已开启)" if info.get("Active") == 1 else "彩色 (已关闭)"
            diag["hotkeyEnabled"] = bool(info.get("HotkeyEnabled") == 1)
            diag["taskInstalled"] = bool(info.get("TaskExists"))
            diag["taskState"] = info.get("TaskState", "NotInstalled")
            diag["lastRunTime"] = info.get("LastRunTime", "-")
            diag["nextRunTime"] = info.get("NextRunTime", "-")
    except Exception:
        pass

    return diag


def export_status_artifact(diag: Dict[str, Any]):
    """导出结构化状态至 output/guard-status.json 与 output/status.md 供看板预览。"""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    try:
        with open(STATUS_JSON, "w", encoding="utf-8") as f:
            json.dump(diag, f, ensure_ascii=False, indent=2)

        md_content = f"""# 灰度守护 (Grayscale Guard) 运行状态简报

> 更新时间：`{diag['updatedAt']}`

### 核心指标概览
- **当前屏幕色彩**：`{diag['currentColorState']}`
- **夜间变灰时段**：`{diag['nightStart']} ~ {diag['morningEnd']}`
- **对表复查频率**：每 `{diag['recheckMinutes']}` 分钟一次
- **守护开关状态**：`{'已启用' if diag['enabled'] else '已禁用'}`
- **临时停用标记**：`{'已暂停 (.paused)' if diag['isPaused'] else '正常守护中'}`

### 系统级基础设施健康度
- **Windows 颜色滤镜快捷键**：`{'已就绪 (开启)' if diag['hotkeyEnabled'] else '未开启'}`
- **计划任务注册状态**：`{'已注册' if diag['taskInstalled'] else '未注册'}` (`{diag['taskState']}`)
- **计划任务上次触发**：`{diag['lastRunTime']}`
- **计划任务下次计划**：`{diag['nextRunTime']}`

---
*由 Personal AI Toolkit · 灰度守护自动维护*
"""
        with open(STATUS_MD, "w", encoding="utf-8") as f:
            f.write(md_content)
    except Exception as e:
        print(f"[提示] 保存状态产物失败: {e}")


def action_status():
    """查看完整诊断状态报告。"""
    print("\n" + "=" * 65)
    print("【灰度守护 · 系统体检与运行状态】")
    print("=" * 65)
    diag = get_system_diagnostic()
    export_status_artifact(diag)

    print(f"■ 作息时间配置 : {diag['nightStart']} ~ {diag['morningEnd']} (每 {diag['recheckMinutes']} 分钟对表)")
    print(f"■ 守护总开关   : {'启用中' if diag['enabled'] else '已关闭'}")
    print(f"■ 临时停用状态 : {'【已临时暂停】(屏幕保持彩色)' if diag['isPaused'] else '正常生效中'}")
    print(f"■ 当前屏幕色彩 : {diag['currentColorState']}")
    print(f"■ 颜色滤镜热键 : {'Win+Ctrl+C 已就绪' if diag['hotkeyEnabled'] else '快捷键尚未开启'}")
    print(f"■ 计划任务安装 : {'已就绪 (状态: ' + diag['taskState'] + ')' if diag['taskInstalled'] else '未注册任务 (请运行安装)'}")
    print(f"■ 上次对齐时间 : {diag['lastRunTime']}")
    print(f"■ 下次触发时间 : {diag['nextRunTime']}")
    print("=" * 65)
    print(f"[产物更新] 已同步输出至: {STATUS_JSON.relative_to(BASE_DIR)}")


def action_install():
    """以管理员身份注册计划任务并立即对齐。"""
    print("\n正在启动安装程序，将请求管理员权限以注册任务计划...")
    run_powershell(INSTALL_PS1)
    # 安装完成后刷新产物
    diag = get_system_diagnostic()
    export_status_artifact(diag)


def action_uninstall():
    """彻底卸载计划任务并还原颜色。"""
    print("\n正在启动卸载程序，将请求管理员权限移除计划任务...")
    run_powershell(UNINSTALL_PS1)
    diag = get_system_diagnostic()
    export_status_artifact(diag)


def action_test():
    """快速测试灰度效果（开4秒后关）。"""
    print("\n正在执行 4 秒快速自检（屏幕将变灰 4 秒后自动恢复）...")
    run_powershell(GUARD_PS1, "selftest")
    diag = get_system_diagnostic()
    export_status_artifact(diag)


def action_pause():
    """临时暂停灰度守护。"""
    print("\n正在设置临时停用标记...")
    run_powershell(GUARD_PS1, "pause")
    diag = get_system_diagnostic()
    export_status_artifact(diag)
    print("✓ 守护已临时暂停，屏幕已恢复彩色。")


def action_resume():
    """恢复灰度守护。"""
    print("\n正在移除临时停用标记并按当前时间对齐...")
    run_powershell(GUARD_PS1, "resume")
    diag = get_system_diagnostic()
    export_status_artifact(diag)
    print("✓ 守护已恢复生效。")


def action_reconcile():
    """立即按当前时间对齐一次颜色状态。"""
    print("\n正在按当前作息时间对齐颜色状态...")
    run_powershell(GUARD_PS1, "reconcile")
    diag = get_system_diagnostic()
    export_status_artifact(diag)
    print("✓ 对齐已完成。")


# ==================== 6. 交互式控制台菜单 ====================
def interactive_menu():
    """终端交互式主菜单。"""
    while True:
        diag = get_system_diagnostic()
        export_status_artifact(diag)

        status_tag = "【临时暂停中】" if diag["isPaused"] else ("【灰度】" if diag["colorStateCode"] == 1 else "【彩色】")
        task_tag = "任务已就绪" if diag["taskInstalled"] else "任务未安装"

        print("\n" + "=" * 60)
        print(f"  🌙 灰度守护 控制台 (Grayscale Guard)  {status_tag}")
        print(f"  作息时段: {diag['nightStart']} ~ {diag['morningEnd']} | {task_tag}")
        print("=" * 60)
        print("  1. 检查运行状态 (Status)")
        print("  2. 安装 / 更新计划任务 (Install)")
        print("  3. 立即测试灰度效果 (Test, 4秒后自动恢复)")
        print("  4. 临时停用 (Pause, 屏幕恢复彩色)")
        print("  5. 恢复守护 (Resume)")
        print("  6. 立即按时间对表 (Reconcile)")
        print("  7. 彻底卸载守护 (Uninstall)")
        print("  0. 退出控制台")
        print("=" * 60)

        try:
            choice = input("请选择操作编号 [0-7]: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n已退出。")
            break

        if choice == "1":
            action_status()
        elif choice == "2":
            action_install()
        elif choice == "3":
            action_test()
        elif choice == "4":
            action_pause()
        elif choice == "5":
            action_resume()
        elif choice == "6":
            action_reconcile()
        elif choice == "7":
            action_uninstall()
        elif choice == "0":
            print("再见！祝你今晚按时入眠。")
            break
        else:
            print("[提示] 请输入有效的选项序号 (0-7)。")


# ==================== 7. 主入口与参数路由 ====================
def main():
    init_directories()
    check_platform_support()

    parser = argparse.ArgumentParser(
        description="灰度守护 Grayscale Guard - 到点自动变灰、到点自动恢复彩色的防熬夜工具"
    )
    parser.add_argument("--status", action="store_true", help="打印详细状态诊断报告并更新产物")
    parser.add_argument("--install", action="store_true", help="安装或更新 Windows 计划任务")
    parser.add_argument("--uninstall", action="store_true", help="彻底卸载计划任务与注册表项")
    parser.add_argument("--test", action="store_true", help="立即开启灰度 4 秒再恢复")
    parser.add_argument("--pause", action="store_true", help="临时暂停守护（恢复彩色且不干预）")
    parser.add_argument("--resume", action="store_true", help="取消临时暂停并恢复守护")
    parser.add_argument("--reconcile", action="store_true", help="立即按当前时间对表对齐")

    args = parser.parse_args()

    # 如果指定了具体命令行参数，则执行单动模式
    if args.status:
        action_status()
    elif args.install:
        action_install()
    elif args.uninstall:
        action_uninstall()
    elif args.test:
        action_test()
    elif args.pause:
        action_pause()
    elif args.resume:
        action_resume()
    elif args.reconcile:
        action_reconcile()
    else:
        # 无参数时：先加载配置（若不存在自动进入配置向导），再呈现交互菜单
        _ = load_config()
        interactive_menu()


if __name__ == "__main__":
    main()
