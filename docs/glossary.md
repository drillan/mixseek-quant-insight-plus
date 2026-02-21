# 用語集

mixseek-quant-insight-plus で使用される主要な用語の定義です。

`ClaudeCodeLocalCodeExecutorAgent`
: `LocalCodeExecutorAgent` を継承した ClaudeCode 版エージェント。pydantic-ai のカスタムツールセットを登録せず、Claude Code の組み込みツール（Bash, Read 等）でコード実行を行う。

`claudecode_local_code_executor`
: TOML 設定の `[agent]` セクションで使用するエージェントタイプ名。`register_claudecode_quant_agents()` の呼び出しにより `MemberAgentFactory` に登録される。

`claudecode:` プレフィックス
: モデル ID の記法。`claudecode:claude-opus-4-6` のように使用し、Claude Code CLI のセッション認証経由でモデルにアクセスする。API キーは不要。mixseek-plus の `create_authenticated_model()` で解決される。

`LocalCodeExecutorAgent`
: mixseek-quant-insight が提供するベースエージェント。pydantic-ai のカスタムツールセット経由でコード実行を行う。`ClaudeCodeLocalCodeExecutorAgent` の親クラス。

`patch_core()`
: mixseek-plus が提供する関数。mixseek-core の `create_authenticated_model()` を拡張し、`claudecode:` および `groq:` プレフィックスのモデル解決を追加する。Leader/Evaluator エージェントでこれらのモデルを使用する前に呼び出しが必要。

`register_claudecode_quant_agents()`
: `ClaudeCodeLocalCodeExecutorAgent` を `MemberAgentFactory` に登録する関数。CLI（`qip`）では自動的に呼び出される。

`MemberAgentFactory`
: mixseek-core が提供するエージェント登録メカニズム。TOML の `type` フィールドとエージェントクラスの対応を管理する。

`ワークスペースコンテキスト埋め込み`
: `ClaudeCodeLocalCodeExecutorAgent` 固有の機能。ラウンドディレクトリ（`submissions/round_{N}/`）内のファイル内容を、タスクプロンプト末尾に Markdown 形式で自動追加する。同一ラウンド内で先に実行されたエージェントの出力を後続エージェントが参照可能。

`FileAnalyzerOutput`
: データ分析エージェントの構造化出力モデル（Pydantic）。`analysis_path`（分析結果ファイルの絶対パス）と `report`（Markdown 形式の分析レポート）のフィールドを持つ。

`FileSubmitterOutput`
: Submission 作成エージェントの構造化出力モデル（Pydantic）。`submission_path`（提出コードファイルの絶対パス）と `description`（概要）のフィールドを持つ。

`ImplementationContext`
: ラウンドディレクトリの特定に使用するコンテキスト情報。`execution_id`（実行識別子）、`team_id`（チーム ID）、`round_number`（ラウンド番号）、`member_agent_name`（エージェント名）の4フィールドで構成される。

`submissions/round_{N}/` ディレクトリ
: エージェントが生成したファイルを保存するラウンドごとのディレクトリ。`ensure_round_dir()` で冪等に作成される。`submission.py`（Submission コード）と `analysis.md`（分析レポート）を格納する。

`SubmissionFileNotFoundError`
: Submission ファイルの読み取り失敗時に送出される例外。`patch_submission_relay()` 内で発生し、呼び出し元に明示的に伝播される。

`qip`
: `quant-insight-plus` CLI の短縮コマンド名。`qip member`、`qip team`、`qip exec` の3つのサブコマンドを提供する。起動時に `patch_core()` とエージェント登録を自動実行する。

`OutputModelConfig`
: 構造化出力モデルの TOML 設定に対応する Pydantic モデル。`module_path`（モジュールパス）と `class_name`（クラス名）のフィールドを持つ。
