<#
  ============================================================
  GrayscaleGuard / 灰度守护   —— 安装 / 重新应用配置
  ============================================================
  做三件事：
    1. 确认 Windows 颜色滤镜可用（灰度、快捷键可用）
    2. 按 config.json 里的时间注册一个计划任务
    3. 立刻对齐一次颜色状态
  需要管理员权限（只为了写「计划任务」，不碰系统其它任何东西）。
#>
[CmdletBinding()]
param(
  [switch]$DryRun   # 只生成并校验计划任务 XML，不注册、不需要管理员（排错用）
)

$ErrorActionPreference = 'Stop'

$ScriptDir  = $PSScriptRoot
$RootDir    = Split-Path -Parent $ScriptDir
$ConfigPath = Join-Path $RootDir 'config.json'
$GuardPath  = Join-Path $ScriptDir 'guard.ps1'
$LogDir     = Join-Path $RootDir 'logs'
$ResultPath = Join-Path $LogDir 'last-apply.txt'
$Snapshot   = Join-Path $LogDir 'registry-snapshot.json'

$RegKey   = 'HKCU:\SOFTWARE\Microsoft\ColorFiltering'
$AccKey   = 'HKCU:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Accessibility'
$TaskName = 'GrayscaleGuard'

if (-not (Test-Path -LiteralPath $LogDir)) { New-Item -ItemType Directory -Path $LogDir -Force | Out-Null }

