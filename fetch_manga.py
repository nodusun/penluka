#!/usr/bin/env python3
"""
ペンルカ用 漫画データ取得スクリプト

- B: インディーズ女性マンガ (5916190051)
- C: Indie Recommended (10409694051)
の2ノードから取得 → ¥0のみ → シリーズ重複除去（最新話採用）
→ ランダムシャッフル → 9冊選抜 → data.json として出力。

毎朝GitHub Actionsから実行する想定。
"""
import json
import random
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import requests


# ===== 設定 =====
CREDS_PATH = Path.home() / ".claude" / "amazon-creators-api.json"
OUTPUT_PATH = Path(__file__).parent / "data.json"
TARGET_COUNT = 9  # トップに表示する数
POOL_SIZE_PER_NODE = 50  # 各ノードから取得する候補数（itemCount=10 × 5ページ）

NODES = {
    "women": "5916190051",      # インディーズ女性マンガ
    "recommended": "10409694051", # Indie Recommended
}

TOKEN_URL = "https://api.amazon.co.jp/auth/o2/token"
API_BASE = "https://creatorsapi.amazon"
MARKETPLACE = "www.amazon.co.jp"

RESOURCES = [
    "images.primary.large",
    "images.primary.medium",
    "itemInfo.title",
    "itemInfo.byLineInfo",
    "itemInfo.contentInfo",
    "offersV2.listings.price",
    "browseNodeInfo.browseNodes",
]


# ===== 認証 =====
def get_access_token(creds: dict) -> str:
    r = requests.post(
        TOKEN_URL,
        json={
            "grant_type": "client_credentials",
            "client_id": creds["credential_id"],
            "client_secret": creds["secret"],
            "scope": "creatorsapi::default",
        },
        headers={"Content-Type": "application/json"},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()["access_token"]


# ===== 検索 =====
def search_browse_node(token: str, partner_tag: str, node_id: str,
                       item_page: int = 1, item_count: int = 10) -> list:
    body = {
        "browseNodeId": node_id,
        "partnerTag": partner_tag,
        "partnerType": "Associates",
        "marketplace": MARKETPLACE,
        "searchIndex": "KindleStore",
        "itemCount": item_count,
        "itemPage": item_page,
        "resources": RESOURCES,
    }
    r = requests.post(
        API_BASE + "/catalog/v1/searchItems",
        json=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "x-marketplace": MARKETPLACE,
        },
        timeout=30,
    )
    if r.status_code != 200:
        print(f"  ⚠️ node={node_id} page={item_page}: {r.status_code} {r.text[:200]}")
        return []
    return r.json().get("searchResult", {}).get("items", []) or []


# ===== フィルタ・正規化 =====
# 全角・半角数字両対応（[\d０-９]）
NUM = r"[\d０-９]+(?:[.．][\d０-９]+)?"
EPISODE_PATTERNS = [
    rf"【第?{NUM}話】",                # 【1話】【第1話】【1.5話】 anywhere
    rf"【{NUM}巻】",                   # 【1巻】 anywhere
    rf"\(\s*{NUM}\s*\)\s*$",          # (1) 末尾
    r"[①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳]\s*$",
    rf"第{NUM}話\s*$",                # 末尾「第N話」
    rf"\s*{NUM}巻\s*$",               # 末尾「N巻」
    rf"[:：]\s*第?{NUM}話.*$",         # ：第N話 以降
    # 先頭マーカー
    rf"^最終話\s*",                    # 「最終話 ...」
    rf"^第?{NUM}話\s*",                # 「N話 ...」「第N話 ...」
    rf"^【最終話】\s*",
    rf"^【第?{NUM}(?:\.\d+)?話】\s*",
    rf"^【{NUM}巻】\s*",
]
EPISODE_NUM_PATTERN = re.compile(rf"(?:第)?({NUM})話|[①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳]|\(({NUM})\)|({NUM})巻")

CIRCLED_NUM_MAP = {c: i+1 for i, c in enumerate("①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳")}


def is_free(item: dict) -> bool:
    listings = (item.get("offersV2") or {}).get("listings") or []
    for L in listings:
        amount = ((L.get("price") or {}).get("money") or {}).get("amount")
        if amount == 0:
            return True
    return False


def title_of(item: dict) -> str:
    return ((item.get("itemInfo") or {}).get("title") or {}).get("displayValue") or ""


