# API Reference

mixseek-quant-insight-plus の API 仕様です。

## 定数

### AGENT_TYPE_NAME

```python
AGENT_TYPE_NAME: str = "claudecode_local_code_executor"
```

MemberAgentFactory に登録されるエージェントタイプ名。TOML 設定の `type` フィールドで使用します。

```toml
[agent]
type = "claudecode_local_code_executor"
```

## ClaudeCodeLocalCodeExecutorAgent

```python
class ClaudeCodeLocalCodeExecutorAgent(LocalCodeExecutorAgent)
```

ClaudeCode 版 LocalCodeExecutorAgent。Claude Code の組み込みツール（Bash, Read 等）を活用し、pydantic-ai のカスタムツールセットは登録しません。

### コンストラクタ

```python
def __init__(self, config: MemberAgentConfig) -> None
```

**引数**

| 名前 | 型 | 説明 |
|------|-----|------|
| `config` | `MemberAgentConfig` | Member Agent 設定 |

**例外**

| 例外 | 条件 |
|------|------|
| `RuntimeError` | DuckDB スキーマが初期化されていない場合 |
| `ValueError` | 認証失敗または TOML 設定不足の場合 |

**初期化の流れ**

1. `BaseMemberAgent.__init__()` を呼び出し（`LocalCodeExecutorAgent.__init__` はスキップ）
2. `_build_executor_config()` で `LocalCodeExecutorConfig` を構築
3. `_verify_database_schema()` で DuckDB スキーマを検証
4. `_resolve_output_type()` で出力型を決定
5. `_create_model_settings()` でモデル設定を作成
6. `create_authenticated_model()` で `claudecode:` プレフィックスを解決
7. ツールセットなしの `pydantic_ai.Agent` を作成

**使用例**

```python
from mixseek.models.member_agent import MemberAgentConfig
from quant_insight_plus import ClaudeCodeLocalCodeExecutorAgent

config = MemberAgentConfig(
    name="code-executor",
    type="claudecode_local_code_executor",
    model="claudecode:claude-opus-4-6",
    description="ClaudeCodeでPythonコード実行・データ分析を行う",
    system_instruction="データ分析を行うエージェントです。",
)

agent = ClaudeCodeLocalCodeExecutorAgent(config)
```

### _enrich_task_with_existing_scripts

```python
async def _enrich_task_with_existing_scripts(self, task: str) -> str
```

既存スクリプトの内容をタスクプロンプトに埋め込みます。

親クラスはファイル名のみ追加しますが、ClaudeCode 版は `read_script` ツールを持たないため、スクリプト内容そのものをプロンプトに埋め込みます。

**引数**

| 名前 | 型 | 説明 |
|------|-----|------|
| `task` | `str` | 元のタスク文字列 |

**戻り値**

- `str`: 既存スクリプト内容が追加されたタスク文字列

**例外**

| 例外 | 条件 |
|------|------|
| `DatabaseReadError` | `list_scripts` / `read_script` の DB 読み込み失敗時 |

**動作**

- `implementation_context` が `None` の場合、タスクをそのまま返す
- 既存スクリプトがない場合、タスクをそのまま返す
- DB エラー時は明示的に例外を伝播する（エンリッチなしでの続行はしない）

## register_claudecode_quant_agents

```python
def register_claudecode_quant_agents() -> None
```

ClaudeCode quant-insight エージェントを `MemberAgentFactory` に登録します。

この関数を呼び出すと、TOML 設定で `type = "claudecode_local_code_executor"` が使用可能になります。

**使用例**

```python
import mixseek_plus
from quant_insight_plus import register_claudecode_quant_agents

# patch_core() の後に呼び出す
mixseek_plus.patch_core()
register_claudecode_quant_agents()
```

> **Note**: CLI (`qip`) を使用する場合、この関数は自動的に呼び出されるため、手動での呼び出しは不要です。

## 構造化出力モデル

エージェントの構造化出力として使用される Pydantic モデルです。`quant_insight.agents.local_code_executor.output_models` モジュールで定義されています。

### ScriptEntry

```python
class ScriptEntry(BaseModel)
```

保存するスクリプトのエントリ。

| フィールド | 型 | 説明 |
|-----------|-----|------|
| `file_name` | `str` | ファイル名（`.py` 拡張子） |
| `code` | `str` | Python コード文字列 |

### AnalyzerOutput

