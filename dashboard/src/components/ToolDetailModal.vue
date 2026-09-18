<script setup lang="ts">
import { ref, computed } from 'vue';
import { marked } from 'marked';
import SteamDealsPreview from './SteamDealsPreview.vue';

const props = defineProps<{
  tool: any;
  show: boolean;
}>();

const emit = defineEmits<{
  (e: 'close'): void;
}>();

const activeTab = ref<'readme' | 'report' | 'config'>('readme');
const copied = ref(false);

const renderedMarkdown = computed(() => {
  if (!props.tool || !props.tool.readmeMarkdown) return '';
  return marked.parse(props.tool.readmeMarkdown);
});

const copyCommand = () => {
  if (!props.tool?.cliCommand) return;
  navigator.clipboard.writeText(props.tool.cliCommand);
  copied.value = true;
  setTimeout(() => {
    copied.value = false;
  }, 2000);
};
</script>

<template>
  <div v-if="show && tool" class="modal-backdrop" @click.self="emit('close')">
    <div class="modal-card">
      <!-- Modal Header -->
      <div class="modal-header">
        <div class="tool-title-meta">
          <span class="tool-cat-icon">{{ tool.categoryIcon }}</span>
          <div>
            <div class="meta-sub-row">
              <span class="cat-pill" :style="{ backgroundColor: tool.categoryColor + '20', color: tool.categoryColor }">
                {{ tool.categoryLabel }}
              </span>
              <span class="tool-status-pill" :class="tool.isConfigured ? 'ready' : 'wizard'">
                {{ tool.isConfigured ? '● 配置就绪' : '○ 需首次配置' }}
              </span>
            </div>
            <h3 class="modal-title">{{ tool.name }}</h3>
          </div>
        </div>

        <button class="close-btn" @click="emit('close')" aria-label="关闭">✕</button>
      </div>

      <!-- Quick Command Bar -->
      <div class="cli-bar">
        <div class="cli-text">
          <span class="cli-prompt">$</span>
          <code>{{ tool.cliCommand }}</code>
        </div>
        <button class="copy-btn" @click="copyCommand">
          {{ copied ? '✓ 已复制' : '复制命令' }}
        </button>
      </div>

      <!-- Tab Switcher -->
      <div class="tab-nav">
        <button 
          class="tab-btn" 
          :class="{ active: activeTab === 'readme' }"
          @click="activeTab = 'readme'"
        >
          📖 使用说明 (README)
        </button>
        <button 
          v-if="tool.hasOutputs"
          class="tab-btn" 
          :class="{ active: activeTab === 'report' }"
          @click="activeTab = 'report'"
        >
          📊 最新运行产物 (Report)
        </button>
        <button 
          class="tab-btn" 
          :class="{ active: activeTab === 'config' }"
          @click="activeTab = 'config'"
        >
          ⚙️ 配置清单 (Config)
        </button>
      </div>

      <!-- Tab Content Area -->
      <div class="modal-body custom-scroll">
        <!-- Tab 1: Readme -->
        <div v-if="activeTab === 'readme'" class="markdown-body" v-html="renderedMarkdown"></div>

        <!-- Tab 2: Live Report -->
        <div v-else-if="activeTab === 'report'" class="report-body">
          <SteamDealsPreview v-if="tool.latestDeals" :dealsData="tool.latestDeals" />
          <div v-else class="generic-outputs">
            <h4 class="output-title">📁 本地产物文件 (output/)</h4>
            <ul class="file-list">
              <li v-for="file in tool.outputFiles" :key="file" class="file-item">
                <span class="file-icon">📄</span>
                <span class="file-name">{{ file }}</span>
              </li>
            </ul>
          </div>
        </div>

        <!-- Tab 3: Config -->
        <div v-else-if="activeTab === 'config'" class="config-body">
          <div class="config-info-card">
            <h4>💡 配置规范说明</h4>
            <p>本工具采用标准的 <code>config.json</code> 本地配置文件进行管理，免除操作系统环境变量配置。未创建时首次运行会自动弹出终端向导。</p>
          </div>

          <div class="config-keys-box">
            <h4>需要配置的字段项 (来自 config.example.json)</h4>
            <div v-if="tool.configKeys && tool.configKeys.length" class="keys-grid">
              <div v-for="key in tool.configKeys" :key="key" class="key-pill">
                <code>{{ key }}</code>
              </div>
            </div>
            <p v-else class="empty-hint">本工具无需任何复杂外部配置即可开箱即用。</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(30, 20, 22, 0.45);
  backdrop-filter: blur(10px);
  z-index: 999;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}

.modal-card {
  width: 95%;
  max-width: 1260px;
  height: 90vh;
  max-height: 90vh;
  background: var(--bg-surface-hover);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-lg);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  animation: modalIn 0.25s cubic-bezier(0.16, 1, 0.3, 1);
}

@keyframes modalIn {
  from {
    opacity: 0;
    transform: scale(0.95) translateY(10px);
  }
  to {
    opacity: 1;
    transform: scale(1) translateY(0);
  }
}

.modal-header {
  padding: 22px 28px;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  border-bottom: 1px solid var(--border-color);
  background: var(--bg-card-header);
}

.tool-title-meta {
  display: flex;
  align-items: center;
  gap: 16px;
}

.tool-cat-icon {
  font-size: 34px;
}

.meta-sub-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.cat-pill {
  font-size: 11px;
  font-weight: 700;
  padding: 3px 10px;
  border-radius: var(--radius-full);
  white-space: nowrap;
  flex-shrink: 0;
}

