"""_format_output_content() と execute() オーバーライドのテスト。

SubmitterOutput が JSON ではなく Markdown 形式にフォーマットされることを検証する。
Evaluator の extract_code_from_submission() でコード抽出できることも確認。
"""

import hashlib
import inspect
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from mixseek.models.member_agent import MemberAgentResult, ResultStatus
from pydantic import BaseModel
from quant_insight.agents.local_code_executor.agent import LocalCodeExecutorAgent
from quant_insight.agents.local_code_executor.output_models import SubmitterOutput
from quant_insight.evaluator.submission_parser import extract_code_from_submission

from quant_insight_plus.agents.agent import ClaudeCodeLocalCodeExecutorAgent

# DuckDB ストアのパッチ対象パス（agent.py が FS ベースに移行するまでの暫定）
_ENRICH_STORE_PATCH = "quant_insight_plus.agents.agent.get_implementation_store"

SAMPLE_CODE = """\
import polars as pl

def generate_signal(
    ohlcv: pl.DataFrame,
    additional_data: dict[str, pl.DataFrame],
) -> pl.DataFrame:
    close = ohlcv.select("datetime", "symbol", "close")
    signal = close.with_columns(
        pl.col("close").pct_change().over("symbol").alias("signal")
    )
    return signal.select("datetime", "symbol", "signal")
"""

SAMPLE_DESCRIPTION = "終値の前日比変化率をシグナルとして使用"


@pytest.fixture
def submitter_output() -> SubmitterOutput:
    """テスト用の SubmitterOutput。"""
    return SubmitterOutput(submission=SAMPLE_CODE, description=SAMPLE_DESCRIPTION)


class TestFormatOutputContent:
    """_format_output_content() の単体テスト。"""

    def test_submitter_output_formatted_as_markdown(
        self,
        agent: ClaudeCodeLocalCodeExecutorAgent,
        submitter_output: SubmitterOutput,
    ) -> None:
        """SubmitterOutput が Markdown 形式にフォーマットされること。"""
        result = agent._format_output_content(submitter_output)

        assert "## Submissionの概要" in result
        assert "## Submissionスクリプト" in result
        assert "```python" in result
        assert SAMPLE_DESCRIPTION in result

    def test_submitter_output_code_verbatim(
        self,
        agent: ClaudeCodeLocalCodeExecutorAgent,
        submitter_output: SubmitterOutput,
    ) -> None:
        """submission フィールドのコードがエスケープなしで含まれること。"""
        result = agent._format_output_content(submitter_output)

        # JSON エスケープ（\\n）ではなく、生のコードが含まれる
        assert SAMPLE_CODE in result
        assert "\\n" not in result  # JSON エスケープされていない

    def test_non_submitter_basemodel_remains_json(
        self,
        agent: ClaudeCodeLocalCodeExecutorAgent,
    ) -> None:
        """SubmitterOutput 以外の BaseModel は JSON のまま返されること。"""

        class OtherOutput(BaseModel):
            report: str

        output = OtherOutput(report="分析レポート")
        result = agent._format_output_content(output)

        assert '"report"' in result
        assert '"分析レポート"' in result

    def test_str_output_unchanged(
        self,
        agent: ClaudeCodeLocalCodeExecutorAgent,
    ) -> None:
        """str 出力はそのまま返されること。"""
        result = agent._format_output_content("plain text output")
        assert result == "plain text output"

    def test_evaluator_can_extract_code_from_formatted_output(
        self,
        agent: ClaudeCodeLocalCodeExecutorAgent,
        submitter_output: SubmitterOutput,
    ) -> None:
        """フォーマット結果から Evaluator がコードを抽出できること。"""
        formatted = agent._format_output_content(submitter_output)

        # Evaluator のコード抽出関数で抽出できることを確認
        extracted_code = extract_code_from_submission(formatted)
        assert "def generate_signal(" in extracted_code
        assert "import polars as pl" in extracted_code


