# Data Model: ファイルシステムベース・コード実行環境

**Feature**: `001-fs-code-execution` | **Date**: 2026-02-21

## Entities

### FileSubmitterOutput

submission-creator エージェントの構造化出力。コード本体はファイルに存在し、
このモデルはパスと説明のみを保持する。

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `submission_path` | `str` | Yes | 書き込んだ submission.py の絶対パス |
| `description` | `str` | Yes | Submission の概要（Markdown） |

**Validation**: `submission_path` に `field_validator` で絶対パス検証を適用

**Relationship**: Submission ファイル（`submissions/round_{N}/submission.py`）と1:1対応

---

### FileAnalyzerOutput

train-analyzer エージェントの構造化出力。

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `analysis_path` | `str` | Yes | 書き込んだ analysis.md の絶対パス |
| `report` | `str` | Yes | 分析結果レポート（Markdown） |

**Validation**: `analysis_path` に `field_validator` で絶対パス検証を適用

**Relationship**: Analysis ファイル（`submissions/round_{N}/analysis.md`）と1:1対応

---

### SubmissionFileNotFoundError

submission.py がラウンドディレクトリに存在しない場合に送出される例外。

| Attribute | Type | Description |
|-----------|------|-------------|
| (inherited) | `FileNotFoundError` | 標準のファイル不在例外を継承 |

---

## Directory Structure (Data Model)

```
$MIXSEEK_WORKSPACE/
├── submissions/                    ← FR-006: setup で作成
│   └── round_{N}/                  ← FR-007: 冪等に作成
│       ├── submission.py           ← FR-001: submission-creator が Write
│       └── analysis.md             ← FR-004: train-analyzer が Write
├── data/inputs/                    ← 既存（変更なし）
│   ├── ohlcv/
│   ├── returns/
│   └── master/
├── configs/                        ← 既存（変更なし）
└── mixseek.db                      ← 既存（leader_board, round_status 用）
```

## Named Constants

| Constant | Value | Module |
|----------|-------|--------|
| `SUBMISSION_FILENAME` | `"submission.py"` | `submission_relay` |
| `ANALYSIS_FILENAME` | `"analysis.md"` | `submission_relay` |
| `SUBMISSIONS_DIR_NAME` | `"submissions"` | `submission_relay` |

## State Transitions

### Round Directory Lifecycle

```
(not exists) → ensure_round_dir() → (empty directory)
                                    → train-analyzer writes analysis.md
                                    → submission-creator writes submission.py
                                    → get_submission_content() reads submission.py
```

### Submission Relay Patch Lifecycle

```
(unpatched) → patch_submission_relay() → (patched)
                                       → patch_submission_relay() again → (no-op, idempotent)
(patched)   → reset_submission_relay_patch() → (unpatched)
```
