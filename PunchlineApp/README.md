# PUNCHLINE iOS App

iOS client for the PUNCHLINE service - Extract memorable moments from conversations

## 概要

PUNCHLINEは、会話から印象的な「パンチライン」を抽出・表示するiOSアプリです。WatchMeインフラを活用し、既存のトランスクリプションデータから面白い・印象的な発言を見つけ出します。

## 機能

- 📱 **Instagram風フィード** - パンチラインをカード形式で表示
- 🎯 **スコアリング** - ユーモア度・記憶度をビジュアル表示
- 💾 **Supabase連携** - punchline_resultsテーブルからデータ取得
- 🎨 **モダンUI** - SwiftUI + Combineによる実装

## 技術スタック

- **Framework**: SwiftUI
- **最小iOS**: 15.0+
- **Database**: Supabase (WatchMeと共用)
- **API**: PUNCHLINE API (`https://api.hey-watch.me/punchline/`)
- **Package Manager**: Swift Package Manager

## セットアップ

### 1. プロジェクトを開く

```bash
cd /Users/kaya.matsumoto/projects/PUNCHLINE/PunchlineApp
open PunchlineApp.xcodeproj
```

### 2. パッケージ依存関係

Supabase Swift SDKは自動的にインストールされます：
- `supabase-swift` v2.40.0

### 3. ビルド＆実行

1. シミュレーターを選択（iPhone 15 Pro推奨）
2. `Cmd + R`で実行

## プロジェクト構造

```
PunchlineApp/
├── PunchlineApp.xcodeproj
└── PunchlineApp/
    ├── Configuration.swift      # API設定
    ├── SupabaseClient.swift    # Supabase接続
    ├── PunchlineModels.swift   # データモデル
    ├── PunchlineService.swift  # API層
    ├── PunchlineFeedView.swift # メインフィード
    └── PunchlineCardView.swift # カードUI
```

## データフロー

```
Supabase (punchline_results)
    ↓
PunchlineService.fetchAllPunchlines()
    ↓
JSON配列をフラット化
    ↓
PunchlineFeedView (表示)
```

## 開発状況

### ✅ 完了
- Supabase連携
- データモデル定義
- Instagram風フィードUI
- パンチラインカード表示
- スコア表示（ユーモア・記憶度）
- いいね・保存ボタン（UI）

### 🚧 今後の実装予定
- 音声再生機能
- 新規パンチライン投稿
- ユーザー認証
- いいね・保存の永続化
- 検索・フィルター機能

## トラブルシューティング

### Supabaseエラー
- APIキーが正しいか確認 (`Configuration.swift`)
- WatchMeと同じ認証情報を使用

### ビルドエラー
1. Clean Build Folder (`Cmd + Shift + K`)
2. Packages → Resolve Package Versions
3. ターゲットにSupabaseがリンクされているか確認

## 関連プロジェクト

- **PUNCHLINE API**: `/Users/kaya.matsumoto/projects/PUNCHLINE`
- **WatchMe iOS**: `/Users/kaya.matsumoto/ios_watchme_v9`
- **WatchMe Infrastructure**: `/Users/kaya.matsumoto/projects/watchme`

## 更新履歴

### 2026-01-22 - v0.1.0
- 初期バージョンリリース
- Supabase連携実装
- Instagram風フィードUI完成
- punchline_resultsからのデータ取得成功

## ライセンス

Private - PUNCHLINE Project

## サポート

Issues: https://github.com/hey-watchme/punchline-ios-app/issues