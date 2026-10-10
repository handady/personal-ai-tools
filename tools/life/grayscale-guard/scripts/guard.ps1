<#
  ============================================================
  GrayscaleGuard / 灰度守护   —— 核心引擎
  ============================================================
  作用：把 Windows 的「颜色滤镜-灰度」按时间自动开关。
        夜间窗口内保持灰度，窗口外恢复彩色。

  用法：
    guard.ps1 -Action reconcile   # 按当前时间自动对齐（计划任务调用这个）
    guard.ps1 -Action on          # 立刻开启灰度
    guard.ps1 -Action off         # 立刻关闭灰度（恢复彩色）
    guard.ps1 -Action status      # 打印完整诊断信息
    guard.ps1 -Action selftest    # 开 4 秒再关，肉眼确认效果
    guard.ps1 -Action pause       # 临时停用（改颜色开关都不再动）
    guard.ps1 -Action resume      # 取消临时停用
    guard.ps1 -Action taskinfo    # 只打印计划任务状态（给 install 用）

  说明：
    * 本脚本只操作当前用户的注册表 HKCU 与一个计划任务，不改系统文件、不装驱动、
      不常驻后台、不联网。用完删掉即可，无残留。
#>
[CmdletBinding()]
param(
  [ValidateSet('reconcile','on','off','status','selftest','pause','resume','taskinfo')]
  [string]$Action = 'reconcile'
)

$ErrorActionPreference = 'Stop'

# ---------- 路径与常量 ----------
$ScriptDir   = $PSScriptRoot
$RootDir     = Split-Path -Parent $ScriptDir
$ConfigPath  = Join-Path $RootDir 'config.json'
$PauseFlag   = Join-Path $RootDir '.paused'
$LogDir      = Join-Path $RootDir 'logs'
$LogFile     = Join-Path $LogDir 'guard.log'

$RegKey          = 'HKCU:\SOFTWARE\Microsoft\ColorFiltering'
$AccKey          = 'HKCU:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Accessibility'
$TaskName        = 'GrayscaleGuard'
$GrayFilterType  = 0          # 0 = 灰度
$LogKeepLines    = 300

# ============================================================
#  基础工具
# ============================================================
function Write-GuardLog {
  param([string]$Message)
  try {
    if (-not (Test-Path -LiteralPath $LogDir)) { New-Item -ItemType Directory -Path $LogDir -Force | Out-Null }
    Add-Content -LiteralPath $LogFile -Value ((Get-Date -Format 'yyyy-MM-dd HH:mm:ss') + '  ' + $Message) -Encoding UTF8
    $all = @(Get-Content -LiteralPath $LogFile -ErrorAction SilentlyContinue)
    if ($all.Count -gt ($LogKeepLines + 100)) {
      $all[($all.Count - $LogKeepLines)..($all.Count - 1)] | Set-Content -LiteralPath $LogFile -Encoding UTF8
    }
  } catch { }
}

function Get-GuardConfig {
  $cfg = [pscustomobject]@{
    nightStart     = '23:00'
    morningEnd     = '07:30'
    recheckMinutes = 10
    enabled        = $true
  }
  if (-not (Test-Path -LiteralPath $ConfigPath)) { return $cfg }
  try {
    $raw = Get-Content -LiteralPath $ConfigPath -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($raw.PSObject.Properties.Name -contains 'nightStart' -and $raw.nightStart) { $cfg.nightStart = [string]$raw.nightStart }
    if ($raw.PSObject.Properties.Name -contains 'morningEnd' -and $raw.morningEnd) { $cfg.morningEnd = [string]$raw.morningEnd }
    if ($raw.PSObject.Properties.Name -contains 'recheckMinutes' -and $null -ne $raw.recheckMinutes) {
      $n = 0
      if ([int]::TryParse([string]$raw.recheckMinutes, [ref]$n)) { if ($n -ge 0 -and $n -le 1440) { $cfg.recheckMinutes = $n } }
    }
    if ($raw.PSObject.Properties.Name -contains 'enabled') { $cfg.enabled = [bool]$raw.enabled }
  } catch { }
  return $cfg
}

function ConvertTo-Minutes {
  param([string]$Text)
  if ($Text -match '^\s*(\d{1,2})\s*[:：]\s*(\d{1,2})\s*$') {
    $h = [int]$matches[1]; $m = [int]$matches[2]
    if ($h -ge 0 -and $h -le 23 -and $m -ge 0 -and $m -le 59) { return ($h * 60 + $m) }
  }
  return -1
}

