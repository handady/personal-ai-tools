<#
  ============================================================
  GrayscaleGuard / 灰度守护   —— 卸载
  ============================================================
  彻底移除本工具在系统里留下的所有东西：
    1. 删除计划任务 GrayscaleGuard
    2. 关闭灰度滤镜（把屏幕恢复成彩色）
    3. 把安装前的注册表原始值还原回去
    4. 删掉临时停用标记
  做完之后，这个文件夹可以直接整个删除，系统里不会有任何残留。
#>
[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'

$ScriptDir  = $PSScriptRoot
$RootDir    = Split-Path -Parent $ScriptDir
$GuardPath  = Join-Path $ScriptDir 'guard.ps1'
$LogDir     = Join-Path $RootDir 'logs'
$ResultPath = Join-Path $LogDir 'last-uninstall.txt'
$Snapshot   = Join-Path $LogDir 'registry-snapshot.json'
$PauseFlag  = Join-Path $RootDir '.paused'

$RegKey   = 'HKCU:\SOFTWARE\Microsoft\ColorFiltering'
$AccKey   = 'HKCU:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Accessibility'
$TaskName = 'GrayscaleGuard'

if (-not (Test-Path -LiteralPath $LogDir)) { New-Item -ItemType Directory -Path $LogDir -Force | Out-Null }

function Test-Admin {
  $id = [Security.Principal.WindowsIdentity]::GetCurrent()
  return ([Security.Principal.WindowsPrincipal]$id).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

if (-not (Test-Admin)) {
  Write-Host ''
  Write-Host '卸载需要管理员权限（只为了删除那个计划任务），马上会弹出「用户账户控制」窗口。' -ForegroundColor Yellow
  Write-Host '请在弹窗里点【是】。' -ForegroundColor Yellow
  Write-Host ''
  if (Test-Path -LiteralPath $ResultPath) { Remove-Item -LiteralPath $ResultPath -Force -ErrorAction SilentlyContinue }
  try {
    $argList = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', ('"' + $PSCommandPath + '"'))
    Start-Process -FilePath 'powershell.exe' -Verb RunAs -ArgumentList $argList -Wait -WindowStyle Normal | Out-Null
  } catch {
    Write-Host '[失败] 没有拿到管理员权限（可能点了「否」）。卸载未完成。' -ForegroundColor Red
    exit 1
  }
  Write-Host ''
  if (Test-Path -LiteralPath $ResultPath) {
    Get-Content -LiteralPath $ResultPath -Encoding UTF8 | ForEach-Object { Write-Host $_ }
  }
  exit 0
}

# ============================ 管理员分支 ============================
$report = New-Object System.Collections.ArrayList
function R { param([string]$s, [string]$c = 'Gray') [void]$report.Add([pscustomobject]@{ Text = $s; Color = $c }) }

$line = '=' * 62
R ''
R '  卸载  GrayscaleGuard 灰度守护' 'Cyan'
R $line 'DarkCyan'
R ''

# 1) 删除计划任务
$taskRemoved = $false
try {
  $t = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
  if ($t) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction Stop
    $taskRemoved = $true
    R '  [1/4] 计划任务 GrayscaleGuard  —— 已删除' 'Green'
  } else {
    R '  [1/4] 计划任务 GrayscaleGuard  —— 本来就不存在，跳过' 'Gray'
  }
} catch {
  R ('  [1/4] 计划任务删除失败: ' + $_.Exception.Message) 'Red'
}

# 2) 关闭灰度
try {
  & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $GuardPath -Action off 2>&1 | Out-Null
  $st = (Get-ItemProperty -Path $RegKey -Name 'Active' -ErrorAction SilentlyContinue).Active
  if ($st -eq 0) { R '  [2/4] 灰度滤镜  —— 已关闭，屏幕已恢复彩色' 'Green' }
  else           { R '  [2/4] 灰度滤镜  —— 仍处于开启，可手动按 Win+Ctrl+C 关闭' 'Yellow' }
} catch {
  R ('  [2/4] 关闭灰度时出错: ' + $_.Exception.Message) 'Red'
}

# 3) 还原注册表原始值
$restored = New-Object System.Collections.ArrayList
if (Test-Path -LiteralPath $Snapshot) {
  try {
    $snap = Get-Content -LiteralPath $Snapshot -Raw -Encoding UTF8 | ConvertFrom-Json
    if (Test-Path -LiteralPath $RegKey) {
      if ($null -ne $snap.active        -and $snap.active        -ne '') { Set-ItemProperty -Path $RegKey -Name 'Active'        -Type DWord -Value ([int]$snap.active);        [void]$restored.Add('Active=' + $snap.active) }
      if ($null -ne $snap.filterType    -and $snap.filterType    -ne '') { Set-ItemProperty -Path $RegKey -Name 'FilterType'    -Type DWord -Value ([int]$snap.filterType);    [void]$restored.Add('FilterType=' + $snap.filterType) }
      if ($null -ne $snap.hotkeyEnabled -and $snap.hotkeyEnabled -ne '') { Set-ItemProperty -Path $RegKey -Name 'HotkeyEnabled' -Type DWord -Value ([int]$snap.hotkeyEnabled); [void]$restored.Add('HotkeyEnabled=' + $snap.hotkeyEnabled) }
    }
    if ($null -ne $snap.configuration -and (Test-Path -LiteralPath $AccKey)) {
      Set-ItemProperty -Path $AccKey -Name 'Configuration' -Type String -Value ([string]$snap.configuration)
      [void]$restored.Add('Configuration=' + $snap.configuration)
    }
    if ($restored.Count -gt 0) { R ('  [3/4] 注册表原始值  —— 已还原: ' + ($restored -join ', ')) 'Green' }
    else                        { R '  [3/4] 注册表原始值  —— 没有需要还原的项' 'Gray' }
  } catch {
    R ('  [3/4] 还原注册表时出错: ' + $_.Exception.Message) 'Red'
  }
} else {
  R '  [3/4] 注册表原始值  —— 没找到安装快照，保持现状（Windows 设置里可随时手动改）' 'Gray'
}

# 4) 删掉停用标记
if (Test-Path -LiteralPath $PauseFlag) {
  Remove-Item -LiteralPath $PauseFlag -Force -ErrorAction SilentlyContinue
  R '  [4/4] 临时停用标记 .paused  —— 已删除' 'Green'
} else {
  R '  [4/4] 临时停用标记 .paused  —— 本来就没有，跳过' 'Gray'
}

# 校验
R ''
R '  ── 校验 ──' 'DarkCyan'
$stillTask = $null
try { $stillTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue } catch { }
if (-not $stillTask) { R '  ✓ 计划任务：已确认不存在' 'Green' }
else                 { R '  ✗ 计划任务：仍然存在，请重试或手动删除' 'Red' }

$activeNow = (Get-ItemProperty -Path $RegKey -Name 'Active' -ErrorAction SilentlyContinue).Active
if ($activeNow -ne 1) { R '  ✓ 灰度滤镜：当前为关闭（彩色）' 'Green' }
else                  { R '  ✗ 灰度滤镜：当前仍开启，按一次 Win+Ctrl+C 即可' 'Yellow' }

R ''
R '  卸载完成。' 'Green'
R '  本工具没有安装任何驱动、服务、开机自启项或后台常驻进程；' 'Gray'
R '  现在【整个 grayscale-guard 文件夹可以直接删除】，系统里不会留任何残留。' 'Gray'
R '  （如果你还想留着这份手册，只删 scripts 文件夹和几个 .cmd 也一样干净。）' 'Gray'
R ''
R '  ※ 唯一的例外：如果你以后想再跑一遍这个任务，需要重新双击「安装.cmd」。' 'DarkGray'
R ''
R $line 'DarkCyan'
R ''

foreach ($r in $report) { Write-Host $r.Text -ForegroundColor $r.Color }
$report | ForEach-Object { $_.Text } | Set-Content -LiteralPath $ResultPath -Encoding UTF8
