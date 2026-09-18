<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import rawManifest from './data/tools-manifest.json';
import ToolCard from './components/ToolCard.vue';
import ToolDetailModal from './components/ToolDetailModal.vue';

// Theme Management (默认采用清新的樱花粉亮色模式)
const isDarkMode = ref(false);

const toggleTheme = () => {
  isDarkMode.value = !isDarkMode.value;
  document.documentElement.setAttribute('data-theme', isDarkMode.value ? 'dark' : 'light');
  localStorage.setItem('pat_theme', isDarkMode.value ? 'dark' : 'light');
};

onMounted(() => {
  const saved = localStorage.getItem('pat_theme');
  if (saved) {
    isDarkMode.value = saved === 'dark';
  } else {
    isDarkMode.value = false; // 默认清新粉色亮色
  }
  document.documentElement.setAttribute('data-theme', isDarkMode.value ? 'dark' : 'light');
});

// Data & Filter State
const manifest = ref(rawManifest);
const selectedCategory = ref<string>('all');
const searchQuery = ref<string>('');

// Modal State
const activeModalTool = ref<any>(null);
const showModal = ref(false);

const filteredTools = computed(() => {
  let list = manifest.value.tools || [];

  if (selectedCategory.value !== 'all') {
    list = list.filter(t => t.category === selectedCategory.value);
  }

  if (searchQuery.value.trim()) {
    const q = searchQuery.value.trim().toLowerCase();
    list = list.filter(t => 
      t.name.toLowerCase().includes(q) || 
      t.description.toLowerCase().includes(q) ||
      t.folderName.toLowerCase().includes(q)
    );
  }

  return list;
});

const totalOutputsCount = computed(() => {
  return (manifest.value.tools || []).reduce((acc, t) => acc + (t.outputFiles ? t.outputFiles.length : 0), 0);
});

const openToolModal = (tool: any) => {
  activeModalTool.value = tool;
  showModal.value = true;
};

const openToolReport = (tool: any) => {
  activeModalTool.value = tool;
  showModal.value = true;
  // Modal 内部默认切至 report
};

const isRefreshing = ref(false);

const handleManualRescan = async () => {
  isRefreshing.value = true;
  try {
    const res = await fetch('/api/rescan');
    if (res.ok) {
      const data = await res.json();
      if (data.manifest) {
        manifest.value = data.manifest;
      }
    }
  } catch (e) {
    console.error('Rescan failed:', e);
  } finally {
    setTimeout(() => {
      isRefreshing.value = false;
    }, 500);
  }
};

const formatTime = (iso: string) => {
  if (!iso) return '刚刚';
  const d = new Date(iso);
  return `${d.getMonth() + 1}月${d.getDate()}日 ${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`;
};
</script>