function Get-DesiredState {
  param([int]$NowMin, [int]$OnMin, [int]$OffMin)
  if ($OnMin -lt 0 -or $OffMin -lt 0 -or $OnMin -eq $OffMin) { return 0 }
  if ($OnMin -gt $OffMin) {
    # 跨零点，例如 23:00 -> 07:30
    if ($NowMin -ge $OnMin -or $NowMin -lt $OffMin) { return 1 } else { return 0 }
  } else {
    # 同一天内，例如 13:00 -> 14:00
    if ($NowMin -ge $OnMin -and $NowMin -lt $OffMin) { return 1 } else { return 0 }
  }
}

function Get-GrayState {
  try {
    $v = (Get-ItemProperty -Path $RegKey -Name 'Active' -ErrorAction Stop).Active
    if ($v -eq 1) { return 1 }
    return 0
  } catch { return -1 }
}

function Get-GrayStateText {
  param([int]$State)
  if ($State -eq 1) { return '灰度（已开启）' }
  if ($State -eq 0) { return '彩色（已关闭）' }
  return '未知'
}

function Send-GrayHotkey {
  if (-not ('GG.KeySim' -as [type])) {
    Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
namespace GG {
  public static class KeySim {
    [DllImport("user32.dll", SetLastError = true)]
    private static extern void keybd_event(byte bVk, byte bScan, uint dwFlags, UIntPtr dwExtraInfo);
    private const uint KEYEVENTF_KEYUP = 0x0002;
    // 模拟 Win + Ctrl + C
    public static void Hotkey() {
      keybd_event(0x5B, 0, 0, UIntPtr.Zero);
      System.Threading.Thread.Sleep(50);
      keybd_event(0x11, 0, 0, UIntPtr.Zero);
      System.Threading.Thread.Sleep(50);
      keybd_event(0x43, 0, 0, UIntPtr.Zero);
      System.Threading.Thread.Sleep(50);
      keybd_event(0x43, 0, KEYEVENTF_KEYUP, UIntPtr.Zero);
      System.Threading.Thread.Sleep(50);
      keybd_event(0x11, 0, KEYEVENTF_KEYUP, UIntPtr.Zero);
      System.Threading.Thread.Sleep(50);
      keybd_event(0x5B, 0, KEYEVENTF_KEYUP, UIntPtr.Zero);
    }
  }
}
'@
  }
  [GG.KeySim]::Hotkey()
}

# 开灰度前的自检：确保「滤镜类型=灰度」「快捷键可用」。
# 防止有人把设置面板里的单选框改成了别的颜色（那样夜里会套错滤镜）。
# 只写 HKCU 下的两个值，其它一律不动。返回被修正项的说明（没改则为空）。
function Confirm-GrayPrereq {
  $fixed = New-Object System.Collections.ArrayList
  try {
    if (-not (Test-Path -LiteralPath $RegKey)) { New-Item -Path $RegKey -Force | Out-Null }
    $cur = Get-ItemProperty -Path $RegKey -ErrorAction SilentlyContinue
    if ($null -eq $cur.FilterType) {
      New-ItemProperty -Path $RegKey -Name 'FilterType' -PropertyType DWord -Value $GrayFilterType -Force | Out-Null
      [void]$fixed.Add('FilterType=0')
    } elseif ($cur.FilterType -ne $GrayFilterType) {
      Set-ItemProperty -Path $RegKey -Name 'FilterType' -Type DWord -Value $GrayFilterType
      [void]$fixed.Add('FilterType ' + $cur.FilterType + '->0(灰度)')
    }
    if ($null -eq $cur.HotkeyEnabled) {
      New-ItemProperty -Path $RegKey -Name 'HotkeyEnabled' -PropertyType DWord -Value 1 -Force | Out-Null
      [void]$fixed.Add('HotkeyEnabled=1')
    } elseif ($cur.HotkeyEnabled -ne 1) {
      Set-ItemProperty -Path $RegKey -Name 'HotkeyEnabled' -Type DWord -Value 1
      [void]$fixed.Add('HotkeyEnabled 0->1')
    }
  } catch { }
  return ($fixed -join ', ')
}

