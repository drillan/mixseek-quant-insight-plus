# Quickstart: ファイルシステムベース・コード実行環境

**Feature**: `001-fs-code-execution`

## 前提条件

- Python 3.13+
- uv (パッケージマネージャ)
- `MIXSEEK_WORKSPACE` 環境変数が設定済み

## セットアップ

```bash
# ワークスペースの初期化（submissions/ ディレクトリが作成される）
qip setup
```

## 実装後の検証

```bash
# 全テスト実行
uv run pytest

# 品質チェック
uv run ruff check --fix . && uv run ruff format . && uv run mypy .
```

## ディレクトリ構造

```
$MIXSEEK_WORKSPACE/
├── submissions/           ← 新規（qip setup で作成）
│   └── round_{N}/         ← 自動作成（ラウンド実行時）
│       ├── submission.py  ← submission-creator が Write
│       └── analysis.md    ← train-analyzer が Write
├── data/inputs/           ← 既存
├── configs/               ← 既存
└── mixseek.db             ← 既存（leader_board 等）
```

## 主要な変更点

| Before | After |
|--------|-------|
| DuckDB `agent_implementation` テーブル | ファイルシステム `submissions/round_{N}/` |
| `SubmitterOutput(submission=code)` | `FileSubmitterOutput(submission_path=path)` |
| `_enrich_task_with_existing_scripts()` | `_enrich_task_with_workspace_context()` |
| `result.output` → Evaluator | `get_submission_content(round_dir)` → Evaluator |

## TDD 実装順序

1. `output_models.py` — 構造化出力モデル
2. `submission_relay.py` — FS 読み取り + パッチ
3. `conftest.py` — DuckDB fixture 削除
4. `agent.py` — FS ベースエージェント
5. TOML テンプレート — 指示変更
6. `cli.py` — セットアップ変更
7. 品質チェック — ruff + mypy + pytest
