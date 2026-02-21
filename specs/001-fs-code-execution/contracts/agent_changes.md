# Contract: agent.py Changes

**Module**: `src/quant_insight_plus/agents/agent.py`

## Modified Methods

### _format_output_content

```python
def _format_output_content(self, output: BaseModel | str) -> str:
```

**Changed behavior**:
- `FileSubmitterOutput` → ファイルからコードを読み取り、Markdown 化
- `FileAnalyzerOutput` → `output.report` を返す
- `BaseModel` (other) → JSON 形式
- `str` → そのまま返す

**Contract**: ファイル読み取り失敗時は例外を伝播（`execute()` の `except` でキャッチ）

---

### execute

```python
async def execute(self, task: str, context: dict[str, str] | None = None, **kwargs: str) -> MemberAgentResult:
```

**Changed behavior**:
- `_ensure_round_directory()` を実行前に呼び出し
- `_enrich_task_with_workspace_context()` でタスクをエンリッチ
- `_save_output_scripts()` 呼び出しを削除

---

## New Methods

### _enrich_task_with_workspace_context

```python
def _enrich_task_with_workspace_context(self, task: str) -> str:
```

**Purpose**: ラウンドディレクトリ内のファイル内容をタスクプロンプトに埋め込む。

**Parameters**:
- `task`: 元のタスク文字列

**Returns**: ファイル内容がフッタに埋め込まれたタスク文字列

**Preconditions**:
- `ImplementationContext` 未設定時はタスクをそのまま返す
- ラウンドディレクトリ非存在時はタスクをそのまま返す

**Raises**: `RuntimeError` — `MIXSEEK_WORKSPACE` 未設定時

---

### _ensure_round_directory

```python
def _ensure_round_directory(self) -> None:
```

**Purpose**: ラウンドディレクトリを作成。`ImplementationContext` 未設定時は何もしない。

---

### _get_workspace_path

```python
def _get_workspace_path(self) -> Path:
```

**Purpose**: `MIXSEEK_WORKSPACE` 環境変数からパスを取得。

**Raises**: `RuntimeError` — 環境変数未設定時

## Removed Dependencies

- `from quant_insight.storage import get_implementation_store` → 削除
- `_verify_database_schema()` 呼び出し → 削除
- `_save_output_scripts()` 呼び出し → 削除
- `_enrich_task_with_existing_scripts()` → `_enrich_task_with_workspace_context()` に置換