<template>
  <div class="app-root">
    <!-- Ambient Lighting Effect -->
    <div class="ambient-glow"></div>

    <div class="app-container">
      <!-- Top Navigation Header -->
      <header class="navbar">
        <div class="brand-group">
          <div class="brand-icon-wrap">🌸</div>
          <div>
            <div class="brand-sub">Personal AI Toolkit</div>
            <h1 class="brand-title">个人 AI 能力库 · 控制台看板</h1>
          </div>
        </div>

        <div class="nav-actions">
          <div class="sync-badge" :title="`上次扫描于: ${manifest.scannedAt}`">
            <span class="pulse-dot"></span>
            同步时间: {{ formatTime(manifest.scannedAt) }}
          </div>
          <button 
            class="refresh-btn" 
            :class="{ spinning: isRefreshing }"
            @click="handleManualRescan"
            title="手动刷新检测 tools 目录最新产物"
          >
            <span class="refresh-icon">🔄</span>
            <span>{{ isRefreshing ? '扫描中...' : '刷新状态' }}</span>
          </button>
          <button class="theme-toggle-btn" @click="toggleTheme" :title="isDarkMode ? '切换至亮色模式' : '切换至暗色模式'">
            {{ isDarkMode ? '☀️' : '🌙' }}
          </button>
        </div>
      </header>

      <!-- Metric Stats Overview Bar -->
      <section class="metrics-grid">
        <div class="metric-card">
          <div class="metric-icon">📦</div>
          <div>
            <div class="metric-num">{{ manifest.totalTools }}</div>
            <div class="metric-label">收录原子工具</div>
          </div>
        </div>
        <div class="metric-card">
          <div class="metric-icon">🏷️</div>
          <div>
            <div class="metric-num">5</div>
            <div class="metric-label">预设应用领域</div>
          </div>
        </div>
        <div class="metric-card">
          <div class="metric-icon">📈</div>
          <div>
            <div class="metric-num">{{ totalOutputsCount }}</div>
            <div class="metric-label">沉淀输出产物</div>
          </div>
        </div>
        <div class="metric-card highlight">
          <div class="metric-icon">🤖</div>
          <div>
            <div class="metric-num">AI-Ready</div>
            <div class="metric-label">统一工程标准 7 要素</div>
          </div>
        </div>
      </section>

      <!-- Filter and Search Bar -->
      <section class="filter-bar">
        <!-- Categories Pills -->
        <div class="category-pills">
          <button 
            class="pill-btn" 
            :class="{ active: selectedCategory === 'all' }"
            @click="selectedCategory = 'all'"
          >
            全部工具 <span class="pill-count">{{ manifest.totalTools }}</span>
          </button>
          <button 
            v-for="cat in manifest.categories" 
            :key="cat.key"
            class="pill-btn"
            :class="{ active: selectedCategory === cat.key }"
            @click="selectedCategory = cat.key"
          >
            <span class="cat-pill-icon">{{ cat.icon }}</span>
            {{ cat.label }}
            <span class="pill-count" v-if="cat.count">{{ cat.count }}</span>
          </button>
        </div>

        <!-- Search Input -->
        <div class="search-wrap">
          <span class="search-icon">🔍</span>
          <input 
            v-model="searchQuery" 
            type="text" 
            placeholder="搜索工具名称、功能或文件名..." 
            class="search-input"
            id="tool-search-input"
          />
          <button v-if="searchQuery" class="clear-btn" @click="searchQuery = ''">✕</button>
        </div>
      </section>

      <!-- Tools Grid -->
      <main class="tools-section">
        <div v-if="filteredTools.length" class="tools-grid">
          <ToolCard 
            v-for="tool in filteredTools" 
            :key="tool.id" 
            :tool="tool" 
            @select="openToolModal"
            @view-report="openToolReport"
          />
        </div>

        <!-- Empty State -->
        <div v-else class="empty-state">
          <div class="empty-icon">📂</div>
          <h3 class="empty-title">未找到匹配的工具</h3>
          <p class="empty-desc">尝试更换搜索词或选择其他领域分类标签</p>
          <button class="empty-reset-btn" @click="selectedCategory = 'all'; searchQuery = ''">重置所有筛选</button>
        </div>
      </main>

      <!-- Footer -->
      <footer class="app-footer">
        <p>Personal AI Toolkit · 面向长期维护的个人 AI 能力库与工作流中心</p>
        <p class="footer-sub">遵循解耦自包含规范 · 人类与各类 AI 编码助手双向友好</p>
      </footer>
    </div>

    <!-- Tool Detail / Report Modal -->
    <ToolDetailModal 
      :tool="activeModalTool" 
      :show="showModal" 
      @close="showModal = false" 
    />
  </div>
</template>

<style scoped>
.app-root {
  min-height: 100vh;
  position: relative;
}

/* Navbar (舒心圆润顶部导航) */
.navbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 32px;
  padding-bottom: 22px;
  border-bottom: 1px solid var(--border-color);
}

.brand-group {
  display: flex;
  align-items: center;
  gap: 16px;
}

