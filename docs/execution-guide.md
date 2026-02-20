# 実行設計ガイド

[User Guide](user-guide.md) で設定方法を学んだ後、このガイドで効果的な実行の設計方法を学びます。以下の 3 つのトピックを扱います:

1. **プロンプトアーキテクチャ** -- タスク文がシステム内部でどう処理されるか
2. **実践的なタスク例** -- `qip member` / `qip team` / `qip exec` の具体的な使い方
3. **マルチチーム構成パターン** -- 複数チームを並列実行する設計パターン

## プロンプトアーキテクチャ

### プロンプトの全体構造

CLI で渡すタスク文（`user_prompt`）と、チーム設定の `system_instruction` は**別レイヤー**として Leader エージェントに注入されます。

```{mermaid}
flowchart TB
    CLI["qip exec 'タスク文'"] --> UP["user_prompt"]
    SI["system_instruction<br>(team.toml)"] --> Leader

    UP --> TPL["Jinja2 Template<br>(prompt_builder_default.toml)"]
    TPL -->|"team_user_prompt"| Leader["Leader Agent"]
    TPL -->|"evaluator_user_prompt"| Evaluator["Evaluator"]
    TPL -->|"judgment_user_prompt"| Judgment["JudgmentClient"]
```

- **system_instruction**: Leader のシステムプロンプトとして注入される（チーム設定で定義）
- **user_prompt**: Jinja2 テンプレートで加工され、ユーザメッセージとして Leader・Evaluator・JudgmentClient の 3 つに渡される

### user_prompt と system_instruction の役割分担

| 項目 | system_instruction | user_prompt（CLI 引数） |
|------|-------------------|----------------------|
| **定義場所** | `team.toml` の `[team.leader]` | `qip exec` / `qip team` の引数 |
| **役割** | チームの「性格」 | 今回の「お題」 |
| **内容例** | 戦略方針、メンバー構成、データ定義、Submission 形式 | 実行ごとの目標、制約、フォーカス |
| **変更頻度** | チーム設計時に固定 | 実行ごとに変更可能 |
| **スコープ** | そのチームのみ | 全チーム共通 |

> **重要**: `user_prompt` はオーケストレーターから全チームに同一の内容で配布されます。チーム固有の戦略は `system_instruction` に記述してください。

### user_prompt の伝播先

`user_prompt` は Leader だけでなく、**評価と継続判定**にも影響します。

| 伝播先 | テンプレート | 用途 | 追加で注入される情報 |
|--------|------------|------|------------------|
| Leader Agent | `team_user_prompt` | タスクの実行指示 | `round_number`, `submission_history`, `ranking_table`, `team_position_message` |
| Evaluator | `evaluator_user_prompt` | Submission の評価基準 | `submission` |
| JudgmentClient | `judgment_user_prompt` | ラウンド継続判定 | `submission_history`, `ranking_table` |

Evaluator は `user_prompt` を「ユーザから指定されたタスク」として参照し、Submission がタスクに適合しているかを判断します。JudgmentClient も同様に、タスクの文脈で改善余地を評価します。

### Jinja2 テンプレート変数

`team_user_prompt` テンプレートで利用可能な変数:

| 変数 | 型 | 説明 |
|------|-----|------|
| `{{ user_prompt }}` | `str` | CLI で指定したタスク文 |
| `{{ round_number }}` | `int` | 現在のラウンド番号 |
| `{{ submission_history }}` | `str` | 過去の Submission 履歴（整形済み） |
| `{{ ranking_table }}` | `str` | リーダーボード順位表（整形済み） |
| `{{ team_position_message }}` | `str` | チーム順位メッセージ（整形済み） |
| `{{ current_datetime }}` | `str` | 現在日時（ISO 8601 形式、タイムゾーン付き） |

テンプレートは `prompt_builder_default.toml` で定義されており、`orchestrator.toml` の `[prompt_builder]` セクションでカスタマイズ可能です。詳細は [Configuration Reference](configuration-reference.md) を参照してください。

## 実践的なタスク例

### タスク設計の原則

タスク文は抽象的すぎても具体的すぎても効果が下がります。

| レベル | 例 | 問題点 |
|--------|-----|--------|
| 抽象的すぎる | `"株価シグナル生成"` | Leader の自由度が高すぎ、初期ラウンドを探索に消費しがち |
| 具体的すぎる | `"RSI(14)を計算し、30以下で買いシグナルを出すコードを書け"` | Agent の自律的な判断や改善の余地がない |
| **適切** | `"RSI とボリンジャーバンドを組み合わせた逆張りシグナルを生成せよ。IC の安定性を重視する"` | 方向性 + 評価基準を示しつつ、実装の判断は Agent に委ねる |

