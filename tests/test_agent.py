"""ClaudeCodeLocalCodeExecutorAgent のユニットテスト（FS ベース版）。"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from mixseek.models.member_agent import MemberAgentConfig

from quant_insight_plus.agents.agent import ClaudeCodeLocalCodeExecutorAgent
from tests.conftest import MODEL_PATCH


class TestClaudeCodeLocalCodeExecutorAgentInit:
    """__init__ の動作を検証するテスト。"""

    @patch(MODEL_PATCH)
    def test_uses_create_authenticated_model(
        self,
        mock_create_model: MagicMock,
        member_agent_config: MemberAgentConfig,
        mock_model: MagicMock,
    ) -> None:
        """create_authenticated_model でモデルを解決すること。"""
        mock_create_model.return_value = mock_model

        agent = ClaudeCodeLocalCodeExecutorAgent(member_agent_config)

        mock_create_model.assert_called_once_with("claudecode:claude-opus-4-6")
        assert agent.agent.model is mock_model

    def test_no_toolsets_registered(
        self,
        agent: ClaudeCodeLocalCodeExecutorAgent,
    ) -> None:
        """pydantic-ai ツールセットを登録しないこと（Claude Code 組み込みツールに委ねる）。"""
        toolset = getattr(agent.agent, "_function_toolset", None)
        assert toolset is None or len(toolset.tools) == 0

    def test_inherits_executor_config(
        self,
        agent: ClaudeCodeLocalCodeExecutorAgent,
    ) -> None:
        """親クラスの executor_config 構築ロジックを再利用すること。"""
        assert agent.executor_config.available_data_paths == ["data/test"]
        assert agent.executor_config.timeout_seconds == 60

    def test_output_type_default_is_str(
        self,
        agent: ClaudeCodeLocalCodeExecutorAgent,
    ) -> None:
        """output_model 未設定時のデフォルト output_type は str であること。"""
        assert agent.agent.output_type is str


class TestEnsureRoundDirectory:
    """_ensure_round_directory のテスト。"""

    @pytest.mark.anyio
    async def test_creates_round_dir_when_context_set(
        self,
        agent: ClaudeCodeLocalCodeExecutorAgent,
        mock_workspace_env: Path,
    ) -> None:
        """ImplementationContext 設定時にラウンドディレクトリを作成すること。"""
        mock_result = MagicMock()
        mock_result.output = "test output"
        mock_result.all_messages.return_value = []
        agent.agent.run = AsyncMock(return_value=mock_result)  # type: ignore[method-assign]

        context = {
            "execution_id": "exec-1",
            "team_id": "team-1",
            "round_number": 1,
            "member_agent_name": "test-agent",
        }
        await agent.execute("タスク", context=context)

        round_dir = mock_workspace_env / "submissions" / "round_1"
        assert round_dir.is_dir()

    @pytest.mark.anyio
    async def test_skips_when_no_context(
        self,
        agent: ClaudeCodeLocalCodeExecutorAgent,
        mock_workspace_env: Path,
    ) -> None:
        """ImplementationContext 未設定時はラウンドディレクトリを作成しないこと。"""
        mock_result = MagicMock()
        mock_result.output = "test output"
        mock_result.all_messages.return_value = []
        agent.agent.run = AsyncMock(return_value=mock_result)  # type: ignore[method-assign]

        await agent.execute("タスク", context=None)

        submissions_dir = mock_workspace_env / "submissions"
        assert not submissions_dir.exists()


class TestGetWorkspacePath:
    """_get_workspace_path のテスト。"""

    def test_returns_workspace_path(
        self,
        agent: ClaudeCodeLocalCodeExecutorAgent,
        mock_workspace_env: Path,
    ) -> None:
        """MIXSEEK_WORKSPACE 環境変数からパスを返すこと。"""
        result = agent._get_workspace_path()
        assert result == mock_workspace_env

    def test_raises_runtime_error_when_unset(
        self,
        agent: ClaudeCodeLocalCodeExecutorAgent,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """MIXSEEK_WORKSPACE 未設定時に RuntimeError を送出すること。"""
        monkeypatch.delenv("MIXSEEK_WORKSPACE", raising=False)

        with pytest.raises(RuntimeError, match="MIXSEEK_WORKSPACE"):
            agent._get_workspace_path()


class TestRegisterAgents:
    """エージェント登録のテスト。"""

    @patch("quant_insight_plus.agents.agent.MemberAgentFactory")
    def test_register_claudecode_quant_agents(
        self,
        mock_factory: MagicMock,
    ) -> None:
        """MemberAgentFactory に正しいタイプ名で登録されること。"""
        from quant_insight_plus import register_claudecode_quant_agents

        register_claudecode_quant_agents()

        mock_factory.register_agent.assert_called_once_with(
            "claudecode_local_code_executor",
            ClaudeCodeLocalCodeExecutorAgent,
        )