class TestExecuteOutputFormat:
    """execute() オーバーライドで SubmitterOutput が Markdown になることを検証。"""

    @pytest.mark.anyio
    @patch(_ENRICH_STORE_PATCH)
    async def test_execute_submitter_output_uses_markdown_format(
        self,
        mock_get_store: MagicMock,
        agent: ClaudeCodeLocalCodeExecutorAgent,
        submitter_output: SubmitterOutput,
    ) -> None:
        """execute() が SubmitterOutput を Markdown 形式で返すこと。"""
        mock_store = MagicMock()
        mock_store.list_scripts = AsyncMock(return_value=[])
        mock_store.save_script = AsyncMock()
        mock_get_store.return_value = mock_store

        mock_result = MagicMock()
        mock_result.output = submitter_output
        mock_result.all_messages.return_value = []

        agent.agent.run = AsyncMock(return_value=mock_result)  # type: ignore[method-assign]

        result = await agent.execute("テスト用タスク", context=None)

        assert isinstance(result, MemberAgentResult)
        assert result.status == ResultStatus.SUCCESS
        assert "```python" in result.content
        assert SAMPLE_CODE in result.content
        assert "## Submissionの概要" in result.content

    @pytest.mark.anyio
    async def test_execute_preserves_script_saving(
        self,
        agent: ClaudeCodeLocalCodeExecutorAgent,
        submitter_output: SubmitterOutput,
    ) -> None:
        """execute() で _save_output_scripts() が呼ばれること。"""
        mock_result = MagicMock()
        mock_result.output = submitter_output
        mock_result.all_messages.return_value = []

        agent.agent.run = AsyncMock(return_value=mock_result)  # type: ignore[method-assign]
        agent._save_output_scripts = AsyncMock()
        agent._enrich_task_with_existing_scripts = AsyncMock(return_value="テスト用タスク")  # type: ignore[method-assign]

        # implementation_context を設定してスクリプト保存を有効化
        context = {
            "execution_id": "exec-1",
            "team_id": "team-1",
            "round_number": 1,
        }
        await agent.execute("テスト用タスク", context=context)

        # _save_output_scripts が元の出力オブジェクトで呼ばれたことを確認
        agent._save_output_scripts.assert_called_once_with(submitter_output)

    @pytest.mark.anyio
    @patch(_ENRICH_STORE_PATCH)
    async def test_execute_error_returns_error_result(
        self,
        mock_get_store: MagicMock,
        agent: ClaudeCodeLocalCodeExecutorAgent,
    ) -> None:
        """execute() で例外発生時に ERROR ステータスの MemberAgentResult を返すこと。"""
        mock_store = MagicMock()
        mock_store.list_scripts = AsyncMock(return_value=[])
        mock_get_store.return_value = mock_store

        agent.agent.run = AsyncMock(side_effect=RuntimeError("テストエラー"))  # type: ignore[method-assign]

        result = await agent.execute("テスト用タスク", context=None)

        assert isinstance(result, MemberAgentResult)
        assert result.status == ResultStatus.ERROR
        assert "テストエラー" in result.content


class TestParentExecuteDrift:
    """親クラス execute() のドリフト検出テスト。"""

    # mixseek-quant-insight==0.1.0 の LocalCodeExecutorAgent.execute() ソースハッシュ。
    # 依存ライブラリ更新時にこのテストが失敗した場合、
    # ClaudeCodeLocalCodeExecutorAgent.execute() を親クラスと照合して更新すること。
    _EXPECTED_HASH = "53ee25cfdacb8edbd945d4faf2bc3d68785df602f8653d72b1ac20a935035bdc"

    def test_parent_execute_source_not_drifted(self) -> None:
        """親クラスの execute() ソースが想定と一致すること。"""
        src = inspect.getsource(LocalCodeExecutorAgent.execute)
        digest = hashlib.sha256(src.encode()).hexdigest()

        if not self._EXPECTED_HASH:
            pytest.fail(f"初回実行: 親クラス execute() の SHA-256 ハッシュを記録してください: {digest}")

        assert digest == self._EXPECTED_HASH, (
            f"親クラス LocalCodeExecutorAgent.execute() が変更されています。"
            f"ClaudeCodeLocalCodeExecutorAgent.execute() を確認してハッシュを更新してください。"
            f"\n  Expected: {self._EXPECTED_HASH}"
            f"\n  Actual:   {digest}"
        )