```python
class AnalyzerOutput(BaseModel)
```

分析エージェントの構造化出力。TOML で `class_name = "AnalyzerOutput"` として使用します。

| フィールド | 型 | 説明 |
|-----------|-----|------|
| `scripts` | `list[ScriptEntry]` | 分析で作成したスクリプトのリスト |
| `report` | `str` | Markdown 形式の分析結果レポート |

### SubmitterOutput

```python
class SubmitterOutput(BaseModel)
```

Submission 作成エージェントの構造化出力。TOML で `class_name = "SubmitterOutput"` として使用します。

| フィールド | 型 | 説明 |
|-----------|-----|------|
| `submission` | `str` | Submission 形式に整合するシグナル生成関数を含む提出コード全体 |
| `description` | `str` | Submission の概要や動作確認結果（Markdown 形式） |

## 依存モデル

エージェントの設定と実行コンテキストに使用される Pydantic モデルです。`quant_insight.agents.local_code_executor.models` モジュールで定義されています。

### LocalCodeExecutorConfig

```python
class LocalCodeExecutorConfig(BaseModel)
```

ローカルコード実行の設定。TOML の `[agent.metadata.tool_settings.local_code_executor]` セクションに対応します。

| フィールド | 型 | デフォルト | 説明 |
|-----------|-----|----------|------|
| `available_data_paths` | `list[str]` | `[]` | `$MIXSEEK_WORKSPACE` からの相対パスリスト |
| `timeout_seconds` | `int` | `120` | 実行タイムアウト秒数（0より大きい値） |
| `max_output_chars` | `int \| None` | `None` | 最大出力文字数（`None` = 無制限） |
| `output_model` | `OutputModelConfig \| None` | `None` | 構造化出力モデル設定 |
| `implementation_context` | `ImplementationContext \| None` | `None` | 実装コンテキスト（DuckDB 保存時に使用） |

### OutputModelConfig

```python
class OutputModelConfig(BaseModel)
```

構造化出力モデルの設定。

| フィールド | 型 | 説明 |
|-----------|-----|------|
| `module_path` | `str` | モジュールパス（例: `quant_insight.agents.local_code_executor.output_models`） |
| `class_name` | `str` | クラス名（例: `AnalyzerOutput`） |

### ImplementationContext

```python
class ImplementationContext(BaseModel)
```

エージェント実装を特定するためのコンテキスト情報。DuckDB へのスクリプト保存時に使用する識別情報です。

| フィールド | 型 | 説明 |
|-----------|-----|------|
| `execution_id` | `str` | 実行識別子（UUID） |
| `team_id` | `str` | チーム ID |
| `round_number` | `int` | ラウンド番号（0以上） |
| `member_agent_name` | `str` | メンバーエージェント名 |

## 例外

### DatabaseReadError

```python
class DatabaseReadError(Exception)
```

DuckDB からの読み込み失敗時に送出される例外です。`_enrich_task_with_existing_scripts()` メソッド内で `list_scripts()` または `read_script()` が失敗したときに発生します。

**発生元**: `quant_insight.storage.implementation_store`

**発生条件**:

- DB ファイルが破損している
- ディスク容量不足
- 他のプロセスによる DB ファイルロック

### DatabaseWriteError

```python
class DatabaseWriteError(Exception)
```

DuckDB への書き込みが3回のリトライ（指数バックオフ: 1秒 → 2秒 → 4秒）後も失敗した場合に送出される例外です。

**発生元**: `quant_insight.storage.implementation_store`

**発生条件**:

- ディスク容量不足
- DB ファイルの書き込み権限なし
- ファイルシステムエラー

### RuntimeError (スキーマ未初期化)

`ClaudeCodeLocalCodeExecutorAgent.__init__()` の `_verify_database_schema()` で DuckDB の `agent_implementation` テーブルが検出できない場合に発生します。

**対処法**:

```bash
export MIXSEEK_WORKSPACE=/path/to/workspace
qip db init
```

### ValueError (認証/設定)

`ClaudeCodeLocalCodeExecutorAgent.__init__()` でモデル認証に失敗した場合、または TOML 設定に必須項目が不足している場合に発生します。

**対処法**:

- `claude --version` で Claude Code CLI の認証状態を確認
- TOML に `type`, `name`, `model` が設定されているか確認

## CLI

### main

```python
def main() -> None
```