**ベストプラクティス**: 「戦略の方向性 + 評価基準」を示し、具体的な実装判断は Agent に委ねる。

### qip member（単体エージェント）

単体エージェントのテスト・探索に使います。タスクは直接的な指示が適しています。

#### データ探索

```bash
# カラム一覧と基本統計量
qip member "trainデータのカラム一覧を確認し、各数値カラムの基本統計量を出力してください" \
    --config $MIXSEEK_WORKSPACE/configs/agents/members/train_analyzer_claudecode.toml

# 欠損値・外れ値の確認
qip member "trainデータの欠損値パターンを調査し、各カラムの欠損率と外れ値の分布を報告してください" \
    --config $MIXSEEK_WORKSPACE/configs/agents/members/train_analyzer_claudecode.toml
```

#### 仮説検証

```bash
# セクター別分析
qip member "sector17_name ごとにリターンの平均・標準偏差・シャープレシオを算出し、セクター間の差異を分析してください" \
    --config $MIXSEEK_WORKSPACE/configs/agents/members/train_analyzer_claudecode.toml

# 特徴量とリターンの相関
qip member "過去5日・20日・60日のリターンモメンタムと翌日リターンの順位相関(IC)を日次で算出し、IC の平均と安定性を報告してください" \
    --config $MIXSEEK_WORKSPACE/configs/agents/members/train_analyzer_claudecode.toml
```

#### 特徴量エンジニアリング

```bash
# テクニカル指標の算出
qip member "RSI(14日)、MACD(12,26,9)、ATR(14日)を算出し、各指標と翌日リターンの順位相関を分析してください" \
    --config $MIXSEEK_WORKSPACE/configs/agents/members/train_analyzer_claudecode.toml
```

### qip team（単一チーム）

Leader がメンバーに指示を分配するため、タスクは目標レベルで記述します。

#### 戦略指定

```bash
# モメンタム戦略
qip team "過去5日・20日・60日のリターンを特徴量として、短期モメンタムに基づくシグナルを生成せよ" \
    --config $MIXSEEK_WORKSPACE/configs/agents/teams/claudecode_team.toml

# 平均回帰戦略
qip team "ボリンジャーバンド(20日,2σ)からの乖離率を用いた平均回帰シグナルを生成せよ" \
    --config $MIXSEEK_WORKSPACE/configs/agents/teams/claudecode_team.toml

# 出来高異常検知
qip team "出来高の20日移動平均に対する比率を計算し、出来高急増銘柄に対するシグナルを生成せよ" \
    --config $MIXSEEK_WORKSPACE/configs/agents/teams/claudecode_team.toml
```

#### 評価制約付き

```bash
# IC（情報係数）の安定性を重視
qip team "月次ICの標準偏差が小さく安定したシグナルを重視せよ。リスク調整後リターン(シャープレシオ)の最大化を目標にシグナルを生成せよ" \
    --config $MIXSEEK_WORKSPACE/configs/agents/teams/claudecode_team.toml
```

### qip exec（オーケストレーター）

複数チーム並列実行では、`user_prompt` は全チーム共通の目標として機能します。`system_instruction` に戦略がある場合、`user_prompt` は焦点や制約の指定に使います。

#### system_instruction に戦略がない場合（デフォルトテンプレート）

```bash
# マルチステップ指示
qip exec "Step1: trainデータの欠損値・外れ値を確認。Step2: リターンの自己相関とセクター効果を分析。Step3: 分析結果に基づき、有効な特徴量を3つ以上選定してシグナルを生成せよ" \
    --config $MIXSEEK_WORKSPACE/configs/orchestrator.toml

# 戦略と評価基準を同時に指定
qip exec "モメンタムとミーンリバーションの複合シグナルを構築し、IC > 0.03 を目標にせよ" \
    --config $MIXSEEK_WORKSPACE/configs/orchestrator.toml
```

#### system_instruction に戦略がある場合（マルチチーム構成時）

各チームの `system_instruction` に戦略が定義されている場合、`user_prompt` は共通目標や実行条件の指定に使います。

