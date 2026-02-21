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

ClaudeCode 版 LocalCodeExecutorAgent（FS ベース版）。Claude Code の組み込みツール（Bash, Read 等）を活用し、pydantic-ai のカスタムツールセットは登録しません。

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
| `ValueError` | 認証失敗または TOML 設定不足の場合 |

**初期化の流れ**

1. `BaseMemberAgent.__init__()` を呼び出し（`LocalCodeExecutorAgent.__init__` はスキップ）
2. `_build_executor_config()` で `LocalCodeExecutorConfig` を構築
3. `_resolve_output_type()` で出力型を決定
4. `_create_model_settings()` でモデル設定を作成
5. `create_authenticated_model()` で `claudecode:` プレフィックスを解決
6. ツールセットなしの `pydantic_ai.Agent` を作成

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

### _enrich_task_with_workspace_context

```python
def _enrich_task_with_workspace_context(self, task: str) -> str
```

ラウンドディレクトリ内のファイル内容をタスクプロンプトに埋め込みます。

親クラスはファイル名のみ追加しますが、ClaudeCode 版は `read_script` ツールを持たないため、ラウンドディレクトリ内の全ファイル内容をプロンプトに埋め込みます。

**引数**

| 名前 | 型 | 説明 |
|------|-----|------|
| `task` | `str` | 元のタスク文字列 |

**戻り値**

- `str`: ワークスペースファイル内容が追加されたタスク文字列

**例外**

| 例外 | 条件 |
|------|------|
| `RuntimeError` | `MIXSEEK_WORKSPACE` 環境変数が未設定の場合 |

**動作**

- `implementation_context` が `None` の場合、タスクをそのまま返す
- ラウンドディレクトリが存在しない場合、タスクをそのまま返す
- ラウンドディレクトリ内の全ファイルを読み取り、Markdown 形式でタスク末尾に追加する

### _get_workspace_path

```python
def _get_workspace_path(self) -> Path
```

`MIXSEEK_WORKSPACE` 環境変数からワークスペースパスを取得します。

**戻り値**

- `Path`: ワークスペースのパス

**例外**

| 例外 | 条件 |
|------|------|
| `RuntimeError` | `MIXSEEK_WORKSPACE` 環境変数が未設定の場合 |

### _ensure_round_directory

```python
def _ensure_round_directory(self) -> None
```

ラウンドディレクトリを作成します。`ImplementationContext` が未設定の場合は何もしません。

### _format_output_content

```python
def _format_output_content(self, output: BaseModel | str) -> str
```

構造化出力をリーダーエージェント向けにフォーマットします。

| 出力型 | フォーマット | 処理内容 |
|-------|----------|--------|
| `FileSubmitterOutput` | Markdown | ファイルからコードを読み取り、markdown 形式で返す |
| `FileAnalyzerOutput` | プレーンテキスト | `output.report` をそのまま返す |
| その他 `BaseModel` | JSON | `model_dump_json(indent=2)` で返す |
| `str` | 文字列 | そのまま返す |

### execute

```python
async def execute(
    self,
    task: str,
    context: dict[str, Any] | None = None,
    **kwargs: Any,
) -> MemberAgentResult
```

エージェントタスクを実行します（FS ベース版）。

**処理の流れ**

1. `context` が指定されていれば `ImplementationContext` を設定
2. `_ensure_round_directory()` でラウンドディレクトリを作成
3. `_enrich_task_with_workspace_context()` でタスクをエンリッチ
4. `pydantic_ai.Agent.run()` でエージェントを実行
5. 結果を `MemberAgentResult` として返す

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

エージェントの構造化出力として使用される Pydantic モデルです。`quant_insight_plus.agents.output_models` モジュールで定義されています。

### FileSubmitterOutput

```python
class FileSubmitterOutput(BaseModel)
```

submission-creator の構造化出力。コード本体はファイルに存在し、構造化出力はファイルパスのみを含みます（コードの二重管理を排除）。TOML で `class_name = "FileSubmitterOutput"` として使用します。

| フィールド | 型 | 説明 |
|-----------|-----|------|
| `submission_path` | `str` | 書き込んだ `submission.py` の絶対パス |
| `description` | `str` | Submission の概要（Markdown 形式） |

**バリデーション**: `submission_path` は絶対パスであることが検証されます。相対パスや空文字列はバリデーションエラーになります。

### FileAnalyzerOutput

```python
class FileAnalyzerOutput(BaseModel)
```

train-analyzer の構造化出力。分析レポートはファイルとモデルの両方に存在します（`report` はリーダーへの主要な報告内容として使用）。TOML で `class_name = "FileAnalyzerOutput"` として使用します。

| フィールド | 型 | 説明 |
|-----------|-----|------|
| `analysis_path` | `str` | 書き込んだ `analysis.md` の絶対パス |
| `report` | `str` | 分析結果レポート（Markdown 形式） |

**バリデーション**: `analysis_path` は絶対パスであることが検証されます。相対パスや空文字列はバリデーションエラーになります。

