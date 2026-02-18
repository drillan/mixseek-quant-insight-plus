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

```python
import mixseek_plus
from quant_insight_plus import register_claudecode_quant_agents

# claudecode: プレフィックスを有効化
mixseek_plus.patch_core()

# MemberAgentFactory に登録
register_claudecode_quant_agents()
```

```toml
# team.toml

[[members]]
name = "code-executor"
type = "claudecode_local_code_executor"
model = "claudecode:claude-sonnet-4-5"
system_prompt = "データ分析を行うエージェントです。"

[members.metadata.tool_settings.local_code_executor]
available_data_paths = ["data/stock"]
timeout_seconds = 120
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
