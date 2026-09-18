<script setup lang="ts">
import { ref } from 'vue';

const props = defineProps<{
  tool: any;
}>();

const emit = defineEmits<{
  (e: 'select', tool: any): void;
  (e: 'view-report', tool: any): void;
}>();

const copied = ref(false);

const copyCommand = (e: Event) => {
  e.stopPropagation();
  navigator.clipboard.writeText(props.tool.cliCommand);
  copied.value = true;
  setTimeout(() => {
    copied.value = false;
  }, 2000);
};
</script>

<template>
  <div class="tool-card" @click="emit('select', tool)">
    <!-- Header -->
    <div class="card-top">
      <div class="category-meta">
        <span class="cat-icon">{{ tool.categoryIcon }}</span>
        <span 
          class="cat-name" 
          :style="{ backgroundColor: tool.categoryColor + '18', color: tool.categoryColor }"
        >
          {{ tool.categoryLabel }}
        </span>
      </div>

      <div class="status-indicator" :class="tool.isConfigured ? 'configured' : 'need-config'">
        <span class="status-dot"></span>
        <span class="status-text">{{ tool.isConfigured ? '已就绪' : '首次向导' }}</span>
      </div>
    </div>

    <!-- Title & Description -->
    <h3 class="tool-title">{{ tool.name }}</h3>
    <p class="tool-desc">{{ tool.description }}</p>

    <!-- CLI Command snippet -->
    <div class="card-cli" @click="copyCommand">
      <span class="prompt">$</span>
      <span class="cli-cmd">{{ tool.cliCommand }}</span>
      <button class="copy-icon-btn" :title="copied ? '已复制' : '复制运行命令'">
        {{ copied ? '✓' : '⧉' }}
      </button>
    </div>

    <!-- Tags row (自适应展开标签，彻底释放空间) -->
    <div class="tags-row" v-if="tool.hasOutputs || (tool.configKeys && tool.configKeys.length)">
      <span v-if="tool.hasOutputs" class="tag-badge output">
        📊 有最新产物
      </span>
      <span v-if="tool.configKeys && tool.configKeys.length" class="tag-badge config">
        🔑 {{ tool.configKeys.length }} 项配置
      </span>
    </div>

    <!-- Card Bottom (操作按钮栏，保证单行完整呈现) -->
    <div class="card-bottom">
      <div class="card-extra-info">
        <span class="tool-folder-text">📂 {{ tool.folderName }}</span>
      </div>

      <div class="action-buttons">
        <button 
          v-if="tool.hasOutputs" 
          class="btn-subtle" 
          @click.stop="emit('view-report', tool)"
        >
          查看产物
        </button>
        <button class="btn-primary" @click.stop="emit('select', tool)">
          说明与详情 →
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.tool-card {
  background: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 24px;
  display: flex;
  flex-direction: column;
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
  cursor: pointer;
  position: relative;
  overflow: hidden;
  backdrop-filter: blur(12px);
  box-shadow: var(--shadow-sm);
}

.tool-card:hover {
  transform: translateY(-5px);
  background: var(--bg-surface-hover);
  border-color: var(--border-hover);
  box-shadow: var(--shadow-lg);
}

.card-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 14px;
}

.category-meta {
  display: flex;
  align-items: center;
  gap: 8px;
}
.cat-icon {
  font-size: 20px;
}
.cat-name {
  font-size: 11px;
  font-weight: 700;
  padding: 3px 10px;
  border-radius: var(--radius-full);
  white-space: nowrap;
  flex-shrink: 0;
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  font-weight: 600;
  padding: 3px 10px;
  border-radius: var(--radius-full);
  white-space: nowrap;
  flex-shrink: 0;
}
.status-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  flex-shrink: 0;
}
.status-indicator.configured {
  color: #10b981;
  background: rgba(16, 185, 129, 0.08);
}
.status-indicator.configured .status-dot {
  background: #10b981;
  box-shadow: 0 0 8px rgba(16, 185, 129, 0.4);
}
.status-indicator.need-config {
  color: #f59e0b;
  background: rgba(245, 158, 11, 0.08);
}
.status-indicator.need-config .status-dot {
  background: #f59e0b;
}

.tool-title {
  font-size: 16px;
  font-weight: 750;
  color: var(--text-main);
  margin-bottom: 8px;
  line-height: 1.4;
}

.tool-desc {
  font-size: 13px;
  color: var(--text-muted);
  line-height: 1.65;
  margin-bottom: 16px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  min-height: 42px;
}

/* 软萌温润的命令行小框 (无压迫感浅底) */
.card-cli {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  padding: 7px 12px;
  border-radius: var(--radius-md);
  font-family: var(--font-mono);
  font-size: 12px;
  margin-bottom: 14px;
  transition: all 0.2s;
}
.card-cli:hover {
  border-color: var(--border-hover);
  background: var(--bg-surface-hover);
}
.prompt {
  color: var(--accent-primary);
  font-weight: 700;
  margin-right: 8px;
  font-size: 11px;
}
.cli-cmd {
  color: var(--text-main);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
}
.copy-icon-btn {
  background: transparent;
  border: none;
  color: var(--text-dim);
  cursor: pointer;
  padding: 2px 6px;
  font-size: 12px;
  transition: color 0.2s;
}
.copy-icon-btn:hover {
  color: var(--accent-primary);
}

/* 独立成行的标签区 */
.tags-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
}
.tag-badge {
  font-size: 11px;
  font-weight: 600;
  padding: 3px 10px;
  border-radius: var(--radius-full);
  white-space: nowrap;
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
}
.tag-badge.output {
  background: rgba(16, 185, 129, 0.08);
  color: #10b981;
}
.tag-badge.config {
  background: rgba(239, 68, 68, 0.08);
  color: var(--accent-primary);
}

/* 底部操作行 */
.card-bottom {
  margin-top: auto;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 14px;
  border-top: 1px solid var(--border-color);
  gap: 12px;
}

.card-extra-info {
  font-size: 11px;
  color: var(--text-dim);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.tool-folder-text {
  opacity: 0.75;
}

.action-buttons {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-left: auto;
  flex-shrink: 0;
}
.btn-subtle {
  background: transparent;
  border: 1px solid var(--border-color);
  color: var(--text-muted);
  font-size: 12px;
  font-weight: 600;
  padding: 6px 13px;
  border-radius: var(--radius-full);
  cursor: pointer;
  white-space: nowrap;
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  transition: all 0.2s;
}
.btn-subtle:hover {
  background: var(--bg-surface-hover);
  color: var(--text-main);
  border-color: var(--border-hover);
}

.btn-primary {
  background: var(--accent-gradient);
  color: #fff;
  border: none;
  font-size: 12px;
  font-weight: 600;
  padding: 7px 16px;
  border-radius: var(--radius-full);
  cursor: pointer;
  white-space: nowrap;
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  box-shadow: 0 3px 10px var(--accent-glow);
  transition: opacity 0.2s, transform 0.15s;
}
.btn-primary:hover {
  opacity: 0.92;
  transform: translateY(-1px);
}
.btn-primary:active {
  transform: scale(0.96);
}
</style>