function Test-Admin {
  $id = [Security.Principal.WindowsIdentity]::GetCurrent()
  return ([Security.Principal.WindowsPrincipal]$id).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

# ---------- 非管理员：提权重启自己，等它跑完，再把结果读回来打印 ----------
if ((-not (Test-Admin)) -and (-not $DryRun)) {
  Write-Host ''
  Write-Host '需要管理员权限来注册计划任务，马上会弹出「用户账户控制」窗口。' -ForegroundColor Yellow
  Write-Host '请在弹窗里点【是】。' -ForegroundColor Yellow
  Write-Host '（授权仅用于创建/更新一个名为 GrayscaleGuard 的计划任务，不会修改系统文件。）' -ForegroundColor DarkGray
  Write-Host ''
  if (Test-Path -LiteralPath $ResultPath) { Remove-Item -LiteralPath $ResultPath -Force -ErrorAction SilentlyContinue }
  try {
    $argList = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', ('"' + $PSCommandPath + '"'))
    Start-Process -FilePath 'powershell.exe' -Verb RunAs -ArgumentList $argList -Wait -WindowStyle Normal | Out-Null
  } catch {
    Write-Host '[失败] 没有拿到管理员权限（可能点了「否」）。安装未完成。' -ForegroundColor Red
    exit 1
  }
  Write-Host ''
  if (Test-Path -LiteralPath $ResultPath) {
    Get-Content -LiteralPath $ResultPath -Encoding UTF8 | ForEach-Object { Write-Host $_ }
  } else {
    Write-Host '[提示] 提权窗口没有留下结果文件，正在自行核实……' -ForegroundColor Yellow
    if (Get-ScheduledTask -TaskName 'GrayscaleGuard' -ErrorAction SilentlyContinue) {
      Write-Host '  [OK] 计划任务 GrayscaleGuard 已存在 —— 安装其实已经成功。' -ForegroundColor Green
      Write-Host '       双击「检查状态.cmd」可以看到完整报告。' -ForegroundColor DarkGray
    } else {
      Write-Host '  [X] 没找到计划任务，安装确实没完成。请重新运行一次。' -ForegroundColor Red
    }
  }
  exit 0
}

# ============================ 以下是管理员分支 ============================
$report = New-Object System.Collections.ArrayList
function R { param([string]$s, [string]$c = 'Gray') [void]$report.Add([pscustomobject]@{ Text = $s; Color = $c }) }

$cfg = [pscustomobject]@{ nightStart = '23:00'; morningEnd = '07:30'; recheckMinutes = 10; enabled = $true }
if (Test-Path -LiteralPath $ConfigPath) {
  try {
    $raw = Get-Content -LiteralPath $ConfigPath -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($raw.nightStart) { $cfg.nightStart = [string]$raw.nightStart }
    if ($raw.morningEnd) { $cfg.morningEnd = [string]$raw.morningEnd }
    if ($null -ne $raw.recheckMinutes) { $cfg.recheckMinutes = [int]$raw.recheckMinutes }
    if ($raw.PSObject.Properties.Name -contains 'enabled') { $cfg.enabled = [bool]$raw.enabled }
  } catch { }
}
function To-Min { param([string]$t) if ($t -match '^\s*(\d{1,2})\s*[:：]\s*(\d{1,2})\s*$') { return ([int]$matches[1] * 60 + [int]$matches[2]) } return -1 }
$onMin = To-Min $cfg.nightStart
$offMin = To-Min $cfg.morningEnd
if ($onMin -lt 0 -or $offMin -lt 0 -or $onMin -eq $offMin) {
  R '' 'Gray'
  R '[失败] config.json 里的时间格式不对，或者两个时间相同。' 'Red'
  R '       正确写法示例： "nightStart": "23:00", "morningEnd": "07:30"' 'Gray'
  $report | ForEach-Object { Write-Host $_.Text -ForegroundColor $_.Color }
  $report | ForEach-Object { $_.Text } | Set-Content -LiteralPath $ResultPath -Encoding UTF8
  exit 1
}

# ---- 1. 记录原始注册表快照（卸载时用来还原）----
try {
  $p = Get-ItemProperty -Path $RegKey -ErrorAction SilentlyContinue
  $a = Get-ItemProperty -Path $AccKey -ErrorAction SilentlyContinue
  $snap = [pscustomobject]@{
    takenAt        = (Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
    active         = if ($p) { $p.Active } else { $null }
    filterType     = if ($p) { $p.FilterType } else { $null }
    hotkeyEnabled  = if ($p) { $p.HotkeyEnabled } else { $null }
    configuration  = if ($a) { $a.Configuration } else { $null }
    taskExisted    = [bool](Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue)
  }
  if (-not $snap.taskExisted -and -not (Test-Path -LiteralPath $Snapshot)) {
    $snap | ConvertTo-Json | Set-Content -LiteralPath $Snapshot -Encoding UTF8
  }
} catch { }

# ---- 2. 确认颜色滤镜可用 ----
$notes = New-Object System.Collections.ArrayList

if (-not (Test-Path -LiteralPath $RegKey)) { New-Item -Path $RegKey -Force | Out-Null }
$cur = Get-ItemProperty -Path $RegKey -ErrorAction SilentlyContinue
if ($null -eq $cur.Active)        { New-ItemProperty -Path $RegKey -Name 'Active'        -PropertyType DWord -Value 0 -Force | Out-Null }
if ($null -eq $cur.FilterType)    { New-ItemProperty -Path $RegKey -Name 'FilterType'    -PropertyType DWord -Value 0 -Force | Out-Null }
if ($null -eq $cur.HotkeyEnabled) { New-ItemProperty -Path $RegKey -Name 'HotkeyEnabled' -PropertyType DWord -Value 1 -Force | Out-Null }

$cur = Get-ItemProperty -Path $RegKey
$changedFilter = $false
if ($cur.FilterType -ne 0) {
  Set-ItemProperty -Path $RegKey -Name 'FilterType' -Type DWord -Value 0
  $changedFilter = $true
}
if ($cur.HotkeyEnabled -ne 1) {
  Set-ItemProperty -Path $RegKey -Name 'HotkeyEnabled' -Type DWord -Value 1
  [void]$notes.Add('已重新启用 Win+Ctrl+C 快捷键（HotkeyEnabled=1）')
}
if ($changedFilter) {
  [void]$notes.Add('原来的颜色滤镜不是「灰度」，已切换为「灰度」(FilterType=0)')
}

# ---- 3. 注册计划任务 ----
$uid = "$env:USERDOMAIN\$env:USERNAME"
$psExe = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
if (-not (Test-Path -LiteralPath $psExe)) { $psExe = 'powershell.exe' }

function Esc-Xml { param([string]$s) return ($s -replace '&', '&amp;' -replace '<', '&lt;' -replace '>', '&gt;') }

$guardArg = '-NoProfile -NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -File "' + (Esc-Xml $GuardPath) + '" -Action reconcile'

$today = (Get-Date).ToString('yyyy-MM-dd')
$onBoundary  = $today + 'T' + $cfg.nightStart + ':00'
$offBoundary = $today + 'T' + $cfg.morningEnd + ':00'

$rep = ''
if ([int]$cfg.recheckMinutes -gt 0) {
  $rep = '<Repetition><Interval>PT' + [int]$cfg.recheckMinutes + 'M</Interval><Duration>P1D</Duration><StopAtDurationEnd>false</StopAtDurationEnd></Repetition>'
}

$xml = @"
<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Author>$uid</Author>
    <Description>GrayscaleGuard 灰度守护：夜间自动开启 Windows 灰度滤镜，早上自动恢复彩色。卸载方式见同目录「卸载.cmd」。</Description>
  </RegistrationInfo>
  <Triggers>
    <TimeTrigger>
      <StartBoundary>$onBoundary</StartBoundary>
      <Enabled>true</Enabled>
      $rep
    </TimeTrigger>
    <TimeTrigger>
      <StartBoundary>$offBoundary</StartBoundary>
      <Enabled>true</Enabled>
    </TimeTrigger>
    <LogonTrigger>
      <Enabled>true</Enabled>
      <UserId>$uid</UserId>
    </LogonTrigger>
    <SessionStateChangeTrigger>
      <Enabled>true</Enabled>
      <UserId>$uid</UserId>
      <StateChange>SessionUnlock</StateChange>
    </SessionStateChangeTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <UserId>$uid</UserId>
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <AllowHardTerminate>true</AllowHardTerminate>
    <StartWhenAvailable>true</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>false</RunOnlyIfNetworkAvailable>
    <IdleSettings>
      <StopOnIdleEnd>false</StopOnIdleEnd>
      <RestartOnIdle>false</RestartOnIdle>
    </IdleSettings>
    <AllowStartOnDemand>true</AllowStartOnDemand>
    <Enabled>true</Enabled>
    <Hidden>false</Hidden>
    <RunOnlyIfIdle>false</RunOnlyIfIdle>
    <WakeToRun>false</WakeToRun>
    <ExecutionTimeLimit>PT2M</ExecutionTimeLimit>
    <Priority>7</Priority>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>$psExe</Command>
      <Arguments>$guardArg</Arguments>
    </Exec>
  </Actions>
</Task>
"@

$taskOk = $false
$taskErr = ''

if ($DryRun) {
  Write-Host ''
  Write-Host '[DryRun] 仅生成并校验计划任务 XML，不做任何注册/修改。' -ForegroundColor Cyan
  try {
    [void][xml]$xml
    Write-Host '  XML 校验: 合法' -ForegroundColor Green
  } catch {
    Write-Host ('  XML 校验: 非法 -> ' + $_.Exception.Message) -ForegroundColor Red
  }
  $xmlPath = Join-Path $LogDir 'generated-task.xml'
  $xml | Set-Content -LiteralPath $xmlPath -Encoding UTF8
  Write-Host ('  已写出  : ' + $xmlPath) -ForegroundColor Gray
  Write-Host ('  执行程序: ' + $psExe) -ForegroundColor Gray
  Write-Host ('  执行参数: ' + $guardArg) -ForegroundColor Gray
  Write-Host ('  触发器  : 每日 ' + $cfg.nightStart + '（重复 ' + $cfg.recheckMinutes + ' 分钟）、每日 ' + $cfg.morningEnd + '、登录时、解锁时') -ForegroundColor Gray
  Write-Host ''
  exit 0
}

try {
  [void][xml]$xml          # 先校验 XML 合法
  Register-ScheduledTask -TaskName $TaskName -Xml $xml -Force -ErrorAction Stop | Out-Null
  $taskOk = $true
} catch {
  $taskErr = $_.Exception.Message
}

# 结果先落盘一次：万一提权窗口被提前关掉，外层窗口也能读到关键结论
@(
  'GrayscaleGuard 安装结果',
  ('计划任务 : ' + $(if ($taskOk) { '已注册成功' } else { '注册失败 - ' + $taskErr })),
  ('夜间窗口 : ' + $cfg.nightStart + ' -> 次日 ' + $cfg.morningEnd),
  ('复查间隔 : ' + $cfg.recheckMinutes + ' 分钟')
) | Set-Content -LiteralPath $ResultPath -Encoding UTF8

# ---- 4. 立刻对齐一次 ----
$reconcileText = '(未执行)'
if ($taskOk) {
  try {
    & $psExe -NoProfile -ExecutionPolicy Bypass -File $GuardPath -Action reconcile 2>&1 | Out-Null
    $reconcileText = '已按当前时间对齐一次'
  } catch { $reconcileText = '对齐时出错: ' + $_.Exception.Message }
}

# ---- 5. 汇总 ----
$line = '=' * 62
R '' 'Gray'
if ($taskOk) {
  R '  安装完成  /  GrayscaleGuard 灰度守护' 'Green'
} else {
  R '  安装失败' 'Red'
}
R $line 'DarkCyan'
R ''
R ('  夜间窗口 : ' + $cfg.nightStart + '  →  次日 ' + $cfg.morningEnd + '  （此区间保持灰度）')
R ('  总开关   : ' + $(if ($cfg.enabled) { '已启用' } else { '已关闭 (enabled=false) —— 守护不会动作！' }))
R ('  复查间隔 : ' + $(if ([int]$cfg.recheckMinutes -gt 0) { '每 ' + $cfg.recheckMinutes + ' 分钟自动复查一次' } else { '不自动复查（仅边界时刻 / 开机 / 解锁时检查）' }))
R ('  计划任务 : ' + $(if ($taskOk) { 'GrayscaleGuard 已注册（可在「任务计划程序」里看到）' } else { '注册失败: ' + $taskErr })) $(if ($taskOk) { 'Gray' } else { 'Red' })
R ('  即时对齐 : ' + $reconcileText)
foreach ($n in $notes) { R ('  提示     : ' + $n) 'Yellow' }
R ''
R '  接下来的使用：' 'Gray'
R '    · 到点自动切换，不需要你做任何事。' 'Gray'
R '    · 双击「检查状态.cmd」可随时核对。' 'Gray'
R '    · 双击「立即测试.cmd」可肉眼确认灰度效果。' 'Gray'
R '    · 想改时间：编辑 config.json 后双击「安装.cmd」重新应用。' 'Gray'
R '    · 想彻底关掉：双击「卸载.cmd」。' 'Gray'
R ''
R $line 'DarkCyan'
R ''

foreach ($r in $report) { Write-Host $r.Text -ForegroundColor $r.Color }
$report | ForEach-Object { $_.Text } | Set-Content -LiteralPath $ResultPath -Encoding UTF8
