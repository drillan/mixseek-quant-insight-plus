# Tasks: ファイルシステムベース・コード実行環境

**Input**: Design documents from `/specs/001-fs-code-execution/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: TDD 必須（Constitution Art.1）。各フェーズで Red → Green → Quality Check の順序を厳守。

**Organization**: ユーザーストーリー単位で構成。各ストーリーは独立して実装・テスト可能。

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

---

## Phase 1: Setup

**Purpose**: 不要になった DuckDB 依存の削除とテスト基盤の整理

- [ ] T001 Delete deprecated DuckDB-based test file tests/test_enrich_scripts.py
- [ ] T002 Refactor tests/conftest.py — DuckDB 関連定数・fixture を削除し、agent fixture を MODEL_PATCH のみに変更

**Checkpoint**: テスト基盤が FS ベースへの移行準備完了

---

## Phase 2: Foundational (Output Models + Submission Relay Core)

**Purpose**: 全ユーザーストーリーの基盤となる構造化出力モデルとディレクトリ管理関数

**⚠️ CRITICAL**: US1〜US4 の実装開始前にこのフェーズを完了すること

### Tests (Red)

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T003 [P] Write tests/test_output_models.py — FileSubmitterOutput・FileAnalyzerOutput のバリデーション（絶対パス検証、必須フィールド、不正パス拒否）
- [ ] T004 [P] Write tests/test_submission_relay.py — get_round_dir パス生成、ensure_round_dir 冪等性、SubmissionFileNotFoundError 定義、名前付き定数（SUBMISSION_FILENAME 等）

### Implementation (Green)

- [ ] T005 [P] Implement src/quant_insight_plus/agents/output_models.py — FileSubmitterOutput, FileAnalyzerOutput with field_validator for absolute path validation
- [ ] T006 [P] Implement src/quant_insight_plus/submission_relay.py — get_round_dir, ensure_round_dir, SubmissionFileNotFoundError, SUBMISSION_FILENAME/ANALYSIS_FILENAME/SUBMISSIONS_DIR_NAME constants
- [ ] T007 Run quality check: `uv run ruff check --fix . && uv run ruff format . && uv run mypy .`

**Checkpoint**: 基盤モジュール完成。T003, T004 のテストが Green であること。

---

## Phase 3: User Story 1 — エージェント生成コードの正確な評価 (Priority: P1) 🎯 MVP

**Goal**: submission-creator が生成した Python コードが Leader LLM を経由せず、ファイルシステムから直接 Evaluator に到達する

**Independent Test**: チーム実行を1ラウンド実行し、submission.py の内容と Evaluator が受け取ったコードが完全一致することを検証

### Tests (Red)

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T008 [P] [US1] Add get_submission_content + patch_submission_relay/reset tests in tests/test_submission_relay.py — 正常読み取り（Python コードブロック形式）、SubmissionFileNotFoundError、空ファイルケース、パッチ適用・冪等性・リセット動作
- [ ] T009 [P] [US1] Rewrite tests/test_execute_output_format.py — FileSubmitterOutput の _format_output_content テスト（FS 読み取り経由）、FileAnalyzerOutput の report 返却テスト
- [ ] T010 [P] [US1] Modify tests/test_agent.py — DuckDB パッチ削除、FS ベースフロー（execute 内の _ensure_round_directory 呼び出し、_get_workspace_path の RuntimeError）

### Implementation (Green)

- [ ] T011 [US1] Implement get_submission_content, patch_submission_relay, reset_submission_relay_patch in src/quant_insight_plus/submission_relay.py
- [ ] T012 [US1] Modify src/quant_insight_plus/agents/agent.py — execute(), _format_output_content(), _ensure_round_directory(), _get_workspace_path(), _enrich_task_with_workspace_context()
- [ ] T013 [P] [US1] Update src/quant_insight_plus/templates/agents/members/submission_creator_claudecode.toml — FS 書き込み指示追加、python_command 設定 (FR-012)
- [ ] T014 [P] [US1] Update src/quant_insight_plus/templates/agents/members/train_analyzer_claudecode.toml — FS 書き込み指示追加、python_command 設定 (FR-012)
- [ ] T015 [P] [US1] Update src/quant_insight_plus/templates/agents/teams/claudecode_team.toml — Leader 指示を概要・戦略のみに変更 (FR-011)
- [ ] T016 [US1] Modify tests/test_leader_template.py — Evaluator ガイダンス更新のアサーション追加
- [ ] T017 [US1] Run quality check: `uv run ruff check --fix . && uv run ruff format . && uv run mypy .`

**Checkpoint**: US1 完了。FS 経由でコードが Evaluator に到達する。T008〜T010 が全て Green。

---

## Phase 4: User Story 2 — 同一ラウンド内のエージェント間ファイル共有 (Priority: P2)

**Goal**: ラウンドディレクトリ内のファイル（analysis.md 等）がエージェントのタスクプロンプトに自動埋め込みされる

**Independent Test**: ラウンドディレクトリに analysis.md を配置し、submission-creator のプロンプトに内容が埋め込まれることを検証

**Note**: `_enrich_task_with_workspace_context` の実装は T012（agent.py 全体改修）で完了済み。本フェーズでは独立テストにより US2 の受け入れ基準を検証する。

### Tests (Red → Green)

- [ ] T018 [US2] Write tests/test_enrich_workspace.py — ImplementationContext 未設定時の素通り、ラウンドディレクトリ非存在時の素通り、単一ファイル埋め込み、複数ファイル埋め込み、MIXSEEK_WORKSPACE 未設定時の RuntimeError
- [ ] T019 [US2] Run quality check: `uv run ruff check --fix . && uv run ruff format . && uv run mypy .`

**Checkpoint**: US2 完了。ワークスペースコンテキスト埋め込みが独立テスト済み。

---

## Phase 5: User Story 3 — セットアップとディレクトリ管理 (Priority: P3)

**Goal**: `qip setup` で submissions/ ディレクトリが自動作成され、ラウンド実行時にラウンドディレクトリが自動作成される

**Independent Test**: `qip setup` を実行し、submissions/ ディレクトリが作成されることを検証

### Tests (Red)

- [ ] T020 [US3] Modify tests/test_setup.py — DB 作成テストを submissions/ ディレクトリ作成テストに変更、patch_submission_relay() 呼び出し検証 (Red)

### Implementation (Green)

- [ ] T021 [US3] Modify src/quant_insight_plus/cli.py — setup コマンドで submissions/ ディレクトリ作成、patch_submission_relay() 登録 (Green)
- [ ] T022 [US3] Run quality check: `uv run ruff check --fix . && uv run ruff format . && uv run mypy .`

**Checkpoint**: US3 完了。`qip setup` が FS ベース管理構造を作成。

---

## Phase 6: User Story 4 — upstream パッチのドリフト検出 (Priority: P3)

**Goal**: upstream の `RoundController._execute_single_round()` が更新された場合にテストで自動検出される

**Independent Test**: ドリフト検出テストを実行し、upstream 変更時にテスト失敗を確認

### Tests (Red)

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T023 [US4] Write drift detection test in tests/test_submission_relay.py — get_upstream_method_hash 呼び出し、既知ハッシュ定数との照合、upstream 更新時にテスト失敗 (Red)

### Implementation (Green)

- [ ] T024 [US4] Implement get_upstream_method_hash in src/quant_insight_plus/submission_relay.py — SHA-256 ハッシュ計算 (Green)
- [ ] T025 [US4] Run quality check: `uv run ruff check --fix . && uv run ruff format . && uv run mypy .`

**Checkpoint**: US4 完了。upstream 変更時にテストが自動的に失敗する仕組みが機能。

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: 全体品質保証と公開 API 整理

- [ ] T026 Update src/quant_insight_plus/__init__.py — 公開 API に output_models, submission_relay のエクスポートを追加
- [ ] T027 Run full quality check: `uv run ruff check --fix . && uv run ruff format . && uv run mypy .`
- [ ] T028 Run full test suite: `uv run pytest`
- [ ] T029 Run quickstart.md validation — 手順通りの動作確認

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: 依存なし — 即時開始可能
- **Foundational (Phase 2)**: Phase 1 完了後 — **全 US をブロック**
- **US1 (Phase 3)**: Phase 2 完了後 — コア機能（MVP）
- **US2 (Phase 4)**: Phase 3 完了後 — agent.py 実装 (T012) に依存
- **US3 (Phase 5)**: US1 の T011 完了後 — patch_submission_relay() に依存
- **US4 (Phase 6)**: Phase 2 完了後 — submission_relay に依存。US1 と並行可能
- **Polish (Phase 7)**: 全 US 完了後

### User Story Dependencies

- **US1 (P1)**: Phase 2 完了後に開始可能。他 US への依存なし 🎯 MVP
- **US2 (P2)**: US1 完了後（agent.py の _enrich_task_with_workspace_context 実装に依存）
- **US3 (P3)**: US1 の T011 完了後に開始可能（patch_submission_relay に依存）
- **US4 (P3)**: Phase 2 完了後に開始可能。US1 と独立してテスト可能

### Within Each User Story

- テスト FIRST → FAIL 確認 → 実装 → GREEN 確認
- submission_relay → agent.py の順（agent が relay を使用）
- 実装 → TOML テンプレート → テスト確認
- 品質チェック通過後に次ストーリーへ

### Parallel Opportunities

- **Phase 2**: T003 + T004（別テストファイル）、T005 + T006（別ソースファイル）
- **Phase 3 Tests**: T008 + T009 + T010（全て別ファイル）
- **Phase 3 TOML**: T013 + T014 + T015（全て別ファイル）
- **US4**: Phase 2 完了後に US1 と並行可能

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1: Setup 完了
2. Phase 2: Foundational 完了（**CRITICAL — 全 US をブロック**）
3. Phase 3: US1 完了
4. **STOP and VALIDATE**: US1 を独立テスト
5. コードが FS 経由で Evaluator に正確に到達することを確認

### Incremental Delivery

1. Setup + Foundational → 基盤完成
2. US1 → テスト → MVP 完了!
3. US2 → テスト → エージェント間ファイル共有追加
4. US3 → テスト → セットアップコマンド対応
5. US4 → テスト → ドリフト検出追加
6. Polish → 全体品質保証

### Parallel Team Strategy

Phase 2 完了後:
- Developer A: US1（最優先、MVP）→ US2（US1 完了後）→ US3（T011 完了後）
- Developer B: US4（Phase 2 完了後に US1 と並行可能）

---

## Notes

- [P] tasks = 異なるファイル、依存関係なし
- [Story] label = 該当ユーザーストーリーへのトレーサビリティ
- 各 US は独立して完了・テスト可能
- テスト失敗を確認してから実装に着手
- 品質チェック通過後にコミット
- 各チェックポイントで独立検証を実施
