# Research: ファイルシステムベース・コード実行環境

**Feature**: `001-fs-code-execution` | **Date**: 2026-02-21

## 1. Monkey-Patch 方式の設計判断

**Decision**: `RoundController._execute_single_round()` のメソッド本体を完全置換する monkey-patch 方式を採用する。

**Rationale**: upstream の `_execute_single_round()` は L310 で `submission_content: str = result.output` を設定し、その後 L337-343 で Evaluator に渡す。この処理はメソッド内部で一体化されており、事後的にラップして差し替える方式は不可。メソッド本体の置換が必須。

**Alternatives considered**:
- Evaluator 手前でのインターセプト → Evaluator 呼び出し前に `submission_content` がセット済みのため不可
- upstream へのPR → upstream は別リポジトリであり、変更サイクルが異なる
- サブクラス化 → `RoundController` はフレームワーク内部で直接インスタンス化されるため、サブクラスへの差し替えが困難

## 2. ドリフト検出メカニズム

**Decision**: パッチ対象メソッドのソースコード SHA-256 ハッシュを定数として記録し、テストで検証する。

**Rationale**: upstream ライブラリの更新時にパッチ対象メソッドが変更された場合、パッチが正しく動作しない可能性がある。ハッシュベースの自動検出により、`uv lock --upgrade` 後のテスト実行で即座に検知できる。

**Alternatives considered**:
- AST ベースの比較 → 実装コストが高く、フォーマット変更にも反応する
- バージョンピン → upstream の他の修正を取り込めなくなる

## 3. 構造化出力モデルの設計

**Decision**: `FileSubmitterOutput(submission_path, description)` と `FileAnalyzerOutput(analysis_path, report)` を新規作成。コード本体はフィールドに含めない。

**Rationale**: upstream の `SubmitterOutput` は `submission` フィールドにコード本体を持つ。FS ベースではコードはファイルに存在するため、パスのみを持つ新モデルが必要。コードの二重管理（ファイル + 構造化出力）を排除する（FR-003）。

**Alternatives considered**:
- `SubmitterOutput` を継承して `submission` を空にする → セマンティクスが不明確
- `submission` フィールドにパスを入れる → フィールド名と内容の意味が乖離

## 4. Python 実行コマンドの注入方式

**Decision**: TOML テンプレートの `[agent.metadata.tool_settings.local_code_executor]` に `python_command` 設定値を追加し、`system_instruction` にテンプレート変数として注入する。

**Rationale**: 既存の TOML 一元管理体系（Constitution Article 3）と整合。環境変数の増加を抑え、エージェントごとに異なるコマンドを設定可能にする。

**Alternatives considered**:
- 環境変数方式 → エージェント単位の設定ができない
- system_instruction に直接記述 → 設定値としての管理ができない

## 5. DuckDB テーブルの段階的廃止

**Decision**: `agent_implementation` テーブルのみをファイルシステムで置き換える。`leader_board`, `round_status` 等の upstream テーブルは維持する。

**Rationale**: `agent_implementation` はスクリプト保存専用テーブル。他のテーブルは upstream の `mixseek-core` が直接使用しており、本機能のスコープ外。

**Alternatives considered**:
- 全テーブル廃止 → upstream の機能が破壊される
- テーブル維持 + FS 併用 → データの二重管理が発生

## 6. ワークスペースコンテキスト埋め込み方式

**Decision**: `_enrich_task_with_workspace_context()` で、ラウンドディレクトリ内の全ファイルをタスクプロンプトのフッタに埋め込む。

**Rationale**: 既存の `_enrich_task_with_existing_scripts()` は DuckDB からスクリプトを読み取っていた。FS ベースでは、ラウンドディレクトリを走査してファイル内容を埋め込む方式に変更する。`ImplementationContext` 未設定時はタスクをそのまま返す。

**Alternatives considered**:
- ファイルパスのみ埋め込み → エージェントが Read ツールで読む必要があり、プロンプト注入の方が効率的
- 特定ファイルのみ埋め込み → 将来の拡張性を考慮し、ディレクトリ走査方式を採用
