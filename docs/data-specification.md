# データ仕様

mixseek-quant-insight-plus で使用するデータの形式、処理方法、シグナル生成と評価の仕様を説明します。

## データセット一覧

| データセット | 役割 | 必須 | ソース |
|------------|------|------|--------|
| OHLCV | 株価データ（始値・高値・安値・終値・出来高） | はい | J-Quants API または自前のParquet |
| Returns | リターン系列（目的変数） | はい | OHLCV から自動計算 |
| Master | 銘柄マスタ情報（企業名・セクター・市場区分） | いいえ | J-Quants API または自前のParquet |
| Signal | エージェントが出力するシグナル | — | エージェントが生成 |

## OHLCV データ

### スキーマ

OHLCV データの標準スキーマです。`OHLCVRow` モデルに対応します。

| カラム名 | 型 | 説明 |
|---------|-----|------|
| `datetime` | `Datetime` | 日付 |
| `symbol` | `String` | 銘柄コード（例: `"7203"`） |
| `open` | `Decimal` / `Float64` | 始値（調整済み） |
| `high` | `Decimal` / `Float64` | 高値（調整済み） |
| `low` | `Decimal` / `Float64` | 安値（調整済み） |
| `close` | `Decimal` / `Float64` | 終値（調整済み） |
| `volume` | `Int64` | 出来高（調整済み、0 以上） |

これら 7 カラムがリターン計算・バックテストで必須です。

### J-Quants API からの追加カラム

`qip data fetch-jquants` で取得した場合、標準スキーマに加えて以下のカラムが含まれます。

**価格・出来高関連:**

| カラム名 | 説明 |
|---------|------|
| `adj_factor` | 調整係数（株式分割・併合等） |
| `raw_open`, `raw_high`, `raw_low`, `raw_close` | 生価格（未調整） |
| `raw_volume` | 生出来高（未調整） |
| `upper_limit`, `lower_limit` | 値幅制限（ストップ高・ストップ安） |
| `turnover` | 売買代金 |

**前場・後場データ:**

| カラム名 | 説明 |
|---------|------|
| `morning_open`, `morning_high`, `morning_low`, `morning_close` | 前場の生価格 |
| `morning_adj_open`, `morning_adj_high`, `morning_adj_low`, `morning_adj_close` | 前場の調整済み価格 |
| `morning_volume`, `morning_turnover` | 前場の出来高・売買代金 |
| `afternoon_open`, `afternoon_high`, `afternoon_low`, `afternoon_close` | 後場の生価格 |
| `afternoon_adj_open`, `afternoon_adj_high`, `afternoon_adj_low`, `afternoon_adj_close` | 後場の調整済み価格 |
| `afternoon_volume`, `afternoon_turnover` | 後場の出来高・売買代金 |

### 調整済み価格について

- J-Quants API の `AdjO`/`AdjH`/`AdjL`/`AdjC`/`AdjVo` が標準スキーマの `open`/`high`/`low`/`close`/`volume` にマッピングされます
- 株式分割・併合・配当による調整済み価格です
- リターン計算やバックテストは調整済み価格を使用します

### データ粒度

- **日足**: 1 営業日 = 1 行 / 銘柄
- 各行は `(datetime, symbol)` の組み合わせで一意に識別されます

## Master データ

### スキーマ

銘柄マスタ情報のスキーマです。

| カラム名 | 型 | 説明 |
|---------|-----|------|
| `datetime` | `Datetime` | 日付 |
| `symbol` | `String` | 銘柄コード |
| `company_name` | `String` | 企業名 |
| `company_name_en` | `String` | 企業名（英語） |
| `sector17_code` | `String` | 17 業種コード |
| `sector17_name` | `String` | 17 業種名 |
| `sector33_code` | `String` | 33 業種コード |
| `sector33_name` | `String` | 33 業種名 |
| `scale_category` | `String` | 規模区分 |
| `market_code` | `String` | 市場コード |
| `market_name` | `String` | 市場名 |
| `margin_code` | `String` | 信用区分コード |
| `margin_name` | `String` | 信用区分名 |

### 用途

- エージェントがセクター分析や市場区分別の特徴抽出に使用します
- バックテスト時に `additional_data` として `generate_signal` 関数に渡されます
- OHLCV との結合キーは `symbol` です

## Returns データ

### スキーマ

リターン系列のスキーマです。`ReturnRow` モデルに対応します。

| カラム名 | 型 | 説明 |
|---------|-----|------|
| `datetime` | `Datetime` | エントリー日時 |
| `symbol` | `String` | 銘柄コード |
| `return_value` | `Float64` | 未来の実現リターン（負値・ゼロ・正値いずれも可） |

Returns データは OHLCV データから自動計算されます。計算方式は `competition.toml` で設定します。

