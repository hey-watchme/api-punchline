# PUNCHLINE API

POC API for extracting memorable punchlines from conversations.

## 概要

会話テキストから面白い・印象的な「パンチライン」を抽出するAPIです。2段階のパイプラインで処理：

1. **会話構造化**: 発話者識別、ターン分割、要約生成
2. **パンチライン抽出**: ユーモア・印象度評価、カテゴリ分類

## 🗺️ ルーティング詳細

| 項目 | 値 | 説明 |
|------|-----|------|
| **🏷️ サービス名** | PUNCHLINE API | パンチライン抽出 |
| **📦 機能** | Conversation Analysis | 会話構造化・パンチライン抽出 |
| | | |
| **🌐 外部アクセス（Nginx）** | | |
| └ 公開エンドポイント | `https://api.hey-watch.me/punchline/` | Nginx経由の公開URL |
| └ Nginx設定ファイル | `/etc/nginx/sites-available/api.hey-watch.me` | |
| └ proxy_pass先 | `http://localhost:8060/` | 内部転送先 |
| └ タイムアウト | 180秒 | read/connect/send |
| | | |
| **🔌 API内部エンドポイント** | | |
| └ ヘルスチェック | `/health` | GET - 死活監視 |
| └ **パンチライン抽出** | `/extract-punchlines` | POST - メイン処理 |
| └ 結果取得 | `/extract/{request_id}` | GET - 抽出結果取得 |
| └ 履歴取得 | `/history?user_id={id}` | GET - ユーザー履歴 |
| | | |
| **🐳 Docker/コンテナ** | | |
| └ コンテナ名 | `punchline-api` | |
| └ ポート（内部） | 8060 | コンテナ内 |
| └ ポート（公開） | `8060:8060` | |
| └ ヘルスチェック | `/health` | Docker healthcheck |
| | | |
| **☁️ AWS ECR** | | |
| └ リポジトリ名 | `punchline_api_profiler` | |
| └ リージョン | ap-southeast-2 (Sydney) | |
| └ URI | `754724220380.dkr.ecr.ap-southeast-2.amazonaws.com/punchline_api_profiler:latest` | |
| | | |
| **📂 ディレクトリ** | | |
| └ ソースコード | `/Users/kaya.matsumoto/projects/PUNCHLINE` | ローカル |
| └ GitHubリポジトリ | `hey-watchme/api-punchline` | |
| └ EC2配置場所 | `/home/ubuntu/punchline-api` | |

## 技術スタック

- **Framework**: FastAPI
- **LLM**: OpenAI GPT-5 nano / Groq
- **Database**: Supabase
- **Deployment**: Docker on EC2
- **CI/CD**: GitHub Actions → AWS ECR → EC2

## APIエンドポイント

### Health Check
```bash
GET /health
```

### Extract Punchlines (メイン機能)
```bash
POST /extract-punchlines

# Request Body
{
  "conversation_text": "会話テキスト",
  "user_id": "optional-user-id",
  "context": {
    "topic": "meeting",
    "participants": ["Alice", "Bob"]
  }
}

# Response
{
  "status": "success",
  "request_id": "uuid",
  "structured_conversation": {...},
  "punchlines": [
    {
      "rank": 1,
      "text": "抽出されたパンチライン",
      "speaker": "Speaker A",
      "humor_score": 85,
      "memorability_score": 90,
      "category": "witty_remark",
      "reasoning": "選定理由"
    }
  ],
  "metadata": {
    "total_punchlines": 5,
    "processing_time_ms": 3500
  }
}
```

### Get Result by ID
```bash
GET /extract/{request_id}
```

### Get User History
```bash
GET /history?user_id={user_id}&limit=10
```

