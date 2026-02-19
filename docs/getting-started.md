# Getting Started

mixseek-quant-insight-plus を使い始めるためのガイドです。

## 前提条件

| 要件 | 説明 |
|------|------|
| Python 3.13+ | 実行環境 |
| Claude Code CLI | `claude` コマンドがインストール・認証済みであること |
| [mixseek-plus](https://github.com/drillan/mixseek-plus) | `patch_core()`, `create_authenticated_model()` |
| [mixseek-quant-insight](https://github.com/drillan/mixseek-quant-insight) | `LocalCodeExecutorAgent` 基底クラス |

Claude Code CLI のインストール確認:

```bash
claude --version
```

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

## 環境変数の設定

| 変数名 | 必須 | 説明 |
|--------|------|------|
| `MIXSEEK_WORKSPACE` | はい | ワークスペースのルートパス |

```bash
export MIXSEEK_WORKSPACE=/path/to/workspace
```

> **Note**: `claudecode:` プレフィックスは Claude Code CLI のセッション認証を使用するため、APIキーの環境変数は不要です。

## クイックスタート

### 1. Member Agent 設定を作成

```toml
# configs/agents/members/code-executor.toml

[agent]
type = "claudecode_local_code_executor"
name = "code-executor"
model = "claudecode:claude-sonnet-4-5"
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
model = "claudecode:claude-sonnet-4-5"

[[team.members]]
config = "configs/agents/members/code-executor.toml"
```

### 3. CLI で実行

```bash
# 単体 Agent テスト
qip member "データのカラム一覧を確認してください" \
    --config $MIXSEEK_WORKSPACE/configs/agents/members/code-executor.toml

# 単一チームの開発・テスト
qip team "データ分析タスク" \
    --config $MIXSEEK_WORKSPACE/configs/agents/teams/team.toml

# 本番実行（オーケストレーター経由）
qip exec "株価シグナル生成" \
    --config $MIXSEEK_WORKSPACE/configs/orchestrator.toml
```

### ライブラリとして使用する場合

Python コードから直接使用する場合は、`patch_core()` とエージェント登録を明示的に呼び出します。

```python
import mixseek_plus
from quant_insight_plus import register_claudecode_quant_agents

mixseek_plus.patch_core()
register_claudecode_quant_agents()
```

CLI (`qip`) を使用する場合はこの操作は不要です。CLI が自動的に実行します。

## 次のステップ

- [User Guide](user-guide.md) - アーキテクチャ、設定詳細、ワークスペースセットアップ
- [API Reference](api-reference.md) - クラスと関数の仕様
