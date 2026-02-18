"""_enrich_task_with_existing_scripts オーバーライドのユニットテスト。

親クラスはファイル名のみをフッタに追加するが、ClaudeCode 版は
スクリプト内容をプロンプトに埋め込む。
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from mixseek.models.member_agent import MemberAgentConfig
from pydantic_ai.models import Model
from quant_insight.agents.local_code_executor.models import ImplementationContext

from quant_insight_plus.agents.agent import ClaudeCodeLocalCodeExecutorAgent

INIT_STORE_PATCH = "quant_insight.agents.local_code_executor.agent.get_implementation_store"
ENRICH_STORE_PATCH = "quant_insight_plus.agents.agent.get_implementation_store"
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


@pytest.fixture
@patch(INIT_STORE_PATCH)
@patch(MODEL_PATCH)
def agent(
    mock_create_model: MagicMock,
    mock_get_store: MagicMock,
    member_agent_config: MemberAgentConfig,
    mock_store: MagicMock,
    mock_model: MagicMock,
) -> ClaudeCodeLocalCodeExecutorAgent:
    """テスト用エージェントインスタンス。"""
    mock_create_model.return_value = mock_model
    mock_get_store.return_value = mock_store
    return ClaudeCodeLocalCodeExecutorAgent(member_agent_config)


class TestEnrichTaskWithExistingScripts:
    """_enrich_task_with_existing_scripts のオーバーライド動作を検証。"""

    async def test_no_context_returns_task_unchanged(
        self,
        agent: ClaudeCodeLocalCodeExecutorAgent,
    ) -> None:
        """implementation_context 未設定時はタスクをそのまま返すこと。"""
        agent.executor_config.implementation_context = None

        result = await agent._enrich_task_with_existing_scripts("分析してください")

        assert result == "分析してください"

    @patch(ENRICH_STORE_PATCH)
    async def test_no_scripts_returns_task_unchanged(
        self,
        mock_get_store: MagicMock,
        agent: ClaudeCodeLocalCodeExecutorAgent,
    ) -> None:
        """既存スクリプトがない場合はタスクをそのまま返すこと。"""
        agent.executor_config.implementation_context = ImplementationContext(
            execution_id="exec-1",
            team_id="team-1",
            round_number=1,
            member_agent_name="test-agent",
        )
        store = MagicMock()
        store.list_scripts = AsyncMock(return_value=[])
        mock_get_store.return_value = store

        result = await agent._enrich_task_with_existing_scripts("分析してください")

        assert result == "分析してください"

    @patch(ENRICH_STORE_PATCH)
    async def test_embeds_script_content(
        self,
        mock_get_store: MagicMock,
        agent: ClaudeCodeLocalCodeExecutorAgent,
    ) -> None:
        """既存スクリプトの内容がプロンプトに埋め込まれること。"""
        agent.executor_config.implementation_context = ImplementationContext(
            execution_id="exec-1",
            team_id="team-1",
            round_number=1,
            member_agent_name="test-agent",
        )
        store = MagicMock()
        store.list_scripts = AsyncMock(return_value=[{"file_name": "analysis.py", "created_at": "2026-01-01"}])
        store.read_script = AsyncMock(return_value="import pandas as pd\ndf = pd.read_csv('data.csv')")
        mock_get_store.return_value = store

        result = await agent._enrich_task_with_existing_scripts("分析してください")

        assert "analysis.py" in result
        assert "import pandas as pd" in result
        assert "df = pd.read_csv('data.csv')" in result

    @patch(ENRICH_STORE_PATCH)
    async def test_embeds_multiple_scripts(
        self,
        mock_get_store: MagicMock,
        agent: ClaudeCodeLocalCodeExecutorAgent,
    ) -> None:
        """複数スクリプトがすべて埋め込まれること。"""
        agent.executor_config.implementation_context = ImplementationContext(
            execution_id="exec-1",
            team_id="team-1",
            round_number=1,
            member_agent_name="test-agent",
        )
        store = MagicMock()
        store.list_scripts = AsyncMock(
            return_value=[
                {"file_name": "preprocess.py", "created_at": "2026-01-01"},
                {"file_name": "model.py", "created_at": "2026-01-01"},
            ]
        )

        async def read_side_effect(
            execution_id: str,
            team_id: str,
            round_number: int,
            file_name: str,
        ) -> str:
            scripts = {
                "preprocess.py": "# preprocessing\ndata = load()",
                "model.py": "# model\nmodel = train(data)",
            }
            return scripts[file_name]

        store.read_script = AsyncMock(side_effect=read_side_effect)
        mock_get_store.return_value = store

        result = await agent._enrich_task_with_existing_scripts("分析してください")

        assert "preprocess.py" in result
        assert "# preprocessing" in result
        assert "model.py" in result
        assert "# model" in result

    @patch(ENRICH_STORE_PATCH)
    async def test_preserves_original_task(
        self,
        mock_get_store: MagicMock,
        agent: ClaudeCodeLocalCodeExecutorAgent,
    ) -> None:
        """元のタスク文字列が先頭に保持されること。"""
        agent.executor_config.implementation_context = ImplementationContext(
            execution_id="exec-1",
            team_id="team-1",
            round_number=1,
            member_agent_name="test-agent",
        )
        store = MagicMock()
        store.list_scripts = AsyncMock(return_value=[{"file_name": "a.py", "created_at": "2026-01-01"}])
        store.read_script = AsyncMock(return_value="code = 1")
        mock_get_store.return_value = store

        result = await agent._enrich_task_with_existing_scripts("元のタスク")

        assert result.startswith("元のタスク")
