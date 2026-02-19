# システム全体フロー

mixseek-quant-insight-plus の処理は、**セットアップ → データ準備 → シグナル生成 → 評価** の 4 フェーズで構成されます。このページでは各フェーズの役割と流れを俯瞰します。

## 概要図

```{mermaid}
flowchart TB
    subgraph Phase1["1. セットアップ"]
        A["qip setup"] --> B["ワークスペース初期化\n設定ファイル配置\nDuckDB スキーマ作成"]
    end

    subgraph Phase2["2. データ準備"]
        C["qip data fetch-jquants"] --> D["OHLCV + Master 取得"]
        D --> E["リターン計算"]
        E --> F["qip data split"]
        F --> G["train / valid / test 分割"]
    end

    subgraph Phase3["3. シグナル生成"]
        H["qip team / qip exec"] --> I["Leader エージェント"]
        I --> J["train-analyzer\n（train データ分析）"]
        I --> K["submission-creator\n（Submission 実装）"]
        J --> L["分析レポート +\nスクリプト"]
        K --> M["Submission スクリプト"]
    end

    subgraph Phase4["4. 評価"]
        M --> N["バックテストループ\n（Time Series API 形式）"]
        N --> O["Spearman 順位相関"]
        O --> P["シャープレシオ\n→ リーダーボード"]
    end

    Phase1 --> Phase2
    Phase2 --> Phase3
    Phase3 --> Phase4
```

## 1. セットアップ

### ワークスペース初期化

`qip setup` コマンドを実行すると、以下が自動的に行われます:

1. `mixseek init` でワークスペースの基本ディレクトリ構造を作成
2. `configs/` 以下に TOML 設定ファイルのテンプレートを配置
3. `quant-insight db init` で DuckDB スキーマ（`agent_implementation` テーブル）を初期化
4. `data/inputs/` ディレクトリを作成

```
$MIXSEEK_WORKSPACE/
├── configs/
│   ├── competition.toml
│   ├── evaluator.toml
│   ├── orchestrator.toml
│   └── agents/
│       ├── members/
│       │   ├── train_analyzer_claudecode.toml
│       │   └── submission_creator_claudecode.toml
│       └── teams/
│           └── claudecode_team.toml
├── data/
│   ├── inputs/         ← データ配置先
│   └── db/             ← DuckDB ファイル
└── logs/
```

### 環境変数

| 変数名 | 用途 |
|--------|------|
| `MIXSEEK_WORKSPACE` | ワークスペースの絶対パス（必須） |
| `JQUANTS_API_KEY` | J-Quants API の認証キー（データ取得時に必要） |

## 2. データ準備

### 2.1 データ取得（qip data fetch-jquants）

J-Quants API から株価データと銘柄マスタを取得します。

```bash
qip data fetch-jquants --plan free --universe prime
```

| オプション | 説明 | 選択肢 |
|-----------|------|--------|
| `--plan` | J-Quants プラン | `free`, `light`, `standard`, `premium` |
| `--universe` | 銘柄ユニバース | `prime`, `standard`, `growth`, `all` |

取得されるデータ:

- **OHLCV**: 日足の株価データ（始値・高値・安値・終値・出来高）
- **Master**: 銘柄マスタ（企業名・セクター・市場区分）

データの詳細なスキーマは [データ仕様](data-specification.md) を参照してください。

### 2.2 リターン計算

OHLCV データから目的変数（リターン系列）を計算します。計算方式は `competition.toml` の `[competition.return_definition]` で設定します。

- **close2close**: 当日終値 → 翌日終値のリターン
- **open2close**: 翌日始値 → 翌日終値のリターン（より現実的）

計算方式の詳細は [データ仕様](data-specification.md) の「Returns データ」セクションを参照してください。

### 2.3 データ分割（qip data split）

時系列に沿ってデータを train / valid / test に分割します。

```bash
qip data split --config $MIXSEEK_WORKSPACE/configs/competition.toml
```

分割後のディレクトリ構成:

```
$MIXSEEK_WORKSPACE/data/inputs/
├── ohlcv/
│   ├── train.parquet
│   ├── valid.parquet
│   └── test.parquet
├── returns/
│   ├── train.parquet
│   ├── valid.parquet
│   └── test.parquet
└── master/
    ├── train.parquet
    ├── valid.parquet
    └── test.parquet
```

境界付近のデータ漏洩を防ぐ **パージ（purge）** 機能があります。詳細は [データ仕様](data-specification.md) の「データ分割」セクションを参照してください。

## 3. シグナル生成

### 3.1 実行モード

| コマンド | 用途 | 設定ファイル |
|---------|------|------------|
| `qip member` | 単体エージェントのテスト | `agent.toml` |
| `qip team` | 単一チームの開発・テスト | `team.toml` |
| `qip exec` | 複数チームの本番実行（オーケストレーター） | `orchestrator.toml` |

