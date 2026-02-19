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

全設定項目の詳細は [Configuration Reference](configuration-reference.md) を参照してください。

### tool_settings 設定

`metadata.tool_settings.local_code_executor` セクションでローカルコード実行の動作を制御します。

| 項目 | 型 | デフォルト | 説明 |
|------|-----|----------|------|
| `available_data_paths` | `list[str]` | `[]` | 利用可能なデータファイルパス（`$MIXSEEK_WORKSPACE` からの相対パス） |
| `timeout_seconds` | `int` | `120` | コード実行のタイムアウト秒数 |
| `max_output_chars` | `int \| null` | `null` | 最大出力文字数 |

データパスは `$MIXSEEK_WORKSPACE` からの相対パスで指定します。例えば `data/inputs/ohlcv/train.parquet` は `$MIXSEEK_WORKSPACE/data/inputs/ohlcv/train.parquet` に解決されます。

### output_model 設定

`output_model` セクションでエージェントの構造化出力を定義します。省略時は `str` 型（自由テキスト）が使用されます。

```toml
[agent.metadata.tool_settings.local_code_executor.output_model]
module_path = "quant_insight.agents.local_code_executor.output_models"
class_name = "AnalyzerOutput"
```

**利用可能な出力モデル:**

| class_name | 用途 | フィールド |
|------------|------|----------|
| `AnalyzerOutput` | データ分析 | `scripts: list[ScriptEntry]`, `report: str` |
| `SubmitterOutput` | Submission 作成 | `submission: str`, `description: str` |

- **AnalyzerOutput**: train データの分析を行うエージェントに使用。分析で作成した Python スクリプトと Markdown レポートを出力
- **SubmitterOutput**: Submission スクリプトを実装するエージェントに使用。提出コードとその説明を出力

### system_instruction の書き方

`system_instruction.text` にはエージェントの役割、目標、ガイドラインを記述します。以下は実際のサンプル設定からの抜粋です。

**データ分析エージェント（train_analyzer）の例:**

```toml
[agent.system_instruction]
text = """
## ロール
株式市場を対象としたシグナル生成のコンペティションが開催されます。
あなたはこのコンペティションに参加するチームのメンバーです。

## 目標
リーダーの指示に従い、利用可能なtrainデータに対するデータ分析を行います。

## ガイドライン:
- Bash ツールを使って Python コードを実行する
- Read ツールでデータファイルの存在確認やスクリプト参照が可能
- 主要な結果と、データ分析結果に基づいた洞察を提供する

## スクリプト参照
- 既存スクリプトがある場合、タスクのフッタに内容が埋め込まれています

## データ
### 利用可能データ
- ohlcv（日足）
- master（銘柄情報）
- リターン(目的変数)

## 最終出力
- scripts: list[ScriptEntry] ... 分析で作成したスクリプト
- report: str ... Markdown形式の分析結果レポート
"""
```

**ポイント:**

- ロール・目標・ガイドラインを明確に分離
- 利用可能なツール（Bash, Read）を明示
- データカラムの詳細をリファレンスとして含める
- 出力形式を `output_model` のフィールドと一致させる
- 「既存スクリプトはフッタに埋め込まれる」旨を記載（スクリプト埋め込み機能との連携）

## チーム設定

チーム設定では、Leader エージェントとメンバーエージェントの構成を定義します。

```toml
[team]
team_id = "team-claudecode"
team_name = "Quant Signal Team ClaudeCode"

[team.leader]
model = "claudecode:claude-sonnet-4-5"
temperature = 0.0

system_instruction = """
あなたはチームのリーダーです。
メンバーに指示を出し、株価シグナル生成を目指します。

## メンバー
- train-analyzer: trainデータの分析を行う
- submission-creator: Submissionスクリプトを実装・動作確認する
"""

[[team.members]]
config = "configs/agents/members/train_analyzer_claudecode.toml"

[[team.members]]
config = "configs/agents/members/submission_creator_claudecode.toml"
```

### Leader の system_instruction

Leader のシステム指示には以下を含めることを推奨します:

- **メンバー一覧**: 各メンバーの名前と役割の説明
- **分析方針**: ラウンドごとの進め方（仮説検証の反復等）
- **コンテキスト共有ルール**: メンバー間でセッション履歴は共有されないが、既存スクリプトは参照可能である旨
- **Submission 形式**: 最終出力として求める形式

### メンバーの追加

`[[team.members]]` セクションを追加することでメンバーを増やせます。各メンバーの設定は個別の TOML ファイルで管理します。

## オーケストレーター設定

複数のチームを並列実行し、リーダーボード形式で結果を評価します。

```toml
[orchestrator]
min_rounds = 3
max_rounds = 5
timeout_per_team_seconds = 3600

evaluator_config = "configs/evaluator.toml"

[[orchestrator.teams]]
config = "configs/agents/teams/claudecode_team.toml"
```

| 項目 | 説明 |
|------|------|
| `min_rounds` | 最小ラウンド数。この回数まではラウンドを継続 |
| `max_rounds` | 最大ラウンド数。この回数に達すると終了 |
| `timeout_per_team_seconds` | チームごとのタイムアウト秒数 |
| `evaluator_config` | 評価設定ファイルのパス |

設定項目の詳細は [Configuration Reference](configuration-reference.md) を参照してください。

## スクリプト埋め込み機能

`ClaudeCodeLocalCodeExecutorAgent` は、過去のラウンドで作成されたスクリプトをプロンプトに自動埋め込みします。

### データフロー