CLI エントリーポイント。`quant-insight-plus` / `qip` コマンドで呼び出されます。

`pyproject.toml` で以下のように登録されています:

```toml
[project.scripts]
quant-insight-plus = "quant_insight_plus.cli:main"
qip = "quant_insight_plus.cli:main"
```

### version_callback

```python
def version_callback(value: bool | None) -> None
```

`--version` / `-v` オプションのコールバック。バージョン情報を表示して終了します。

```bash
$ qip --version
quant-insight-plus version 0.1.0
```

### CLI 起動時の自動登録

`cli.py` モジュールのインポート時に以下が順次実行されます:

| 順序 | 関数 | パッケージ | 説明 |
|------|------|----------|------|
| 1 | `patch_core()` | mixseek-plus | `claudecode:` プレフィックス有効化 |
| 2 | `register_groq_agents()` | mixseek-plus | Groq エージェント登録 |
| 3 | `register_claudecode_agents()` | mixseek-plus | ClaudeCode エージェント登録 |
| 4 | `register_claudecode_quant_agents()` | quant-insight-plus | 本パッケージのエージェント登録 |
| 5 | `add_typer()` / `command()` | quant-insight | quant-insight サブコマンド（setup, data, db, export）統合 |

### CLI コマンド仕様

**`qip member TASK --config PATH`**

| 引数 | 型 | 必須 | 説明 |
|------|-----|------|------|
| `TASK` | `str` | はい | タスクの説明文字列 |
| `--config` | `str` | はい | Member Agent 設定ファイルのパス |

**`qip team TASK --config PATH`**

| 引数 | 型 | 必須 | 説明 |
|------|-----|------|------|
| `TASK` | `str` | はい | タスクの説明文字列 |
| `--config` | `str` | はい | チーム設定ファイルのパス |

**`qip exec TASK --config PATH`**

| 引数 | 型 | 必須 | 説明 |
|------|-----|------|------|
| `TASK` | `str` | はい | タスクの説明文字列 |
| `--config` | `str` | はい | オーケストレーター設定ファイルのパス |

**`qip setup`**

| 引数 | 型 | 必須 | 説明 |
|------|-----|------|------|
| `--workspace, -w` | `Path` | いいえ | ワークスペースパス（未指定時は `$MIXSEEK_WORKSPACE`） |

**`qip data fetch-jquants`**

| 引数 | 型 | 必須 | 説明 |
|------|-----|------|------|
| `--plan, -p` | `JQuantsPlan` | いいえ | J-Quants API プラン（free/light/standard/premium、デフォルト: free） |
| `--universe, -u` | `JQuantsUniverse` | いいえ | 対象ユニバース（prime/standard/growth/all、デフォルト: prime） |
| `--start-date, -s` | `str` | いいえ | 開始日（YYYY-MM-DD、デフォルト: end_date - 2年） |
| `--end-date, -e` | `str` | いいえ | 終了日（YYYY-MM-DD、デフォルト: 12週間前） |

**`qip data build-returns`**

| 引数 | 型 | 必須 | 説明 |
|------|-----|------|------|
| `--config, -c` | `Path` | はい | competition.toml のパス |

**`qip data split`**

| 引数 | 型 | 必須 | 説明 |
|------|-----|------|------|
| `--config, -c` | `Path` | はい | competition.toml のパス |

**`qip db init`**

| 引数 | 型 | 必須 | 説明 |
|------|-----|------|------|
| `--workspace, -w` | `Path` | いいえ | ワークスペースパス（未指定時は `$MIXSEEK_WORKSPACE`） |

**`qip export logs EXECUTION_ID`**

| 引数 | 型 | 必須 | 説明 |
|------|-----|------|------|
| `EXECUTION_ID` | `str` | はい | エクスポート対象の execution_id |
| `--config, -c` | `Path` | はい | orchestrator.toml のパス |
| `--output, -o` | `Path` | いいえ | 出力ディレクトリ（デフォルト: `$MIXSEEK_WORKSPACE/data/outputs/export`） |
| `--workspace, -w` | `Path` | いいえ | ワークスペースパス（未指定時は `$MIXSEEK_WORKSPACE`） |
| `--team, -t` | `str` | いいえ | 特定チームのみエクスポート |
| `--logs-only` | `bool` | いいえ | ログ MD のみエクスポート |
| `--submissions-only` | `bool` | いいえ | サブミッション MD のみエクスポート |
