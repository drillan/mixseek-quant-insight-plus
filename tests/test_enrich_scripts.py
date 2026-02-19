"""_enrich_task_with_existing_scripts オーバーライドのユニットテスト。

親クラスはファイル名のみをフッタに追加するが、ClaudeCode 版は
スクリプト内容をプロンプトに埋め込む。
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from quant_insight.agents.local_code_executor.models import ImplementationContext
from quant_insight.storage import DatabaseReadError

from quant_insight_plus.agents.agent import ClaudeCodeLocalCodeExecutorAgent
from tests.conftest import ENRICH_STORE_PATCH


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
        implementation_context: ImplementationContext,
    ) -> None:
        """既存スクリプトがない場合はタスクをそのまま返すこと。"""
        agent.executor_config.implementation_context = implementation_context
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
        implementation_context: ImplementationContext,
    ) -> None:
        """既存スクリプトの内容がプロンプトに埋め込まれること。"""
        agent.executor_config.implementation_context = implementation_context
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
        implementation_context: ImplementationContext,
    ) -> None:
        """複数スクリプトがすべて埋め込まれること。"""
        agent.executor_config.implementation_context = implementation_context
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
        implementation_context: ImplementationContext,
    ) -> None:
        """元のタスク文字列が先頭に保持されること。"""
        agent.executor_config.implementation_context = implementation_context
        store = MagicMock()
        store.list_scripts = AsyncMock(return_value=[{"file_name": "a.py", "created_at": "2026-01-01"}])
        store.read_script = AsyncMock(return_value="code = 1")
        mock_get_store.return_value = store

        result = await agent._enrich_task_with_existing_scripts("元のタスク")

        assert result.startswith("元のタスク")


class TestEnrichTaskDatabaseReadError:
    """DatabaseReadError が明示的に伝播されることを検証。

    エンリッチメントは補助的機能だが、CLAUDE.md の「フォールバック全面禁止」
    ルールに従い、DB エラー時はデフォルト値（エンリッチなしの task）で続行せず、
    例外を呼び出し元に伝播させる。
    """

    @patch(ENRICH_STORE_PATCH)
    async def test_list_scripts_database_error_propagates(
        self,
        mock_get_store: MagicMock,
        agent: ClaudeCodeLocalCodeExecutorAgent,
        implementation_context: ImplementationContext,
    ) -> None:
        """list_scripts の DatabaseReadError が伝播すること。"""
        agent.executor_config.implementation_context = implementation_context
        store = MagicMock()
        store.list_scripts = AsyncMock(
            side_effect=DatabaseReadError("Failed to list scripts: connection lost"),
        )
        mock_get_store.return_value = store

        with pytest.raises(DatabaseReadError, match="connection lost"):
            await agent._enrich_task_with_existing_scripts("分析してください")

    @patch(ENRICH_STORE_PATCH)
    async def test_read_script_database_error_propagates(
        self,
        mock_get_store: MagicMock,
        agent: ClaudeCodeLocalCodeExecutorAgent,
        implementation_context: ImplementationContext,
    ) -> None:
        """read_script の DatabaseReadError が伝播すること。"""
        agent.executor_config.implementation_context = implementation_context
        store = MagicMock()
        store.list_scripts = AsyncMock(
            return_value=[{"file_name": "script.py", "created_at": "2026-01-01"}],
        )
        store.read_script = AsyncMock(
            side_effect=DatabaseReadError("Failed to read script: disk I/O error"),
        )
        mock_get_store.return_value = store

        with pytest.raises(DatabaseReadError, match="disk I/O error"):
            await agent._enrich_task_with_existing_scripts("分析してください")

    @patch(ENRICH_STORE_PATCH)
    async def test_read_script_error_mid_loop_propagates(
        self,
        mock_get_store: MagicMock,
        agent: ClaudeCodeLocalCodeExecutorAgent,
        implementation_context: ImplementationContext,
    ) -> None:
        """複数スクリプトの途中で read_script が失敗した場合、部分結果ではなく例外を伝播すること。"""
        agent.executor_config.implementation_context = implementation_context
        store = MagicMock()
        store.list_scripts = AsyncMock(
            return_value=[
                {"file_name": "ok.py", "created_at": "2026-01-01"},
                {"file_name": "fail.py", "created_at": "2026-01-01"},
            ],
        )
        call_count = 0

        async def read_side_effect(
            execution_id: str,
            team_id: str,
            round_number: int,
            file_name: str,
        ) -> str:
            nonlocal call_count
            call_count += 1
            if file_name == "fail.py":
                raise DatabaseReadError("Failed to read script: corrupted")
            return "code = 1"

        store.read_script = AsyncMock(side_effect=read_side_effect)
        mock_get_store.return_value = store

        with pytest.raises(DatabaseReadError, match="corrupted"):
            await agent._enrich_task_with_existing_scripts("分析してください")
