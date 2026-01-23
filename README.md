# PUNCHLINE Project

Extract memorable moments from conversations.

## 概要

PUNCHLINEは、会話から印象的な「パンチライン」（面白い・記憶に残る発言）を抽出・表示するプロジェクトです。

**特徴**:
- WatchMeのインフラ（Supabase、EC2、トランスクリプションデータ）を活用
- 2段階のLLMパイプライン：会話構造化 → パンチライン抽出
- iOSアプリとAPIで構成

## プロジェクト構成

```
PUNCHLINE/
├── api/
│   └── profiler/              # Profiler API（パンチライン抽出）
│       ├── main.py
│       ├── llm_providers.py
│       ├── supabase_client.py
│       ├── hume_processor.py
│       ├── prompts/
│       ├── docker-compose.prod.yml
│       ├── Dockerfile.prod
│       ├── requirements.txt
│       └── README.md          # API詳細ドキュメント
├── PunchlineApp/              # iOSアプリ
│   ├── PunchlineApp.xcodeproj
│   ├── PunchlineApp/
│   │   ├── PunchlineFeedView.swift
│   │   ├── PunchlineCardView.swift
│   │   └── ...
│   └── README.md              # iOSアプリドキュメント
├── docs/                      # プロジェクトドキュメント
├── .github/workflows/         # CI/CD設定
└── README.md                  # このファイル
```

## APIサービス

### Profiler API

**役割**: 会話から印象的なパンチラインを抽出

**詳細**: [api/profiler/README.md](api/profiler/README.md)

**エンドポイント**: `https://api.hey-watch.me/punchline/`

**主要機能**:
- `/extract-punchlines` - テキストからパンチライン抽出
- `/extract-from-watchme` - WatchMeデータベースからパンチライン抽出
- `/health` - ヘルスチェック

## iOSアプリ

**役割**: パンチラインをInstagram風フィードで表示

**詳細**: [PunchlineApp/README.md](PunchlineApp/README.md)

**主要機能**:
- パンチラインフィード表示
- ユーモア度・記憶度スコア表示
- カード型UI

## クイックスタート

### APIのテスト

```bash
# ヘルスチェック
curl https://api.hey-watch.me/punchline/health

# WatchMeデータを使ったパンチライン抽出
curl -X POST https://api.hey-watch.me/punchline/extract-from-watchme \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "5638e419-67d1-457b-8415-29f5f0a4ef98",
    "local_date": "2026-01-22",
    "local_time": "2026-01-22 23:17:41.038"
  }'
```

### iOSアプリのビルド

```bash
cd PunchlineApp
open PunchlineApp.xcodeproj
# Xcodeで Cmd + R で実行
```

## 技術スタック

**Backend**:
- FastAPI
- OpenAI GPT-4.1 / Groq
- Supabase (WatchMeと共用)
- Docker on EC2

**Frontend**:
- SwiftUI
- Combine
- Supabase Swift SDK

**Infrastructure**:
- AWS EC2 (Sydney)
- AWS ECR
- GitHub Actions (CI/CD)
- Nginx (リバースプロキシ)

## データフロー

```
WatchMe spot_features テーブル（トランスクリプション）
    ↓
PUNCHLINE Profiler API
    ↓ Pipeline 1: 会話構造化（話者分離、ターン分割）
    ↓ Pipeline 2: パンチライン抽出（スコアリング、カテゴリ分類）
    ↓
punchline_results テーブル
    ↓
PUNCHLINE iOS App（フィード表示）
```

## デプロイ

### APIデプロイ

```bash
cd api/profiler
git add .
git commit -m "Update: feature description"
git push origin main
# GitHub Actionsが自動でECRビルド → EC2デプロイ
```

### デプロイ確認

```bash
# CI/CD状況確認
gh run watch

# ヘルスチェック
curl https://api.hey-watch.me/punchline/health

# ログ確認（EC2上）
ssh -i ~/watchme-key.pem ubuntu@3.24.16.82
docker logs punchline-api --tail 100 -f
```

## 開発状況

### ✅ 完了（v0.1.1）
- Profiler API実装（2段階パイプライン）
- WatchMeデータ連携（spot_features統合）
- LLM話者分離機能
- iOSアプリ基本実装（フィード表示）
- CI/CD構築（GitHub Actions）
- EC2本番環境デプロイ

### 🚧 今後の実装予定
- 音声再生機能
- 新規パンチライン投稿（独自トランスクリプション）
- ユーザー認証
- いいね・保存の永続化
- 検索・フィルター機能

## 関連プロジェクト

- **WatchMe Infrastructure**: `/Users/kaya.matsumoto/projects/watchme`
- **WatchMe iOS**: `/Users/kaya.matsumoto/ios_watchme_v9`
- **WatchMe Server Configs**: `/Users/kaya.matsumoto/projects/watchme/server-configs`

## ライセンス

Private - PUNCHLINE Project

## サポート

Issues: https://github.com/hey-watchme/api-punchline/issues
