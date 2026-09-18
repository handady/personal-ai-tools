#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Steam 每日高性价比折扣挖掘器 (Steam Discount Finder)
Personal AI Toolkit - Gaming 领域标准自动化工具

评分模型：
  Q = 0.75 * 贝叶斯平滑 Steam 好评率 + 0.25 * (Metacritic / 100)
  H = 由游戏类型 + 成就体量 + 原价档位综合估算的中位游玩小时数
  V = Q^2 * H / P （每 1 元人民币能买到多少小时的优质游戏时间）

核心功能：
  1. 免费抓取 Steam 官方搜索在售折扣列表与评测数据；
  2. 自动拉取详情接口（类型标签、Metacritic 评分、成就总数）；
  3. 支持通过 Steam Web API 或本地手动清单排除已拥有游戏（自适应动态扩扫补齐）；
  4. 逐日沉淀价格历史至 data/ 目录，自动打标「🔥观测新低」；
  5. 自动渲染多维度报告至 output/ 目录（Markdown / HTML / JSON）；
  6. 首次运行自动检测 config.json，缺失时提供交互式配置向导。
"""

import argparse
import html as html_mod
import json
import logging
import re
import sys
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

# ==================== 1. 路径与目录规范 ====================
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"
OUTPUT_DIR = BASE_DIR / "output"

CONFIG_FILE = BASE_DIR / "config.json"
CONFIG_EXAMPLE_FILE = BASE_DIR / "config.example.json"

HISTORY_FILE = DATA_DIR / "history.json"
APPINFO_CACHE_FILE = DATA_DIR / "appinfo_cache.json"
OWNED_TXT_FILE = DATA_DIR / "owned.txt"
OWNED_CACHE_FILE = DATA_DIR / "owned.json"
RUN_LOG_FILE = LOGS_DIR / "run.log"

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

# 兼容 Windows 控制台编码
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# 贝叶斯好评率平滑先验常数
PRIOR_M = 200
PRIOR_RATE = 0.80

# 默认运行参数
DEFAULT_CONFIG: Dict[str, Any] = {
    "min_reviews": 150,        # 最低评测篇数（过滤小样本刷分游戏）
    "min_raw_rate": 0.70,      # 原始好评率下限
    "min_quality": 0.80,       # 平滑后综合质量分 Q 下限
    "max_price": 200.0,        # 折后价上限（元）
    "min_price": 5.0,          # 折后价下限（元）
    "min_discount": 35,        # 最低折扣百分比
    "deep_discount": 70,       # 深度折扣榜准入门槛（%）
    "chinese_only": True,      # 是否仅筛选支持简体中文的游戏
    "sorts": ["Reviews_Desc", "Released_DESC"],
    "pages_per_sort": 6,       # 每种排序扫描深度（100款/页）
    "page_size": 100,
    "deep_check": 250,         # 进入详情精算的最大候选数
    "top_n": 20,               # 榜单呈现游戏数量
    "exclude_owned": True,     # 排除已拥有游戏
    "target_results": 60,      # 排除后至少保留的候选目标数（不足则自动扩扫）
    "expand_rounds": 3,        # 自适应扩扫最大轮数
    "pages_expand_step": 4,    # 每一轮扩扫增加的页数
    "owned_cache_days": 7,     # 个人游戏库缓存有效期（天）
}

# ==================== 2. 日志规范配置 ====================
def setup_logger() -> logging.Logger:
    """初始化并配置日志记录器，同时输出至控制台与 logs/run.log。"""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("steam_discount_finder")
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        file_handler = logging.FileHandler(RUN_LOG_FILE, encoding="utf-8", mode="a")
        file_handler.setLevel(logging.INFO)
        file_fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
        file_handler.setFormatter(file_fmt)

        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_fmt = logging.Formatter("%(message)s")
        console_handler.setFormatter(console_fmt)

        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    return logger


logger = setup_logger()


# ==================== 3. 配置加载与首次运行向导 ====================
def init_directories() -> None:
    """确保运行时所需的本地数据、日志与输出目录全部就绪。"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def setup_wizard() -> None:
    """
    首次运行交互式配置向导：
    自动检测 config.json 是否存在，若缺失则引导用户完成配置，并自动生成 config.json。
    """
    logger.info("=" * 60)
    logger.info("[配置向导] 检测到尚未生成 config.json，正在启动首次配置向导...")
    logger.info("=" * 60)
    logger.info("说明：本工具支持配置 Steam Web API Key 自动同步游戏库以排除已拥有游戏。")
    logger.info("如果暂时没有 Key，可直接按回车跳过，工具将通过 data/owned.txt 手动清单工作。")
    logger.info("-" * 60)

    template_config: Dict[str, Any] = {}
    if CONFIG_EXAMPLE_FILE.exists():
        try:
            with open(CONFIG_EXAMPLE_FILE, "r", encoding="utf-8") as f:
                template_config = json.load(f)
        except Exception as e:
            logger.warning(f"读取 config.example.json 失败: {e}")

    user_config: Dict[str, Any] = {
        "steam_api_key": "",
        "steam_id": "",
        "vanity": "",
        "owned_extra": []
    }

    try:
        api_key = input("- 请输入 Steam Web API Key (留空跳过): ").strip()
        user_config["steam_api_key"] = api_key

        sid = input("- 请输入 SteamID64 或 个人主页链接 (留空跳过): ").strip()
        user_config["steam_id"] = sid

        vanity = input("- 请输入 Steam 自定义主页昵称 (留空跳过): ").strip()
        user_config["vanity"] = vanity
    except (KeyboardInterrupt, EOFError):
        logger.info("\n[INFO] 用户中断了首次配置向导。")
        sys.exit(1)

    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(user_config, f, ensure_ascii=False, indent=2)
        logger.info("=" * 60)
        logger.info(f"[SUCCESS] 配置文件已生成: {CONFIG_FILE.name}")
        logger.info("首次配置已完成，请重新运行本程序以启动折扣扫描：")
        logger.info("  python main.py")
        logger.info("=" * 60)
    except Exception as e:
        logger.error(f"写入 config.json 失败: {e}")
        sys.exit(1)

    sys.exit(0)