.brand-icon-wrap {
  width: 48px;
  height: 48px;
  border-radius: var(--radius-md);
  background: var(--bg-surface-hover);
  border: 1.5px solid rgba(239, 68, 68, 0.2);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 26px;
  box-shadow: 0 4px 16px rgba(239, 68, 68, 0.08), inset 0 1px 2px rgba(255, 255, 255, 0.9);
  transition: transform 0.3s cubic-bezier(0.34, 1.56, 0.64, 1), border-color 0.2s ease, box-shadow 0.2s ease;
  cursor: default;
}
.brand-icon-wrap:hover {
  transform: scale(1.1) rotate(6deg);
  border-color: var(--accent-primary);
  box-shadow: 0 6px 20px rgba(239, 68, 68, 0.16);
}

.brand-sub {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--accent-primary);
  margin-bottom: 2px;
}

.brand-title {
  font-size: 20px;
  font-weight: 750;
  color: var(--text-main);
  letter-spacing: -0.01em;
  white-space: nowrap;
}

.nav-actions {
  display: flex;
  align-items: center;
  gap: 14px;
  flex-shrink: 0;
}

.sync-badge {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--text-muted);
  background: var(--bg-surface);
  border: 1px solid var(--border-color);
  padding: 7px 14px;
  border-radius: var(--radius-full);
  box-shadow: var(--shadow-sm);
  white-space: nowrap;
  flex-shrink: 0;
  transition: all 0.2s ease;
}
.sync-badge:hover {
  border-color: var(--border-hover);
}

.pulse-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #10b981;
  box-shadow: 0 0 10px rgba(16, 185, 129, 0.5);
  flex-shrink: 0;
}

.refresh-btn {
  background: var(--bg-surface);
  border: 1px solid var(--border-color);
  color: var(--text-muted);
  font-size: 12px;
  font-weight: 600;
  padding: 7px 14px;
  border-radius: var(--radius-full);
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  box-shadow: var(--shadow-sm);
  white-space: nowrap;
  flex-shrink: 0;
  transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
}
.refresh-btn:hover {
  background: var(--bg-surface-hover);
  color: var(--text-main);
  border-color: var(--border-hover);
  transform: translateY(-1px);
}
.refresh-btn.spinning {
  opacity: 0.75;
  pointer-events: none;
}
.refresh-btn.spinning .refresh-icon {
  animation: spinIcon 0.8s linear infinite;
  display: inline-block;
}
@keyframes spinIcon {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.theme-toggle-btn {
  background: var(--bg-surface);
  border: 1px solid var(--border-color);
  color: var(--text-main);
  width: 40px;
  height: 40px;
  border-radius: var(--radius-full);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  font-size: 17px;
  box-shadow: var(--shadow-sm);
  flex-shrink: 0;
  transition: all 0.25s cubic-bezier(0.34, 1.56, 0.64, 1);
}
.theme-toggle-btn:hover {
  background: var(--bg-surface-hover);
  border-color: var(--border-hover);
  transform: scale(1.08) rotate(15deg);
  box-shadow: var(--shadow-md);
}

/* Metrics Section (软萌面包卡片) */
.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 18px;
  margin-bottom: 34px;
}

.metric-card {
  background: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 20px 22px;
  display: flex;
  align-items: center;
  gap: 16px;
  backdrop-filter: blur(12px);
  box-shadow: var(--shadow-sm);
  transition: transform 0.25s cubic-bezier(0.16, 1, 0.3, 1), border-color 0.2s ease, box-shadow 0.25s ease;
}
.metric-card:hover {
  transform: translateY(-3px);
  border-color: var(--border-hover);
  box-shadow: var(--shadow-md);
}
.metric-card.highlight {
  background: linear-gradient(135deg, rgba(254, 226, 226, 0.45) 0%, rgba(254, 202, 202, 0.2) 100%);
  border-color: rgba(239, 68, 68, 0.22);
}

