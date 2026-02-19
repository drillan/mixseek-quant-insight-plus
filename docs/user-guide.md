# User Guide

mixseek-quant-insight-plus の詳細な使用方法を説明します。

## アーキテクチャ

### レイヤー構成

```
mixseek-core (フレームワーク)
  └── mixseek-plus (ClaudeCode/Groq 拡張)
        └── mixseek-quant-insight (ドメインプラグイン: ローカルコード実行)
              └── mixseek-quant-insight-plus (本パッケージ: Claude Code 統合)
```

### 親クラスとの差分

`ClaudeCodeLocalCodeExecutorAgent` は `LocalCodeExecutorAgent` を継承し、Claude Code 環境向けにカスタマイズしています。

| 観点 | LocalCodeExecutorAgent | ClaudeCodeLocalCodeExecutorAgent |
|------|----------------------|--------------------------------|
| モデル解決 | `Agent(model=config.model)` (文字列直接) | `create_authenticated_model()` (`claudecode:` 対応) |
| ツールセット | pydantic-ai カスタムツール 4 種 | 登録なし (Claude Code 組み込みツール) |
| 既存スクリプト参照 | ファイル名のみフッタに追加 | スクリプト内容を Markdown 形式で埋め込み |
| `execute()` | 自前実装 | 親クラスから継承 |

## エージェント設定

### TOML 設定構造

エージェントの設定は TOML ファイルで定義します。`type` に `claudecode_local_code_executor` を指定します。

```toml
[agent]
type = "claudecode_local_code_executor"
name = "code-executor"
model = "claudecode:claude-sonnet-4-5"
description = "ClaudeCodeでPythonコード実行・データ分析を行う"

[agent.system_instruction]
text = """
あなたはデータ分析エージェントです。
与えられたデータに対して分析を実行し、結果を報告してください。
"""

[agent.metadata.tool_settings.local_code_executor]
available_data_paths = ["data/inputs/ohlcv/train.parquet"]
timeout_seconds = 120
```

### 主要設定項目

| 項目 | 型 | 説明 |
|------|-----|------|
| `type` | `str` | `"claudecode_local_code_executor"` を指定 |
| `name` | `str` | エージェント名（チーム内で一意） |
| `model` | `str` | モデルID（`claudecode:claude-sonnet-4-5` 等） |
| `description` | `str` | エージェントの説明（Leader がタスク委譲時に参照） |
| `system_instruction.text` | `str` | システム指示 |
| `max_retries` | `int` | リトライ回数 |
| `temperature` | `float` | 生成の温度パラメータ |
| `max_tokens` | `int` | 最大トークン数 |
| `timeout_seconds` | `float` | リクエストタイムアウト秒数 |

### tool_settings 設定

`metadata.tool_settings.local_code_executor` セクションでローカルコード実行の動作を制御します。

| 項目 | 型 | 説明 |
|------|-----|------|
| `available_data_paths` | `list[str]` | 利用可能なデータファイルパス |
| `timeout_seconds` | `int` | コード実行のタイムアウト秒数 |

## チーム設定

チーム設定では、Leader エージェントとメンバーエージェントの構成を定義します。

```toml
# configs/agents/teams/claudecode_team.toml

[team]
team_id = "team-claudecode"
team_name = "ClaudeCode Analysis Team"

[team.leader]
model = "claudecode:claude-sonnet-4-5"

[[team.members]]
config = "configs/agents/members/train_analyzer_claudecode.toml"

[[team.members]]
config = "configs/agents/members/submission_creator_claudecode.toml"
```

### Leader の設定

Leader エージェントはタスクをメンバーに委譲する役割を持ちます。`claudecode:` プレフィックスのモデルを使用可能です。

### メンバーの追加

`[[team.members]]` セクションを追加することでメンバーを増やせます。各メンバーの設定は個別の TOML ファイルで管理します。

## オーケストレーター設定

複数のチームを並列実行し、リーダーボード形式で結果を評価します。

```toml
# configs/orchestrator.toml

[orchestrator]
execution_id = "exec-001"
max_rounds = 3

[orchestrator.competition]
config = "configs/competition.toml"

[orchestrator.evaluator]
config = "configs/evaluator.toml"

[[orchestrator.teams]]
config = "configs/agents/teams/claudecode_team.toml"
```

## スクリプト埋め込み機能

`ClaudeCodeLocalCodeExecutorAgent` は、過去のラウンドで作成されたスクリプトをプロンプトに自動埋め込みします。

### 動作の流れ