### 3.2 チーム構造

```{mermaid}
flowchart TB
    Leader["Leader\n（claudecode:claude-sonnet-4-5）\nチーム全体を指揮"]
    Leader -->|"タスク指示"| TA["train-analyzer\ntrain データの分析\n仮説検証"]
    Leader -->|"タスク指示"| SC["submission-creator\nSubmission スクリプト実装\n動作確認"]
    TA -->|"AnalyzerOutput\nscripts + report"| Leader
    SC -->|"SubmitterOutput\nsubmission + description"| Leader
```

| エージェント | 入力データ | 出力 | タイムアウト |
|------------|----------|------|------------|
| **train-analyzer** | train の OHLCV, Master, Returns | `AnalyzerOutput`（スクリプト + レポート） | 120 秒 |
| **submission-creator** | valid の OHLCV, Master | `SubmitterOutput`（Submission + 説明） | 300 秒 |

Leader はメンバーの出力を受け取り、仮説の検証結果に基づいて次のラウンドの指示を組み立てます。

### 3.3 ラウンド制と反復改善

オーケストレーター実行時、各チームは複数ラウンドにわたりシグナル生成を繰り返します。前ラウンドで作成されたスクリプトは自動的にプロンプトに埋め込まれ、反復改善を可能にします。

```{mermaid}
flowchart LR
    R1["Round 1\nエージェント実行"] -->|"スクリプト保存"| DB[(DuckDB\nagent_implementation)]
    DB -->|"スクリプト埋め込み\nプロンプトに自動追加"| R2["Round 2\nエージェント実行"]
    R2 -->|"スクリプト更新"| DB
    DB -->|"スクリプト埋め込み"| R3["Round 3\nエージェント実行"]
```

- 各ラウンドで生成されたスクリプトは DuckDB の `agent_implementation` テーブルに保存されます
- 次ラウンドの実行時、保存済みスクリプトがプロンプトの末尾に Markdown 形式で自動追加されます
- DB 読み込みエラー時は例外を明示的に伝播します（暗黙のデータ欠損は許容しません）

スクリプト埋め込み機能の詳細は [User Guide](user-guide.md) の「スクリプト埋め込み機能」セクションを参照してください。

### 3.4 オーケストレーター（qip exec）

```bash
qip exec "株価シグナル生成" --config $MIXSEEK_WORKSPACE/configs/orchestrator.toml
```

- 複数のチームを並列実行
- `min_rounds` 〜 `max_rounds` の範囲でラウンドを反復
- 各ラウンドの Submission を自動評価
- チームごとに `timeout_per_team_seconds` でタイムアウト管理

設定の詳細は [Configuration Reference](configuration-reference.md) を参照してください。

## 4. 評価

### 4.1 評価フロー

Submission スクリプトは `CorrelationSharpeRatio` メトリックによって自動評価されます。

```{mermaid}
flowchart TB
    Sub["Submission スクリプト"] --> Parse["パース\ngenerate_signal 関数を抽出"]
    Parse --> BT["バックテストループ\nテストデータの各日時を順に処理"]
    BT --> Filter["現在日時までの\nデータをフィルタ"]
    Filter --> Gen["generate_signal を呼び出し\nシグナルを生成"]
    Gen --> Corr["Spearman 順位相関\nシグナル vs リターン"]
    Corr --> Next{"全日時を\n処理済み?"}
    Next -->|"いいえ"| Filter
    Next -->|"はい"| Stats["シャープレシオ算出\nmean / std of correlations"]
    Stats --> Score["MetricScore\nリーダーボードに反映"]
```

- エージェントが生成した Submission スクリプトから `generate_signal` 関数を抽出
- **テストデータのみ** で評価（エージェントはテストデータにアクセスできません）
- Time Series API 形式: 各日時で「現在までのデータのみ」を渡してシグナルを生成
- 各日時の Spearman 順位相関を計算し、その系列のシャープレシオが最終スコア

`generate_signal` 関数の仕様と評価方式の詳細は [データ仕様](data-specification.md) の「評価方式」セクションを参照してください。

### 4.2 リーダーボード

- 各チーム・各ラウンドのシャープレシオがリーダーボードに記録されます
- Submission 起因のエラー時のスコアは `-100.0` となります

## 関連ドキュメント

- [Getting Started](getting-started.md) -- インストールと初期セットアップの手順
- [データ仕様](data-specification.md) -- データスキーマ、リターン計算、分割、評価の詳細
- [User Guide](user-guide.md) -- エージェント設定、チーム設定、スクリプト埋め込み機能
- [Configuration Reference](configuration-reference.md) -- 全設定ファイルのリファレンス
