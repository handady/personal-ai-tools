<script setup lang="ts">
import { ref, computed } from 'vue';

const props = defineProps<{
  dealsData: any;
}>();

const activeTab = ref<'all' | 'featured'>('all'); // 默认展示全量大榜单，避免遗漏
const viewLayout = ref<'grid' | 'list'>('grid'); // 'grid' 3列卡片, 'list' 极速紧凑清单
const searchQuery = ref('');
const sortBy = ref<'value' | 'discount' | 'price_asc' | 'rate' | 'hours'>('value');

const scrollToTop = () => {
  const modalBody = document.querySelector('.modal-body');
  if (modalBody) {
    modalBody.scrollTo({ top: 0, behavior: 'smooth' });
  }
};

const topValueGames = computed(() => {
  if (!props.dealsData) return [];
  return props.dealsData.top_value || [];
});

const topDiscountGames = computed(() => {
  if (!props.dealsData) return [];
  return props.dealsData.top_discount || [];
});

// 获取包含全部进榜游戏的全量清单
const allGames = computed(() => {
  if (!props.dealsData) return [];
  if (Array.isArray(props.dealsData.all_ranked) && props.dealsData.all_ranked.length) {
    return props.dealsData.all_ranked;
  }
  // 兜底合并
  const map = new Map();
  (props.dealsData.top_value || []).forEach((g: any) => map.set(g.appid, g));
  (props.dealsData.top_discount || []).forEach((g: any) => map.set(g.appid, g));
  return Array.from(map.values());
});

// 全量游戏的动态搜索与多维排序
const filteredAllGames = computed(() => {
  let list = [...allGames.value];

  if (searchQuery.value.trim()) {
    const q = searchQuery.value.trim().toLowerCase();
    list = list.filter((g: any) => {
      const nameMatch = (g.name || '').toLowerCase().includes(q);
      const genresMatch = (g.info?.genres || []).some((genre: string) => genre.toLowerCase().includes(q));
      return nameMatch || genresMatch;
    });
  }

  switch (sortBy.value) {
    case 'discount':
      list.sort((a, b) => b.discount - a.discount);
      break;
    case 'price_asc':
      list.sort((a, b) => a.final - b.final);
      break;
    case 'rate':
      list.sort((a, b) => (b.raw_rate || 0) - (a.raw_rate || 0));
      break;
    case 'hours':
      list.sort((a, b) => (b.hours || 0) - (a.hours || 0));
      break;
    case 'value':
    default:
      list.sort((a, b) => (b.value || 0) - (a.value || 0));
      break;
  }

  return list;
});
</script>