### Extract from WatchMe Data (POC検証用)
```bash
POST /extract-from-watchme

# Request Body
{
  "device_id": "5638e419-67d1-457b-8415-29f5f0a4ef98",
  "local_date": "2026-01-21",
  "local_time": "2026-01-21 08:57:05.078"  # オプション
}

# Response
{
  "status": "success",
  "request_id": "uuid",
  "structured_conversation": {
    "speakers": ["Speaker A", "Speaker B"],  # LLMが文脈から推測
    "turns": [...],
    "summary": "会話の要約"
  },
  "punchlines": [...],
  "metadata": {
    "source": "watchme_spot_features",
    "device_id": "...",
    "local_date": "...",
    "processing_time_ms": 36000
  }
}
```

## WatchMeデータを使ったテスト（POC検証）

### 概要
PUNCHLINEサービスの価値検証のため、WatchMeの既存トランスクリプションデータ（spot_featuresテーブル）を活用できます。新規録音不要で、豊富な実データでテストが可能です。

### データソース

PUNCHLINEは独自のトランスクリプション機能を持たないため、**WatchMeのインフラ（spot_featuresテーブル）** を借りてテストします。

**テストに必要な情報**:
- **データベース**: WatchMe Supabase `spot_features` テーブル
- **指定する値**:
  - `device_id`: デバイスID
  - `local_date`: 録音日（YYYY-MM-DD）
  - `local_time`: 録音時刻（YYYY-MM-DD HH:MM:SS.mmm）※オプション

**テストの流れ**:
1. ユーザーからデータベースの特定レコード（device_id, local_date, local_time）が指定される
2. その値を使って `/extract-from-watchme` エンドポイントにPOSTリクエスト
3. APIが自動的にSupabaseから該当する`vibe_transcriber_result`を取得
4. パンチライン抽出処理を実行
5. 結果を確認

**重要**: トランスクリプション内容は手動で渡す必要はありません。APIが自動的にデータベースから取得します。

### テスト方法

#### 1. データベースのレコードを指定してテスト（推奨）

指定された`device_id`、`local_date`、`local_time`を使用：

```bash
# 例: 指定されたデータベースレコードでテスト
# --max-time 120: 最大120秒待機（LLM処理に30-40秒かかるため）
# 2>&1: 進捗表示を有効化
curl --max-time 120 -X POST https://api.hey-watch.me/punchline/extract-from-watchme \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "5638e419-67d1-457b-8415-29f5f0a4ef98",
    "local_date": "2026-01-22",
    "local_time": "2026-01-22 23:17:41.038"
  }' 2>&1 | jq '.'
```

**ポイント**:
- ユーザーから指定された`device_id`、`local_date`、`local_time`を使用
- APIが自動的にSupabaseから該当する`vibe_transcriber_result`を取得
- トランスクリプション内容を手動で渡す必要はなし
- **処理時間**: 2段階LLM処理のため30-40秒かかる（タイムアウト設定推奨）

#### 2. 基本的なテスト（device_id + local_dateのみ）

```bash
curl --max-time 120 -X POST https://api.hey-watch.me/punchline/extract-from-watchme \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "5638e419-67d1-457b-8415-29f5f0a4ef98",
    "local_date": "2026-01-21"
  }' 2>&1 | jq '.'
```

**動作**: その日の最新の録音データを自動取得

#### 3. 特定の録音を指定（local_time付き）

```bash
curl --max-time 120 -X POST https://api.hey-watch.me/punchline/extract-from-watchme \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "5638e419-67d1-457b-8415-29f5f0a4ef98",
    "local_date": "2026-01-21",
    "local_time": "2026-01-21 08:57:05.078"
  }' 2>&1 | jq '.'
```

**動作**: 指定した時刻の録音データを正確に取得

### データフロー
1. spot_featuresテーブルから`vibe_transcriber_result`を取得
2. Pipeline 1: 会話構造化（話者分離、ターン分割）
3. Pipeline 2: パンチライン抽出（スコアリング、カテゴリ分類）
4. 結果をpunchline_requestsテーブルに保存

### 注意事項
- **話者分離（ダイアライゼーション）について**
  - WatchMeのトランスクリプションには話者情報が含まれていません
  - LLMが文脈・内容から話者交代を推測して分離します
  - 実際の話者とは異なる可能性があります
- **local_time省略時**
  - その日の最新の録音データを取得します