.metric-icon {
  font-size: 26px;
  width: 46px;
  height: 46px;
  border-radius: var(--radius-md);
  background: var(--bg-card-header);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.metric-num {
  font-size: 22px;
  font-weight: 750;
  color: var(--text-main);
  line-height: 1.2;
  white-space: nowrap;
}
.metric-label {
  font-size: 12px;
  color: var(--text-muted);
  font-weight: 500;
  margin-top: 2px;
  white-space: nowrap;
}

/* Filter Bar (胶囊按钮与圆润搜索框) */
.filter-bar {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  margin-bottom: 26px;
}

.category-pills {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.pill-btn {
  background: var(--bg-surface);
  border: 1px solid var(--border-color);
  color: var(--text-muted);
  padding: 8px 16px;
  border-radius: var(--radius-full);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 7px;
  box-shadow: var(--shadow-sm);
  white-space: nowrap;
  flex-shrink: 0;
  transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
}
.pill-btn:hover {
  color: var(--text-main);
  background: var(--bg-surface-hover);
  border-color: var(--border-hover);
  transform: translateY(-1px);
}
.pill-btn.active {
  background: var(--accent-gradient);
  color: #ffffff;
  border-color: transparent;
  box-shadow: 0 4px 14px var(--accent-glow);
  transform: translateY(-1px);
}

.cat-pill-icon {
  font-size: 15px;
  flex-shrink: 0;
}
.pill-count {
  font-size: 11px;
  background: rgba(0, 0, 0, 0.08);
  padding: 2px 7px;
  border-radius: var(--radius-full);
  white-space: nowrap;
  flex-shrink: 0;
}
.pill-btn.active .pill-count {
  background: rgba(255, 255, 255, 0.25);
  color: #ffffff;
}

.search-wrap {
  position: relative;
  min-width: 280px;
}
.search-icon {
  position: absolute;
  left: 14px;
  top: 50%;
  transform: translateY(-50%);
  font-size: 14px;
  color: var(--text-dim);
  pointer-events: none;
}
.search-input {
  width: 100%;
  background: var(--bg-surface);
  border: 1px solid var(--border-color);
  padding: 10px 36px 10px 38px;
  border-radius: var(--radius-full);
  font-size: 13px;
  color: var(--text-main);
  outline: none;
  box-shadow: var(--shadow-sm);
  transition: all 0.25s ease;
}
.search-input:focus {
  border-color: var(--accent-primary);
  box-shadow: 0 0 0 4px var(--accent-glow);
}
.clear-btn {
  position: absolute;
  right: 14px;
  top: 50%;
  transform: translateY(-50%);
  background: transparent;
  border: none;
  color: var(--text-dim);
  cursor: pointer;
  font-size: 12px;
}

/* Tools Grid */
.tools-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
  gap: 24px;
}

/* Empty State */
.empty-state {
  text-align: center;
  padding: 64px 20px;
  background: var(--bg-surface);
  border: 1.5px dashed var(--border-color);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-sm);
}
.empty-icon {
  font-size: 46px;
  margin-bottom: 12px;
}
.empty-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-main);
  margin-bottom: 6px;
}
.empty-desc {
  font-size: 13px;
  color: var(--text-muted);
  margin-bottom: 18px;
}
.empty-reset-btn {
  background: var(--accent-gradient);
  color: #fff;
  border: none;
  padding: 9px 20px;
  border-radius: var(--radius-full);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
  box-shadow: 0 4px 12px var(--accent-glow);
  transition: opacity 0.2s, transform 0.1s;
}
.empty-reset-btn:hover {
  opacity: 0.92;
  transform: scale(1.02);
}

/* Footer */
.app-footer {
  margin-top: 72px;
  padding-top: 28px;
  border-top: 1px solid var(--border-color);
  text-align: center;
  font-size: 13px;
  color: var(--text-dim);
  line-height: 1.8;
}
.footer-sub {
  font-size: 11px;
  margin-top: 4px;
}
</style>