<template>
  <div class="deals-preview-wrap">
    <!-- Header Title Bar -->
    <div class="deals-header-bar">
      <div>
        <h4 class="deals-title">🎮 实时抓取产物 · Steam 每日高性价比折扣榜</h4>
        <p class="deals-subtitle">
          更新时间: {{ dealsData.updated_at || '最新' }} · 
          共挖掘进入精选池 {{ allGames.length }} 款 · 
          已自动排除个人库存 {{ dealsData.excluded_owned_count || 0 }} 款
        </p>
      </div>

      <div class="header-tags-cluster">
        <span class="bubble-tag">扫描折扣位 {{ dealsData.scanned_deals_count || 1183 }}</span>
        <span class="bubble-tag highlight">进榜共 {{ allGames.length }} 款</span>
      </div>
    </div>

    <!-- 视图切换胶囊栏 -->
    <div class="view-switch-bar">
      <div class="tab-pills">
        <button 
          class="switch-pill" 
          :class="{ active: activeTab === 'all' }"
          @click="activeTab = 'all'"
        >
          📋 全量入选清单 (共 {{ allGames.length }} 款)
        </button>
        <button 
          class="switch-pill" 
          :class="{ active: activeTab === 'featured' }"
          @click="activeTab = 'featured'"
        >
          🌟 精选焦点卡片 (TOP 榜单)
        </button>
      </div>

      <!-- 右侧视图模式切换 (仅在全量列表下生效) -->
      <div v-if="activeTab === 'all'" class="layout-toggle-pills">
        <button 
          class="layout-pill" 
          :class="{ active: viewLayout === 'grid' }"
          @click="viewLayout = 'grid'"
          title="一行四列卡片视图"
        >
          🎴 四列卡片
        </button>
        <button 
          class="layout-pill" 
          :class="{ active: viewLayout === 'list' }"
          @click="viewLayout = 'list'"
          title="紧凑单行极速清单（一屏看全）"
        >
          📑 极速清单
        </button>
      </div>
    </div>

    <!-- 视图 1: 全量 57 款游戏清单与即时筛选 -->
    <div v-if="activeTab === 'all'" class="all-games-section">
      <!-- 过滤与排序工具条 -->
      <div class="toolbar-box">
        <div class="search-field">
          <span class="search-lens">🔍</span>
          <input 
            v-model="searchQuery" 
            type="text" 
            :placeholder="`搜索全部 ${allGames.length} 款游戏名称或标签（如 动作/独立/模拟）...`" 
            class="all-search-input"
          />
          <button v-if="searchQuery" class="mini-clear" @click="searchQuery = ''">✕</button>
        </div>

        <div class="sort-selector-group">
          <span class="sort-label">排序方式:</span>
          <button 
            class="sort-pill" 
            :class="{ active: sortBy === 'value' }"
            @click="sortBy = 'value'"
          >
            性价比最高
          </button>
          <button 
            class="sort-pill" 
            :class="{ active: sortBy === 'discount' }"
            @click="sortBy = 'discount'"
          >
            折扣力度最大
          </button>
          <button 
            class="sort-pill" 
            :class="{ active: sortBy === 'price_asc' }"
            @click="sortBy = 'price_asc'"
          >
            现价最低
          </button>
          <button 
            class="sort-pill" 
            :class="{ active: sortBy === 'rate' }"
            @click="sortBy = 'rate'"
          >
            好评率最高
          </button>
          <button 
            class="sort-pill" 
            :class="{ active: sortBy === 'hours' }"
            @click="sortBy = 'hours'"
          >
            游玩时间最长
          </button>
        </div>
      </div>

      <!-- 模式 A: 一行四列紧凑卡片 -->
      <div v-if="viewLayout === 'grid' && filteredAllGames.length" class="game-cards-grid four-cols">
        <div 
          v-for="(game, idx) in filteredAllGames" 
          :key="game.appid"
          class="game-card compact-card"
        >
          <div class="game-cover-wrap compact-cover">
            <img 
              :src="`https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/${game.appid}/capsule_sm_120.jpg`" 
              class="game-cover"
              loading="lazy"
              alt=""
              @error="($event.target as HTMLElement).style.display = 'none'"
            />
            <span class="game-rank-num">#{{ Number(idx) + 1 }}</span>
            <span class="discount-pill">-{{ game.discount }}%</span>
          </div>

          <div class="game-info compact-info">
            <div class="game-name-row">
              <a 
                :href="`https://store.steampowered.com/app/${game.appid}/?cc=cn`" 
                target="_blank" 
                class="game-name"
                :title="game.name"
              >
                {{ game.name }}
              </a>
            </div>

            <!-- 类型标签预览 -->
            <div v-if="game.info && game.info.genres" class="genre-tags-row">
              <span 
                v-for="genre in game.info.genres.slice(0, 2)" 
                :key="genre" 
                class="genre-chip"
              >
                {{ genre }}
              </span>
            </div>

            <div class="price-row compact-price">
              <span class="current-price">¥{{ Math.round(game.final) }}</span>
              <span class="original-price">¥{{ game.original }}</span>
              <span class="cost-per-hour">¥{{ game.cost_per_hour }}/h</span>
            </div>

            <div class="metrics-row compact-metrics">
              <span class="metric-item">
                <span class="m-val highlight">{{ Math.round((game.raw_rate || 0) * 100) }}% 好评</span>
                <span class="m-sub" v-if="game.reviews">({{ game.reviews }}篇)</span>
              </span>
              <span class="metric-item">
                <span class="m-val">{{ game.hours }}h</span>
              </span>
            </div>

            <div class="card-footer-row compact-footer">
              <div class="value-score">
                V指数: <span class="score-number">{{ game.value }}</span>
              </div>
              <span class="low-price-tag">🔥 进榜</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 模式 B: 极速单行手帐清单 (一屏能看十多款，彻底告别长滚动) -->
      <div v-else-if="viewLayout === 'list' && filteredAllGames.length" class="compact-list-view">
        <div 
          v-for="(game, idx) in filteredAllGames" 
          :key="game.appid"
          class="compact-list-row"
        >
          <span class="row-rank">#{{ Number(idx) + 1 }}</span>
          <img 
            :src="`https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/${game.appid}/capsule_sm_120.jpg`" 
            class="row-thumb"
            loading="lazy"
            alt=""
            @error="($event.target as HTMLElement).style.display = 'none'"
          />
          <div class="row-main">
            <a 
              :href="`https://store.steampowered.com/app/${game.appid}/?cc=cn`" 
              target="_blank" 
              class="row-name"
              :title="game.name"
            >
              {{ game.name }}
            </a>
            <div class="row-genres">
              <span v-for="g in (game.info?.genres || []).slice(0, 2)" :key="g" class="row-genre-badge">{{ g }}</span>
            </div>
          </div>

          <div class="row-right">
            <span class="discount-pill mini">-{{ game.discount }}%</span>
            <div class="row-price-group">
              <span class="row-final">¥{{ Math.round(game.final) }}</span>
              <span class="row-original">¥{{ game.original }}</span>
            </div>
            <span class="row-cph">¥{{ game.cost_per_hour }}/h</span>
            <span class="row-rate">{{ Math.round((game.raw_rate || 0) * 100) }}%</span>
            <span class="row-hours">{{ game.hours }}h</span>
            <div class="row-value-badge">
              <span class="v-sub">V</span>
              <span class="v-num">{{ game.value }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 空筛选状态 -->
      <div v-else class="empty-filter-state">
        <span class="empty-icon">🎮</span>
        <p>未找到符合搜索条件的游戏，试试其他关键词或重置筛选</p>
        <button class="reset-filter-btn" @click="searchQuery = ''; sortBy = 'value'">重置筛选</button>
      </div>
    </div>

    <!-- 视图 2: 原有精选高亮 TOP 榜 -->
    <div v-else class="featured-view-wrap">
      <!-- 榜一: 性价比之王 -->
      <div class="rank-section">
        <div class="section-title-wrap">
          <span class="rank-badge gold">TOP 1</span>
          <h5 class="section-title">性价比之王 (按 V 指数降序，闭眼买区 · 前 {{ topValueGames.length }} 款)</h5>
        </div>

        <div class="game-cards-grid four-cols">
          <div 
            v-for="(game, idx) in topValueGames" 
            :key="game.appid"
            class="game-card compact-card"
          >
            <div class="game-cover-wrap compact-cover">
              <img 
                :src="`https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/${game.appid}/capsule_sm_120.jpg`" 
                class="game-cover"
                loading="lazy"
                alt=""
                @error="($event.target as HTMLElement).style.display = 'none'"
              />
              <span class="game-rank-num">#{{ Number(idx) + 1 }}</span>
              <span class="discount-pill">-{{ game.discount }}%</span>
            </div>

            <div class="game-info compact-info">
              <div class="game-name-row">
                <a 
                  :href="`https://store.steampowered.com/app/${game.appid}/?cc=cn`" 
                  target="_blank" 
                  class="game-name"
                  :title="game.name"
                >
                  {{ game.name }}
                </a>
              </div>

              <div class="price-row compact-price">
                <span class="current-price">¥{{ Math.round(game.final) }}</span>
                <span class="original-price">¥{{ game.original }}</span>
                <span class="cost-per-hour">¥{{ game.cost_per_hour }}/h</span>
              </div>

              <div class="metrics-row compact-metrics">
                <span class="metric-item">
                  <span class="m-val highlight">{{ Math.round((game.raw_rate || 0) * 100) }}% 好评</span>
                  <span class="m-sub" v-if="game.reviews">({{ game.reviews }}篇)</span>
                </span>
                <span class="metric-item">
                  <span class="m-val">{{ game.hours }}h</span>
                </span>
              </div>

              <div class="card-footer-row compact-footer">
                <div class="value-score">
                  V指数: <span class="score-number">{{ game.value }}</span>
                </div>
                <span class="low-price-tag">🔥 史低</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 榜二: 深度折扣 -->
      <div v-if="topDiscountGames.length" class="rank-section" style="margin-top: 24px;">
        <div class="section-title-wrap">
          <span class="rank-badge silver">TOP 2</span>
          <h5 class="section-title">深度折扣精选 (手慢无大作 · 前 {{ topDiscountGames.length }} 款)</h5>
        </div>

        <div class="mini-game-list">
          <div 
            v-for="game in topDiscountGames" 
            :key="game.appid"
            class="mini-game-row"
          >
            <div class="mini-left">
              <span class="discount-pill mini">-{{ game.discount }}%</span>
              <a 
                :href="`https://store.steampowered.com/app/${game.appid}/?cc=cn`" 
                target="_blank" 
                class="game-name mini"
              >
                {{ game.name }}
              </a>
            </div>
            <div class="mini-right">
              <span class="original-price">¥{{ game.original }}</span>
              <span class="current-price mini">¥{{ Math.round(game.final) }}</span>
              <span class="m-val highlight" style="font-size: 12px;">{{ Math.round((game.raw_rate || 0) * 100) }}% 好评</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 浮动快速返回顶部小纽扣 -->
    <button class="back-to-top-btn" @click="scrollToTop" title="返回顶部">
      ↑ 回到顶部
    </button>
  </div>
</template>

<style scoped>
.deals-preview-wrap {
  padding: 16px 0;
}

.deals-header-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 18px;
  border-bottom: 1px solid var(--border-color);
  gap: 16px;
  flex-wrap: wrap;
}