def load_config() -> Dict[str, Any]:
    """读取本地 config.json。若不存在则触发交互式向导。"""
    if not CONFIG_FILE.exists():
        setup_wizard()

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"读取 config.json 失败: {e}")
        return {}


# ==================== 4. 基础 HTTP 与 JSON 工具 ====================
def http_get(url: str, timeout: int = 40, retries: int = 3) -> str:
    """带重试机制的 HTTP GET 请求，返回响应文本。"""
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read().decode("utf-8", "ignore")
        except Exception as e:
            code = getattr(e, "code", 0)
            if code in (429, 500, 502, 503):
                time.sleep(5 * (i + 1))
            if i == retries - 1:
                return ""
            time.sleep(1.5 * (i + 1))
    return ""


def http_json(url: str, timeout: int = 30) -> Optional[Dict[str, Any]]:
    """发送 HTTP 请求并直接反序列化为 JSON。"""
    raw = http_get(url, timeout=timeout)
    if not raw:
        return None
    try:
        return json.loads(raw)
    except Exception:
        return None


def load_json(path: Path, default: Any) -> Any:
    """从本地文件安全读取 JSON 数据。"""
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default
    return default


def save_json(path: Path, obj: Any) -> None:
    """将数据安全格式化写入本地 JSON 文件。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


# ==================== 5. Steam 折扣检索与 HTML 解析 ====================
RE_TITLE = re.compile(r'<span class="title">([^<]+)</span>')
RE_FINAL = re.compile(r'data-price-final="(\d+)"')
RE_PCT = re.compile(r'<div class="discount_pct">-?(\d+)%</div>')
RE_TIP = re.compile(r'data-tooltip-html="([^"]*)"')
RE_RELEASE = re.compile(r'<div class="search_released[^"]*">\s*([^<]+?)\s*</div>', re.S)


def parse_results_html(page: str) -> List[Dict[str, Any]]:
    """解析 Steam 搜索结果页面 HTML 片段，提取在售游戏数据。"""
    starts = [m.start() for m in re.finditer(r'<a href="https://store\.steampowered\.com/(?:app|bundle|sub)/\d+', page)]
    starts.append(len(page))
    out = []
    for i in range(len(starts) - 1):
        row = page[starts[i]:starts[i + 1]]
        m_app = re.search(r'store\.steampowered\.com/app/(\d+)', row)
        if not m_app:
            continue
        m_final = RE_FINAL.search(row)
        if not m_final:
            continue
        final_price = int(m_final.group(1)) / 100.0

        m_title = RE_TITLE.search(row)
        m_pct = RE_PCT.search(row)
        m_tip = RE_TIP.search(row)
        m_rel = RE_RELEASE.search(row)

        rate, reviews = None, 0
        if m_tip:
            tip = html_mod.unescape(m_tip.group(1))
            m_r = re.search(r'(\d+)\s*%\s*为好评', tip)
            m_n = re.search(r'([\d,]+)\s*篇用户评测', tip)
            if m_r:
                rate = int(m_r.group(1)) / 100.0
            if m_n:
                reviews = int(m_n.group(1).replace(",", ""))

        out.append({
            "appid": int(m_app.group(1)),
            "name": m_title.group(1).strip() if m_title else "",
            "final": final_price,
            "discount": int(m_pct.group(1)) if m_pct else 0,
            "raw_rate": rate,
            "reviews": reviews,
            "released": m_rel.group(1).strip() if m_rel else "",
        })
    return out


def fetch_search_page(cfg: Dict[str, Any], sort: str, start: int) -> List[Dict[str, Any]]:
    """抓取单页 Steam 在售搜索结果列表。"""
    params = {
        "query": "",
        "start": start,
        "count": cfg["page_size"],
        "dynamic_data": "",
        "sort_by": sort,
        "filter": "onsale",
        "infinite": "1",
        "cc": "cn",
        "l": "schinese",
        "json": "1",
    }
    if cfg.get("chinese_only"):
        params["supportedlang"] = "schinese"

    url = "https://store.steampowered.com/search/results?" + urllib.parse.urlencode(params)
    raw = http_get(url)
    if not raw:
        return []
    try:
        page_html = json.loads(raw).get("results_html", "")
    except Exception:
        return []
    return parse_results_html(page_html)


def quality_pass(item: Dict[str, Any], cfg: Dict[str, Any]) -> bool:
    """初筛过滤：检查折扣力度、价格区间、评测数下限与好评率门槛。"""
    return (
        item["discount"] >= cfg["min_discount"]
        and cfg["min_price"] <= item["final"] <= cfg["max_price"]
        and item["reviews"] >= cfg["min_reviews"]
        and (item["raw_rate"] or 0) >= cfg["min_raw_rate"]
    )


def norm_name(s: str) -> str:
    """规范化游戏名称以便模糊对比（去除空格、标点符号并转小写）。"""
    return re.sub(r"[\s\-_:：（）()\[\]【】™®'\"!.。·,，、#!/\\]", "", (s or "").lower())


def is_owned(item: Dict[str, Any], owned_ids: Set[str], owned_names: Set[str]) -> bool:
    """根据 AppID 或游戏名称比对是否已在玩家游戏库中。"""
    return str(item["appid"]) in owned_ids or norm_name(item["name"]) in owned_names


def collect_all_pages(cfg: Dict[str, Any], from_page: int = 0, to_page: Optional[int] = None) -> List[Dict[str, Any]]:
    """并发抓取各排序规则下的搜索页面，合并去重。"""
    max_p = to_page if to_page is not None else cfg["pages_per_sort"]
    jobs = [(s, p * cfg["page_size"]) for s in cfg["sorts"] for p in range(from_page, max_p)]
    seen: Dict[int, Dict[str, Any]] = {}
    with ThreadPoolExecutor(max_workers=3) as ex:
        for res in ex.map(lambda a: fetch_search_page(cfg, *a), jobs):
            for it in res:
                seen[it["appid"]] = it
    return list(seen.values())


def collect_candidates(
    cfg: Dict[str, Any], owned_ids: Set[str], owned_names: Set[str]
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], int]:
    """
    抓取在售折扣并剔除已拥有游戏。
    自适应扩扫机制：若排除后数量少于 target_results，自动追加后续页面扫描，避免库多导致榜单清空。
    """
    target = cfg["target_results"]
    base = cfg["pages_per_sort"]
    scanned = 0
    pool: Dict[int, Dict[str, Any]] = {}
    avail: List[Dict[str, Any]] = []
    skipped: List[Dict[str, Any]] = []
    round_no = 0

    while True:
        from_p = 0 if round_no == 0 else base
        to_p = base if round_no == 0 else base + cfg["pages_expand_step"]
        got = collect_all_pages(cfg, from_page=from_p, to_page=to_p)
        for it in got:
            pool[it["appid"]] = it
        scanned = len(pool)

        avail, skipped = [], []
        for it in pool.values():
            if not quality_pass(it, cfg):
                continue
            if cfg["exclude_owned"] and is_owned(it, owned_ids, owned_names):
                skipped.append(it)
            else:
                avail.append(it)

        logger.info(
            f"      第 {round_no + 1} 轮扫描 {scanned} 个折扣位 → "
            f"符合质量门槛 {len(avail)} 款（排除已拥有 {len(skipped)} 款）"
        )

        if len(avail) >= target or round_no >= cfg["expand_rounds"]:
            break

        base += cfg["pages_expand_step"]
        round_no += 1

    return avail, skipped, scanned


# ==================== 6. 游戏详情丰富与时长估算 ====================
GENRE_HOURS = [
    ("开放世界|Open World", 45), ("沙盒|Sandbox| automobil", 60), ("模拟|Simulation", 32),
    ("策略|Strategy|Grand", 30), ("战术|Turn-Based", 26), ("城市营造|City", 40),
    ("角色扮演|RPG|Roguelite", 28), ("生存|Survival", 26), ("经营|Management|Building", 26),
    ("回合制|Turn-Based Tactics", 26), ("竞速|Racing|体育|Sport", 16), ("射击|Shooter|FPS", 14),
    ("冒险|Adventure", 12), ("动作|Action", 11), ("步行模拟|Walking", 6),
    (" Roguelike|Roguelite| roguelike", 20), ("解谜|Puzzle", 9), ("平台|Platformer|Platform", 9),
    ("恐怖|Horror", 9), ("节奏|Rhythm", 8), ("视觉小说|Visual Novel", 12),
    ("叙事|Interactive Fiction|故事", 8), ("益智|Casual|休闲", 10), ("即时制|Real-Time", 18),
]


def estimate_hours(info: Optional[Dict[str, Any]], original_price: float) -> float:
    """基于类型标签、成就总数与原价档位先验估算游戏的中位游玩时长。"""
    if not info:
        return 10.0
    genres = "|".join(info.get("genres", []))
    base = 0.0
    for pat, h in GENRE_HOURS:
        if re.search(pat, genres, re.I):
            base = max(base, float(h))
    if base == 0:
        base = 10.0

    ach = info.get("achievements") or 0
    if ach >= 150:
        base *= 1.35
    elif ach >= 60:
        base *= 1.18
    elif ach >= 20:
        base *= 1.08

    if original_price >= 200:
        base *= 1.30
    elif original_price >= 120:
        base *= 1.15
    elif original_price <= 25:
        base *= 0.85

    return round(base, 1)


def fetch_appinfo(appid: int) -> Optional[Dict[str, Any]]:
    """调用 Steam 官方 appdetails API 获取游戏分类、Metacritic 评分与成就信息。"""
    url = (
        f"https://store.steampowered.com/api/appdetails?appids={appid}&cc=cn&l=schinese"
        "&filters=basic,genres,metacritic,achievements,categories,release_date"
    )
    raw = http_get(url, timeout=30)
    if not raw:
        return None
    try:
        j = json.loads(raw).get(str(appid), {})
        if not j.get("success"):
            return None
        d = j["data"]
        return {
            "genres": [g.get("description", "") for g in d.get("genres", [])],
            "metacritic": (d.get("metacritic") or {}).get("score"),
            "achievements": (d.get("achievements") or {}).get("total"),
            "short_desc": d.get("short_description", "")[:120],
            "release_year": (d.get("release_date") or {}).get("date", ""),
        }
    except Exception:
        return None


def enrich(cands: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """批量丰富候选游戏详情，带本地持久化缓存以避免重复请求。"""
    cache: Dict[str, Any] = load_json(APPINFO_CACHE_FILE, {})
    need = [c for c in cands if str(c["appid"]) not in cache]
    if need:
        def work(c: Dict[str, Any]) -> Tuple[int, Optional[Dict[str, Any]]]:
            return c["appid"], fetch_appinfo(c["appid"])

        with ThreadPoolExecutor(max_workers=4) as ex:
            for appid, info in ex.map(work, need):
                if info:
                    cache[str(appid)] = info
                time.sleep(0.05)
        save_json(APPINFO_CACHE_FILE, cache)

    for c in cands:
        c["info"] = cache.get(str(c["appid"]))
    return cands


# ==================== 7. 已拥有游戏库同步 ====================
def resolve_vanity(key: str, vanity: str) -> Optional[str]:
    """将 Steam 自定义主页昵称转换为 17 位 SteamID64。"""
    j = http_json(
        "https://api.steampowered.com/ISteamUser/ResolveVanityURL/v0001/"
        f"?key={key}&vanityurl={urllib.parse.quote(vanity)}"
    )
    if j and j.get("response", {}).get("success") == 1:
        return j["response"]["steamid"]
    return None


def get_steam_id(cfg: Dict[str, Any], key: str) -> str:
    """提取或自动解析用户的 17 位 SteamID64。"""
    sid = str(cfg.get("steam_id", "") or "").strip()
    if sid.isdigit() and len(sid) == 17:
        return sid
    vanity = str(cfg.get("vanity", "") or "").strip()
    if vanity:
        vanity = vanity.rstrip("/").split("/")[-1]
    if not vanity and sid:
        vanity = sid.rstrip("/").split("/")[-1]
    if not vanity:
        return ""

    got = resolve_vanity(key, vanity)
    if got:
        cfg["steam_id"] = got
        try:
            save_json(CONFIG_FILE, cfg)
        except Exception:
            pass
        return got
    return ""


def fetch_owned_via_api(key: str, steamid: str) -> Optional[Dict[str, Any]]:
    """调用 Steam GetOwnedGames 接口获取用户全部库存游戏列表。"""
    url = (
        "https://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/"
        f"?key={key}&steamid={steamid}&format=json"
        "&include_appinfo=1&include_played_free_games=1"
    )
    j = http_json(url)
    if not j or not j.get("response", {}).get("games"):
        return None
    games: Dict[str, Any] = {}
    for g in j["response"]["games"]:
        games[str(g["appid"])] = {
            "name": g.get("name", ""),
            "playtime": int(g.get("playtime_forever", 0) or 0),
        }
    return games


def load_manual_owned() -> Tuple[Set[str], Set[str]]:
    """读取 data/owned.txt 手动清单（一行一个 AppID 或游戏名）。"""
    appids: Set[str] = set()
    names: Set[str] = set()
    if not OWNED_TXT_FILE.exists():
        return appids, names
    try:
        with open(OWNED_TXT_FILE, "r", encoding="utf-8") as f:
            for line in f:
                s = line.strip()
                if not s or s.startswith("#"):
                    continue
                if s.isdigit():
                    appids.add(s)
                else:
                    names.add(norm_name(s))
    except Exception as e:
        logger.warning(f"读取 owned.txt 失败: {e}")
    return appids, names


def build_owned(force_sync: bool = False) -> Tuple[Set[str], Set[str], Dict[str, Any]]:
    """
    构建已拥有游戏库集合。
    优先级：Steam Web API 自动同步 > data/owned.json 缓存 > data/owned.txt 手动清单。
    """
    cfg = load_config()
    cache: Dict[str, Any] = load_json(OWNED_CACHE_FILE, {})
    age_days = 999.0
    if cache.get("synced_at"):
        try:
            age_days = (time.time() - float(cache["synced_at"])) / 86400.0
        except Exception:
            age_days = 999.0

    games: Dict[str, Any] = cache.get("games", {})
    source = cache.get("source", "")

    key = cfg.get("steam_api_key", "")
    sid = get_steam_id(cfg, key) if key else ""

    if key and sid and (force_sync or age_days > cfg.get("owned_cache_days", 7) or not games):
        got = fetch_owned_via_api(key, sid)
        if got:
            games, source = got, "Steam Web API"
            save_json(OWNED_CACHE_FILE, {"synced_at": time.time(), "source": source, "games": games})
        else:
            logger.warning("Steam Web API 同步失败，回退使用本地缓存/手动清单")

    for a in cfg.get("owned_extra", []):
        games[str(a)] = {"name": "", "playtime": 0}

    appids = set(games.keys())
    names = {norm_name(g.get("name", "")) for g in games.values() if g.get("name")}
    m_appids, m_names = load_manual_owned()
    appids |= m_appids
    names |= m_names

    meta = {
        "count": len(appids),
        "source": source or ("手动清单" if (m_appids or m_names) else "无"),
        "games": games,
    }
    return appids, names, meta


# ==================== 8. 评分模型计算 ====================
def score(item: Dict[str, Any]) -> Dict[str, Any]:
    """
    执行高性价比计算模型：
    Q = 0.75 * 贝叶斯好评率 + 0.25 * (Metacritic/100)
    H = 游玩时长估算值
    V = Q^2 * H / P
    """
    n = item["reviews"]
    rate = item["raw_rate"] or 0
    pos = round(rate * n)
    bayes = (pos + PRIOR_M * PRIOR_RATE) / (n + PRIOR_M)

    mc = None
    if item.get("info") and item["info"].get("metacritic"):
        mc = item["info"]["metacritic"]

    if mc:
        q = 0.75 * bayes + 0.25 * (mc / 100.0)
    else:
        q = bayes * 0.97

    discount = item["discount"]
    original = item["final"] / (1 - discount / 100.0) if discount else item["final"]
    hours = estimate_hours(item.get("info"), original) or 10.0

    price = max(item["final"], 1.0)
    value = (q ** 2 * hours) / price

    item.update({
        "Q": round(q, 4),
        "bayes": round(bayes, 4),
        "metacritic": mc,
        "hours": hours,
        "original": round(original),
        "value": round(value, 3),
        "cost_per_hour": round(price / max(hours, 0.5), 2),
    })
    return item


# ==================== 9. 本地价格历史追溯 ====================
def update_history(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """更新 data/history.json 价格沉淀记录，保留最近 400 天数据。"""
    hist: Dict[str, Any] = load_json(HISTORY_FILE, {})
    today = time.strftime("%Y-%m-%d")
    for it in items:
        rec = hist.setdefault(str(it["appid"]), {"name": it["name"], "points": {}})
        rec["name"] = it["name"]
        rec["points"][today] = round(it["final"], 2)

    for k in list(hist.keys()):
        pts = hist[k]["points"]
        if len(pts) > 400:
            for d in sorted(pts.keys())[:-400]:
                pts.pop(d, None)

    save_json(HISTORY_FILE, hist)
    return hist


def history_flag(appid: int, price: float, hist: Dict[str, Any]) -> Tuple[str, Optional[float], int]:
    """对比价格历史判断是否创下新低：LOW(观测新低), NEW(首次记录), DOWN(降价), SAME(持平)。"""
    rec = hist.get(str(appid))
    if not rec:
        return "NEW", None, 0
    pts = rec["points"]
    days = sorted(pts.keys())
    if len(days) <= 1:
        return "NEW", None, 1

    lowest_day = min(days[:-1], key=lambda d: pts[d])
    low_val = pts[lowest_day]
    prev_val = pts[days[-2]]

    if price < low_val:
        return "LOW", low_val, len(pts)
    if prev_val is not None and price < prev_val:
        return "DOWN", prev_val, len(pts)
    return "SAME", low_val, len(pts)


# ==================== 10. 报告生成与渲染 ====================
CSS = """
*{box-sizing:border-box}
body{margin:0;padding:28px 24px 60px;background:#f5f6f8;color:#1b1f24;
 font:14px/1.6 -apple-system,"Segoe UI","Microsoft YaHei",sans-serif}
