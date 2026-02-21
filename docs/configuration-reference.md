# Configuration Reference

mixseek-quant-insight-plus で使用する全設定ファイルのリファレンスです。

## Member Agent 設定

### `[agent]` セクション

| 項目 | 型 | 必須 | デフォルト | 説明 |
|------|-----|------|----------|------|
| `type` | `str` | はい | — | `"claudecode_local_code_executor"` を指定 |
| `name` | `str` | はい | — | エージェント名（チーム内で一意） |
| `model` | `str` | はい | — | モデルID（例: `claudecode:claude-opus-4-6`） |
| `description` | `str` | いいえ | `""` | エージェントの説明（Leader がタスク委譲時に参照） |
| `temperature` | `float` | いいえ | モデル依存 | 生成の温度パラメータ |
| `max_tokens` | `int` | いいえ | モデル依存 | 最大トークン数 |
| `max_retries` | `int` | いいえ | `1` | リトライ回数 |
| `timeout_seconds` | `float` | いいえ | `30.0` | リクエストタイムアウト秒数 |

### `[agent.system_instruction]` セクション

| 項目 | 型 | 必須 | 説明 |
|------|-----|------|------|
| `text` | `str` | はい | エージェントへのシステム指示（複数行可） |

### `[agent.metadata.tool_settings.local_code_executor]` セクション

`LocalCodeExecutorConfig` に対応する設定です。

| 項目 | 型 | 必須 | デフォルト | 説明 |
|------|-----|------|----------|------|
| `available_data_paths` | `list[str]` | いいえ | `[]` | 利用可能なデータファイルパス（`$MIXSEEK_WORKSPACE` からの相対パス） |
| `timeout_seconds` | `int` | いいえ | `120` | コード実行のタイムアウト秒数（0より大きい値） |
| `max_output_chars` | `int \| null` | いいえ | `null` | 最大出力文字数（`null` = 無制限） |
| `python_command` | `str` | はい | — | Python 実行コマンド（例: `"uv run python"`）。システム指示の `{python_command}` プレースホルダーに注入される |

### `[agent.metadata.tool_settings.local_code_executor.output_model]` セクション

構造化出力モデルの設定です。省略時は `str` 型が使用されます。

| 項目 | 型 | 必須 | 説明 |
|------|-----|------|------|
| `module_path` | `str` | はい | 出力モデルのモジュールパス |
| `class_name` | `str` | はい | 出力モデルのクラス名 |

**利用可能な出力モデル:**

| クラス名 | モジュールパス | 用途 |
|---------|-------------|------|
| `FileAnalyzerOutput` | `quant_insight_plus.agents.output_models` | データ分析エージェント |
| `FileSubmitterOutput` | `quant_insight_plus.agents.output_models` | Submission 作成エージェント |

#### FileAnalyzerOutput のフィールド

| フィールド | 型 | 説明 |
|-----------|-----|------|
| `analysis_path` | `str` | 書き込んだ `analysis.md` の絶対パス |
| `report` | `str` | Markdown 形式の分析結果レポート |

#### FileSubmitterOutput のフィールド

| フィールド | 型 | 説明 |
|-----------|-----|------|
| `submission_path` | `str` | 書き込んだ `submission.py` の絶対パス |
| `description` | `str` | Submission の概要や動作確認結果（Markdown 形式） |

### 設定例

**データ分析エージェント（train_analyzer）:**

```toml
[agent]
type = "claudecode_local_code_executor"
name = "train-analyzer"
model = "claudecode:claude-opus-4-6"
description = "ClaudeCodeでPythonコード実行・trainデータ分析を行う"
temperature = 0.0

[agent.system_instruction]
text = """
あなたはデータ分析エージェントです。
trainデータに対する分析を行い、結果を報告してください。
"""

[agent.metadata.tool_settings.local_code_executor]
available_data_paths = [
    "data/inputs/ohlcv/train.parquet",
    "data/inputs/master/train.parquet",
    "data/inputs/returns/train.parquet",
]
timeout_seconds = 120
python_command = "uv run python"

[agent.metadata.tool_settings.local_code_executor.output_model]
module_path = "quant_insight_plus.agents.output_models"
class_name = "FileAnalyzerOutput"
```

**Submission 作成エージェント（submission_creator）:**

```toml
[agent]
type = "claudecode_local_code_executor"
name = "submission-creator"
model = "claudecode:claude-opus-4-6"
description = "ClaudeCodeでSubmissionスクリプトを実装・動作確認する"
temperature = 0.0

[agent.system_instruction]
text = """
リーダーの指示に従い、最終Submissionスクリプトを実装します。
"""

[agent.metadata.tool_settings.local_code_executor]
available_data_paths = [
    "data/inputs/ohlcv/valid.parquet",
    "data/inputs/master/valid.parquet",
]
timeout_seconds = 300
python_command = "uv run python"

[agent.metadata.tool_settings.local_code_executor.output_model]
module_path = "quant_insight_plus.agents.output_models"
class_name = "FileSubmitterOutput"
```