.deals-title {
  font-size: 19px;
  font-weight: 750;
  color: var(--text-main);
  margin-bottom: 4px;
}

.deals-subtitle {
  font-size: 13px;
  color: var(--text-muted);
}

.header-tags-cluster {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.bubble-tag {
  font-size: 11px;
  font-weight: 600;
  padding: 4px 10px;
  border-radius: var(--radius-full);
  background: var(--bg-surface);
  border: 1px solid var(--border-color);
  color: var(--text-muted);
  white-space: nowrap;
}
.bubble-tag.highlight {
  background: rgba(239, 68, 68, 0.08);
  border-color: rgba(239, 68, 68, 0.2);
  color: var(--accent-primary);
}

/* 视图切换胶囊栏 */
.view-switch-bar {
  display: flex;
  align-items: center;
  margin-bottom: 22px;
}
.tab-pills {
  display: flex;
  gap: 10px;
  background: var(--bg-card-header);
  padding: 4px;
  border-radius: var(--radius-full);
  border: 1px solid var(--border-color);
}
.switch-pill {
  background: transparent;
  border: none;
  color: var(--text-muted);
  font-size: 13px;
  font-weight: 650;
  padding: 8px 18px;
  border-radius: var(--radius-full);
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
}
.switch-pill:hover {
  color: var(--text-main);
}
.switch-pill.active {
  background: var(--accent-gradient);
  color: #fff;
  box-shadow: 0 3px 10px var(--accent-glow);
}

/* 全量游戏视图工具条 */
.toolbar-box {
  background: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 16px 20px;
  margin-bottom: 22px;
  display: flex;
  flex-direction: column;
  gap: 14px;
  box-shadow: var(--shadow-sm);
}
.search-field {
  position: relative;
  width: 100%;
}
.search-lens {
  position: absolute;
  left: 14px;
  top: 50%;
  transform: translateY(-50%);
  font-size: 13px;
  color: var(--text-dim);
  pointer-events: none;
}
.all-search-input {
  width: 100%;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  padding: 9px 34px 9px 38px;
  border-radius: var(--radius-full);
  font-size: 13px;
  color: var(--text-main);
  outline: none;
  transition: all 0.2s;
}
.all-search-input:focus {
  border-color: var(--accent-primary);
  box-shadow: 0 0 0 3px var(--accent-glow);
}
.mini-clear {
  position: absolute;
  right: 12px;
  top: 50%;
  transform: translateY(-50%);
  background: transparent;
  border: none;
  color: var(--text-dim);
  cursor: pointer;
  font-size: 12px;
}

.sort-selector-group {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.sort-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-muted);
  white-space: nowrap;
  margin-right: 4px;
}
.sort-pill {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  color: var(--text-muted);
  font-size: 12px;
  font-weight: 600;
  padding: 5px 12px;
  border-radius: var(--radius-full);
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.2s;
}
.sort-pill:hover {
  color: var(--text-main);
  border-color: var(--border-hover);
}
.sort-pill.active {
  background: var(--accent-primary);
  color: #fff;
  border-color: var(--accent-primary);
}

