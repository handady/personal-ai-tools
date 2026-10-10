<script setup lang="ts">
import { ref, watch, onUnmounted, nextTick } from 'vue';

const props = defineProps<{
  show: boolean;
  tool: any;
  action?: string;
}>();

const emit = defineEmits<{
  (e: 'close'): void;
  (e: 'completed'): void;
}>();

const logs = ref<Array<{ id: number; type: 'stdout' | 'stderr' | 'system'; text: string }>>([]);
const status = ref<'idle' | 'running' | 'success' | 'error' | 'stopped'>('idle');
const executedCommand = ref('');
const duration = ref(0);
const terminalBody = ref<HTMLElement | null>(null);
const copied = ref(false);

let runId = '';
let timer: any = null;
let abortController: AbortController | null = null;

// 过滤控制台常见的 ANSI 颜色转义字符，保持清晰整洁
const stripAnsi = (str: string) => {
  return str.replace(/[\u001b\u009b][[()#;?]*(?:[0-9]{1,4}(?:;[0-9]{0,4})*)?[0-9A-ORZcf-nqry=><]/g, '');
};

const scrollToBottom = () => {
  nextTick(() => {
    if (terminalBody.value) {
      terminalBody.value.scrollTop = terminalBody.value.scrollHeight;
    }
  });
};

const startExecution = async () => {
  if (!props.tool) return;

  runId = 'run_' + Date.now();
  status.value = 'running';
  duration.value = 0;
  logs.value = [
    { id: 1, type: 'system', text: `[系统] 正在准备启动工具: ${props.tool.name} (${props.tool.id})...` }
  ];

  clearInterval(timer);
  timer = setInterval(() => {
    duration.value += 1;
  }, 1000);

  abortController = new AbortController();

  try {
    const response = await fetch('/api/run-tool', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        toolId: props.tool.id,
        action: props.action || undefined,
        runId
      }),
      signal: abortController.signal
    });

    if (!response.ok) {
      const err = await response.text();
      logs.value.push({ id: Date.now(), type: 'stderr', text: `[错误] 启动失败 (${response.status}): ${err}` });
      status.value = 'error';
      clearInterval(timer);
      return;
    }

    const reader = response.body?.getReader();
    if (!reader) throw new Error('无法读取事件流');

    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6));
            if (data.type === 'start') {
              executedCommand.value = data.command;
              logs.value.push({ id: Date.now(), type: 'system', text: `[执行命令] $ ${data.command}` });
            } else if (data.type === 'stdout') {
              logs.value.push({ id: Date.now() + Math.random(), type: 'stdout', text: stripAnsi(data.text) });
            } else if (data.type === 'stderr') {
              logs.value.push({ id: Date.now() + Math.random(), type: 'stderr', text: stripAnsi(data.text) });
            } else if (data.type === 'exit') {
              if (data.code === 0) {
                status.value = 'success';
                logs.value.push({ id: Date.now(), type: 'system', text: `[完成] 进程正常退出 (退出码 0)` });
              } else {
                status.value = 'error';
                logs.value.push({ id: Date.now(), type: 'system', text: `[异常] 进程退出 (退出码 ${data.code})` });
              }
              clearInterval(timer);
              emit('completed');
            } else if (data.type === 'error') {
              status.value = 'error';
              logs.value.push({ id: Date.now(), type: 'stderr', text: `[系统错误] ${data.text}` });
              clearInterval(timer);
            }
            scrollToBottom();
          } catch (e) {
            // ignore parse err
          }
        }
      }
    }
  } catch (err: any) {
    if (err.name === 'AbortError') {
      logs.value.push({ id: Date.now(), type: 'system', text: '[系统] 用户已手动中止执行' });
      status.value = 'stopped';
    } else {
      logs.value.push({ id: Date.now(), type: 'stderr', text: `[网络异常] ${err.message}` });
      status.value = 'error';
    }
  } finally {
    clearInterval(timer);
  }
};