## ClaudeCode プリセット設定（claudecode.toml）

ClaudeCode プロバイダのツール権限を名前付きプリセットとして定義します。プリセットファイルは `configs/presets/claudecode.toml` に配置します。

### プリセットの参照

チーム設定の `[team.leader.tool_settings.claudecode]` セクションで `preset` キーを指定します。

```toml
[team.leader.tool_settings.claudecode]
preset = "delegate_only"
```

### プリセット項目

各プリセットセクション（例: `[delegate_only]`）で設定可能な項目です。

| 項目 | 型 | 必須 | 説明 |
|------|-----|------|------|
| `permission_mode` | `str` | はい | ツール権限モード（例: `"bypassPermissions"`） |
| `disallowed_tools` | `list[str]` | いいえ | ブロックするツール名のリスト |

### 組み込みプリセット

#### `delegate_only`

Leader がメンバーへの作業委譲のみを行うプリセットです。コーディングツールとメタツールの両方をブロックし、MCP 経由のメンバーツールのみ使用可能にします。

```toml
[delegate_only]
permission_mode = "bypassPermissions"
disallowed_tools = [
  # コーディングツール
  "Bash", "Write", "Edit", "Read", "Glob", "Grep",
  "WebFetch", "WebSearch", "NotebookEdit", "Task",
  # メタツール（承認者不在で無限ループを引き起こす）
  "EnterPlanMode", "ExitPlanMode", "AskUserQuestion",
  # タスク・チーム管理（リーダーには不要）
  "TodoWrite", "TaskCreate", "TaskUpdate", "TaskList", "TaskGet",
  "TeamCreate", "TeamDelete", "SendMessage",
]
```

> **Note**: `Skill` はリーダーの能力拡張に有用なため、ブロック対象外です。

#### `full_access`

全ツールへのアクセスを許可するプリセットです。

```toml
[full_access]
permission_mode = "bypassPermissions"
```

#### `read_only`

ファイルの読み取りのみを許可するプリセットです。

```toml
[read_only]
permission_mode = "bypassPermissions"
disallowed_tools = ["Write", "Edit", "NotebookEdit"]
```

## チーム設定（team.toml）

### `[team]` セクション

| 項目 | 型 | 必須 | 説明 |
|------|-----|------|------|
| `team_id` | `str` | はい | チームID（実行内で一意） |
| `team_name` | `str` | はい | チーム表示名 |

### `[team.leader]` セクション

| 項目 | 型 | 必須 | デフォルト | 説明 |
|------|-----|------|----------|------|
| `model` | `str` | はい | — | モデルID（例: `claudecode:claude-opus-4-6`） |
| `temperature` | `float` | いいえ | モデル依存 | 生成の温度パラメータ |
| `system_instruction` | `str` | いいえ | `""` | Leader への指示（複数行可） |

### `[team.leader.tool_settings.claudecode]` セクション

| 項目 | 型 | 必須 | 説明 |
|------|-----|------|------|
| `preset` | `str` | いいえ | プリセット名（`claudecode.toml` で定義） |

プリセット以外の項目をローカルオーバーライドとして追加できます。

### `[[team.members]]` セクション

| 項目 | 型 | 必須 | 説明 |
|------|-----|------|------|
| `config` | `str` | はい | Member Agent 設定ファイルのパス（`$MIXSEEK_WORKSPACE` からの相対パス） |

### 設定例

```toml
[team]
team_id = "team-claudecode"
team_name = "Quant Signal Team ClaudeCode"

[team.leader]
model = "claudecode:claude-opus-4-6"
temperature = 0.0

system_instruction = """
あなたはチームのリーダーです。
メンバーに指示を出し、株価シグナル生成を目指します。
"""

[team.leader.tool_settings.claudecode]
preset = "delegate_only"

[[team.members]]
config = "configs/agents/members/train_analyzer_claudecode.toml"

[[team.members]]
config = "configs/agents/members/submission_creator_claudecode.toml"
```

## オーケストレーター設定（orchestrator.toml）

### `[orchestrator]` セクション

| 項目 | 型 | 必須 | デフォルト | 説明 |
|------|-----|------|----------|------|
| `min_rounds` | `int` | いいえ | `1` | 最小ラウンド数 |
| `max_rounds` | `int` | はい | — | 最大ラウンド数 |
| `timeout_per_team_seconds` | `int` | いいえ | `3600` | チームごとのタイムアウト秒数 |
| `evaluator_config` | `str` | はい | — | Evaluator 設定ファイルのパス |

### `[[orchestrator.teams]]` セクション

