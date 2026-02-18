"""ClaudeCodeLocalCodeExecutorAgent のユニットテスト。"""

from unittest.mock import MagicMock, patch

import pytest
from mixseek.models.member_agent import MemberAgentConfig
from pydantic_ai.models import Model

from quant_insight_plus.agents.agent import ClaudeCodeLocalCodeExecutorAgent

STORE_PATCH = "quant_insight.agents.local_code_executor.agent.get_implementation_store"
MODEL_PATCH = "quant_insight_plus.agents.agent.create_authenticated_model"


@pytest.fixture
def member_agent_config() -> MemberAgentConfig:
    """テスト用の MemberAgentConfig を生成。"""
    return MemberAgentConfig(
        name="test-agent",
        type="custom",
        model="claudecode:claude-sonnet-4-5",
        description="Test agent",
        system_instruction="You are a test agent.",
        metadata={
            "tool_settings": {
                "local_code_executor": {
                    "available_data_paths": ["data/test"],
                    "timeout_seconds": 60,
                }
            }
        },
    )


@pytest.fixture
def mock_store() -> MagicMock:
    """DuckDB ストアの mock。"""
    store = MagicMock()
    store.table_exists.return_value = True
    return store


@pytest.fixture
def mock_model() -> MagicMock:
    """pydantic-ai Model の mock。"""
    return MagicMock(spec=Model)


class TestClaudeCodeLocalCodeExecutorAgentInit:
    """__init__ の動作を検証するテスト。"""

    @patch(STORE_PATCH)
    @patch(MODEL_PATCH)
    def test_uses_create_authenticated_model(
        self,
        mock_create_model: MagicMock,
        mock_get_store: MagicMock,
        member_agent_config: MemberAgentConfig,
        mock_store: MagicMock,
        mock_model: MagicMock,
    ) -> None:
        """create_authenticated_model でモデルを解決すること。"""
        mock_create_model.return_value = mock_model
        mock_get_store.return_value = mock_store

        agent = ClaudeCodeLocalCodeExecutorAgent(member_agent_config)

        mock_create_model.assert_called_once_with("claudecode:claude-sonnet-4-5")
        assert agent.agent.model is mock_model

    @patch(STORE_PATCH)
    @patch(MODEL_PATCH)
    def test_no_toolsets_registered(
        self,
        mock_create_model: MagicMock,
        mock_get_store: MagicMock,
        member_agent_config: MemberAgentConfig,
        mock_store: MagicMock,
        mock_model: MagicMock,
    ) -> None:
        """pydantic-ai ツールセットを登録しないこと（Claude Code 組み込みツールに委ねる）。"""
        mock_create_model.return_value = mock_model
        mock_get_store.return_value = mock_store

        agent = ClaudeCodeLocalCodeExecutorAgent(member_agent_config)

        # _function_toolset にツールが登録されていないことを確認
        toolset = getattr(agent.agent, "_function_toolset", None)
        if toolset is not None:
            assert len(toolset.tools) == 0

    @patch(STORE_PATCH)
    @patch(MODEL_PATCH)
    def test_inherits_executor_config(
        self,
        mock_create_model: MagicMock,
        mock_get_store: MagicMock,
        member_agent_config: MemberAgentConfig,
        mock_store: MagicMock,
        mock_model: MagicMock,
    ) -> None:
        """親クラスの executor_config 構築ロジックを再利用すること。"""
        mock_create_model.return_value = mock_model
        mock_get_store.return_value = mock_store

        agent = ClaudeCodeLocalCodeExecutorAgent(member_agent_config)

        assert agent.executor_config.available_data_paths == ["data/test"]
        assert agent.executor_config.timeout_seconds == 60

    @patch(STORE_PATCH)
    @patch(MODEL_PATCH)
    def test_output_type_default_is_str(
        self,
        mock_create_model: MagicMock,
        mock_get_store: MagicMock,
        member_agent_config: MemberAgentConfig,
        mock_store: MagicMock,
        mock_model: MagicMock,
    ) -> None:
        """output_model 未設定時のデフォルト output_type は str であること。"""
        mock_create_model.return_value = mock_model
        mock_get_store.return_value = mock_store

        agent = ClaudeCodeLocalCodeExecutorAgent(member_agent_config)

        assert agent.agent.output_type is str


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