const killExecution = async () => {
  if (status.value !== 'running') return;
  try {
    logs.value.push({ id: Date.now(), type: 'system', text: '[系统] 正在发送终止信号 (SIGTERM/taskkill)...' });
    await fetch('/api/kill-tool', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ runId })
    });
    if (abortController) {
      abortController.abort();
    }
    status.value = 'stopped';
  } catch (e: any) {
    logs.value.push({ id: Date.now(), type: 'stderr', text: `[终止失败] ${e.message}` });
  }
};

const copyLogs = () => {
  const fullText = logs.value.map(l => l.text).join('\n');
  navigator.clipboard.writeText(fullText);
  copied.value = true;
  setTimeout(() => { copied.value = false; }, 2000);
};

const handleClose = () => {
  if (status.value === 'running') {
    if (!confirm('工具仍在后台执行中，确定要关闭窗口吗？')) {
      return;
    }
    killExecution();
  }
  emit('close');
};

watch(() => props.show, (newVal) => {
  if (newVal) {
    startExecution();
  } else {
    clearInterval(timer);
  }
});

onUnmounted(() => {
  clearInterval(timer);
});
</script>

<template>
  <div v-if="show" class="console-backdrop" @click.self="handleClose">
    <div class="console-window">
      <!-- Terminal Header -->
      <div class="console-header">
        <div class="header-left">
          <div class="window-dots">
            <span class="dot dot-red" @click="handleClose" title="关闭"></span>
            <span class="dot dot-yellow" @click="killExecution" title="中断"></span>
            <span class="dot dot-green"></span>
          </div>
          <span class="console-title">
            🖥️ {{ tool?.name || '终端控制台' }}
            <span v-if="action" class="action-tag">--{{ action }}</span>
          </span>
        </div>

        <div class="header-right">
          <span class="status-indicator" :class="status">
            <span class="status-dot"></span>
            {{ status === 'running' ? '执行中...' : (status === 'success' ? '运行成功' : (status === 'error' ? '运行失败' : '已中止')) }}
          </span>
          <span class="timer-badge">{{ duration }}s</span>
          <button class="close-icon-btn" @click="handleClose">✕</button>
        </div>
      </div>

      <!-- Command Ribbon -->
      <div v-if="executedCommand" class="command-ribbon">
        <span class="prompt-sign">$</span>
        <code>{{ executedCommand }}</code>
      </div>

      <!-- Terminal Body -->
      <div ref="terminalBody" class="terminal-body custom-scroll">
        <div v-for="log in logs" :key="log.id" class="log-line" :class="'log-' + log.type">
          <pre>{{ log.text }}</pre>
        </div>
        <div v-if="status === 'running'" class="running-cursor">
          <span class="cursor-block"></span>
        </div>
      </div>

      <!-- Terminal Footer Toolbar -->
      <div class="console-footer">
        <div class="footer-left-info">
          <span v-if="status === 'running'" class="hint-text">💡 提示：长时间任务可随时点击右侧「终止」强行掐断。</span>
          <span v-else class="hint-text">✓ 执行完毕，产物变动已自动感应并刷新看板。</span>
        </div>

        <div class="footer-actions">
          <button class="btn-tool" @click="copyLogs">
            {{ copied ? '✓ 已复制全部日志' : '📋 复制日志' }}
          </button>
          <button 
            v-if="status === 'running'" 
            class="btn-tool btn-danger" 
            @click="killExecution"
          >
            ⏹️ 终止运行 (Kill)
          </button>
          <button 
            v-else 
            class="btn-tool btn-primary" 
            @click="handleClose"
          >
            完成并关闭
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.console-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.65);
  backdrop-filter: blur(8px);
  z-index: 1100;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1.5rem;
}

.console-window {
  width: 100%;
  max-width: 900px;
  height: 80vh;
  max-height: 680px;
  background: #0f172a;
  border-radius: 0.85rem;
  border: 1px solid rgba(255, 255, 255, 0.12);
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.6);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  color: #f8fafc;
  font-family: var(--font-mono, 'JetBrains Mono', 'Fira Code', monospace);
}