```
Round N:
  Agent 実行 → output.scripts を DuckDB (agent_implementation テーブル) に保存

Round N+1:
  _enrich_task_with_existing_scripts()
    → DuckDB から既存スクリプト一覧を取得 (list_scripts)
    → 各スクリプトの内容を取得 (read_script)
    → タスクプロンプトの末尾に Markdown 形式で追加
```

### ImplementationContext

スクリプトの保存・読み込みは `ImplementationContext` で識別されます。

| フィールド | 型 | 説明 |
|-----------|-----|------|
| `execution_id` | `str` | 実行識別子（UUID） |
| `team_id` | `str` | チーム ID |
| `round_number` | `int` | ラウンド番号 |
| `member_agent_name` | `str` | メンバーエージェント名 |

同一の `(execution_id, team_id, round_number)` に対して保存されたスクリプトが、次ラウンドのエンリッチメント対象となります。

### 埋め込み例

タスクプロンプトに以下のようなフッタが自動追加されます:

````markdown
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
````

### エラー処理

DB 読み込みエラー（`DatabaseReadError`）は呼び出し元に明示的に伝播します。エンリッチメント失敗時にエンリッチなしで処理を続行する（暗黙のデータ欠損）ことはありません。

## DuckDB テーブル構造

エージェントが生成したスクリプトは `agent_implementation` テーブルに永続化されます。

### テーブル定義

```sql
CREATE TABLE IF NOT EXISTS agent_implementation (
    id INTEGER PRIMARY KEY DEFAULT nextval('agent_implementation_id_seq'),

    -- 識別子
    execution_id TEXT NOT NULL,
    team_id TEXT NOT NULL,
    round_number INTEGER NOT NULL,
    member_agent_name TEXT NOT NULL,
    file_name TEXT NOT NULL,

    -- コンテンツ
    code TEXT NOT NULL,

    -- メタデータ
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- 一意性制約
    UNIQUE(execution_id, team_id, round_number, member_agent_name, file_name)
)
```

### インデックス

```sql
CREATE INDEX IF NOT EXISTS idx_agent_implementation_context
ON agent_implementation (execution_id, team_id, round_number, member_agent_name)
```

### 書き込み動作

- UPSERT 方式: 同一の `(execution_id, team_id, round_number, member_agent_name, file_name)` が存在する場合は `code` を更新
- スレッドローカルコネクション: 各エージェントが独立したコネクションを使用（MVCC 並列書き込み）
- 非同期実行: `asyncio.to_thread` でスレッドプールに退避
- リトライ: 書き込み失敗時は指数バックオフで3回リトライ（1秒 → 2秒 → 4秒）

## CLI の使用

`quant-insight-plus`（短縮形: `qip`）コマンドを使用します。

### コマンド一覧

| コマンド | 引数 | 設定ファイル | 用途 |
|---------|------|------------|------|
| `qip member` | `TASK` `--config PATH` | `agent.toml` | 単体 Agent テスト |
| `qip team` | `TASK` `--config PATH` | `team.toml` | 単一チーム開発・テスト |
| `qip exec` | `TASK` `--config PATH` | `orchestrator.toml` | 複数チーム本番実行 |
| `qip --version` | — | — | バージョン表示 |
| `qip --help` | — | — | ヘルプ表示 |

- `TASK`: タスクの説明文字列（クォートで囲む）
- `--config PATH`: TOML 設定ファイルのパス

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
```

### CLI の自動登録

CLI は起動時に以下を自動実行します:

| 順序 | 関数 | パッケージ | 説明 |
|------|------|----------|------|
| 1 | `patch_core()` | mixseek-plus | `claudecode:` プレフィックス有効化 |
| 2 | `register_groq_agents()` | mixseek-plus | Groq エージェント登録 |
| 3 | `register_claudecode_agents()` | mixseek-plus | ClaudeCode エージェント登録 |
| 4 | `register_claudecode_quant_agents()` | quant-insight-plus | 本パッケージのエージェント登録 |

そのため、CLI 使用時は Python コードでの初期化は不要です。

## ワークスペースセットアップ

`examples/setup.sh` を使用してワークスペースを初期化できます。

### セットアップ手順

```bash
./examples/setup.sh /path/to/workspace
```

セットアップスクリプトの実行内容:

1. `mixseek init` でワークスペース基本構造を作成
2. `configs/` 以下の TOML 設定ファイルをコピー
3. `qip db init` で DuckDB スキーマを初期化
4. `data/inputs/` ディレクトリを作成

### データの配置

ワークスペース内の `data/inputs/` ディレクトリに parquet ファイルを配置します。

```
$MIXSEEK_WORKSPACE/data/inputs/
├── ohlcv/ohlcv.parquet
├── returns/returns.parquet
└── master/master.parquet
```

### データの分割

```bash
export MIXSEEK_WORKSPACE=/path/to/workspace
qip data split --config $MIXSEEK_WORKSPACE/configs/competition.toml
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

各設定ファイルのスキーマ詳細は [Configuration Reference](configuration-reference.md) を参照してください。

## Gemini 版との差分

| 項目 | Gemini 版 (quant-insight) | ClaudeCode 版 (本パッケージ) |
|------|----------|--------------|
| model | `google-gla:gemini-3-flash-preview` | `claudecode:claude-sonnet-4-5` |
| agent type | `custom` + `plugin` 指定 | `claudecode_local_code_executor` |
| コード実行 | pydantic-ai `execute_python_code` ツール | Claude Code 組み込み Bash ツール |
| スクリプト参照 | `read_script` ツール | プロンプトに内容を自動埋め込み |
| CLI | `mixseek exec` / `quant-insight` | `qip exec` / `quant-insight-plus` |
