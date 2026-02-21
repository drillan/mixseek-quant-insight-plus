# CLAUDE.md

## プロジェクト概要

**mixseek-quant-insight-plus**はmixseek-quant-insightのClaudeCode拡張パッケージ。

```
mixseek-core → mixseek-plus → mixseek-quant-insight → mixseek-quant-insight-plus（本パッケージ）
```

**参照ドキュメント**:
- `.specify/memory/constitution.md` - プロジェクト憲法
- `.claude/git-conventions.md` - Git命名規則

## 開発ワークフロー

### DDD（ドキュメント駆動開発）

**原則**: 実装前にドキュメント影響を確認し、必要に応じて更新

**ワークフロー開始時のチェック**:
- README.mdに更新すべき情報がないか
- docs/に更新すべきドキュメントがないか
- specs/に関連する仕様がないか

**開始方法**（状況に応じて選択）:

**A. 仕様定義から始める場合（speckit）**:
1. `/speckit.specify` → `specs/<連番>-<name>/spec.md`
2. `/speckit.plan` → `plan.md`, `research.md`, `data-model.md`
3. `/speckit.tasks` → `tasks.md`
4. `/speckit.implement` → TDDに従って実装

**B. Issueから始める場合（issue-workflow）**:
1. `/start-issue <number>` → Issue開始、ブランチ作成
2. TDDに従って実装
3. `/commit-push-pr` → コミット・プッシュ・PR作成
4. `/review-pr-comments` → レビュー対応
5. `/merge-pr <number>` → PR統合

**必須チェック**:
- 実装前にドキュメント影響を確認
- 仕様が曖昧な場合は明確化要求
- 品質ゲート通過後にコミット

#### doc-updaterスキル発動条件

以下の状況でdoc-updaterスキル（`/doc-updater`）を起動:

1. **API/インターフェース変更**: 公開クラス・関数・メソッドのシグネチャ変更時
2. **新機能追加**: 新しいクラス、モジュール、重要な機能の追加時
3. **アーキテクチャ変更**: システム設計・構造に影響する変更時
4. ユーザーからの明示的なドキュメント更新依頼時
5. コードとドキュメントの乖離を検出した時

## 品質チェック・開発コマンド

- 品質チェック: `uv run ruff check --fix . && uv run ruff format . && uv run mypy .`
- テスト: `uv run pytest` / `uv run pytest -m unit`
- ドキュメントビルド: `uv run make -C docs html`

## CLI & Agent設計ルール

### CLI要件

- 全コマンドに`--help`で明確な使用方法を表示
- 対話モードと`--non-interactive`非対話モードをサポート
- エラーメッセージに具体的な解決方法を含める
- 終了コード: 成功=0, 失敗=非0

### Agent要件

- エージェントは独立してテスト可能にする
- 設定はTOMLファイルで一元管理（`src/quant_insight_plus/templates/`配下）
- `MemberAgentFactory`への登録はパッケージ初期化時に自動実行

## 命名規則

- 詳細: `.claude/git-conventions.md`
- specs/: `<3桁連番>-<name>`（例: `001-auth`）
- ブランチ: ゼロパディングなし

## CLIコマンド

- **コマンド名**: `quant-insight-plus` または `qip`（短縮形）
- **単体テスト**: `qip member "タスク" --config <agent.toml>`
- **チーム実行**: `qip team "タスク" --config <team.toml>`
- **本番実行**: `qip exec "タスク" --config <orchestrator.toml>`
- **環境構築**: `qip setup` / `qip data` / `qip db` / `qip export`

## 技術スタック

| カテゴリ | 技術 |
|---------|------|
| 言語 | Python 3.13+ |
| AIフレームワーク | pydantic-ai |
| CLI | Typer |
| データバリデーション | Pydantic 2.10+ |
| DB | DuckDB |
| パッケージ管理 | uv |
| 品質ツール | ruff, mypy, pytest |
| ドキュメント | Sphinx + MyST-Parser + shibuya |