- **処理時間**
  - 2段階のLLM処理のため、30-40秒程度かかります

## ローカル開発

### セットアップ

1. 環境変数設定
```bash
cp .env.example .env
# .envファイルを編集してAPIキーを設定
```

2. 依存パッケージインストール
```bash
pip3 install -r requirements.txt
```

3. ローカル実行
```bash
python3 main.py
# http://localhost:8060 でアクセス可能
```

### 構文チェック
```bash
# Python構文チェック
python3 -m py_compile main.py
python3 -m py_compile llm_providers.py
python3 -m py_compile supabase_client.py

# エンコーディング確認
file *.py
```

## データベース設計

### punchline_requests
- `request_id` (UUID): リクエストID
- `conversation_text` (TEXT): 会話テキスト
- `user_id` (TEXT): ユーザーID
- `context_data` (JSONB): コンテキスト情報
- `created_at` (TIMESTAMPTZ): 作成日時

### punchline_structured_conversations
- `request_id` (UUID): リクエストID参照
- `structured_result` (JSONB): 構造化結果
- `speakers` (JSONB): 発話者リスト
- `turn_count` (INTEGER): ターン数
- `summary` (TEXT): 要約

### punchline_results
- `result_id` (UUID): 結果ID
- `request_id` (UUID): リクエストID参照
- `punchlines` (JSONB): パンチライン配列
- `metadata` (JSONB): メタデータ
- `llm_model` (TEXT): 使用モデル

## デプロイ

### GitHub経由の自動デプロイ

```bash
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

## 環境変数

### 必須環境変数

- `OPENAI_API_KEY`: OpenAI APIキー
- `GROQ_API_KEY`: Groq APIキー（Groq使用時）
- `SUPABASE_URL`: SupabaseプロジェクトURL
- `SUPABASE_KEY`: Supabase Anonキー

### LLMモデル切り替え

**現在の本番設定**: `GPT-4.1` (OpenAI)

**方法1: プリセット使用（推奨）**

```bash
# .env ファイルに設定
LLM_PRESET=gpt-4.1
```

利用可能なプリセット:
- `gpt-4.1` - GPT-4.1（現在の本番設定）
- `gpt-5-nano` - GPT-5 Nano（軽量・高速）
- `gpt-4o` - GPT-4 Optimized
- `gpt-4o-mini` - GPT-4 Mini
- `o1` - O1（推論特化）
- `o1-mini` - O1 Mini
- `llama-3.3-70b` - Llama 3.3 70B（Groq）
- `llama-3.1-8b` - Llama 3.1 8B（Groq・高速）
- `gpt-oss-120b` - GPT OSS 120B（Groq・推論）

**方法2: 直接指定**

```bash
# .env ファイルに設定
LLM_PROVIDER=openai
LLM_MODEL=gpt-4.1
LLM_REASONING_EFFORT=medium  # Groq推論モデルのみ
LLM_MAX_TOKENS=8192
```

**GitHub Secretsでの設定（本番環境）**

```bash
# GitHub Secrets に追加
LLM_PRESET=gpt-4.1
```

モデル切り替え後、コンテナ再起動のみで反映（コード変更不要）

## パンチライン評価基準（v0.2.0以降）

### 評価コンセプト：SNS時代の「バズる名言」抽出

このAPIは、単なる「面白い発言」ではなく、**SNSでシェアしたくなる、話者の魅力が伝わるパンチライン**を抽出します。

### 評価指標

#### Status Score (0-100)
「これをシェアしたら、話者が頭いい・面白いと思ってもらえるか？」という承認欲求の充足度。

- 80点未満: 普通の発言
- 80-89点: シェアしたくなる
- 90-95点: フォロワーが増えそう
- 96-100点: バズる可能性

#### Shareability (0-100)
「TikTokやXで流れてきたら、思わず指が止まるか？」という瞬発的なインパクト。

- 70点未満: スルーされる
- 70-79点: 立ち止まる
- 80-89点: 保存したくなる
- 90-100点: 拡散したくなる

### カテゴリ

- `Deep`: 核心を突いた哲学的な一言
- `Sharp`: 既存の概念を壊すような新しい視点
- `Authentic`: 飾らない言葉で出た、本音の重み
- `Witty`: 言葉遊びや、絶妙な例え話

### 新機能：リアクションパネル（AI観客）

各パンチラインに対して、3人のAI観客が反応します：

1. **エディ**: ツッコミ担当。「出たよｗ」「ドヤ顔確定演出」
2. **ミーナ**: 共感・盛り上げ担当。「待って天才ｗ」「エモすぎ無理」
3. **博士**: 冷静・分析担当。「これは希少な肉声だ」「エントロピーが高いね」

各反応は15文字以内の短いコメントで、ショート動画のワイプ風演出に使えます。

### タグ付け機能

会話の内容を分類するキーワードを自動生成：
- 例：`#起業`、`#人生観`、`#恋バナ`、`#技術論`

