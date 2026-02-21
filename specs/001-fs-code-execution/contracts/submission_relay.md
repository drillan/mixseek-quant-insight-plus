# Contract: submission_relay module

**Module**: `src/quant_insight_plus/submission_relay.py`

## Public Functions

### get_round_dir

```python
def get_round_dir(workspace: Path, round_number: int) -> Path:
```

**Purpose**: ラウンドディレクトリのパスを返す（作成しない）。

**Parameters**:
- `workspace`: ワークスペースのルートパス
- `round_number`: ラウンド番号（1-indexed）

**Returns**: `Path` — `{workspace}/submissions/round_{round_number}`

**Raises**: なし

---

### ensure_round_dir

```python
def ensure_round_dir(workspace: Path, round_number: int) -> Path:
```

**Purpose**: ラウンドディレクトリを作成して返す（冪等）。

**Parameters**:
- `workspace`: ワークスペースのルートパス
- `round_number`: ラウンド番号

**Returns**: `Path` — 作成（または既存）のラウンドディレクトリパス

**Raises**: `OSError` — ディレクトリ作成に失敗した場合

**Idempotency**: 複数回呼び出しても安全（`mkdir(parents=True, exist_ok=True)`）

---

### get_submission_content

```python
def get_submission_content(round_dir: Path) -> str:
```

**Purpose**: submission.py を読み取り、Python コードブロックとして返す。

**Parameters**:
- `round_dir`: ラウンドディレクトリのパス

**Returns**: `str` — `` ```python\n{code}\n``` `` 形式の文字列

**Raises**: `SubmissionFileNotFoundError` — submission.py が存在しない場合

---

### patch_submission_relay

```python
def patch_submission_relay() -> None:
```

**Purpose**: `RoundController._execute_single_round()` を monkey-patch する。

**Idempotency**: 複数回呼び出しても安全（パッチ適用済みなら何もしない）。

**Side Effects**: `RoundController._execute_single_round` のメソッド本体を置換。

---

### reset_submission_relay_patch

```python
def reset_submission_relay_patch() -> None:
```

**Purpose**: パッチをリセットし、元のメソッドに戻す（テスト用）。

---

### get_upstream_method_hash

```python
def get_upstream_method_hash() -> str:
```

**Purpose**: パッチ対象メソッドの現在のソースコード SHA-256 ハッシュを返す。

**Returns**: `str` — 16進数のハッシュ文字列

## Exceptions

### SubmissionFileNotFoundError

```python
class SubmissionFileNotFoundError(FileNotFoundError):
    """submission.py がラウンドディレクトリに存在しない場合に送出。"""
```
