# Getting Started

mixseek-quant-insight-plus を使い始めるためのガイドです。

## 前提条件

| 要件 | 説明 |
|------|------|
| [uv](https://docs.astral.sh/uv/) | 推奨インストーラー (`uv tool install` で使用) |
| Python 3.13+ | 実行環境 |
| Claude Code CLI | `claude` コマンドがインストール・認証済みであること |
| [mixseek-plus](https://github.com/drillan/mixseek-plus) | `patch_core()`, `create_authenticated_model()` |
| [mixseek-quant-insight](https://github.com/drillan/mixseek-quant-insight) | `LocalCodeExecutorAgent` 基底クラス |

### Claude Code CLI のインストール

```bash
# macOS / Linux / WSL
curl -fsSL https://claude.ai/install.sh | bash

# Homebrew (macOS)
brew install --cask claude-code

# インストール確認
claude --version
```

初回起動時にブラウザで認証フローが開始されます。

## インストール

```bash
uv tool install git+https://github.com/drillan/mixseek-quant-insight-plus
```

> **Note**: `pip install git+https://github.com/drillan/mixseek-quant-insight-plus` でもインストール可能ですが、CLI ツールには隔離環境で管理できる `uv tool install` を推奨します。

### ローカル開発

```bash
git clone https://github.com/drillan/mixseek-quant-insight-plus
cd mixseek-quant-insight-plus
uv sync
```

`uv.sources` により `mixseek-plus` と `mixseek-quant-insight` はローカルの editable パスから解決されます。

### インストールの検証

```bash
# CLI が利用可能であることを確認
qip --version

# Claude Code CLI が認証済みであることを確認
claude --version

# Python からのインポートを確認
python -c "from quant_insight_plus import ClaudeCodeLocalCodeExecutorAgent; print('OK')"
```

## 環境変数の設定

| 変数名 | 必須 | 説明 |
|--------|------|------|
| `MIXSEEK_WORKSPACE` | はい | ワークスペースのルートパス |

```bash
export MIXSEEK_WORKSPACE=/path/to/workspace
```

> **Note**: `claudecode:` プレフィックスは Claude Code CLI のセッション認証を使用するため、API キーの環境変数は不要です。

## ワークスペースの初期化

`qip setup` コマンドでワークスペースを初期化できます。

```bash
# ワークスペースを初期化
qip setup -w /path/to/workspace
```

実行内容:

1. ワークスペース基本構造を作成（`logs/`, `configs/`, `templates/`）
2. テンプレート設定ファイルを `configs/` にコピー（ClaudeCode 専用設定）
3. `submissions/` ディレクトリを作成
4. `data/inputs/` ディレクトリを作成

### データの配置

ワークスペース内の `data/inputs/` ディレクトリに parquet ファイルを配置します。

```
$MIXSEEK_WORKSPACE/data/inputs/
├── ohlcv/ohlcv.parquet
├── returns/returns.parquet
└── master/master.parquet
```

### データの分割

train/valid/test に分割します。

```bash
qip data split --config $MIXSEEK_WORKSPACE/configs/competition.toml
```

分割後のディレクトリ構造:

```
$MIXSEEK_WORKSPACE/data/inputs/
├── ohlcv/
│   ├── ohlcv.parquet      # 元データ
│   ├── train.parquet      # train 期間
│   └── valid.parquet      # validation 期間
├── returns/
│   ├── returns.parquet
│   ├── train.parquet
│   └── valid.parquet
└── master/
    ├── master.parquet
    ├── train.parquet
    └── valid.parquet
```

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

設定項目の詳細は [Configuration Reference](configuration-reference.md) を参照してください。

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

- [User Guide](user-guide.md) - アーキテクチャ、設定詳細、スクリプト埋め込み機能
- [実行設計ガイド](execution-guide.md) - タスク設計、マルチチーム構成、プロンプトアーキテクチャ
- [Configuration Reference](configuration-reference.md) - 全設定項目のリファレンス
- [API Reference](api-reference.md) - クラスと関数の仕様
- [Troubleshooting](troubleshooting.md) - エラー対処法
