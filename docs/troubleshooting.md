# Troubleshooting

mixseek-quant-insight-plus 使用時に発生する可能性のあるエラーと対処法です。

## Claude Code CLI

### claude コマンドが見つからない

Claude Code CLI がインストールされていません。

```bash
# macOS / Linux / WSL
curl -fsSL https://claude.ai/install.sh | bash

# Homebrew (macOS)
brew install --cask claude-code

# インストール確認
claude --version
```

### セッションが無効です

Claude Code CLI のセッションが期限切れになっています。再認証が必要です。

```bash
claude
```

初回起動時または再認証時に、ブラウザで認証フローが開始されます。

## ファイルシステム

### SubmissionFileNotFoundError

ラウンドディレクトリに `submission.py` が存在しない場合、またはファイルが空の場合に発生します。`get_submission_content()` 内で送出されます。

**考えられる原因:**

- submission-creator がコードを生成したが、ファイルへの書き込みに失敗した
- ラウンドディレクトリは存在するが `submission.py` が書き込まれていない
- `submission.py` が存在するが空

**対処法:**

```bash
# ラウンドディレクトリの内容を確認
ls -la $MIXSEEK_WORKSPACE/submissions/round_{N}/

# submission.py の内容を確認
cat $MIXSEEK_WORKSPACE/submissions/round_{N}/submission.py
```

### RuntimeError: MIXSEEK_WORKSPACE 未設定

`_get_workspace_path()` で `MIXSEEK_WORKSPACE` 環境変数が設定されていない場合に発生します。

```bash
export MIXSEEK_WORKSPACE=/path/to/workspace
```

## 設定ファイル

### ValueError: 認証失敗または TOML 設定不足

TOML 設定ファイルに必須項目が不足している、またはモデル認証に失敗した場合に発生します。

**チェックリスト:**

- [ ] `[agent]` セクションに `type`, `name`, `model` が設定されているか
- [ ] `type` が `"claudecode_local_code_executor"` であるか
- [ ] `model` が `claudecode:` プレフィックスで始まっているか
- [ ] `claude --version` が正常に動作するか
- [ ] `[agent.system_instruction]` セクションに `text` が設定されているか

### エージェントタイプが認識されない

TOML の `type = "claudecode_local_code_executor"` が `MemberAgentFactory` に登録されていない場合に発生します。

**CLI 使用時:**

CLI（`qip`）は自動的にエージェントを登録するため、通常はこのエラーは発生しません。

**ライブラリ使用時:**

```python
import mixseek_plus
from quant_insight_plus import register_claudecode_quant_agents

# 必ずこの順序で呼び出す
mixseek_plus.patch_core()
register_claudecode_quant_agents()
```

### output_model のクラスが見つからない

`output_model.module_path` または `output_model.class_name` の指定が誤っている場合に発生します。

**確認方法:**

```python
# モジュールパスとクラス名が正しいか確認
from quant_insight_plus.agents.output_models import FileAnalyzerOutput
print(FileAnalyzerOutput.model_json_schema())
```

**利用可能な出力モデル:**

| class_name | module_path | 用途 |
|------------|-------------|------|
| `FileAnalyzerOutput` | `quant_insight_plus.agents.output_models` | データ分析 |
| `FileSubmitterOutput` | `quant_insight_plus.agents.output_models` | Submission 作成 |

## Leader の動作異常

### Leader がメンバーツールを使用せず EnterPlanMode/AskUserQuestion ループに入る

`delegate_only` プリセットでメタツール（`EnterPlanMode`, `AskUserQuestion`, `ExitPlanMode`）がブロックされていない場合、Leader がプランモードに入り承認を永久に待つサイクルに陥ります。

**症状:**

- 全ラウンドでスコアが `-100.0`（`CorrelationSharpeRatio.INVALID_SUBMISSION_SCORE`）
- セッションログに `EnterPlanMode`, `AskUserQuestion`, `ExitPlanMode` の呼び出しのみが記録される
- MCP 経由のメンバーツール呼び出しが 0 回
- `Leader did not call any member tools` 警告

