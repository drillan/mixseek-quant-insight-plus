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
    model="claudecode:claude-sonnet-4-5",
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
from quant_insight_plus import register_claudecode_quant_agents

register_claudecode_quant_agents()
```

> **Note**: CLI (`qip`) を使用する場合、この関数は自動的に呼び出されるため、手動での呼び出しは不要です。

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