/* 标签小胶囊 */
.genre-tags-row {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}
.genre-chip {
  font-size: 10px;
  color: var(--text-dim);
  background: var(--bg-card-header);
  padding: 2px 7px;
  border-radius: var(--radius-full);
  white-space: nowrap;
}

/* 空搜索 */
.empty-filter-state {
  text-align: center;
  padding: 48px 20px;
  background: var(--bg-surface);
  border: 1.5px dashed var(--border-color);
  border-radius: var(--radius-lg);
  font-size: 13px;
  color: var(--text-muted);
}
.empty-filter-state .empty-icon {
  font-size: 36px;
  display: block;
  margin-bottom: 8px;
}
.reset-filter-btn {
  margin-top: 14px;
  background: var(--accent-gradient);
  color: #fff;
  border: none;
  padding: 6px 16px;
  border-radius: var(--radius-full);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
}

.rank-section {
  background: var(--bg-card-header);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-xl);
  padding: 24px;
  box-shadow: var(--shadow-sm);
}

.section-title-wrap {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
}

.rank-badge {
  padding: 4px 12px;
  border-radius: var(--radius-full);
  font-size: 11px;
  font-weight: 750;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}
.rank-badge.gold {
  background: linear-gradient(135deg, #fbbf24, #f59e0b);
  color: #fff;
  box-shadow: 0 2px 8px rgba(245, 158, 11, 0.25);
}
.rank-badge.silver {
  background: linear-gradient(135deg, #f87171, #ef4444);
  color: #fff;
  box-shadow: 0 2px 8px rgba(239, 68, 68, 0.25);
}

.section-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--text-main);
}

