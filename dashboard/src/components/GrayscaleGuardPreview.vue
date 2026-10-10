<script setup lang="ts">
import { computed, ref } from 'vue';

const props = defineProps<{
  guardData: {
    tool: string;
    nightStart: string;
    morningEnd: string;
    recheckMinutes: number;
    enabled: boolean;
    isPaused: boolean;
    currentColorState: string;
    colorStateCode: number;
    hotkeyEnabled: boolean;
    taskInstalled: boolean;
    taskState: string;
    lastRunTime: string;
    nextRunTime: string;
    updatedAt: string;
  };
}>();

const emit = defineEmits<{
  (e: 'run', action: string): void;
}>();

const copiedCmd = ref('');

const copyCmd = (cmd: string) => {
  navigator.clipboard.writeText(cmd);
  copiedCmd.value = cmd;
  setTimeout(() => {
    copiedCmd.value = '';
  }, 2000);
};

const isNightMode = computed(() => props.guardData.colorStateCode === 1);
const isPaused = computed(() => props.guardData.isPaused);
</script>

<template>
  <div class="guard-preview-container">
    <!-- Top Hero Status Card -->
    <div class="hero-status-card" :class="{ 'is-night': isNightMode, 'is-paused': isPaused }">
      <div class="hero-status-left">
        <div class="status-orb" :class="{ 'orb-gray': isNightMode, 'orb-color': !isNightMode && !isPaused, 'orb-paused': isPaused }">
          <span class="orb-icon">{{ isPaused ? '⏸️' : (isNightMode ? '🌙' : '☀️') }}</span>
        </div>
        <div class="status-meta">
          <div class="status-tag">
            <span v-if="isPaused" class="tag-badge paused">● 临时停用中</span>
            <span v-else-if="isNightMode" class="tag-badge gray">● 灰度生效中 (夜间护眼模式)</span>
            <span v-else class="tag-badge day">● 彩色正常模式 (日间作息)</span>
          </div>
          <h2 class="current-screen-title">{{ guardData.currentColorState }}</h2>
          <p class="status-tip">
            {{ isPaused ? '已临时暂停，定时干预已挂起，屏幕保持彩色' : (isNightMode ? '已到点自动变灰，掐断熬夜心流冲动' : '屏幕正常色彩，将在设定的就寝时间自动变灰') }}
          </p>
        </div>
      </div>
      <div class="hero-status-right">
        <div class="schedule-clock-badge">
          <span class="clock-label">夜间作息窗口</span>
          <span class="clock-time">{{ guardData.nightStart }} → {{ guardData.morningEnd }}</span>
          <span class="clock-sub">每 {{ guardData.recheckMinutes }} 分钟自动对表</span>
        </div>
      </div>
    </div>

    <!-- Quick Stats Grid -->
    <div class="stats-grid">
      <div class="stat-box">
        <div class="stat-icon">🕒</div>
        <div class="stat-content">
          <span class="stat-title">上次自动对齐</span>
          <span class="stat-val">{{ guardData.lastRunTime || '-' }}</span>
        </div>
      </div>
      <div class="stat-box">
        <div class="stat-icon">⏳</div>
        <div class="stat-content">
          <span class="stat-title">下次触发计划</span>
          <span class="stat-val">{{ guardData.nextRunTime || '-' }}</span>
        </div>
      </div>
      <div class="stat-box">
        <div class="stat-icon">🛡️</div>
        <div class="stat-content">
          <span class="stat-title">计划任务状态</span>
          <span class="stat-val" :class="guardData.taskInstalled ? 'text-green' : 'text-amber'">
            {{ guardData.taskInstalled ? `已注册 (${guardData.taskState})` : '未注册' }}
          </span>
        </div>
      </div>
      <div class="stat-box">
        <div class="stat-icon">⌨️</div>
        <div class="stat-content">
          <span class="stat-title">Win+Ctrl+C 热键</span>
          <span class="stat-val" :class="guardData.hotkeyEnabled ? 'text-green' : 'text-red'">
            {{ guardData.hotkeyEnabled ? '系统热键已就绪' : '未开启' }}
          </span>
        </div>
      </div>
    </div>

    <!-- Quick Action Launcher Commands -->
    <div class="quick-commands-panel">
      <div class="panel-header">
        <span class="panel-title">⚡ 终端快捷指令与动作</span>
        <span class="panel-sub">可直接点击运行，或复制到终端执行</span>
      </div>
      <div class="commands-list">
        <div class="command-row">
          <div class="cmd-info">
            <span class="cmd-desc">测试灰度效果 (4秒后自动恢复)</span>
            <code>python tools/life/grayscale-guard/main.py --test</code>
          </div>
          <div class="row-btns">
            <button class="action-run-btn" @click="emit('run', 'test')">
              ▶ 立即测试
            </button>
            <button 
              class="action-copy-btn" 
              @click="copyCmd('python tools/life/grayscale-guard/main.py --test')"
            >
              {{ copiedCmd.includes('--test') ? '✓' : '复制' }}
            </button>
          </div>
        </div>
        <div class="command-row">
          <div class="cmd-info">
            <span class="cmd-desc">加班时临时暂停守护 (恢复彩色)</span>
            <code>python tools/life/grayscale-guard/main.py --pause</code>
          </div>
          <div class="row-btns">
            <button class="action-run-btn btn-warn" @click="emit('run', 'pause')">
              ⏸️ 临时暂停
            </button>
            <button 
              class="action-copy-btn" 
              @click="copyCmd('python tools/life/grayscale-guard/main.py --pause')"
            >
              {{ copiedCmd.includes('--pause') ? '✓' : '复制' }}
            </button>
          </div>
        </div>
        <div class="command-row">
          <div class="cmd-info">
            <span class="cmd-desc">恢复守护 (取消暂停并对齐)</span>
            <code>python tools/life/grayscale-guard/main.py --resume</code>
          </div>
          <div class="row-btns">
            <button class="action-run-btn btn-success" @click="emit('run', 'resume')">
              ▶ 恢复守护
            </button>
            <button 
              class="action-copy-btn" 
              @click="copyCmd('python tools/life/grayscale-guard/main.py --resume')"
            >
              {{ copiedCmd.includes('--resume') ? '✓' : '复制' }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <div class="footer-note">
      <span>最后更新时间：{{ guardData.updatedAt }}</span>
      <span>• 零常驻后台进程 • Windows 任务计划驱动</span>
    </div>
  </div>
</template>

<style scoped>
.guard-preview-container {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
  color: var(--text-main, #1e293b);
}

.hero-status-card {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 1.25rem;
  padding: 1.5rem;
  border-radius: 1rem;
  background: linear-gradient(135deg, rgba(244, 63, 94, 0.08) 0%, rgba(251, 113, 133, 0.03) 100%);
  border: 1px solid rgba(244, 63, 94, 0.2);
  transition: all 0.3s ease;
}

.hero-status-card.is-night {
  background: linear-gradient(135deg, rgba(100, 116, 139, 0.15) 0%, rgba(51, 65, 85, 0.08) 100%);
  border-color: rgba(148, 163, 184, 0.3);
}

.hero-status-card.is-paused {
  background: linear-gradient(135deg, rgba(245, 158, 11, 0.1) 0%, rgba(217, 119, 6, 0.04) 100%);
  border-color: rgba(245, 158, 11, 0.3);
}

.hero-status-left {
  display: flex;
  align-items: center;
  gap: 1.25rem;
}

.status-orb {
  width: 3.8rem;
  height: 3.8rem;
  border-radius: 1rem;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.8rem;
  box-shadow: 0 8px 16px rgba(0, 0, 0, 0.08);
}

.orb-color {
  background: linear-gradient(135deg, #fb7185, #f43f5e);
}

.orb-gray {
  background: linear-gradient(135deg, #64748b, #475569);
}

.orb-paused {
  background: linear-gradient(135deg, #f59e0b, #d97706);
}

.status-meta {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.tag-badge {
  font-size: 0.75rem;
  font-weight: 600;
  padding: 0.2rem 0.6rem;
  border-radius: 9999px;
  display: inline-block;
  margin-bottom: 0.2rem;
}

.tag-badge.day {
  background: rgba(244, 63, 94, 0.15);
  color: #e11d48;
}

.tag-badge.gray {
  background: rgba(100, 116, 139, 0.2);
  color: #cbd5e1;
}

.tag-badge.paused {
  background: rgba(245, 158, 11, 0.2);
  color: #d97706;
}

.current-screen-title {
  margin: 0;
  font-size: 1.45rem;
  font-weight: 700;
  letter-spacing: -0.02em;
}

.status-tip {
  margin: 0;
  font-size: 0.85rem;
  opacity: 0.75;
}

.hero-status-right {
  display: flex;
  align-items: center;
}

.schedule-clock-badge {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  background: rgba(255, 255, 255, 0.5);
  backdrop-filter: blur(8px);
  padding: 0.75rem 1.1rem;
  border-radius: 0.75rem;
  border: 1px solid rgba(0, 0, 0, 0.05);
}

:root[data-theme='dark'] .schedule-clock-badge {
  background: rgba(30, 41, 59, 0.6);
  border-color: rgba(255, 255, 255, 0.08);
}

.clock-label {
  font-size: 0.72rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  opacity: 0.7;
}

.clock-time {
  font-size: 1.25rem;
  font-weight: 700;
  font-family: var(--font-mono, monospace);
  color: #e11d48;
}

.clock-sub {
  font-size: 0.75rem;
  opacity: 0.65;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 0.75rem;
}

.stat-box {
  display: flex;
  align-items: center;
  gap: 0.85rem;
  padding: 0.85rem 1rem;
  border-radius: 0.75rem;
  background: var(--bg-card, rgba(255, 255, 255, 0.6));
  border: 1px solid var(--border-color, rgba(0, 0, 0, 0.08));
}

.stat-icon {
  font-size: 1.4rem;
}

.stat-content {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
}

.stat-title {
  font-size: 0.75rem;
  opacity: 0.65;
}

.stat-val {
  font-size: 0.9rem;
  font-weight: 600;
  font-family: var(--font-mono, monospace);
}

.text-green { color: #10b981; }
.text-amber { color: #f59e0b; }
.text-red { color: #ef4444; }

.quick-commands-panel {
  border-radius: 0.85rem;
  background: var(--bg-card, rgba(255, 255, 255, 0.5));
  border: 1px solid var(--border-color, rgba(0, 0, 0, 0.08));
  padding: 1rem;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 0.75rem;
}

.panel-title {
  font-weight: 600;
  font-size: 0.92rem;
}

.panel-sub {
  font-size: 0.75rem;
  opacity: 0.6;
}

.commands-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.command-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
  padding: 0.55rem 0.85rem;
  border-radius: 0.5rem;
  background: rgba(0, 0, 0, 0.03);
  border: 1px solid rgba(0, 0, 0, 0.04);
}

:root[data-theme='dark'] .command-row {
  background: rgba(255, 255, 255, 0.03);
  border-color: rgba(255, 255, 255, 0.04);
}

.cmd-info {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
  overflow: hidden;
}

.cmd-desc {
  font-size: 0.78rem;
  font-weight: 500;
}

.cmd-info code {
  font-size: 0.78rem;
  font-family: var(--font-mono, monospace);
  color: #0284c7;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.action-copy-btn {
  padding: 0.35rem 0.75rem;
  font-size: 0.75rem;
  border-radius: 0.35rem;
  border: 1px solid var(--border-color, rgba(0, 0, 0, 0.1));
  background: var(--bg-card, #fff);
  cursor: pointer;
  transition: all 0.2s ease;
  flex-shrink: 0;
}

.action-copy-btn:hover {
  background: #f1f5f9;
}

.row-btns {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  flex-shrink: 0;
}

.action-run-btn {
  padding: 0.35rem 0.75rem;
  font-size: 0.75rem;
  font-weight: 600;
  border-radius: 0.35rem;
  border: none;
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
  color: #fff;
  cursor: pointer;
  transition: all 0.2s ease;
  flex-shrink: 0;
}
.action-run-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 10px rgba(16, 185, 129, 0.3);
}

.action-run-btn.btn-warn {
  background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
}
.action-run-btn.btn-warn:hover {
  box-shadow: 0 4px 10px rgba(245, 158, 11, 0.3);
}

.action-run-btn.btn-success {
  background: linear-gradient(135deg, #38bdf8 0%, #0284c7 100%);
}
.action-run-btn.btn-success:hover {
  box-shadow: 0 4px 10px rgba(56, 189, 248, 0.3);
}

.footer-note {
  display: flex;
  justify-content: space-between;
  font-size: 0.72rem;
  opacity: 0.5;
  padding: 0 0.25rem;
}
</style>
