# examples - ClaudeCode quant-insight ワークスペースサンプル

## 前提条件

- `mixseek-quant-insight-plus` がインストール済み（`uv tool install git+https://github.com/drillan/mixseek-quant-insight-plus`）
- `claude` CLI がログイン済み（`claudecode:` プレフィックスは CLI 経由で認証）
- データファイル（parquet）が手元にある

## セットアップ

### 1. ワークスペースを初期化

```bash
qip setup -w /path/to/workspace
```

実行内容:
1. `mixseek init` でワークスペース基本構造を作成
2. `configs/` 以下の TOML 設定ファイルをコピー（ClaudeCode 設定を自動適用）
3. `qip db init` で DuckDB スキーマを初期化
4. `data/inputs/` ディレクトリを作成

### 2. データを配置

以下のディレクトリに parquet ファイルを配置してください:

```
/path/to/workspace/data/inputs/
├── ohlcv/ohlcv.parquet
├── returns/returns.parquet
└── master/master.parquet
```

### 3. データを分割（train/valid/test）

```bash
export MIXSEEK_WORKSPACE=/path/to/workspace
qip data split --config $MIXSEEK_WORKSPACE/configs/competition.toml
```

### 4. 環境変数を設定

```bash
export MIXSEEK_WORKSPACE=/path/to/workspace
```

## 実行

### 単一チームの開発・テスト

```bash
qip team "trainデータの基本統計量を分析してください" \
    --config $MIXSEEK_WORKSPACE/configs/agents/teams/claudecode_team.toml
```

### 本番実行（オーケストレーター経由）

```bash
qip exec "株価シグナル生成" \
    --config $MIXSEEK_WORKSPACE/configs/orchestrator.toml
```

### 単体 Agent テスト

```bash
qip member "trainデータのカラム一覧を確認してください" \
    --config $MIXSEEK_WORKSPACE/configs/agents/members/train_analyzer_claudecode.toml
```

## 設定ファイル構成

```
configs/
├── competition.toml               # コンペティション定義（データ分割設定）
├── evaluator.toml                 # 評価メトリクス設定
├── judgment.toml                  # ラウンド継続判定設定
├── orchestrator.toml              # 本番実行用（exec コマンド）
└── agents/
    ├── members/
    │   ├── train_analyzer_claudecode.toml      # データ分析 Agent
    │   └── submission_creator_claudecode.toml  # Submission 作成 Agent
    └── teams/
        └── claudecode_team.toml               # チーム構成（team コマンド）
```

## Gemini 版との主な差分

| 項目 | Gemini 版 | ClaudeCode 版 |
|------|----------|--------------|
| model | `google-gla:gemini-3-flash-preview` | `claudecode:claude-opus-4-6` |
| agent type | `custom` + `plugin` 指定 | `claudecode_local_code_executor` |
| コード実行 | pydantic-ai `execute_python_code` ツール | Claude Code 組み込み Bash ツール |
| スクリプト参照 | `read_script` ツール | プロンプトに内容を自動埋め込み |
| CLI | `mixseek exec` / `quant-insight` | `qip exec` / `quant-insight-plus` |