### リターン計算方式

`[competition.return_definition]` で以下を設定します:

| 設定項目 | 説明 | デフォルト |
|---------|------|----------|
| `window` | リターン計算のウィンドウ幅（日数） | `1` |
| `method` | 計算方式 | `"close2close"` |

#### close2close 方式

```
return_value = close(t + window) / close(t) - 1
```

t 時点の終値でエントリーし、t + window 時点の終値でエグジットする想定です。シンプルで直感的ですが、厳密には t 時点の終値を確認してから t 時点の終値でエントリーすることは現実には不可能であり、look-ahead bias があります。シミュレーション上の慣習として許容されます。

#### open2close 方式

```
return_value = (close(t + window) - open(t + 1)) / open(t + 1)
```

t 時点のシグナルに基づき、翌営業日 (t+1) の寄付で約定、t + window 時点の終値でエグジットする想定です。シグナルは t 時点までの情報で生成されるため、look-ahead bias がありません。

#### タイムラインの比較（window = 1 の場合）

```{mermaid}
flowchart LR
    subgraph close2close["close2close 方式"]
        direction LR
        CC1["t 日<br>シグナル生成<br>（close 参照）"] --> CC2["t 日<br>エントリー<br>（close）"]
        CC2 --> CC3["t+1 日<br>エグジット<br>（close）"]
    end
    subgraph open2close["open2close 方式"]
        direction LR
        OC1["t 日<br>シグナル生成<br>（close 参照）"] --> OC2["t+1 日<br>エントリー<br>（open）"]
        OC2 --> OC3["t+1 日<br>エグジット<br>（close）"]
    end
```

## データ分割（train / valid / test）

### 分割方式

時系列データのため、ランダム分割ではなく **日時ベースの分割** を行います。`competition.toml` の `[competition.data_split]` で設定します。

| 設定項目 | 型 | 説明 |
|---------|-----|------|
| `train_end` | `datetime` | train 期間の終了日時（この日時を含む） |
| `valid_end` | `datetime` | valid 期間の終了日時（この日時を含む） |
| `purge_rows` | `int` | パージ日数（各境界のデータ除外日数） |

### 分割ルール

```
                  train_end              valid_end
                     |                      |
  ┌──────────────────┼──────────────────────┼──────────────────┐
  │      train       │       valid          │       test       │
  │ datetime         │ train_end <          │ valid_end <      │
  │ <= train_end     │ datetime <= valid_end│ datetime         │
  └──────────────────┼──────────────────────┼──────────────────┘
```

### パージ（Purge）

リターン計算では `shift(-window)` により未来の価格を参照します。分割境界付近のデータは、境界を跨いだ未来の価格情報を含む可能性があります。**パージ** はこのデータ漏洩（look-ahead bias）を防止するため、境界付近のデータを除外します。

```
  ┌────────┬───────┬───────┬──────────────┬───────┬───────┬────────┐
  │ train  │ purge │ purge │    valid     │ purge │ purge │  test  │
  │ (使用) │(末尾  │(先頭  │    (使用)    │(末尾  │(先頭  │ (使用) │
  │        │ 除外) │ 除外) │             │ 除外) │ 除外) │        │
  └────────┴───────┴───────┴──────────────┴───────┴───────┴────────┘
           ↑ train_end                    ↑ valid_end
```

- train の末尾 `purge_rows` 日分を除外
- valid の先頭 `purge_rows` 日分を除外
- valid の末尾 `purge_rows` 日分を除外
- test の先頭 `purge_rows` 日分を除外

パージ適用後にいずれかの分割が空になった場合は `DataSplitError` が発生します。

### 各分割の用途

| 分割 | エージェントの用途 | 評価への関与 |
|------|----------------|------------|
| **train** | train-analyzer がデータ分析・仮説検証に使用 | 使用しない |
| **valid** | submission-creator が Submission の動作確認に使用 | 使用しない |
| **test** | エージェントからはアクセス不可 | `CorrelationSharpeRatio` が評価に使用 |

### 設定例

```toml
[competition.data_split]
train_end = "2021-12-31T23:59:59"
valid_end = "2023-12-31T23:59:59"
purge_rows = 1

[competition.return_definition]
window = 1
method = "open2close"
```

## Signal データ（シグナル出力）

### スキーマ

エージェントが生成するシグナルのスキーマです。`SignalRow` モデルに対応します。

| カラム名 | 型 | 説明 |
|---------|-----|------|
| `datetime` | `Datetime` | 日時 |
| `symbol` | `String` | 銘柄コード |
| `signal` | 数値型（`Float64` 等） | シグナル値（負値・ゼロ・正値いずれも可） |

### generate_signal 関数の仕様

