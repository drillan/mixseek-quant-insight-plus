# Troubleshooting

mixseek-quant-insight-plus 使用時に発生する可能性のあるエラーと対処法です。

## Claude Code CLI

### claude コマンドが見つからない

Claude Code CLI がインストールされていません。

```bash
# macOS / Linux / WSL
curl -fsSL https://claude.ai/install.sh | bash

# Homebrew (macOS)
brew install --cask claude-code

# インストール確認
claude --version
```

### セッションが無効です

Claude Code CLI のセッションが期限切れになっています。再認証が必要です。

```bash
claude
```

初回起動時または再認証時に、ブラウザで認証フローが開始されます。

## DuckDB

### RuntimeError: DuckDB スキーマが初期化されていない

`ClaudeCodeLocalCodeExecutorAgent` の初期化時に `_verify_database_schema()` が DuckDB の `agent_implementation` テーブルを検出できない場合に発生します。

```bash
# DuckDB スキーマを初期化
export MIXSEEK_WORKSPACE=/path/to/workspace
qip db init
```

ワークスペースの `mixseek.db` に `agent_implementation` テーブルが作成されます。

### DatabaseReadError

DuckDB からのスクリプト読み込みに失敗した場合に発生します。`_enrich_task_with_existing_scripts()` メソッド内で `list_scripts()` または `read_script()` が失敗したときに送出されます。

**考えられる原因:**

- DB ファイル（`mixseek.db`）が破損している
- ディスク容量不足
- 他のプロセスが DB ファイルをロックしている

**対処法:**

```bash
# DB ファイルの存在確認
ls -la $MIXSEEK_WORKSPACE/mixseek.db

# ディスク容量の確認
df -h $MIXSEEK_WORKSPACE

# DB を再初期化（既存データは失われます）
qip db init
```

> **重要**: `DatabaseReadError` は明示的に伝播されます。スクリプト埋め込みが失敗した場合、エンリッチなしで処理を続行することはありません。

### DatabaseWriteError

スクリプトの DuckDB への書き込みが3回のリトライ後も失敗した場合に発生します。

**考えられる原因:**

- ディスク容量不足
- DB ファイルの書き込み権限なし
- 一時的なファイルシステムエラー

## 設定ファイル

### ValueError: 認証失敗または TOML 設定不足

TOML 設定ファイルに必須項目が不足している、またはモデル認証に失敗した場合に発生します。

**チェックリスト:**

- [ ] `[agent]` セクションに `type`, `name`, `model` が設定されているか
- [ ] `type` が `"claudecode_local_code_executor"` であるか
- [ ] `model` が `claudecode:` プレフィックスで始まっているか
- [ ] `claude --version` が正常に動作するか
- [ ] `[agent.system_instruction]` セクションに `text` が設定されているか

### エージェントタイプが認識されない

TOML の `type = "claudecode_local_code_executor"` が `MemberAgentFactory` に登録されていない場合に発生します。

**CLI 使用時:**

CLI（`qip`）は自動的にエージェントを登録するため、通常はこのエラーは発生しません。

**ライブラリ使用時:**

```python
import mixseek_plus
from quant_insight_plus import register_claudecode_quant_agents

# 必ずこの順序で呼び出す
mixseek_plus.patch_core()
register_claudecode_quant_agents()
```

### output_model のクラスが見つからない

`output_model.module_path` または `output_model.class_name` の指定が誤っている場合に発生します。

**確認方法:**

```python
# モジュールパスとクラス名が正しいか確認
from quant_insight.agents.local_code_executor.output_models import AnalyzerOutput
print(AnalyzerOutput.model_json_schema())
```

**利用可能な出力モデル:**

| class_name | module_path | 用途 |
|------------|-------------|------|
| `AnalyzerOutput` | `quant_insight.agents.local_code_executor.output_models` | データ分析 |
| `SubmitterOutput` | `quant_insight.agents.local_code_executor.output_models` | Submission 作成 |

## 実行時エラー

### タイムアウト

エージェントの実行がタイムアウトした場合の対処法です。タイムアウトは複数のレベルで設定されています。

| レベル | 設定場所 | デフォルト | 説明 |
|--------|---------|----------|------|
| コード実行 | `tool_settings.local_code_executor.timeout_seconds` | `120` | 個別のコード実行タイムアウト |
| リクエスト | `agent.timeout_seconds` | `30.0` | LLM リクエストタイムアウト |
| チーム | `orchestrator.timeout_per_team_seconds` | `3600` | チーム全体のタイムアウト |

```toml
# コード実行のタイムアウトを延長
[agent.metadata.tool_settings.local_code_executor]
timeout_seconds = 300  # 5分

# チーム全体のタイムアウトを延長
[orchestrator]
timeout_per_team_seconds = 7200  # 2時間
```

### MIXSEEK_WORKSPACE 未設定

`MIXSEEK_WORKSPACE` 環境変数が設定されていない場合、ワークスペースの検出に失敗します。

```bash
export MIXSEEK_WORKSPACE=/path/to/workspace
```

## よくある質問

### Gemini 版との違いは？

[User Guide](user-guide.md) の「Gemini 版との差分」セクションを参照してください。主な差分は、コード実行方式（pydantic-ai ツール vs Claude Code 組み込みツール）とスクリプト参照方式です。

### API キーは必要？

`claudecode:` プレフィックスは Claude Code CLI のセッション認証を使用するため、API キーの環境変数は不要です。`claude --version` が正常に動作すれば認証済みです。

### CLI と Python ライブラリの違いは？

CLI（`qip`）は起動時に `patch_core()` とエージェント登録を自動実行します。Python ライブラリとして使用する場合は、明示的にこれらを呼び出す必要があります。詳細は [Getting Started](getting-started.md) の「ライブラリとして使用する場合」セクションを参照してください。
