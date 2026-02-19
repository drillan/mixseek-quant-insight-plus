"""pytest fixtures for mixseek-quant-insight-plus tests.

patch_core() はテストコレクション前に呼び出す必要がある。
pytest_configure フックで実行。
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from mixseek.models.member_agent import MemberAgentConfig
from pydantic_ai.models import Model
from quant_insight.agents.local_code_executor.models import ImplementationContext

from quant_insight_plus.agents.agent import ClaudeCodeLocalCodeExecutorAgent

# --- パッチ対象パス定数 ---
INIT_STORE_PATCH = "quant_insight.agents.local_code_executor.agent.get_implementation_store"
ENRICH_STORE_PATCH = "quant_insight_plus.agents.agent.get_implementation_store"
MODEL_PATCH = "quant_insight_plus.agents.agent.create_authenticated_model"


def pytest_configure(config: pytest.Config) -> None:
    """Configure pytest: patch mixseek-core for claudecode: prefix support."""
    import mixseek_plus

    mixseek_plus.patch_core()


@pytest.fixture(autouse=True)
def mock_workspace_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """全テストで MIXSEEK_WORKSPACE 環境変数を設定。"""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    monkeypatch.setenv("MIXSEEK_WORKSPACE", str(workspace))
    return workspace


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


@pytest.fixture
def implementation_context() -> ImplementationContext:
    """テスト用の ImplementationContext。"""
    return ImplementationContext(
        execution_id="exec-1",
        team_id="team-1",
        round_number=1,
        member_agent_name="test-agent",
    )