---

## プロンプト設計思想（v0.2.0）

### Pipeline 1: 保守的・音声復元エンジニア

**核心原則：最小介入（Minimum Intervention）**

- 原文が日本語として意味を成している場合は一切変更しない
- 語調・敬語の維持（「はい」を「うん」に変えるなどの改変厳禁）
- 音響的な聞き間違いのみを修復
- 捏造の禁止（推測で無理に修正しない）

### Pipeline 2: 毒舌カリスマ・エディター

**キャラクター設定：**
- フレンドリーかつRude（失礼）
- SNSノリ（「〜じゃん」「〜すぎる笑」「ぶっちゃけ」「ズルい」）
- 煽りと賞賛の同居（「よくそんなドヤ顔で言えたね（笑）」＋「でもこれ、本質すぎて悔しいわ…」）

**出力スタイル：**
- reasoning: 丁寧な解説ではなく、愛を持ったイジり＋渾身の賞賛
- 例：「いやこれズルすぎ笑。悔しいけどめっちゃ強すぎ。」

## プロンプト管理

### プロンプトファイルの場所

プロンプトは以下のディレクトリに格納されています：

```
/Users/kaya.matsumoto/projects/PUNCHLINE/api/profiler/prompts/
├── structure_conversation.txt  # Pipeline 1: 会話構造化プロンプト
└── extract_punchlines.txt       # Pipeline 2: パンチライン抽出プロンプト
```

### ⚠️ 重要：プロンプト変更時の必須作業

**プロンプトでJSONフィールドを追加/変更する場合は、必ず2箇所を更新してください：**

#### 問題の本質

プロンプトで新しいフィールドを定義しても、`main.py`のPydanticモデルに定義されていないと、**LLMが生成したデータがバリデーションで自動的に捨てられます**。

#### 修正が必要な2箇所

1. **プロンプトファイル** (`prompts/extract_punchlines.txt`)
   - LLMに出力させるJSON構造を定義

2. **Pydanticモデル** (`main.py` の `PunchlineResponse` クラス)
   - APIが受け取るデータ構造を定義

#### 例：新フィールド追加時

```python
# main.py の PunchlineResponse クラスに追加
class PunchlineResponse(BaseModel):
    rank: int
    text: str
    speaker: str
    # ... 既存フィールド ...
    new_field: Optional[str] = None  # ← 新しいフィールドを追加
```

#### チェックリスト

プロンプト変更時：
- [ ] プロンプトファイルを編集
- [ ] `main.py`のPydanticモデルを更新
- [ ] 両方をGitHubにプッシュ
- [ ] デプロイ後にテスト実行

---

## トラブルシューティング

### ローカルテストの制限事項

**⚠️ 重要: ローカル環境でのテストはCORS問題により動作しません**

### LLMモデル切り替えが反映されない

```bash
# EC2上でコンテナ再起動
ssh -i ~/watchme-key.pem ubuntu@3.24.16.82
cd /home/ubuntu/punchline-api
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d

# ログでモデル確認
docker logs punchline-api --tail 50 | grep "Using LLM"
```