.game-cards-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}

/* 一行四列布局 (桌面大弹窗下严格四列对齐，向下响应式适配) */
.game-cards-grid.four-cols {
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

@media (max-width: 1200px) {
  .game-cards-grid.four-cols {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}
@media (max-width: 860px) {
  .game-cards-grid.four-cols {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
@media (max-width: 560px) {
  .game-cards-grid.four-cols {
    grid-template-columns: 1fr;
  }
}

.game-card {
  background: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  box-shadow: var(--shadow-sm);
  transition: transform 0.25s cubic-bezier(0.16, 1, 0.3, 1), border-color 0.2s ease, box-shadow 0.25s ease;
}
.game-card:hover {
  transform: translateY(-3px);
  border-color: var(--border-hover);
  box-shadow: var(--shadow-md);
}

/* 紧凑精致型卡片 (解决原先过高导致滑动过久的问题) */
.compact-card {
  border-radius: var(--radius-md);
}
.compact-cover {
  height: 88px !important;
}
.compact-info {
  padding: 10px 12px !important;
  gap: 6px !important;
}
.compact-price {
  gap: 6px !important;
}
.compact-price .current-price {
  font-size: 16px !important;
}
.compact-metrics {
  font-size: 11px !important;
}
.compact-footer {
  padding-top: 6px !important;
}

.game-cover-wrap {
  position: relative;
  width: 100%;
  height: 116px;
  background: var(--bg-secondary);
  overflow: hidden;
}
.game-cover {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.game-rank-num {
  position: absolute;
  top: 6px;
  left: 6px;
  background: rgba(38, 25, 26, 0.7);
  color: #fff;
  font-size: 10px;
  font-weight: 700;
  padding: 2px 7px;
  border-radius: var(--radius-full);
  backdrop-filter: blur(6px);
  white-space: nowrap;
  flex-shrink: 0;
}
.discount-pill {
  position: absolute;
  bottom: 6px;
  right: 6px;
  background: #10b981;
  color: #fff;
  font-size: 11px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: var(--radius-full);
  box-shadow: 0 2px 6px rgba(16, 185, 129, 0.3);
  white-space: nowrap;
  flex-shrink: 0;
}
.discount-pill.mini {
  position: static;
  padding: 2px 8px;
  font-size: 11px;
  box-shadow: none;
  white-space: nowrap;
  flex-shrink: 0;
}

.game-info {
  padding: 16px;
  display: flex;
  flex-direction: column;
  flex: 1;
  gap: 10px;
}

.game-name {
  font-size: 13.5px;
  font-weight: 650;
  color: var(--text-main);
  text-decoration: none;
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
  overflow: hidden;
  transition: color 0.2s;
}
.game-name:hover {
  color: var(--accent-primary);
}

.price-row {
  display: flex;
  align-items: baseline;
  gap: 8px;
}
.current-price {
  font-size: 18px;
  font-weight: 750;
  color: var(--accent-primary);
  white-space: nowrap;
  flex-shrink: 0;
}
.current-price.mini {
  font-size: 15px;
}
.original-price {
  font-size: 12px;
  color: var(--text-dim);
  text-decoration: line-through;
  white-space: nowrap;
  flex-shrink: 0;
}
.cost-per-hour {
  font-size: 11px;
  color: var(--text-muted);
  margin-left: auto;
  background: var(--bg-card-header);
  padding: 2px 7px;
  border-radius: var(--radius-full);
  white-space: nowrap;
  flex-shrink: 0;
}

.metrics-row {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: var(--text-muted);
}
.m-val {
  color: var(--text-main);
  font-weight: 600;
  white-space: nowrap;
}
.m-val.highlight {
  color: #10b981;
}
.m-sub {
  font-size: 10px;
  color: var(--text-dim);
  margin-left: 2px;
  white-space: nowrap;
}

.card-footer-row {
  margin-top: auto;
  padding-top: 8px;
  border-top: 1px dashed var(--border-color);
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 11.5px;
}
.value-score {
  color: var(--text-muted);
  white-space: nowrap;
}
.score-number {
  font-size: 13.5px;
  font-weight: 750;
  color: #d97706;
  white-space: nowrap;
}
.low-price-tag {
  font-size: 10.5px;
  color: var(--accent-primary);
  background: rgba(239, 68, 68, 0.08);
  padding: 2px 7px;
  border-radius: var(--radius-full);
  font-weight: 600;
  white-space: nowrap;
  flex-shrink: 0;
}

/* 布局模式切换胶囊 */
.layout-toggle-pills {
  margin-left: auto;
  display: flex;
  gap: 6px;
  background: var(--bg-card-header);
  padding: 3px;
  border-radius: var(--radius-full);
  border: 1px solid var(--border-color);
}
.layout-pill {
  background: transparent;
  border: none;
  color: var(--text-muted);
  font-size: 12px;
  font-weight: 600;
  padding: 5px 12px;
  border-radius: var(--radius-full);
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.2s;
}
.layout-pill:hover {
  color: var(--text-main);
}
.layout-pill.active {
  background: var(--bg-surface-hover);
  color: var(--accent-primary);
  box-shadow: var(--shadow-sm);
}

/* 极速单行手帐列表 (紧凑高效，一屏看全) */
.compact-list-view {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.compact-list-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 6px 14px;
  gap: 12px;
  box-shadow: var(--shadow-sm);
  transition: transform 0.15s ease, border-color 0.15s ease;
}
.compact-list-row:hover {
  border-color: var(--border-hover);
  transform: translateX(2px);
  background: var(--bg-surface-hover);
}

.row-rank {
  font-size: 11px;
  font-weight: 700;
  color: var(--text-dim);
  width: 26px;
  flex-shrink: 0;
}
.row-thumb {
  width: 60px;
  height: 28px;
  object-fit: cover;
  border-radius: 4px;
  flex-shrink: 0;
  background: var(--bg-secondary);
}
.row-main {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: 1;
  overflow: hidden;
}
.row-name {
  font-size: 13px;
  font-weight: 650;
  color: var(--text-main);
  text-decoration: none;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 320px;
}
.row-name:hover {
  color: var(--accent-primary);
}
.row-genres {
  display: flex;
  gap: 4px;
  flex-shrink: 0;
}
.row-genre-badge {
  font-size: 10px;
  color: var(--text-dim);
  background: var(--bg-card-header);
  padding: 1px 6px;
  border-radius: var(--radius-full);
  white-space: nowrap;
}

.row-right {
  display: flex;
  align-items: center;
  gap: 14px;
  flex-shrink: 0;
}
.row-price-group {
  display: flex;
  align-items: baseline;
  gap: 6px;
  min-width: 80px;
  justify-content: flex-end;
}
.row-final {
  font-size: 15px;
  font-weight: 750;
  color: var(--accent-primary);
  white-space: nowrap;
}
.row-original {
  font-size: 11px;
  color: var(--text-dim);
  text-decoration: line-through;
  white-space: nowrap;
}
.row-cph {
  font-size: 11px;
  color: var(--text-muted);
  min-width: 60px;
  white-space: nowrap;
}
.row-rate {
  font-size: 11px;
  color: #10b981;
  font-weight: 600;
  min-width: 45px;
  white-space: nowrap;
}
.row-hours {
  font-size: 11px;
  color: var(--text-dim);
  min-width: 40px;
  white-space: nowrap;
}
.row-value-badge {
  display: flex;
  align-items: baseline;
  gap: 3px;
  background: rgba(217, 119, 6, 0.08);
  padding: 2px 8px;
  border-radius: var(--radius-full);
  white-space: nowrap;
}
.v-sub {
  font-size: 9px;
  font-weight: 700;
  color: #d97706;
}
.v-num {
  font-size: 12px;
  font-weight: 750;
  color: #d97706;
}

/* 浮动返回顶部按钮 */
.back-to-top-btn {
  position: sticky;
  bottom: 8px;
  float: right;
  margin-top: 14px;
  background: var(--bg-surface);
  border: 1px solid var(--border-color);
  color: var(--accent-primary);
  font-size: 12px;
  font-weight: 650;
  padding: 7px 16px;
  border-radius: var(--radius-full);
  cursor: pointer;
  box-shadow: var(--shadow-md);
  backdrop-filter: blur(10px);
  white-space: nowrap;
  transition: all 0.2s ease;
  z-index: 10;
}
.back-to-top-btn:hover {
  background: var(--accent-primary);
  color: #fff;
  transform: translateY(-2px);
  box-shadow: 0 4px 14px var(--accent-glow);
}

.mini-game-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.mini-game-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 8px 14px;
  box-shadow: var(--shadow-sm);
  transition: all 0.2s ease;
}
.mini-game-row:hover {
  border-color: var(--border-hover);
  transform: translateX(2px);
}
.mini-left {
  display: flex;
  align-items: center;
  gap: 12px;
}
.mini-right {
  display: flex;
  align-items: center;
  gap: 14px;
}
</style>