| 項目 | 型 | 必須 | 説明 |
|------|-----|------|------|
| `config` | `str` | はい | チーム設定ファイルのパス |

### 設定例

```toml
[orchestrator]
min_rounds = 3
max_rounds = 5
timeout_per_team_seconds = 3600

evaluator_config = "configs/evaluator.toml"

[[orchestrator.teams]]
config = "configs/agents/teams/claudecode_team.toml"
```

複数チームの構成パターンは [実行設計ガイド](execution-guide.md) を参照してください。

## コンペティション設定（competition.toml）

### `[competition]` セクション

| 項目 | 型 | 必須 | 説明 |
|------|-----|------|------|
| `name` | `str` | はい | コンペティション名 |
| `description` | `str` | いいえ | コンペティションの説明 |

### `[[competition.data]]` セクション

利用するデータセットを定義します。複数指定可能です。

| 項目 | 型 | 必須 | 説明 |
|------|-----|------|------|
| `name` | `str` | はい | データセット名（`data/inputs/{name}/` ディレクトリに対応） |
| `datetime_column` | `str` | はい | 日付カラム名 |

### `[competition.data_split]` セクション

| 項目 | 型 | 必須 | 説明 |
|------|-----|------|------|
| `train_end` | `str` | はい | train 期間の終了日時（ISO 8601） |
| `valid_end` | `str` | はい | validation 期間の終了日時（ISO 8601） |
| `purge_rows` | `int` | はい | パージ行数（train/valid 間のギャップ） |

### `[competition.return_definition]` セクション

| 項目 | 型 | 必須 | 説明 |
|------|-----|------|------|
| `window` | `int` | はい | リターン計算のウィンドウサイズ |
| `method` | `str` | はい | リターン計算方法（例: `"open2close"`） |

### 設定例

```toml
[competition]
name = "sample competition"
description = "株価シグナル生成コンペティションサンプル"

[[competition.data]]
name = "ohlcv"
datetime_column = "datetime"

[[competition.data]]
name = "returns"
datetime_column = "datetime"

[[competition.data]]
name = "master"
datetime_column = "datetime"

[competition.data_split]
train_end = "2021-12-31T23:59:59"
valid_end = "2023-12-31T23:59:59"
purge_rows = 1

[competition.return_definition]
window = 1
method = "open2close"
```

## 評価設定（evaluator.toml）

### `[[metrics]]` セクション

| 項目 | 型 | 必須 | 説明 |
|------|-----|------|------|
| `name` | `str` | はい | メトリクス名（`[custom_metrics]` のキーと一致） |
| `weight` | `float` | はい | 評価における重み |

### `[custom_metrics]` セクション

カスタムメトリクスの実装クラスを指定します。キーは `[[metrics]]` の `name` と一致させます。

| 項目 | 型 | 必須 | 説明 |
|------|-----|------|------|
| `module` | `str` | はい | メトリクス実装のモジュールパス |
| `class` | `str` | はい | メトリクス実装のクラス名 |

### 設定例

```toml
[[metrics]]
name = "CorrelationSharpeRatio"
weight = 1.0

[custom_metrics]
CorrelationSharpeRatio = { module = "quant_insight.evaluator.correlation_sharpe_ratio", class = "CorrelationSharpeRatio" }
```

## 環境変数

| 変数名 | 必須 | 説明 |
|--------|------|------|
| `MIXSEEK_WORKSPACE` | はい | ワークスペースのルートパス。設定ファイルのパスやデータパスの基準ディレクトリ |

> **Note**: `claudecode:` プレフィックスは Claude Code CLI のセッション認証を使用するため、API キーの環境変数は不要です。

## 設定ファイル構成

ワークスペース内での推奨ディレクトリ構成です。

```
$MIXSEEK_WORKSPACE/
├── configs/
│   ├── competition.toml
│   ├── evaluator.toml
│   ├── orchestrator.toml
│   ├── presets/
│   │   └── claudecode.toml
│   └── agents/
│       ├── members/
│       │   ├── train_analyzer_claudecode.toml
│       │   └── submission_creator_claudecode.toml
│       └── teams/
│           └── claudecode_team.toml
├── submissions/                   # エージェント生成コード（setup で作成）
│   └── round_{N}/                 # ラウンドごとに自動作成
│       ├── submission.py          # submission-creator が Write
│       └── analysis.md            # train-analyzer が Write
├── data/
│   └── inputs/
│       ├── ohlcv/
│       │   ├── ohlcv.parquet      # 元データ
│       │   ├── train.parquet      # data split 後
│       │   └── valid.parquet
│       ├── returns/
│       │   ├── returns.parquet
│       │   ├── train.parquet
│       │   └── valid.parquet
│       └── master/
│           ├── master.parquet
│           ├── train.parquet
│           └── valid.parquet
└── mixseek.db                     # DuckDB（leader_board, round_status 用）
```