# 把系统切换到目标状态（0=彩色, 1=灰度）
# 返回对象：Ok / Changed / State / Method / Note
function Invoke-SetGrayState {
  param([int]$Target, [switch]$Simulate)

  $current = Get-GrayState
  if ($current -eq -1) {
    return [pscustomobject]@{ Ok = $false; Changed = $false; State = -1; Method = 'none'; Note = '读不到颜色滤镜状态' }
  }
  if ($current -eq $Target) {
    return [pscustomobject]@{ Ok = $true; Changed = $false; State = $current; Method = 'already'; Note = '本来就一致' }
  }
  if ($Simulate) {
    return [pscustomobject]@{ Ok = $true; Changed = $true; State = $current; Method = 'simulate'; Note = '仅模拟' }
  }

  # 0) 开灰度前先做前置自检：滤镜类型必须是「灰度」、快捷键必须启用
  $prereqFix = ''
  if ($Target -eq 1) { $prereqFix = Confirm-GrayPrereq }

  # 1) 首选：模拟 Win+Ctrl+C（和手动按快捷键完全同一条路径）
  $method = ''
  for ($i = 1; $i -le 3; $i++) {
    Send-GrayHotkey
    Start-Sleep -Milliseconds 700
    if ((Get-GrayState) -eq $Target) { $method = 'hotkey'; break }
  }

  # 2) 兜底：直接改注册表（个别情况下快捷键被占用）
  if (-not $method) {
    try {
      if (-not (Test-Path -LiteralPath $RegKey)) { New-Item -Path $RegKey -Force | Out-Null }
      Set-ItemProperty -Path $RegKey -Name 'Active' -Type DWord -Value $Target
      if ($Target -eq 1) {
        Set-ItemProperty -Path $RegKey -Name 'FilterType' -Type DWord -Value $GrayFilterType
        Set-ItemProperty -Path $RegKey -Name 'HotkeyEnabled' -Type DWord -Value 1
        if (-not (Test-Path -LiteralPath $AccKey)) { New-Item -Path $AccKey -Force | Out-Null }
        Set-ItemProperty -Path $AccKey -Name 'Configuration' -Type String -Value 'colorfiltering'
      } else {
        if (Test-Path -LiteralPath $AccKey) {
          Set-ItemProperty -Path $AccKey -Name 'Configuration' -Type String -Value ''
        }
      }
      Start-Sleep -Milliseconds 400
      $method = 'registry'
    } catch {
      return [pscustomobject]@{ Ok = $false; Changed = $false; State = $current; Method = 'failed'; Note = $_.Exception.Message }
    }
  }

  $now = Get-GrayState
  $ok = ($now -eq $Target)
  $note = ''
  if ($ok -and $method -eq 'registry') { $note = '快捷键未生效，已改写注册表（可能需重新登录才可见）' }
  if ($ok -and $prereqFix) { $note = (($note + ' | 已自检修正: ' + $prereqFix) -replace '^\s*\|\s*', '') }
  return [pscustomobject]@{ Ok = $ok; Changed = $true; State = $now; Method = $method; Note = $note }
}

function Test-Paused {
  if (Test-Path -LiteralPath $PauseFlag) { return $true }
  return $false
}

# ============================================================
#  动作实现
# ============================================================

function Invoke-Reconcile {
  $cfg = Get-GuardConfig

  if (-not $cfg.enabled) {
    Write-GuardLog '[跳过] 配置中 enabled = false'
    return
  }
  if (Test-Paused) {
    Write-GuardLog '[跳过] 处于「临时停用」状态（.paused 存在）'
    return
  }

  $onMin  = ConvertTo-Minutes $cfg.nightStart
  $offMin = ConvertTo-Minutes $cfg.morningEnd
  $now    = Get-Date
  $nowMin = $now.Hour * 60 + $now.Minute
  $target = Get-DesiredState -NowMin $nowMin -OnMin $onMin -OffMin $offMin

  $r = Invoke-SetGrayState -Target $target
  $tag = if ($target -eq 1) { '夜间' } else { '日间' }

  if ($r.Changed) {
    Write-GuardLog ("[$tag] 目标=" + (Get-GrayStateText $target) + " | 已切换 -> " + (Get-GrayStateText $r.State) + " | 方式=" + $r.Method + $(if ($r.Note) { ' | ' + $r.Note } else { '' }))
  } elseif ($now.Minute -lt [int]$cfg.recheckMinutes) {
    # 无变化时每小时只留一条心跳记录，避免日志被刷满
    Write-GuardLog ("[$tag] 目标=" + (Get-GrayStateText $target) + " | 已一致，无需操作")
  }
}

