# ペンルカ

無料漫画キュレーションサイト。羽根ペンを持った読書家のペンギン「ペンルカ」が、Amazonインディーズ漫画から無料の作品を毎日セレクトします。

- 公開URL: https://penluka.com
- X: [@penluka](https://x.com/penluka)

## 構成
- 静的サイト（HTML + CSS + Vanilla JS）
- ホスティング: GitHub Pages
- 作品データ: `data.json`（Amazon Creators APIから毎日自動取得）

## ローカル動作確認
```bash
python3 -m http.server 4173
# ブラウザで http://localhost:4173/
```

## データ更新
```bash
python3 fetch_manga.py
```
- 認証情報: `~/.claude/amazon-creators-api.json`
- ノードB（インディーズ女性マンガ）+ ノードC（Indie Recommended）から候補取得
- ¥0のみ → シリーズ重複除去 → ランダム9件選抜

## 自動更新
GitHub Actionsで毎日朝6時(JST)に `fetch_manga.py` を実行 → `data.json` 更新 → 自動デプロイ。