Submission スクリプトには `generate_signal` 関数を含める必要があります。

```python
def generate_signal(
    ohlcv: pl.DataFrame,
    additional_data: dict[str, pl.DataFrame],
) -> pl.DataFrame:
    """シグナル生成関数。

    Args:
        ohlcv: OHLCV DataFrame（現在の日時までのデータ）
        additional_data: 追加データセット（master 等）

    Returns:
        カラム (datetime, symbol, signal) を持つ DataFrame
    """
    ...
```

**引数の制約:**

- `ohlcv` と `additional_data` は **現在の日時までのデータのみ** を含みます（Time Series API 制約）
- 未来のデータにはアクセスできません

**戻り値の制約:**

- `pl.DataFrame` または `pd.DataFrame` を返す（`pd.DataFrame` は内部で `pl.from_pandas()` により変換されます）
- 必須カラム: `datetime`（`Datetime` 型）, `symbol`（`String` 型）, `signal`（数値型）
- 必須カラムが不足、または型が不正な場合は `SubmissionInvalidError` が発生します

**引数の型検証:**

- 第 1 引数: `pl.DataFrame` または `pd.DataFrame`
- 第 2 引数: `dict[str, pl.DataFrame]` または互換型
- 引数が 2 つでない場合は `SubmissionInvalidError` が発生します

## 評価方式

### バックテストループ（Time Series API 形式）

Submission は Kaggle Time Series API スタイルのバックテストで評価されます。テストデータ内のユニーク日時を順に処理し、各日時で「現在までのデータのみ」を渡してシグナルを生成します。

```{mermaid}
flowchart TB
    Start["テストデータの<br>ユニーク日時リストを取得<br>（ソート済み）"] --> Loop{"次の日時<br>がある?"}
    Loop -->|"はい"| Filter["current_datetime までの<br>データをフィルタ"]
    Filter --> Gen["generate_signal<br>(available_ohlcv, available_additional)"]
    Gen --> Validate["シグナル形式を検証<br>(datetime, symbol, signal)"]
    Validate --> Join["current_datetime の<br>シグナルとリターンを結合<br>(datetime, symbol で inner join)"]
    Join --> Corr["Spearman 順位相関を計算"]
    Corr --> Store["相関値を記録"]
    Store --> Loop
    Loop -->|"いいえ"| Stats["相関系列から統計計算"]
    Stats --> SR["シャープレシオ算出"]
    SR --> Result["BacktestResult"]
```

**評価に使用するデータ:**

| データ | パス |
|--------|------|
| OHLCV | `$MIXSEEK_WORKSPACE/data/inputs/ohlcv/test.parquet` |
| Returns | `$MIXSEEK_WORKSPACE/data/inputs/returns/test.parquet` |
| 追加データ | `$MIXSEEK_WORKSPACE/data/inputs/{name}/test.parquet` |

### Spearman 順位相関

各イテレーション（日時）で、シグナル値とリターン値の断面（cross-sectional）Spearman 順位相関を計算します。

**NaN の処理:**

- シグナルの NaN 値 → 平均値で補完
- リターンの NaN 値 → そのシンボルを除外
- 有効データポイントが 2 未満の場合 → そのイテレーションの相関値は `None`

### シャープレシオ

全イテレーションの相関値（`None` を除く）からシャープレシオを算出します。

```
sharpe_ratio = mean(correlations) / std(correlations, ddof=1)
```

**エッジケース:**

| 条件 | 結果 |
|------|------|
| 有効イテレーションが 0 件 | `SubmissionFailedError`（Submission 失敗扱い） |
| 有効イテレーションが 1 件 | `std = None`, `sharpe_ratio = 0.0` |
| 標準偏差が 0 | `sharpe_ratio = 0.0` |
| Submission 起因のエラー | スコア = `-100.0` |

## ファイル形式

### Parquet

全データは Apache Parquet 形式で保存されます。

- 列指向フォーマットにより効率的な圧縮と高速な読み込みが可能
- Polars (`pl.read_parquet`) で直接読み込み可能
- Pandas (`pd.read_parquet`) でも読み込み可能

### datetime 精度

- Polars はマイクロ秒精度（`us`）をデフォルトとします
- Pandas はナノ秒精度（`ns`）をデフォルトとします
- バックテスト時に **自動的にマイクロ秒精度に統一** されます（join 時の型不一致エラーを防止するため）

## 関連ドキュメント

- [システム全体フロー](system-flow.md) -- 全体的な処理フローの概要
- [Configuration Reference](configuration-reference.md) -- `competition.toml` の全設定項目
- [User Guide](user-guide.md) -- エージェント設定、スクリプト埋め込み機能
- [Glossary](glossary.md) -- 用語定義
