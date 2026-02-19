# mixseek-quant-insight-plus

[mixseek-quant-insight](https://github.com/drillan/mixseek-quant-insight) の ClaudeCode 拡張パッケージ。
`LocalCodeExecutorAgent` を Claude Code の組み込みツール（Bash, Read 等）で動作するように拡張します。

## Overview

mixseek-quant-insight の `LocalCodeExecutorAgent` は pydantic-ai のカスタムツールセット経由でコード実行を行いますが、
Claude Code モデル（`claudecode:` プレフィックス）使用時は CLI の組み込みツールで直接コード実行が可能です。

本パッケージは以下を提供します:

- **ClaudeCodeLocalCodeExecutorAgent** - pydantic-ai ツールセットを登録せず、Claude Code 組み込みツールに委ねるエージェント
- **スクリプト内容のプロンプト埋め込み** - DuckDB に保存済みの既存スクリプトをプロンプトに直接埋め込み（MCP 不要）
- **`claudecode_local_code_executor`** エージェントタイプの MemberAgentFactory 登録
- **CLI エントリーポイント** (`quant-insight-plus` / `qip`) - `patch_core()` とエージェント登録を自動実行

## 依存関係

| パッケージ | 役割 |
|-----------|------|
| [mixseek-plus](https://github.com/drillan/mixseek-plus) | `patch_core()`, `create_authenticated_model()` |
| [mixseek-quant-insight](https://github.com/drillan/mixseek-quant-insight) | `LocalCodeExecutorAgent` 基底クラス |

## インストール

```bash
pip install git+https://github.com/drillan/mixseek-quant-insight-plus
```

### ローカル開発

```bash
git clone https://github.com/drillan/mixseek-quant-insight-plus
cd mixseek-quant-insight-plus
uv sync
```

`uv.sources` により `mixseek-plus` と `mixseek-quant-insight` はローカルの editable パスから解決されます。

## クイックスタート

### 1. Member Agent 設定を作成

```toml
# configs/agents/members/code-executor.toml

[agent]
type = "claudecode_local_code_executor"
name = "code-executor"
model = "claudecode:claude-opus-4-6"
description = "ClaudeCodeでPythonコード実行・データ分析を行う"

[agent.system_instruction]
text = "データ分析を行うエージェントです。"

[agent.metadata.tool_settings.local_code_executor]
available_data_paths = ["data/inputs/ohlcv/train.parquet"]
timeout_seconds = 120
```

### 2. チーム設定を作成

```toml
# configs/agents/teams/team.toml

[team]
team_id = "team-claudecode"
team_name = "ClaudeCode Analysis Team"

[team.leader]
model = "claudecode:claude-opus-4-6"

[[team.members]]
config = "configs/agents/members/code-executor.toml"
```

### 3. CLI で実行

```bash
# 単一チームの開発・テスト
qip team "データ分析タスク" --config configs/agents/teams/team.toml

# 本番実行（オーケストレーター経由）
qip exec "データ分析タスク" --config orchestrator.toml
```

Python コードの記述は不要です。CLI が `patch_core()` と `register_claudecode_quant_agents()` を自動実行します。

### CLI コマンド一覧

| コマンド | 設定ファイル | 用途 |
|---------|------------|------|
| `qip member` | `agent.toml` | 単体 Agent テスト |
| `qip team` | `team.toml` | 単一チーム開発・テスト |
| `qip exec` | `orchestrator.toml` | 複数チーム本番実行 |
| `qip setup` | - | 環境を一括セットアップ（mixseek init → config init → db init） |
| `qip data` | - | データ取得・加工・分割 |
| `qip db` | - | データベース管理 |
| `qip export` | - | ログエクスポート |

### ライブラリとして使用する場合

```python
import mixseek_plus
from quant_insight_plus import register_claudecode_quant_agents

mixseek_plus.patch_core()
register_claudecode_quant_agents()
```

## アーキテクチャ

```
mixseek-core (フレームワーク)
  └── mixseek-plus (ClaudeCode/Groq 拡張)
        └── mixseek-quant-insight (ドメインプラグイン)
              └── mixseek-quant-insight-plus (本パッケージ)
```

### 親クラスとの差分

| 観点 | LocalCodeExecutorAgent | ClaudeCodeLocalCodeExecutorAgent |
|------|----------------------|--------------------------------|
| モデル解決 | `Agent(model=config.model)` (文字列直接) | `create_authenticated_model()` (`claudecode:` 対応) |
| ツールセット | pydantic-ai カスタムツール 4 種 | 登録なし (Claude Code 組み込みツール) |
| 既存スクリプト参照 | ファイル名のみフッタに追加 | スクリプト内容を Markdown 形式で埋め込み |
| `execute()` | 自前実装 | 親クラスから継承 |

## 開発

```bash
# テスト
uv run pytest

# リント・フォーマット
uv run ruff check --fix . && uv run ruff format .

# 型チェック
uv run mypy .
```

## ライセンス

Apache License 2.0