```bash
# 共通の定量目標
qip exec "IC > 0.03 のシグナルを目指せ" \
    --config $MIXSEEK_WORKSPACE/configs/orchestrator.toml

# 今回のフォーカス
qip exec "特に小型株セクターに注力せよ" \
    --config $MIXSEEK_WORKSPACE/configs/orchestrator.toml

# 実行条件の制約
qip exec "計算コストの低いシンプルな特徴量のみ使用し、低ターンオーバーを重視したシグナルを生成せよ" \
    --config $MIXSEEK_WORKSPACE/configs/orchestrator.toml
```

## マルチチーム構成パターン

### orchestrator.toml でのチーム追加

`[[orchestrator.teams]]` セクションを追加することでチームを増やせます。

```toml
[orchestrator]
min_rounds = 3
max_rounds = 5
timeout_per_team_seconds = 3600
evaluator_config = "configs/evaluator.toml"

[[orchestrator.teams]]
config = "configs/agents/teams/team_momentum.toml"

[[orchestrator.teams]]
config = "configs/agents/teams/team_mean_reversion.toml"

[[orchestrator.teams]]
config = "configs/agents/teams/team_composite.toml"
```

> **注意**: 各チームの `team_id` は一意である必要があります。重複がある場合、Orchestrator が `ValueError` を送出します。

### チーム間の独立性と共有リソース

各チームは独立した実行環境を持ちますが、評価基準とデータは共有されます。

```{mermaid}
flowchart TB
    subgraph Shared["共有リソース"]
        EV["evaluator.toml<br>（評価基準）"]
        DB[(DuckDB)]
        TD["テストデータ"]
    end

    subgraph TeamA["Team A（独立）"]
        RC1["RoundController"]
        RH1["round_history"]
        S1["scripts"]
    end

    subgraph TeamB["Team B（独立）"]
        RC2["RoundController"]
        RH2["round_history"]
        S2["scripts"]
    end

    EV --> RC1
    EV --> RC2
    RC1 --> DB
    RC2 --> DB
```

| 区分 | リソース | 説明 |
|------|---------|------|
| **独立** | `RoundController` | 各チームごとに独立したインスタンス |
| **独立** | `round_history` | ラウンド履歴はチーム固有 |
| **独立** | スクリプト保存 | DuckDB の `agent_implementation` テーブルに `team_id` で区別して保存 |
| **共有** | `evaluator.toml` | 全チーム同一の評価基準で比較 |
| **共有** | テストデータ | 全チーム同一のテストデータで評価 |
| **共有** | DuckDB | 物理的には共有だが、データは `team_id` で論理的に分離 |

### チーム間の差別化軸

| 差別化軸 | 変更箇所 | 効果 |
|---------|---------|------|
| **戦略指示** | Leader の `system_instruction` | アルファ源泉の多様化 |
| **温度** | Leader/Member の `temperature` | 探索 vs 最適化のバランス |
| **メンバー構成** | `[[team.members]]` の数・種類 | 分業の深さ vs 回転速度 |
| **モデル** | `model` フィールド | 推論能力 vs コスト |

### パターン 1: 戦略分岐

Leader の `system_instruction` で異なるアルファ戦略を指示します。

```toml
# configs/agents/teams/team_momentum.toml
[team]
team_id = "team-momentum"
team_name = "Momentum Strategy Team"

[team.leader]
model = "claudecode:claude-opus-4-6"
temperature = 0.0
system_instruction = """
## 分析方針
モメンタム効果に特化したシグナルを構築せよ。
- 短期(5日)・中期(20日)・長期(60日)のリターンモメンタムを分析
- 出来高加速度との組み合わせを検討
- セクターモメンタム（業種内相対強度）も考慮
...(ロール、メンバー、データ、Submission形式は共通部分のため省略)
"""
# ... (以下共通設定)
```

```toml
# configs/agents/teams/team_mean_reversion.toml
[team]
team_id = "team-mean-reversion"
team_name = "Mean Reversion Strategy Team"

[team.leader]
model = "claudecode:claude-opus-4-6"
temperature = 0.0
system_instruction = """
## 分析方針
平均回帰効果に特化したシグナルを構築せよ。
- ボリンジャーバンド乖離率、RSI の逆張りシグナルを分析
- 過剰反応の検出（急落後リバウンド、急騰後反落）
- ボラティリティレジーム別の効果差を検証
...(共通部分省略)
"""
# ... (以下共通設定)
```

### パターン 2: 探索温度分岐

同じ戦略でも `temperature` を変えることで、探索と最適化のバランスを調整します。