function Show-Status {
  $cfg    = Get-GuardConfig
  $onMin  = ConvertTo-Minutes $cfg.nightStart
  $offMin = ConvertTo-Minutes $cfg.morningEnd
  $now    = Get-Date
  $nowMin = $now.Hour * 60 + $now.Minute
  $target = Get-DesiredState -NowMin $nowMin -OnMin $onMin -OffMin $offMin
  $actual = Get-GrayState

  $line = '=' * 62
  Write-Host ''
  Write-Host $line -ForegroundColor DarkCyan
  Write-Host '  GrayscaleGuard / 灰度守护  —— 状态检查' -ForegroundColor Cyan
  Write-Host $line -ForegroundColor DarkCyan

  Write-Host ''
  Write-Host '【1】配置' -ForegroundColor Yellow
  Write-Host ("    夜间窗口   : " + $cfg.nightStart + "  →  次日 " + $cfg.morningEnd + "  （此区间保持灰度）")
  Write-Host ("    总开关     : " + $(if ($cfg.enabled) { '已启用' } else { '已关闭 (enabled=false)' }))
  Write-Host ("    复查间隔   : " + $(if ($cfg.recheckMinutes -gt 0) { "每 $($cfg.recheckMinutes) 分钟自动复查一次" } else { '不自动复查（只在边界时刻/开机/解锁时检查）' }))
  Write-Host ("    配置文件   : " + $ConfigPath)

  Write-Host ''
  Write-Host '【2】此刻状态' -ForegroundColor Yellow
  Write-Host ("    当前时间   : " + $now.ToString('yyyy-MM-dd HH:mm:ss') + "  (" + $now.ToString('dddd') + ")")
  Write-Host ("    当前时段   : " + $(if ($target -eq 1) { '处于夜间窗口内' } else { '处于日间窗口内' }))
  Write-Host ("    应有状态   : " + (Get-GrayStateText $target))
  Write-Host ("    实际状态   : " + (Get-GrayStateText $actual)) -ForegroundColor $(if ($actual -eq $target) { 'Green' } else { 'Red' })
  if ($actual -eq $target) {
    Write-Host '    → 一致，无需干预。' -ForegroundColor Green
  } else {
    Write-Host '    → 不一致！下一次计划任务运行时会自动纠正（或双击「立即测试」。）' -ForegroundColor Yellow
  }
  if (Test-Paused) {
    Write-Host '    → 注意：当前处于「临时停用」状态，守护不会自动改颜色。' -ForegroundColor Magenta
  }

  Write-Host ''
  Write-Host '【3】计划任务' -ForegroundColor Yellow
  try {
    $t = Get-ScheduledTask -TaskName $TaskName -ErrorAction Stop
    $i = Get-ScheduledTaskInfo -TaskName $TaskName -ErrorAction SilentlyContinue
    Write-Host ("    任务名     : " + $t.TaskName + "  状态: " + $t.State)
    Write-Host ("    触发器数量 : " + $t.Triggers.Count)
    if ($i) {
      Write-Host ("    上次运行   : " + $i.LastRunTime + "   结果: " + $i.LastTaskResult)
      Write-Host ("    下次运行   : " + $i.NextRunTime)
    }
  } catch {
    Write-Host '    未找到计划任务 —— 说明还没安装（或已被卸载）。' -ForegroundColor Red
  }

  Write-Host ''
  Write-Host '【4】注册表原始值（Windows 自己存在这里的）' -ForegroundColor Yellow
  try {
    $p = Get-ItemProperty -Path $RegKey -ErrorAction Stop
    Write-Host ("    " + $RegKey)
    Write-Host ("      Active        = " + $p.Active + $(if ($p.Active -eq 1) { '   (1=滤镜开启)' } else { '   (0=滤镜关闭)' }))
    Write-Host ("      FilterType    = " + $p.FilterType + $(if ($p.FilterType -eq 0) { '   (0=灰度)' } else { '   (非 0，可能不是灰度！)' }))
    Write-Host ("      HotkeyEnabled = " + $p.HotkeyEnabled + $(if ($p.HotkeyEnabled -eq 1) { '   (Win+Ctrl+C 可用)' } else { '   (快捷键被禁用！)' }))
  } catch {
    Write-Host '    读不到，可能从未启用过颜色滤镜。' -ForegroundColor Red
  }

  Write-Host ''
  Write-Host '【5】最近日志' -ForegroundColor Yellow
  if (Test-Path -LiteralPath $LogFile) {
    @(Get-Content -LiteralPath $LogFile -Tail 8) | ForEach-Object { Write-Host ('    ' + $_) }
  } else {
    Write-Host '    暂无日志。'
  }

  Write-Host ''
  Write-Host $line -ForegroundColor DarkCyan
  Write-Host ''
}

