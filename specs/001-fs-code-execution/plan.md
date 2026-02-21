# Implementation Plan: ファイルシステムベース・コード実行環境

**Branch**: `001-fs-code-execution` | **Date**: 2026-02-21 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-fs-code-execution/spec.md`

## Summary

エージェント生成コードをファイルシステムで管理し、Leader LLM によるコード改変を排除する（Issue #32）。
DuckDB の `agent_implementation` テーブルをファイルシステム（`submissions/round_{N}/`）で完全に置き換え、
`RoundController._execute_single_round()` を monkey-patch して Evaluator への提出をファイルから直接行う。

## Technical Context

**Language/Version**: Python 3.13+
**Primary Dependencies**: pydantic-ai, pydantic 2.10+, Typer (CLI)
**Storage**: ファイルシステム（`submissions/round_{N}/`）。DuckDB は leader_board/round_status 用に維持
**Testing**: pytest + unittest.mock
**Target Platform**: Linux (CLI)
**Project Type**: Single project (Python package)
**Performance Goals**: ファイル読み書き < 1秒（SC-002）
**Constraints**: シングルプロセス・逐次実行、MIXSEEK_WORKSPACE 環境変数必須
**Scale/Scope**: 1パッケージ、新規2ファイル + 既存5ファイル変更 + TOML 3ファイル変更

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Article | Status | Notes |
|---------|--------|-------|
| Art.1 TDD | PASS | 7 Phase の TDD 実装順序を定義。テスト → 実装 → 品質チェック |
| Art.2 Documentation | PASS | spec.md, plan.md, research.md, data-model.md, contracts/ を事前生成 |
| Art.3 CLI/Agent Design | PASS | TOML 一元管理維持。CLI `qip setup` 更新。エージェント独立テスト可能 |
| Art.4 Simplicity | PASS | 単一プロジェクト構造維持。不要なラッパー・抽象化なし |
| Art.5 Code Quality | PASS | 各 Phase で `ruff check --fix . && ruff format . && mypy .` 実行 |
| Art.6 Data Accuracy | PASS | ハードコード値なし。定数は名前付き定数（`SUBMISSION_FILENAME` 等） |
| Art.7 DRY | PASS | `get_round_dir` を共通関数化。TOML テンプレート変更は最小限 |
| Art.8 Refactoring | PASS | 既存クラスを直接修正（V2 クラス作成なし） |
| Art.9 Type Safety | PASS | 全関数に型注釈。`Any` 不使用 |
| Art.10 Docstring | WILL COMPLY | 全 public 関数に Google-style docstring 付与 |
| Art.11 Naming | PASS | git-conventions.md 準拠 |

**Post-Design Re-check**: 全 Article PASS。Complexity Tracking 対象なし。

## Project Structure

### Documentation (this feature)

```text
specs/001-fs-code-execution/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   ├── submission_relay.md
│   ├── output_models.md
│   └── agent_changes.md
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
src/quant_insight_plus/
├── __init__.py                    ← 修正: 公開 API 更新
├── agents/
│   ├── __init__.py
│   ├── agent.py                   ← 大幅修正: FS ベースエージェント
│   └── output_models.py           ← 新規: FileSubmitterOutput, FileAnalyzerOutput
├── submission_relay.py            ← 新規: FS 読み取り + パッチ
├── cli.py                         ← 修正: パッチ登録、setup 更新
└── templates/
    └── agents/
        ├── members/
        │   ├── submission_creator_claudecode.toml  ← 修正: FS 書き込み指示
        │   └── train_analyzer_claudecode.toml      ← 修正: FS 書き込み指示
        └── teams/
            └── claudecode_team.toml                ← 修正: Leader 指示

tests/
├── conftest.py                    ← 修正: DuckDB パッチ削除
├── test_output_models.py          ← 新規
├── test_submission_relay.py       ← 新規
├── test_enrich_workspace.py       ← 新規
├── test_agent.py                  ← 修正: DuckDB パッチ削除
├── test_execute_output_format.py  ← 大幅修正: FS ベース
├── test_setup.py                  ← 修正: DB → submissions/ 作成
├── test_leader_template.py        ← 修正: Evaluator ガイダンス更新
└── test_enrich_scripts.py         ← 削除
```

**Structure Decision**: 既存の単一プロジェクト構造を維持。新規ファイル2つ（`output_models.py`, `submission_relay.py`）を追加し、既存ファイルを直接修正する（Art.8 準拠）。

## Implementation Phases (TDD)

### Phase 1: 出力モデル

1. `tests/test_output_models.py` を作成（Red）
2. `src/quant_insight_plus/agents/output_models.py` を作成（Green）
3. 品質チェック

### Phase 2: Submission Relay

1. `tests/test_submission_relay.py` を作成（Red）
2. `src/quant_insight_plus/submission_relay.py` を作成（Green）
3. 品質チェック

### Phase 3: conftest リファクタリング

1. `tests/conftest.py` から DuckDB 関連定数・fixture を削除
2. `agent` fixture を `MODEL_PATCH` のみに変更

### Phase 4: Agent 改修

1. `tests/test_enrich_scripts.py` を削除
2. `tests/test_enrich_workspace.py` を作成（Red）
3. `tests/test_execute_output_format.py` を修正（Red）
4. `tests/test_agent.py` を修正（Red）
5. `src/quant_insight_plus/agents/agent.py` を改修（Green）
6. 品質チェック

### Phase 5: TOML テンプレート

1. `submission_creator_claudecode.toml` を修正
2. `train_analyzer_claudecode.toml` を修正
3. `claudecode_team.toml` を修正
4. `tests/test_leader_template.py` を修正

### Phase 6: CLI

1. `tests/test_setup.py` を修正（Red）
2. `src/quant_insight_plus/cli.py` を修正（Green）
3. 品質チェック

### Phase 7: 全体品質チェック

1. `uv run ruff check --fix . && uv run ruff format .`
2. `uv run mypy .`
3. `uv run pytest`