```toml
# configs/agents/teams/team_exploit.toml
[team]
team_id = "team-exploit"
team_name = "Exploitation Team"

[team.leader]
model = "claudecode:claude-opus-4-6"
temperature = 0.0
system_instruction = """
## 分析方針
確実性の高いシンプルな特徴量から始め、段階的に精度を改善せよ。
既知の有効因子（モメンタム、バリュー、低ボラティリティ）を中心に、堅牢なシグナルの構築を優先する。
"""
```

```toml
# configs/agents/teams/team_explore.toml
[team]
team_id = "team-explore"
team_name = "Exploration Team"

[team.leader]
model = "claudecode:claude-opus-4-6"
temperature = 0.7
system_instruction = """
## 分析方針
従来の因子にとらわれず、データから新しいパターンを発見せよ。
- ローソク足パターンの非線形組み合わせ
- 出来高プロファイルの異常検知
- セクター間のリードラグ関係
大胆な仮説を積極的に検証し、意外性のあるシグナルを目指す。
"""
```

### パターン 3: メンバー構成分岐

メンバーの数や役割を変えて、分業の深さと回転速度のトレードオフを調整します。

```toml
# configs/agents/teams/team_deep.toml -- 3名体制
[team]
team_id = "team-deep"
team_name = "Deep Analysis Team"

[team.leader]
# ...
system_instruction = """
## メンバー
- train-analyzer: trainデータの探索的分析を行う
- feature-engineer: 分析結果を基に特徴量エンジニアリングを行う
- submission-creator: 特徴量を組み込んだSubmissionスクリプトを実装する

分析→特徴量設計→実装の3段階で進めてください。
"""

[[team.members]]
config = "configs/agents/members/train_analyzer_claudecode.toml"

[[team.members]]
config = "configs/agents/members/feature_engineer_claudecode.toml"

[[team.members]]
config = "configs/agents/members/submission_creator_claudecode.toml"
```

### パターン 4: モデル比較

異なる LLM の推論特性を比較します。

```toml
# configs/agents/teams/team_sonnet.toml -- コスト効率重視
[team]
team_id = "team-sonnet"
team_name = "Sonnet Cost-Efficient Team"

[team.leader]
model = "claudecode:claude-sonnet-4-6"
temperature = 0.0
# ...

[[team.members]]
config = "configs/agents/members/train_analyzer_sonnet.toml"

[[team.members]]
config = "configs/agents/members/submission_creator_sonnet.toml"
```

### パターン 5: ハイブリッド構成

上記の差別化軸を組み合わせた実用的な構成例:

```toml
# orchestrator.toml
[orchestrator]
min_rounds = 3
max_rounds = 5
timeout_per_team_seconds = 3600
evaluator_config = "configs/evaluator.toml"

# モメンタム × Opus × 確定的
[[orchestrator.teams]]
config = "configs/agents/teams/team_momentum.toml"

# 平均回帰 × Opus × 確定的
[[orchestrator.teams]]
config = "configs/agents/teams/team_mean_reversion.toml"

# 自由探索 × Opus × 探索的
[[orchestrator.teams]]
config = "configs/agents/teams/team_explore.toml"
```

| チーム | 戦略 | モデル | temperature |
|--------|------|--------|-------------|
| team-momentum | モメンタム特化 | claude-opus-4-6 | 0.0 |
| team-mean-reversion | 平均回帰特化 | claude-opus-4-6 | 0.0 |
| team-explore | 自由探索 | claude-opus-4-6 | 0.7 |

### 設定ファイルの管理

マルチチーム構成では、`configs/agents/teams/` 配下に複数のチーム設定を配置します。

```
configs/
├── orchestrator.toml            # 全チームを束ねる
├── evaluator.toml               # 共通の評価基準
└── agents/
    ├── members/
    │   ├── train_analyzer_claudecode.toml
    │   ├── submission_creator_claudecode.toml
    │   └── feature_engineer_claudecode.toml  # パターン3用
    └── teams/
        ├── team_momentum.toml
        ├── team_mean_reversion.toml
        └── team_explore.toml
```

共通の `system_instruction` テンプレートを用意し、戦略部分のみを差し替えることで管理コストを抑えられます。

## 関連ドキュメント

- [User Guide](user-guide.md) -- エージェント設定、チーム設定、オーケストレーター設定
- [Configuration Reference](configuration-reference.md) -- 全設定ファイルのリファレンス
- [システム全体フロー](system-flow.md) -- 4 フェーズの処理フローと評価方式
- [データ仕様](data-specification.md) -- データスキーマ、評価メトリクスの詳細