.wrap{max-width:1120px;margin:0 auto}
h1{font-size:22px;margin:0 0 4px}
h2{font-size:16px;margin:28px 0 10px}
.sub{color:#6b7280;font-size:13px;margin-bottom:18px}
.card{background:#fff;border:1px solid #e5e7eb;border-radius:12px;overflow:hidden;
 box-shadow:0 1px 3px rgba(0,0,0,.04);margin-bottom:8px}
table{width:100%;border-collapse:collapse}
th{background:#fafafa;text-align:left;padding:9px 12px;font-size:12px;color:#6b7280;
 font-weight:600;border-bottom:1px solid #eef0f2;white-space:nowrap}
td{padding:9px 12px;border-bottom:1px solid #f2f4f6;vertical-align:middle}
tr:last-child td{border-bottom:none}
tr:hover td{background:#fafbfc}
.rank{color:#9ca3af;font-variant-numeric:tabular-nums;width:30px}
.g{display:flex;gap:10px;align-items:center;min-width:300px}
.g img{width:58px;height:27px;object-fit:cover;border-radius:4px;background:#eee;flex:none}
.name{color:#111827;text-decoration:none;font-weight:600;font-size:14px}
.name:hover{color:#2563eb}
.meta{color:#9ca3af;font-size:11px;margin-top:2px}
.orig{color:#9ca3af;font-size:12px;text-decoration:line-through}
.pct2{color:#16a34a;font-weight:600;font-size:12px}
.price{color:#dc2626;font-weight:700;font-size:16px;white-space:nowrap}
.val b{color:#b45309;font-size:16px}
.pct{background:#16a34a;color:#fff;border-radius:4px;padding:2px 6px;font-size:12px;font-weight:600}
.tag{font-size:11px;padding:1px 6px;border-radius:4px;margin-left:6px}
.tag.low{background:#fee2e2;color:#b91c1c}
.tag.new{background:#e0f2fe;color:#0369a1}
.tag.down{background:#fef3c7;color:#92400e}
.tag.same{color:#c0c4cc}
.bar{display:flex;gap:10px;align-items:center;margin:10px 0 6px}
.bar input{flex:1;max-width:300px;padding:6px 10px;border:1px solid #d1d5db;border-radius:7px;font-size:13px;outline:none}
.bar input:focus{border-color:#2563eb}
.bar .cnt{color:#6b7280;font-size:12px}
th.sortable{cursor:pointer;user-select:none}
th.sortable:hover{color:#2563eb}
th.sortable::after{content:" ⇅";color:#c0c4cc;font-size:10px}
th.asc::after{content:" ↑";color:#2563eb}
th.desc::after{content:" ↓";color:#2563eb}
details.have{margin-top:14px;background:#fff;border:1px solid #e5e7eb;border-radius:10px;padding:10px 16px;font-size:13px}
details.have summary{cursor:pointer;color:#6b7280;font-weight:600;outline:none}
details.have ul{margin:10px 0 2px;padding-left:18px;columns:3;column-gap:24px;color:#4b5563}
details.have li{margin:3px 0;break-inside:avoid}
details.have a{color:#374151;text-decoration:none}
details.have a:hover{color:#2563eb}
details.have .pt{margin-left:6px;color:#9ca3af;font-size:11px}
.lead{background:#fff;border:1px solid #e5e7eb;border-left:3px solid #2563eb;border-radius:8px;
 padding:12px 16px;margin-bottom:18px;font-size:13px;color:#374151}
"""


def rows_html(items: List[Dict[str, Any]], hist: Dict[str, Any], kind: str) -> str:
    """生成榜单一、二的 HTML 表格行。"""
    out = []
    for i, it in enumerate(items, 1):
        flag, _, _ = history_flag(it["appid"], it["final"], hist)
        badge = {
            "LOW": '<span class="tag low">观测新低</span>',
            "NEW": '<span class="tag new">首次记录</span>',
            "DOWN": '<span class="tag down">降价</span>',
            "SAME": '<span class="tag same">持平</span>',
        }[flag]
        genres = " · ".join((it.get("info") or {}).get("genres", [])[:3]) if it.get("info") else ""
        main_cell = f'<b>{it["value"]}</b>' if kind == "value" else f'<span class="pct">-{it["discount"]}%</span>'
        out.append(f"""
        <tr>
          <td class="rank">{i}</td>
          <td class="g">
            <img src="https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/{it['appid']}/capsule_sm_120.jpg"
                 onerror="this.style.visibility='hidden'" loading="lazy" alt="">
            <div>
              <a class="name" href="https://store.steampowered.com/app/{it['appid']}/?cc=cn" target="_blank">{html_mod.escape(it['name'])}</a>
              <div class="meta">{html_mod.escape(genres)} · {it['reviews']} 篇评测 {badge}</div>
            </div>
          </td>
          <td><div class="orig">¥{it['original']}</div><div class="pct2">-{it['discount']}%</div></td>
          <td class="price">¥{it['final']:.0f}</td>
          <td>{int((it['raw_rate'] or 0) * 100)}%<div class="meta">Q {it['Q']:.2f}</div></td>
          <td>{it['hours']}h<div class="meta">¥{it['cost_per_hour']}/h</div></td>
          <td class="val">{main_cell}</td>
        </tr>""")
    return "".join(out)


def full_rows_html(items: List[Dict[str, Any]], hist: Dict[str, Any]) -> str:
    """生成完整清单的 HTML 表格行（支持前端即时搜索与列排序）。"""
    out = []
    for i, it in enumerate(items, 1):
        flag, _, _ = history_flag(it["appid"], it["final"], hist)
        badge = {
            "LOW": '<span class="tag low">观测新低</span>',
            "NEW": '<span class="tag new">首次记录</span>',
            "DOWN": '<span class="tag down">降价</span>',
            "SAME": '<span class="tag same">持平</span>',
        }[flag]
        genres = " · ".join((it.get("info") or {}).get("genres", [])[:3]) if it.get("info") else ""
        out.append(f"""
        <tr data-name="{html_mod.escape(it['name'].lower())}">
          <td class="rank">{i}</td>
          <td class="g">
            <a class="name" href="https://store.steampowered.com/app/{it['appid']}/?cc=cn" target="_blank">{html_mod.escape(it['name'])}</a>
            <div class="meta">{html_mod.escape(genres)} {badge}</div>
          </td>
          <td data-v="{it['original']}"><span class="orig">¥{it['original']}</span></td>
          <td data-v="{it['discount']}"><span class="pct2">-{it['discount']}%</span></td>
          <td data-v="{it['final']:.0f}" class="price">¥{it['final']:.0f}</td>
          <td data-v="{(it['raw_rate'] or 0)*100:.1f}">{int((it['raw_rate'] or 0) * 100)}%<div class="meta">{it['reviews']} 篇</div></td>
          <td data-v="{it['Q']:.3f}">{it['Q']:.2f}</td>
          <td data-v="{it['hours']}">{it['hours']}h</td>
          <td data-v="{it['cost_per_hour']}">¥{it['cost_per_hour']}</td>
          <td data-v="{it['value']:.3f}" class="val"><b>{it['value']}</b></td>
        </tr>""")
    return "".join(out)


def render_html(
    cfg: Dict[str, Any],
    top_value: List[Dict[str, Any]],
    top_discount: List[Dict[str, Any]],
    scored: List[Dict[str, Any]],
    hist: Dict[str, Any],
    skipped: List[Dict[str, Any]],
    scanned: int,
    owned_meta: Dict[str, Any],
) -> str:
    """渲染自包含交互式 HTML 报告页面。"""
    today = time.strftime("%Y-%m-%d %H:%M")
    best = top_value[0] if top_value else None
    owned_note = f" · 已排除你库里已有的 {owned_meta['count']} 款" if cfg["exclude_owned"] else ""
    lead = (
        f"今天最值：<b>{html_mod.escape(best['name'])}</b> ¥{best['final']:.0f}"
        f"（原价 ¥{best['original']}，- {best['discount']}%），好评 {int((best['raw_rate'] or 0)*100)}%，"
        f"估算 {best['hours']} 小时内容，折合 ¥{best['cost_per_hour']}/小时。"
        if best
        else "本轮未检测到符合准入门槛的游戏。"
    )

    owned_box = ""
    if skipped:
        lis = "".join(
            f'<li><a href="https://store.steampowered.com/app/{it["appid"]}/?cc=cn" target="_blank">'
            f'{html_mod.escape(it["name"])}</a> −{it["discount"]}% ¥{it["final"]:.0f}'
            f'<span class="pt">{str(it.get("played_h", 0)) + "h" if it.get("played_h") else "未玩过"}</span></li>'
            for it in sorted(skipped, key=lambda x: -x["discount"])[:40]
        )
        owned_box = (
            f'<details class="have"><summary>你已拥有的打折游戏 · {len(skipped)} 款'
            f'（已排除，点开看看有没有想推荐给朋友的）</summary><ul>{lis}</ul></details>'
        )

    return f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Steam 高性价比折扣榜 · {today}</title><style>{CSS}</style></head>
<body><div class="wrap">
<h1>🎮 Steam 每日高性价比折扣挖掘报告</h1>
<div class="sub">{today} · 扫描 {scanned} 个折扣位 · {len(scored)} 款进入榜单{owned_note}</div>
<div class="lead">{lead}</div>

<h2>榜一 · 性价比之王 (TOP {len(top_value)})</h2>
<div class="card"><table>
<thead><tr><th></th><th>游戏</th><th>原价/折扣</th><th>现价</th><th>好评/Q</th><th>时长</th><th>性价比</th></tr></thead>
<tbody>{rows_html(top_value, hist, "value")}</tbody></table></div>

<h2>榜二 · 深度折扣 (TOP {len(top_discount)})</h2>
<div class="card"><table>
<thead><tr><th></th><th>游戏</th><th>原价/折扣</th><th>现价</th><th>好评</th><th>时长</th><th>折扣</th></tr></thead>
<tbody>{rows_html(top_discount, hist, "discount")}</tbody></table></div>

<h2>完整清单 · 全部 {len(scored)} 款（支持按列点击排序与名称过滤）</h2>
<div class="bar">
  <input id="q" placeholder="在列表中过滤游戏名..." autocomplete="off">
  <span id="cnt" class="cnt">匹配 {len(scored)} 款</span>
</div>
<div class="card"><table>
<thead><tr>
  <th>#</th><th>游戏</th>
  <th class="sortable">原价</th>
  <th class="sortable">折扣</th>
  <th class="sortable">现价</th>
  <th class="sortable">好评率</th>
  <th class="sortable">Q分</th>
  <th class="sortable">时长</th>
  <th class="sortable">¥/h</th>
  <th class="sortable">性价比</th>
</tr></thead>
<tbody id="tb">{full_rows_html(scored, hist)}</tbody></table></div>

{owned_box}
</div>

<script>
(function() {{
  var tb = document.getElementById('tb');
  if (!tb) return;
  var rows = Array.from(tb.querySelectorAll('tr'));

  document.querySelectorAll('th.sortable').forEach(function(th, colIdx) {{
    var col = colIdx + 2;
    th.addEventListener('click', function() {{
      var cur = th.dataset.dir || '';
      var next = cur === 'desc' ? 'asc' : 'desc';
      th.parentNode.querySelectorAll('th').forEach(function(h) {{ h.classList.remove('asc','desc'); delete h.dataset.dir; }});
      th.dataset.dir = next; th.classList.add(next);
      var visible = rows.filter(function(r){{ return r.style.display !== 'none'; }});
      visible.sort(function(a, b) {{
        var av = parseFloat(a.cells[col].dataset.v), bv = parseFloat(b.cells[col].dataset.v);
        if (isNaN(av)) av = -1; if (isNaN(bv)) bv = -1;
        return next === 'asc' ? av - bv : bv - av;
      }});
      var frag = document.createDocumentFragment();
      visible.forEach(function(r){{ frag.appendChild(r); }});
      tb.appendChild(frag);
    }});
  }});

  var searchInput = document.getElementById('q');
  if (searchInput) {{
    searchInput.addEventListener('input', function() {{
      var k = this.value.trim().toLowerCase(), n = 0;
      rows.forEach(function(r) {{
        var hit = !k || r.dataset.name.indexOf(k) >= 0;
        r.style.display = hit ? '' : 'none';
        if (hit) n++;
      }});
      document.getElementById('cnt').textContent = '匹配 ' + n + ' 款';
    }});
  }}
}})();
</script>
</body></html>"""


def render_md(
    cfg: Dict[str, Any],
    top_value: List[Dict[str, Any]],
    top_discount: List[Dict[str, Any]],
    scored: List[Dict[str, Any]],
    hist: Dict[str, Any],
    skipped: List[Dict[str, Any]],
    owned_meta: Dict[str, Any],
) -> str:
    """生成 Markdown 格式的完整日报内容。"""
    today = time.strftime("%Y-%m-%d %H:%M")
    owned_line = f" · 已拥有过滤：{owned_meta['source']}，{owned_meta['count']} 款" if cfg["exclude_owned"] else ""
    lines = [
        f"# Steam 每日高性价比折扣挖掘 · {today}",
        "",
        f"扫描 {cfg['pages_per_sort'] * cfg['page_size'] * len(cfg['sorts'])} 个折扣位 · "
        f"{len(scored)} 款进榜 · 排除已拥有 {len(skipped)} 款{owned_line}",
        "",
        "## 榜一 · 性价比之王",
        "",
        "| # | 游戏 | 原价→现价 | 折扣 | 好评 | 时长 | ¥/小时 | 性价比 | 历史 |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for i, it in enumerate(top_value, 1):
        flag, _, _ = history_flag(it["appid"], it["final"], hist)
        badge = {"LOW": "🔥新低", "NEW": "🆕首次", "DOWN": "⬇降价", "SAME": "—"}[flag]
        lines.append(
            f"| {i} | [{it['name']}](https://store.steampowered.com/app/{it['appid']}/?cc=cn) | "
            f"¥{it['original']}→¥{it['final']:.0f} | -{it['discount']}% | {int((it['raw_rate'] or 0)*100)}% "
            f"({it['reviews']}) | {it['hours']}h | ¥{it['cost_per_hour']} | **{it['value']}** | {badge} |"
        )

    lines += ["", "## 榜二 · 深度折扣 TOP", "", "| # | 游戏 | 原价→现价 | 折扣 | 好评 | ¥/小时 |", "|---|---|---|---|---|---|"]
    for i, it in enumerate(top_discount, 1):
        lines.append(
            f"| {i} | [{it['name']}](https://store.steampowered.com/app/{it['appid']}/?cc=cn) | "
            f"¥{it['original']}→¥{it['final']:.0f} | -{it['discount']}% | {int((it['raw_rate'] or 0)*100)}% "
            f"({it['reviews']}) | ¥{it['cost_per_hour']} |"
        )

    lines += [
        "",
        f"## 完整清单 · 全部 {len(scored)} 款（按性价比降序）",
        "",
        "| # | 游戏 | 原价→现价 | 折扣 | 好评 | Q | 时长 | ¥/小时 | 性价比 | 历史 |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for i, it in enumerate(scored, 1):
        flag, _, _ = history_flag(it["appid"], it["final"], hist)
        badge = {"LOW": "🔥新低", "NEW": "🆕首次", "DOWN": "⬇降价", "SAME": "—"}[flag]
        genres = " · ".join((it.get("info") or {}).get("genres", [])[:2]) if it.get("info") else ""
        lines.append(
            f"| {i} | [{it['name']}](https://store.steampowered.com/app/{it['appid']}/?cc=cn) "
            f"<br><sub>{genres}</sub> | ¥{it['original']}→¥{it['final']:.0f} | -{it['discount']}% | "
            f"{int((it['raw_rate'] or 0)*100)}% ({it['reviews']}) | {it['Q']:.2f} | {it['hours']}h | "
            f"¥{it['cost_per_hour']} | **{it['value']}** | {badge} |"
        )

    if skipped:
        lines += ["", f"## 已拥有 · 本次被排除的 {len(skipped)} 款（也在打折）", ""]
        lines += [
            "- " + it["name"] + f"（-{it['discount']}% ¥{it['final']:.0f}"
            f"，{str(it.get('played_h', 0)) + 'h' if it.get('played_h') else '未玩过'}）"
            for it in sorted(skipped, key=lambda x: -x["discount"])[:30]
        ]

    lines += ["", "> 提示：已同时在 output/ 目录生成交互式 HTML 报表与结构化 JSON 数据。"]
    return "\n".join(lines)


# ==================== 11. 主执行入口 ====================
def main() -> None:
    """主程序入口：参数解析、拉取、精算、持久化与报告生成。"""
    init_directories()

    ap = argparse.ArgumentParser(description="Steam 每日高性价比折扣挖掘器")
    for k, v in DEFAULT_CONFIG.items():
        flag = "--" + k.replace("_", "-")
        if isinstance(v, bool):
            ap.add_argument(flag, dest=k, action="store_true", default=False)
        else:
            ap.add_argument(flag, type=type(v) if isinstance(v, (int, float)) else str, default=None)
    ap.add_argument("--sync-owned", dest="sync_owned", action="store_true", help="强制重新同步 Steam 个人库存")
    args = ap.parse_args()

    cfg = dict(DEFAULT_CONFIG)
    for k in DEFAULT_CONFIG:
        val = getattr(args, k, None)
        if isinstance(DEFAULT_CONFIG[k], bool):
            cfg[k] = True if val else DEFAULT_CONFIG[k]
        elif val is not None:
            cfg[k] = val
    cfg["chinese_only"] = True

    logger.info("=" * 60)
    logger.info("[START] 启动 Steam 高性价比折扣挖掘任务...")
    logger.info("=" * 60)

    # 1. 加载库存
    logger.info("[1/6] 加载你的游戏库...")
    owned_ids, owned_names, owned_meta = build_owned(force_sync=bool(args.sync_owned))
    logger.info(f"      已登记游戏 {owned_meta['count']} 款（来源：{owned_meta['source']}）")

    # 2. 检索折扣与排除已拥有
    logger.info("[2/6] 抓取在售折扣并排除已拥有...")
    avail, skipped, scanned = collect_candidates(cfg, owned_ids, owned_names)

    games_dict = owned_meta.get("games", {})
    for it in skipped:
        it["played_h"] = round(games_dict.get(str(it["appid"]), {}).get("playtime", 0) / 60.0, 1)

    avail.sort(key=lambda x: -(x["reviews"] * (x["raw_rate"] or 0)))
    deep = avail[: min(len(avail), cfg["deep_check"])]
    logger.info(f"      最终可用 {len(avail)} 款（排除 {len(skipped)} 款已拥有），精算前 {len(deep)} 款")

    # 3. 详情信息丰富
    logger.info("[3/6] 抓取 Steam 游戏详情（类型/媒体分/成就）...")
    enrich(deep)

    # 4. 计算综合性价比
    logger.info("[4/6] 计算综合性价比 Q, H, V...")
    scored = [score(c) for c in deep]
    scored = [s for s in scored if s["Q"] >= cfg["min_quality"]]
    scored.sort(key=lambda x: -x["value"])
    top_value = scored[: cfg["top_n"]]

    seen_ids = {s["appid"] for s in top_value}
    dd = [s for s in scored if s["discount"] >= cfg["deep_discount"] and s["appid"] not in seen_ids]
    if len(dd) < 5:
        dd = [s for s in scored if s["appid"] not in seen_ids and s["discount"] >= cfg["min_discount"]]
    dd.sort(key=lambda x: -x["value"])
    top_discount = dd[: cfg["top_n"]]
    logger.info(f"      完成精算评分，进榜候选 {len(scored)} 款")

    # 5. 更新本地价格沉淀
    logger.info("[5/6] 更新本地历史价格数据...")
    hist = update_history(scored + skipped)

    # 6. 生成输出物
    logger.info("[6/6] 生成 Markdown, HTML 与 JSON 输出产物...")
    d_str = time.strftime("%Y-%m-%d")
    p_md = OUTPUT_DIR / f"deals-{d_str}.md"
    p_html = OUTPUT_DIR / f"deals-{d_str}.html"
    p_latest_html = OUTPUT_DIR / "latest.html"
    p_latest_json = OUTPUT_DIR / "deals-latest.json"

    md_content = render_md(cfg, top_value, top_discount, scored, hist, skipped, owned_meta)
    html_content = render_html(cfg, top_value, top_discount, scored, hist, skipped, scanned, owned_meta)

    # 输出结构化 JSON 产物，极大便利 AI 进一步处理
    json_output_payload = {
        "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "scanned_deals_count": scanned,
        "qualified_games_count": len(scored),
        "excluded_owned_count": len(skipped),
        "top_value": top_value,
        "top_discount": top_discount,
        "all_ranked": scored,
    }

    try:
        with open(p_md, "w", encoding="utf-8") as f:
            f.write(md_content)
        with open(p_html, "w", encoding="utf-8") as f:
            f.write(html_content)
        with open(p_latest_html, "w", encoding="utf-8") as f:
            f.write(html_content)
        save_json(p_latest_json, json_output_payload)

        logger.info(f"[SUCCESS] 任务执行完毕！产物已输出至：")
        logger.info(f"  - Markdown: {p_md.name}")
        logger.info(f"  - HTML:     {p_html.name} / latest.html")
        logger.info(f"  - JSON:     {p_latest_json.name}")
    except Exception as e:
        logger.error(f"写入产物失败: {e}")


if __name__ == "__main__":
    main()