.tool-status-pill {
  font-size: 11px;
  font-weight: 600;
  padding: 3px 10px;
  border-radius: var(--radius-full);
  white-space: nowrap;
  flex-shrink: 0;
}
.tool-status-pill.ready {
  background: rgba(16, 185, 129, 0.1);
  color: #10b981;
}
.tool-status-pill.wizard {
  background: rgba(245, 158, 11, 0.1);
  color: #f59e0b;
}

.modal-title {
  font-size: 19px;
  font-weight: 750;
  color: var(--text-main);
}

.close-btn {
  background: var(--bg-surface);
  border: 1px solid var(--border-color);
  color: var(--text-muted);
  width: 34px;
  height: 34px;
  border-radius: var(--radius-full);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  font-size: 14px;
  box-shadow: var(--shadow-sm);
  flex-shrink: 0;
  transition: all 0.2s cubic-bezier(0.34, 1.56, 0.64, 1);
}
.close-btn:hover {
  background: var(--bg-surface-hover);
  color: var(--text-main);
  transform: rotate(90deg);
}

/* 舒缓暖底 CLI 提示栏 */
.cli-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 28px;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-color);
  gap: 12px;
}

.cli-text {
  display: flex;
  align-items: center;
  gap: 8px;
  font-family: var(--font-mono);
  font-size: 13px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.cli-prompt {
  color: var(--accent-primary);
  font-weight: 700;
}
.cli-text code {
  color: var(--text-main);
}

.copy-btn {
  background: var(--accent-gradient);
  color: #fff;
  border: none;
  padding: 6px 14px;
  border-radius: var(--radius-full);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
  flex-shrink: 0;
  box-shadow: 0 2px 8px var(--accent-glow);
  transition: opacity 0.2s, transform 0.1s;
}
.copy-btn:hover {
  opacity: 0.92;
  transform: translateY(-1px);
}

.tab-nav {
  display: flex;
  gap: 10px;
  padding: 12px 28px 0;
  background: var(--bg-card-header);
  border-bottom: 1px solid var(--border-color);
}

.tab-btn {
  background: transparent;
  border: none;
  border-bottom: 2.5px solid transparent;
  padding: 9px 18px;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-muted);
  cursor: pointer;
  white-space: nowrap;
  flex-shrink: 0;
  transition: all 0.2s;
}
.tab-btn:hover {
  color: var(--text-main);
}
.tab-btn.active {
  color: var(--accent-primary);
  border-bottom-color: var(--accent-primary);
}

.modal-body {
  padding: 28px;
  overflow-y: auto;
  flex: 1;
  scroll-behavior: smooth;
}

/* 舒缓可爱的 Markdown 排版 */
.markdown-body :deep(h1) {
  font-size: 22px;
  margin-bottom: 14px;
  border-bottom: 1px solid var(--border-color);
  padding-bottom: 10px;
  color: var(--text-main);
  font-weight: 750;
}
.markdown-body :deep(h2) {
  font-size: 17px;
  margin: 22px 0 10px;
  color: var(--text-main);
  font-weight: 700;
}
.markdown-body :deep(p) {
  margin-bottom: 14px;
  color: var(--text-muted);
  font-size: 14px;
  line-height: 1.75;
}
/* 告别冷酷黑底，采用温润无压代码卡片 */
.markdown-body :deep(pre) {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  color: var(--text-main);
  padding: 16px 18px;
  border-radius: var(--radius-md);
  overflow-x: auto;
  margin-bottom: 16px;
  font-family: var(--font-mono);
  font-size: 13px;
  line-height: 1.6;
}
.markdown-body :deep(code) {
  background: rgba(239, 68, 68, 0.08);
  color: var(--accent-primary);
  padding: 3px 8px;
  border-radius: var(--radius-sm);
  font-family: var(--font-mono);
  font-size: 13px;
}
.markdown-body :deep(pre code) {
  background: transparent;
  color: inherit;
  padding: 0;
}
.markdown-body :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin-bottom: 18px;
  border-radius: var(--radius-md);
  overflow: hidden;
}
.markdown-body :deep(th),
.markdown-body :deep(td) {
  border: 1px solid var(--border-color);
  padding: 10px 14px;
  font-size: 13px;
  text-align: left;
}
.markdown-body :deep(th) {
  background: var(--bg-card-header);
  font-weight: 650;
}

.config-body {
  display: flex;
  flex-direction: column;
  gap: 20px;
}
.config-info-card {
  background: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 18px 20px;
  box-shadow: var(--shadow-sm);
}
.config-info-card h4 {
  font-size: 14px;
  font-weight: 750;
  margin-bottom: 6px;
}
.config-info-card p {
  font-size: 13px;
  color: var(--text-muted);
  line-height: 1.6;
}
.config-keys-box h4 {
  font-size: 14px;
  font-weight: 750;
  margin-bottom: 12px;
}
.keys-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}
.key-pill {
  background: var(--bg-surface);
  border: 1px solid var(--border-color);
  padding: 7px 14px;
  border-radius: var(--radius-full);
  font-size: 13px;
  box-shadow: var(--shadow-sm);
}
.empty-hint {
  font-size: 13px;
  color: var(--text-dim);
}

.file-list {
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 12px;
}
.file-item {
  display: flex;
  align-items: center;
  gap: 12px;
  background: var(--bg-surface);
  border: 1px solid var(--border-color);
  padding: 12px 16px;
  border-radius: var(--radius-md);
  font-size: 13px;
  box-shadow: var(--shadow-sm);
}
</style>
