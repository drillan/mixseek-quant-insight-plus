"""US2: ワークスペースコンテキスト埋め込みテスト。

_enrich_task_with_workspace_context の受け入れ基準を独立テストで検証:
- ImplementationContext 未設定時の素通り
- ラウンドディレクトリ非存在時の素通り
- ラウンドディレクトリが空の場合の素通り
- 空白のみファイルの素通り
- 単一ファイル埋め込み
- 複数ファイル埋め込み
- サブディレクトリのスキップ（ファイルのみ埋め込み）
- MIXSEEK_WORKSPACE 未設定時の RuntimeError
"""

from pathlib import Path

import pytest
from quant_insight.agents.local_code_executor.models import ImplementationContext

from quant_insight_plus.agents.agent import ClaudeCodeLocalCodeExecutorAgent
from quant_insight_plus.submission_relay import SUBMISSIONS_DIR_NAME


class TestEnrichTaskWithWorkspaceContext:
    """_enrich_task_with_workspace_context のテスト。"""

    def test_returns_task_unchanged_when_no_implementation_context(
        self,
        agent: ClaudeCodeLocalCodeExecutorAgent,
    ) -> None:
        """ImplementationContext 未設定時はタスクをそのまま返す。"""
        assert agent.executor_config.implementation_context is None

        result = agent._enrich_task_with_workspace_context("original task")

        assert result == "original task"

    def test_returns_task_unchanged_when_round_dir_not_exists(
        self,
        agent: ClaudeCodeLocalCodeExecutorAgent,
        implementation_context: ImplementationContext,
        mock_workspace_env: Path,
    ) -> None:
        """ラウンドディレクトリが存在しない場合はタスクをそのまま返す。"""
        agent.executor_config.implementation_context = implementation_context
        # ラウンドディレクトリを作成しない — submissions/round_1 が存在しない

        result = agent._enrich_task_with_workspace_context("original task")

        assert result == "original task"

    def test_returns_task_unchanged_when_round_dir_empty(
        self,
        agent: ClaudeCodeLocalCodeExecutorAgent,
        implementation_context: ImplementationContext,
        mock_workspace_env: Path,
    ) -> None:
        """ラウンドディレクトリが空の場合はタスクをそのまま返す。"""
        agent.executor_config.implementation_context = implementation_context
        round_dir = mock_workspace_env / SUBMISSIONS_DIR_NAME / "round_1"
        round_dir.mkdir(parents=True)

        result = agent._enrich_task_with_workspace_context("original task")

        assert result == "original task"

    def test_returns_task_unchanged_when_files_are_whitespace_only(
        self,
        agent: ClaudeCodeLocalCodeExecutorAgent,
        implementation_context: ImplementationContext,
        mock_workspace_env: Path,
    ) -> None:
        """ファイルが空白のみの場合はタスクをそのまま返す。"""
        agent.executor_config.implementation_context = implementation_context
        round_dir = mock_workspace_env / SUBMISSIONS_DIR_NAME / "round_1"
        round_dir.mkdir(parents=True)
        (round_dir / "empty.txt").write_text("   \n  ")

        result = agent._enrich_task_with_workspace_context("original task")

        assert result == "original task"

    def test_embeds_single_file_content(
        self,
        agent: ClaudeCodeLocalCodeExecutorAgent,
        implementation_context: ImplementationContext,
        mock_workspace_env: Path,
    ) -> None:
        """単一ファイルの内容がタスクプロンプトに埋め込まれる。"""
        agent.executor_config.implementation_context = implementation_context
        round_dir = mock_workspace_env / SUBMISSIONS_DIR_NAME / "round_1"
        round_dir.mkdir(parents=True)
        (round_dir / "analysis.md").write_text("# Analysis Report\nData looks good.")

        result = agent._enrich_task_with_workspace_context("original task")

        assert result.startswith("original task")
        assert "ワークスペースファイル" in result
        assert "### analysis.md" in result
        assert "# Analysis Report" in result
        assert "Data looks good." in result

    def test_embeds_multiple_files_sorted_by_name(
        self,
        agent: ClaudeCodeLocalCodeExecutorAgent,
        implementation_context: ImplementationContext,
        mock_workspace_env: Path,
    ) -> None:
        """複数ファイルが名前順でタスクプロンプトに埋め込まれる。"""
        agent.executor_config.implementation_context = implementation_context
        round_dir = mock_workspace_env / SUBMISSIONS_DIR_NAME / "round_1"
        round_dir.mkdir(parents=True)
        (round_dir / "analysis.md").write_text("Analysis content")
        (round_dir / "submission.py").write_text("print('hello')")

        result = agent._enrich_task_with_workspace_context("original task")

        assert "### analysis.md" in result
        assert "### submission.py" in result
        # analysis.md は submission.py より前にある（ソート順）
        analysis_pos = result.index("### analysis.md")
        submission_pos = result.index("### submission.py")
        assert analysis_pos < submission_pos

    def test_skips_subdirectories(
        self,
        agent: ClaudeCodeLocalCodeExecutorAgent,
        implementation_context: ImplementationContext,
        mock_workspace_env: Path,
    ) -> None:
        """サブディレクトリはスキップされる（ファイルのみ埋め込み）。"""
        agent.executor_config.implementation_context = implementation_context
        round_dir = mock_workspace_env / SUBMISSIONS_DIR_NAME / "round_1"
        round_dir.mkdir(parents=True)
        (round_dir / "analysis.md").write_text("Real content")
        subdir = round_dir / "subdir"
        subdir.mkdir()
        (subdir / "nested.txt").write_text("Nested content")

        result = agent._enrich_task_with_workspace_context("original task")

        assert "### analysis.md" in result
        assert "nested.txt" not in result

    def test_raises_runtime_error_when_workspace_env_not_set(
        self,
        agent: ClaudeCodeLocalCodeExecutorAgent,
        implementation_context: ImplementationContext,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """MIXSEEK_WORKSPACE 未設定時に RuntimeError を送出。"""
        agent.executor_config.implementation_context = implementation_context
        monkeypatch.delenv("MIXSEEK_WORKSPACE")

        with pytest.raises(RuntimeError, match="MIXSEEK_WORKSPACE"):
            agent._enrich_task_with_workspace_context("any task")
