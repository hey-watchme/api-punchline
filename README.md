# PUNCHLINE API

POC API for extracting memorable punchlines from conversations.

## 概要

会話テキストから面白い・印象的な「パンチライン」を抽出するAPIです。2段階のパイプラインで処理：

1. **会話構造化**: 発話者識別、ターン分割、要約生成
2. **パンチライン抽出**: ユーモア・印象度評価、カテゴリ分類

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

必須環境変数：

- `OPENAI_API_KEY`: OpenAI APIキー
- `GROQ_API_KEY`: Groq APIキー（オプション）
- `SUPABASE_URL`: SupabaseプロジェクトURL
- `SUPABASE_KEY`: Supabase Anonキー
- `LLM_PROVIDER`: 使用プロバイダー（openai/groq）
- `LLM_MODEL`: 使用モデル名

## パンチライン評価基準

### Humor Score (0-100)
- 0-20: 全く面白くない
- 21-40: 少し面白い
- 41-60: 普通に面白い
- 61-80: かなり面白い
- 81-100: 爆笑レベル

### Memorability Score (0-100)
- 0-20: 忘れやすい
- 21-40: やや印象的
- 41-60: 印象的
- 61-80: とても印象的
- 81-100: 忘れられない

### Categories
- `witty_remark`: 機知に富んだ発言
- `unexpected_twist`: 予想外の展開
- `insightful_comment`: 洞察的コメント
- `emotional_moment`: 感動的瞬間
- `hilarious_joke`: 爆笑ジョーク

## トラブルシューティング

### LLMプロバイダー切り替え

```python
# llm_providers.py を編集
CURRENT_PROVIDER = "groq"  # openai → groq
CURRENT_MODEL = "llama-3.3-70b-versatile"
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

## ライセンス

Private - WatchMe Project

## サポート

Issues: https://github.com/hey-watchme/api-punchline/issues