## submission_relay モジュール

`quant_insight_plus.submission_relay` モジュールは、エージェントが生成したコードをファイルシステム経由で Evaluator に直接受け渡すための機能を提供します。

### 定数

| 定数 | 値 | 説明 |
|------|-----|------|
| `SUBMISSION_FILENAME` | `"submission.py"` | Submission ファイル名 |
| `ANALYSIS_FILENAME` | `"analysis.md"` | 分析レポートファイル名 |
| `SUBMISSIONS_DIR_NAME` | `"submissions"` | submissions ディレクトリ名 |

### get_round_dir

```python
def get_round_dir(workspace: Path, round_number: int) -> Path
```

ラウンドディレクトリのパスを返します（ディレクトリの作成は行いません）。

**引数**

| 名前 | 型 | 説明 |
|------|-----|------|
| `workspace` | `Path` | ワークスペースのパス |
| `round_number` | `int` | ラウンド番号 |

**戻り値**

- `Path`: `{workspace}/submissions/round_{round_number}`

### ensure_round_dir

```python
def ensure_round_dir(workspace: Path, round_number: int) -> Path
```

ラウンドディレクトリを作成して返します（冪等）。

**引数**

| 名前 | 型 | 説明 |
|------|-----|------|
| `workspace` | `Path` | ワークスペースのパス |
| `round_number` | `int` | ラウンド番号 |

**戻り値**

- `Path`: 作成（または既存）のラウンドディレクトリパス

**例外**

| 例外 | 条件 |
|------|------|
| `OSError` | ディレクトリ作成失敗時 |

### get_submission_content

```python
def get_submission_content(round_dir: Path) -> str
```

`submission.py` を読み取り、Python コードブロック形式で返します。

**引数**

| 名前 | 型 | 説明 |
|------|-----|------|
| `round_dir` | `Path` | ラウンドディレクトリのパス |

**戻り値**

- `str`: `` ```python\n{code}\n``` `` 形式の文字列

**例外**

| 例外 | 条件 |
|------|------|
| `SubmissionFileNotFoundError` | ファイルが存在しない場合、またはファイルが空の場合 |

### patch_submission_relay

```python
def patch_submission_relay() -> None
```

`RoundController._execute_single_round()` を monkey-patch し、ファイルシステム経由でのコード受け渡しを有効にします。

**動作**

- Leader エージェント実行後、`submission.py` をファイルから直接読み取り、Evaluator に渡す
- Leader の出力テキストの代わりに原本コードを使用する
- 冪等（複数回呼び出し時は何もしない）

### reset_submission_relay_patch

```python
def reset_submission_relay_patch() -> None
```

パッチをリセットし、元のメソッドに戻します（テスト用）。

### get_upstream_method_hash

```python
def get_upstream_method_hash() -> str
```

パッチ対象メソッドの現在のソースコード SHA-256 ハッシュを返します。upstream の変更を自動検出するために使用します。

**戻り値**

- `str`: 16進数のハッシュ文字列（64 文字）

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
| `implementation_context` | `ImplementationContext \| None` | `None` | 実装コンテキスト（ラウンドディレクトリ識別に使用） |

### OutputModelConfig

```python
class OutputModelConfig(BaseModel)
```

構造化出力モデルの設定。

| フィールド | 型 | 説明 |
|-----------|-----|------|
| `module_path` | `str` | モジュールパス（例: `quant_insight_plus.agents.output_models`） |
| `class_name` | `str` | クラス名（例: `FileSubmitterOutput`） |

### ImplementationContext

```python
class ImplementationContext(BaseModel)
```

エージェント実装を特定するためのコンテキスト情報。ラウンドディレクトリの識別に使用します。

| フィールド | 型 | 説明 |
|-----------|-----|------|
| `execution_id` | `str` | 実行識別子（UUID） |
| `team_id` | `str` | チーム ID |
| `round_number` | `int` | ラウンド番号（0以上） |
| `member_agent_name` | `str` | メンバーエージェント名 |

## 例外

### SubmissionFileNotFoundError

```python
class SubmissionFileNotFoundError(FileNotFoundError)
```

`submission.py` がラウンドディレクトリに存在しない場合、またはファイルが空の場合に送出される例外です。`get_submission_content()` 内で発生します。

**発生元**: `quant_insight_plus.submission_relay`

**発生条件**:

- ラウンドディレクトリに `submission.py` が存在しない
- `submission.py` が存在するがファイルが空

### RuntimeError (MIXSEEK_WORKSPACE 未設定)

`ClaudeCodeLocalCodeExecutorAgent._get_workspace_path()` で `MIXSEEK_WORKSPACE` 環境変数が設定されていない場合に発生します。

**対処法**:

```bash
export MIXSEEK_WORKSPACE=/path/to/workspace
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
| 5 | `patch_submission_relay()` | quant-insight-plus | Submission リレーの monkey-patch 適用 |
| 6 | `add_typer()` / `command()` | quant-insight | quant-insight サブコマンド（setup, data, db, export）統合 |

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
