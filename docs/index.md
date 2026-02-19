# mixseek-quant-insight-plus

[mixseek-quant-insight](https://github.com/drillan/mixseek-quant-insight) の ClaudeCode 拡張パッケージ。`LocalCodeExecutorAgent` を Claude Code の組み込みツール（Bash, Read 等）で動作するように拡張します。

## 概要

mixseek-quant-insight-plus は、mixseek-quant-insight の `LocalCodeExecutorAgent` を拡張し、Claude Code モデル（`claudecode:` プレフィックス）でのデータ分析エージェント実行を可能にします。

主な機能:

- **ClaudeCodeLocalCodeExecutorAgent**: pydantic-ai ツールセットを登録せず、Claude Code 組み込みツールに委ねるエージェント
- **スクリプト内容のプロンプト埋め込み**: DuckDB に保存済みの既存スクリプトをプロンプトに直接埋め込み（MCP 不要）
- **`claudecode_local_code_executor`** エージェントタイプの MemberAgentFactory 登録
- **CLI エントリーポイント** (`quant-insight-plus` / `qip`): `patch_core()` とエージェント登録を自動実行

```{toctree}
:caption: 'ガイド'
:maxdepth: 2

getting-started
user-guide
```

```{toctree}
:caption: 'リファレンス'
:maxdepth: 2

api-reference
configuration-reference
```

```{toctree}
:caption: 'サポート'
:maxdepth: 1

troubleshooting
glossary
```