1. `implementation_context` から実行ID・チームID・ラウンド番号を取得
2. DuckDB から既存スクリプトの一覧を取得（`list_scripts`）
3. 各スクリプトの内容を取得（`read_script`）
4. Markdown コードブロック形式でタスクプロンプトの末尾に追加

### 埋め込み例

タスクプロンプトに以下のようなフッタが自動追加されます:

```markdown
---
## 既存スクリプト

### analyze_train.py
```python
import pandas as pd
df = pd.read_parquet("data/inputs/ohlcv/train.parquet")
print(df.describe())
```

### create_signal.py
```python
import pandas as pd
# シグナル生成ロジック
...
```
```

### エラー処理

DB 読み込みエラー（`DatabaseReadError`）は呼び出し元に明示的に伝播します。エンリッチメント失敗時にエンリッチなしで処理を続行する（暗黙のデータ欠損）ことはありません。

## CLI の使用

`quant-insight-plus`（短縮形: `qip`）コマンドを使用します。

### コマンド一覧

| コマンド | 設定ファイル | 用途 |
|---------|------------|------|
| `qip member` | `agent.toml` | 単体 Agent テスト |
| `qip team` | `team.toml` | 単一チーム開発・テスト |
| `qip exec` | `orchestrator.toml` | 複数チーム本番実行 |

### 実行例

```bash
# 単体 Agent テスト
qip member "trainデータのカラム一覧を確認してください" \
    --config $MIXSEEK_WORKSPACE/configs/agents/members/train_analyzer_claudecode.toml

# 単一チームの開発・テスト
qip team "trainデータの基本統計量を分析してください" \
    --config $MIXSEEK_WORKSPACE/configs/agents/teams/claudecode_team.toml

# 本番実行（オーケストレーター経由）
qip exec "株価シグナル生成" \
    --config $MIXSEEK_WORKSPACE/configs/orchestrator.toml

# バージョン表示
qip --version

# ヘルプ表示
qip --help
```

### CLI の自動登録

CLI は起動時に以下を自動実行します:

1. `patch_core()` で `claudecode:` プレフィックスを有効化
2. `register_groq_agents()` で Groq エージェント登録
3. `register_claudecode_agents()` で ClaudeCode エージェント登録
4. `register_claudecode_quant_agents()` で本パッケージのエージェント登録

そのため、CLI 使用時は Python コードでの初期化は不要です。

## ワークスペースセットアップ

`examples/setup.sh` を使用してワークスペースを初期化できます。

### セットアップ手順

```bash
# 1. ワークスペースを初期化
./examples/setup.sh /path/to/workspace
```

セットアップスクリプトの実行内容:

1. `mixseek init` でワークスペース基本構造を作成
2. `configs/` 以下の TOML 設定ファイルをコピー
3. `quant-insight db init` で DuckDB スキーマを初期化
4. `data/inputs/` ディレクトリを作成

### データの配置

ワークスペース内の `data/inputs/` ディレクトリに parquet ファイルを配置します。

```
/path/to/workspace/data/inputs/
├── ohlcv/ohlcv.parquet
├── returns/returns.parquet
└── master/master.parquet
```

### データの分割

```bash
export MIXSEEK_WORKSPACE=/path/to/workspace
quant-insight data split --config $MIXSEEK_WORKSPACE/configs/competition.toml
```

### 設定ファイル構成

```
configs/
├── competition.toml               # コンペティション定義（データ分割設定）
├── evaluator.toml                 # 評価メトリクス設定
├── orchestrator.toml              # 本番実行用（exec コマンド）
└── agents/
    ├── members/
    │   ├── train_analyzer_claudecode.toml      # データ分析 Agent
    │   └── submission_creator_claudecode.toml  # Submission 作成 Agent
    └── teams/
        └── claudecode_team.toml               # チーム構成（team コマンド）
```

## Gemini 版との差分

| 項目 | Gemini 版 (quant-insight) | ClaudeCode 版 (本パッケージ) |
|------|----------|--------------|
| model | `google-gla:gemini-3-flash-preview` | `claudecode:claude-sonnet-4-5` |
| agent type | `custom` + `plugin` 指定 | `claudecode_local_code_executor` |
| コード実行 | pydantic-ai `execute_python_code` ツール | Claude Code 組み込み Bash ツール |
| スクリプト参照 | `read_script` ツール | プロンプトに内容を自動埋め込み |
| CLI | `mixseek exec` / `quant-insight` | `qip exec` / `quant-insight-plus` |