**対処法:**

`configs/presets/claudecode.toml` の `delegate_only` プリセットでメタツールがブロックされていることを確認してください。

```toml
[delegate_only]
permission_mode = "bypassPermissions"
disallowed_tools = [
  # コーディングツール
  "Bash", "Write", "Edit", "Read", "Glob", "Grep",
  "WebFetch", "WebSearch", "NotebookEdit", "Task",
  # メタツール（承認者不在で無限ループを引き起こす）
  "EnterPlanMode", "ExitPlanMode", "AskUserQuestion",
  # タスク・チーム管理（リーダーには不要）
  "TodoWrite", "TaskCreate", "TaskUpdate", "TaskList", "TaskGet",
  "TeamCreate", "TeamDelete", "SendMessage",
]
```

### Leader がメンバーに委任せず自力でコードを生成する

`delegate_only` プリセットが正しく設定されているにもかかわらず、Leader がメンバーツールを呼び出さずテキストでコードを直接生成する場合があります。

**症状:**

- `round_history.member_submissions_record` の `total_count` が `0`
- Leader がテキストで Python コードを出力し、エラー修正だけでラウンドを消費する
- メタツールの呼び出しは発生しない

**原因:**

Leader の `system_instruction` に MCP ツールの実名が記載されていないため、モデルがツールの存在を認識できません。

**対処法:**

チーム設定の `system_instruction` で、各メンバーの MCP ツール名を明示的に記載してください。

```toml
system_instruction = """
## メンバー
- train-analyzer:
    - ツール名: `mcp__team__delegate_to_train-analyzer`
    - タスクの指示を `task` パラメータ（文字列）で渡す
- submission-creator:
    - ツール名: `mcp__team__delegate_to_submission-creator`
    - タスクの指示を `task` パラメータ（文字列）で渡す
"""
```

MCP ツール名の規則: `mcp__team__delegate_to_{agent_name}`（`agent_name` はメンバー設定の `[agent] name`）

## 実行時エラー

### タイムアウト

エージェントの実行がタイムアウトした場合の対処法です。タイムアウトは複数のレベルで設定されています。

| レベル | 設定場所 | デフォルト | 説明 |
|--------|---------|----------|------|
| コード実行 | `tool_settings.local_code_executor.timeout_seconds` | `120` | 個別のコード実行タイムアウト |
| リクエスト | `agent.timeout_seconds` | `30.0` | LLM リクエストタイムアウト |
| チーム | `orchestrator.timeout_per_team_seconds` | `3600` | チーム全体のタイムアウト |

```toml
# コード実行のタイムアウトを延長
[agent.metadata.tool_settings.local_code_executor]
timeout_seconds = 300  # 5分

# チーム全体のタイムアウトを延長
[orchestrator]
timeout_per_team_seconds = 7200  # 2時間
```

### MIXSEEK_WORKSPACE 未設定

`MIXSEEK_WORKSPACE` 環境変数が設定されていない場合、ワークスペースの検出に失敗します。

```bash
export MIXSEEK_WORKSPACE=/path/to/workspace
```

## よくある質問

### Gemini 版との違いは？

[User Guide](user-guide.md) の「Gemini 版との差分」セクションを参照してください。主な差分は、コード実行方式（pydantic-ai ツール vs Claude Code 組み込みツール）とスクリプト参照方式です。

### API キーは必要？

`claudecode:` プレフィックスは Claude Code CLI のセッション認証を使用するため、API キーの環境変数は不要です。`claude --version` が正常に動作すれば認証済みです。

### CLI と Python ライブラリの違いは？

CLI（`qip`）は起動時に `patch_core()` とエージェント登録を自動実行します。Python ライブラリとして使用する場合は、明示的にこれらを呼び出す必要があります。詳細は [Getting Started](getting-started.md) の「ライブラリとして使用する場合」セクションを参照してください。