def series_key(title: str) -> str:
    """シリーズキー（エピソードマーカーを除去）。"""
    s = title
    # 「：」「:」以降のサブタイトルを切り捨てる（「シリーズ名：第N話 サブタイトル」対応）
    s = re.split(r"[:：]", s, 1)[0].strip()
    for p in EPISODE_PATTERNS:
        s = re.sub(p, "", s).strip()
    # タイトル末尾の数字・丸数字を正規化（「レムリア３」「姉貴のカス旦那④」→ root）
    s = re.sub(r"[0-9０-９①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳]+$", "", s).strip()
    # 末尾の余分な記号・空白を除去
    s = re.sub(r"[\s　・:：\-—【】]+$", "", s).strip()
    return s


def _zen_to_han(s: str) -> str:
    return s.translate(str.maketrans("０１２３４５６７８９．", "0123456789."))


def episode_num(title: str) -> float:
    """タイトルから話数を抽出（取れなければ0、最終話は999）。"""
    if "最終話" in title:
        return 999.0
    # 丸数字
    for c in title:
        if c in CIRCLED_NUM_MAP:
            return float(CIRCLED_NUM_MAP[c])
    m = EPISODE_NUM_PATTERN.search(title)
    if m:
        for g in m.groups():
            if g:
                try:
                    return float(_zen_to_han(g))
                except ValueError:
                    pass
    return 0.0


# ===== 整形 =====
def to_card(item: dict, source: str) -> dict:
    info = item.get("itemInfo") or {}
    title = (info.get("title") or {}).get("displayValue") or "(タイトル不明)"
    contributors = ((info.get("byLineInfo") or {}).get("contributors") or [])
    author = contributors[0]["name"] if contributors else "作者不詳"

    images = (item.get("images") or {}).get("primary") or {}
    img_url = (images.get("large") or images.get("medium") or {}).get("url")

    # ジャンル推定（browseNodesから）
    nodes = (item.get("browseNodeInfo") or {}).get("browseNodes") or []
    genre = None
    for n in nodes:
        name = n.get("displayName", "")
        if "女性" in name and "インディーズ" in name:
            genre = "女性"; break
        if "少年" in name and "インディーズ" in name:
            genre = "少年"; break
        if "青年" in name and "インディーズ" in name:
            genre = "青年"; break
    if not genre:
        genre = "インディーズ"

    return {
        "asin": item.get("asin"),
        "title": title,
        "author": author,
        "image": img_url,
        "url": item.get("detailPageURL"),
        "genre": genre,
        "source": source,
    }


# ===== メイン =====
def main():
    creds = json.loads(CREDS_PATH.read_text())
    partner_tag = creds["partner_tag"]

    print(f"🔑 partner_tag={partner_tag}")
    print(f"📥 トークン取得中...")
    token = get_access_token(creds)
    print(f"   ✅ 取得完了")

    # 各ノードから候補を集める
    pool = {}  # ASIN -> (item, source)
    for source, node_id in NODES.items():
        print(f"\n📚 {source} (node {node_id}) から候補取得")
        per_page = 10
        pages = (POOL_SIZE_PER_NODE + per_page - 1) // per_page
        for page in range(1, pages + 1):
            items = search_browse_node(token, partner_tag, node_id, page, per_page)
            print(f"   page{page}: {len(items)}件")
            for it in items:
                asin = it.get("asin")
                if asin and asin not in pool:
                    pool[asin] = (it, source)
            time.sleep(0.5)  # API負荷を避ける
            if not items:
                break

    print(f"\n🧮 候補総数（重複除去後）: {len(pool)}件")

    # ¥0フィルタ
    free = [(it, src) for it, src in pool.values() if is_free(it)]
    print(f"   うち無料: {len(free)}件")

    # シリーズ重複除去（最新話採用）
    by_series = {}  # series_key -> (item, source, ep_num)
    for it, src in free:
        title = title_of(it)
        key = series_key(title)
        ep = episode_num(title)
        if key not in by_series or ep > by_series[key][2]:
            by_series[key] = (it, src, ep)
    print(f"   シリーズ重複除去後: {len(by_series)}件")

    # ランダムシャッフル → 9冊選抜
    candidates = list(by_series.values())
    random.shuffle(candidates)
    selected = candidates[:TARGET_COUNT]
    print(f"   今日のセレクト: {len(selected)}件")

    cards = [to_card(it, src) for it, src, _ in selected]

    output = {
        "generated_at": datetime.now().isoformat(),
        "count": len(cards),
        "cards": cards,
    }
    OUTPUT_PATH.write_text(json.dumps(output, ensure_ascii=False, indent=2))
    print(f"\n💾 {OUTPUT_PATH} に書き出し")
    print(f"\n=== 今日のセレクト ===")
    for i, c in enumerate(cards, 1):
        print(f"  [{i}] [{c['genre']}] {c['title'][:50]}  / {c['author']}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ ERROR: {type(e).__name__}: {e}")
        sys.exit(1)