### エラー対応

1. **JSON抽出エラー**: LLMレスポンス形式を確認
2. **タイムアウト**: 処理時間制限を調整
3. **データベースエラー**: Supabase接続を確認

## 今後の拡張計画

1. **Phase 2**: 音声入力対応（STT統合）
2. **Phase 3**: Web UI開発
3. **Phase 4**: リアルタイム分析
4. **Phase 5**: パーソナライゼーション

## 更新履歴

### 2026-01-24 - v0.2.0（プロンプト大幅刷新＋リアクションパネル機能）

**プロンプト設計の根本的な見直し：**

#### Pipeline 1（会話構造化）の変更
- **旧**: 文脈依存型・積極的な音声復元エンジニア
- **新**: 保守的・音声復元エンジニア（最小介入原則）
  - 原文尊重の徹底
  - 語調・敬語の維持厳守
  - 音響的な聞き間違いのみ修復
  - 捏造の禁止

#### Pipeline 2（パンチライン抽出）の変更
- **旧**: カリスマ・コンテンツエディター（丁寧な解説スタイル）
- **新**: 毒舌カリスマ・エディター（SNSノリ＋愛のあるイジり）
  - キャラクター設定追加（フレンドリー＆Rudeなトーン）
  - reasoningを「煽り＋賞賛」スタイルに変更
  - 例：「いやこれズルすぎ笑。悔しいけどめっちゃ強すぎ。」

#### 評価基準の変更
- **旧**: Humor Score / Memorability Score
- **新**: Status Score / Shareability
  - SNS時代に特化した評価軸
  - 「承認欲求の充足度」「瞬発的なインパクト」を測定

#### 新機能追加
- **リアクションパネル（AI観客3人）**:
  - エディ（ツッコミ担当）
  - ミーナ（共感・盛り上げ担当）
  - 博士（冷静・分析担当）
  - 各15文字以内の短いコメント
  - ショート動画のワイプ風演出に対応
- **タグ付け機能**: 会話内容を分類するキーワード自動生成（#起業、#人生観など）

#### データ構造の変更
- `PunchlineResponse`モデルに`tags`フィールド追加
- `PunchlineResponse`モデルに`panel_reactions`フィールド追加
- Pydanticバリデーション問題の修正

**影響範囲:**
- プロンプトファイル2つを全面刷新
- main.pyのPydanticモデル更新
- README.mdのドキュメント大幅更新

### 2026-01-21 - v0.1.1（WatchMeデータ連携）
- **WatchMe連携機能追加**: `/extract-from-watchme` エンドポイント実装
- **spot_featuresテーブル統合**: device_id + local_dateでトランスクリプション取得
- **話者分離機能**: LLMによる文脈ベースの話者推測（ダイアライゼーション）
- **本番環境テスト成功**:
  - 処理時間: 約36秒（改善）
  - LLMモデル: GPT-4.1に更新
  - 実データでのパンチライン抽出確認
- **POC検証環境構築**: 新規録音不要でテスト可能に

### 2026-01-20 - v0.1.0（POC初回リリース）
- **プロジェクト初期構築**: PUNCHLINE API POC完成
- **2段階パイプライン実装**: 会話構造化 → パンチライン抽出
- **LLM統合**: OpenAI GPT-4.1対応
- **Supabaseデータベース**: 3テーブル構成（requests, structured_conversations, results）
- **CI/CD構築**: GitHub Actions → AWS ECR → EC2自動デプロイ
- **Docker化**: ARM64対応、ポート8060で稼働
- **Nginx設定**: `https://api.hey-watch.me/punchline/` で公開
- **初回テスト成功**:
  - 処理時間: 約122秒（2段階LLM処理）
  - 発話者識別・ターン分割正常動作
  - ユーモアスコアリング（0-100）実装
  - Top 5パンチライン抽出成功
- **WatchMeインフラ活用**: EC2、ECR、Supabaseを共用

## ライセンス

Private - WatchMe Project

## サポート

Issues: https://github.com/hey-watchme/api-punchline/issues