function Invoke-SelfTest {
  Write-Host ''
  Write-Host '即将把屏幕切成灰度，4 秒后自动恢复彩色……' -ForegroundColor Yellow
  Write-Host '（如果什么都没变，见手册「故障排查」。）' -ForegroundColor DarkGray
  Write-Host ''
  $r1 = Invoke-SetGrayState -Target 1
  Write-Host ('  开启 -> ' + (Get-GrayStateText $r1.State) + '  [方式: ' + $r1.Method + ']') -ForegroundColor $(if ($r1.State -eq 1) { 'Green' } else { 'Red' })
  for ($i = 4; $i -ge 1; $i--) { Write-Host ("    " + $i + '...'); Start-Sleep -Seconds 1 }
  $r0 = Invoke-SetGrayState -Target 0
  Write-Host ('  恢复 -> ' + (Get-GrayStateText $r0.State) + '  [方式: ' + $r0.Method + ']') -ForegroundColor $(if ($r0.State -eq 0) { 'Green' } else { 'Red' })
  Write-Host ''
  if ($r1.State -eq 1 -and $r0.State -eq 0) {
    Write-Host '自检通过：开关都正常。' -ForegroundColor Green
  } else {
    Write-Host '自检异常：没能正常切换，请看手册故障排查一节。' -ForegroundColor Red
    Write-Host ('  细节: ' + $r1.Note + ' / ' + $r0.Note) -ForegroundColor DarkGray
  }
  Write-Host ''
}

function Invoke-Pause {
  if (-not (Test-Path -LiteralPath $PauseFlag)) {
    New-Item -ItemType File -Path $PauseFlag -Force | Out-Null
  }
  $r = Invoke-SetGrayState -Target 0
  Write-GuardLog '[暂停] 已进入临时停用，并把屏幕恢复为彩色'
  Write-Host ''
  Write-Host '已【临时停用】灰度守护：' -ForegroundColor Green
  Write-Host '  · 屏幕已恢复彩色'
  Write-Host '  · 从此刻起，守护不会再自动改变颜色（无论白天黑夜）'
  Write-Host '  · 想恢复，双击「恢复.cmd」即可'
  Write-Host ''
}

function Invoke-Resume {
  if (Test-Path -LiteralPath $PauseFlag) { Remove-Item -LiteralPath $PauseFlag -Force }
  Write-GuardLog '[恢复] 已退出临时停用'
  Write-Host ''
  Write-Host '已【恢复】灰度守护。' -ForegroundColor Green
  Write-Host '  下次到点后会自动开/关灰度。现在先对齐一次：' -ForegroundColor DarkGray
  Invoke-Reconcile
  Show-StatusBrief
  Write-Host ''
}

function Show-StatusBrief {
  $cfg    = Get-GuardConfig
  $onMin  = ConvertTo-Minutes $cfg.nightStart
  $offMin = ConvertTo-Minutes $cfg.morningEnd
  $now    = Get-Date
  $target = Get-DesiredState -NowMin ($now.Hour * 60 + $now.Minute) -OnMin $onMin -OffMin $offMin
  Write-Host ('  当前应有状态: ' + (Get-GrayStateText $target) + '   实际: ' + (Get-GrayStateText (Get-GrayState))) -ForegroundColor DarkGray
}

function Show-TaskInfo {
  try {
    $t = Get-ScheduledTask -TaskName $TaskName -ErrorAction Stop
    Write-Host ('任务: ' + $t.TaskName + '  状态: ' + $t.State)
    $i = Get-ScheduledTaskInfo -TaskName $TaskName
    Write-Host ('上次: ' + $i.LastRunTime + '  下次: ' + $i.NextRunTime + '  结果: ' + $i.LastTaskResult)
  } catch {
    Write-Host '任务不存在'
  }
}

# ============================================================
#  入口
# ============================================================
switch ($Action) {
  'reconcile' { Invoke-Reconcile }
  'on'        { $r = Invoke-SetGrayState -Target 1; Write-GuardLog ('[手动] 开启灰度 -> ' + (Get-GrayStateText $r.State) + $(if ($r.Note) { ' | ' + $r.Note } else { '' })); Write-Host ('现在: ' + (Get-GrayStateText $r.State)) -ForegroundColor $(if ($r.State -eq 1) { 'Green' } else { 'Red' }) }
  'off'       { $r = Invoke-SetGrayState -Target 0; Write-GuardLog ('[手动] 关闭灰度 -> ' + (Get-GrayStateText $r.State)); Write-Host ('现在: ' + (Get-GrayStateText $r.State)) -ForegroundColor $(if ($r.State -eq 0) { 'Green' } else { 'Red' }) }
  'status'    { Show-Status }
  'selftest'  { Invoke-SelfTest }
  'pause'     { Invoke-Pause }
  'resume'    { Invoke-Resume }
  'taskinfo'  { Show-TaskInfo }
}