.console-header {
  height: 44px;
  background: #1e293b;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 1rem;
  user-select: none;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 0.85rem;
}

.window-dots {
  display: flex;
  gap: 6px;
}

.dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  cursor: pointer;
  transition: opacity 0.2s;
}

.dot-red { background: #ef4444; }
.dot-yellow { background: #f59e0b; }
.dot-green { background: #10b981; }
.dot:hover { opacity: 0.8; }

.console-title {
  font-size: 0.82rem;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.action-tag {
  background: rgba(56, 189, 248, 0.2);
  color: #38bdf8;
  padding: 0.1rem 0.4rem;
  border-radius: 4px;
  font-size: 0.75rem;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.75rem;
  padding: 0.2rem 0.55rem;
  border-radius: 9999px;
  background: rgba(255, 255, 255, 0.08);
}

.status-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
}

.status-indicator.running .status-dot {
  background: #38bdf8;
  box-shadow: 0 0 8px #38bdf8;
  animation: pulse 1.5s infinite;
}
.status-indicator.running { color: #38bdf8; }

.status-indicator.success .status-dot { background: #10b981; }
.status-indicator.success { color: #10b981; }

.status-indicator.error .status-dot { background: #ef4444; }
.status-indicator.error { color: #ef4444; }

.status-indicator.stopped .status-dot { background: #94a3b8; }
.status-indicator.stopped { color: #94a3b8; }

@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.4; transform: scale(1.2); }
}

.timer-badge {
  font-size: 0.75rem;
  opacity: 0.6;
}

.close-icon-btn {
  background: transparent;
  border: none;
  color: #94a3b8;
  font-size: 1rem;
  cursor: pointer;
  padding: 0.2rem;
}
.close-icon-btn:hover { color: #f8fafc; }

.command-ribbon {
  background: #090d16;
  padding: 0.45rem 1rem;
  font-size: 0.78rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.prompt-sign {
  color: #10b981;
  font-weight: 700;
}

.command-ribbon code {
  color: #94a3b8;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.terminal-body {
  flex: 1;
  padding: 1rem;
  background: #020617;
  overflow-y: auto;
  font-size: 0.85rem;
  line-height: 1.5;
}

.log-line pre {
  margin: 0;
  font-family: inherit;
  white-space: pre-wrap;
  word-break: break-all;
}

.log-system { color: #38bdf8; }
.log-stdout { color: #e2e8f0; }
.log-stderr { color: #f87171; }

.running-cursor {
  display: inline-block;
  margin-top: 4px;
}

.cursor-block {
  display: inline-block;
  width: 8px;
  height: 15px;
  background: #38bdf8;
  animation: blink 1s step-end infinite;
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}

.console-footer {
  height: 52px;
  background: #1e293b;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 1rem;
}

.hint-text {
  font-size: 0.75rem;
  color: #94a3b8;
}

.footer-actions {
  display: flex;
  gap: 0.6rem;
}

.btn-tool {
  padding: 0.4rem 0.85rem;
  font-size: 0.78rem;
  border-radius: 0.4rem;
  border: 1px solid rgba(255, 255, 255, 0.15);
  background: rgba(255, 255, 255, 0.08);
  color: #f8fafc;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-tool:hover {
  background: rgba(255, 255, 255, 0.15);
}

.btn-danger {
  background: rgba(239, 68, 68, 0.2);
  border-color: rgba(239, 68, 68, 0.4);
  color: #fca5a5;
}
.btn-danger:hover {
  background: rgba(239, 68, 68, 0.35);
}

.btn-primary {
  background: #0284c7;
  border-color: #0284c7;
  color: #fff;
}
.btn-primary:hover {
  background: #0369a1;
}

.custom-scroll::-webkit-scrollbar {
  width: 6px;
}
.custom-scroll::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.15);
  border-radius: 4px;
}
</style>
