"""_format_output_content() と execute() オーバーライドのテスト（FS ベース版）。

FileSubmitterOutput はファイルからコードを読み取り Markdown 形式にフォーマット。
FileAnalyzerOutput は report フィールドをそのまま返す。
"""

import hashlib
import inspect
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from mixseek.models.member_agent import MemberAgentResult, ResultStatus
from pydantic import BaseModel
from quant_insight.agents.local_code_executor.agent import LocalCodeExecutorAgent
from quant_insight.evaluator.submission_parser import extract_code_from_submission

from quant_insight_plus.agents.agent import ClaudeCodeLocalCodeExecutorAgent
from quant_insight_plus.agents.output_models import FileAnalyzerOutput, FileSubmitterOutput
from quant_insight_plus.submission_relay import SUBMISSION_FILENAME

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
def round_dir(mock_workspace_env: Path) -> Path:
    """テスト用のラウンドディレクトリを作成し、submission.py を配置。"""
    rd = mock_workspace_env / "submissions" / "round_1"
    rd.mkdir(parents=True)
    (rd / SUBMISSION_FILENAME).write_text(SAMPLE_CODE)
    return rd


@pytest.fixture
def file_submitter_output(round_dir: Path) -> FileSubmitterOutput:
    """テスト用の FileSubmitterOutput。"""
    return FileSubmitterOutput(
        submission_path=str(round_dir / SUBMISSION_FILENAME),
        description=SAMPLE_DESCRIPTION,
    )


@pytest.fixture
def file_analyzer_output(round_dir: Path) -> FileAnalyzerOutput:
    """テスト用の FileAnalyzerOutput。"""
    return FileAnalyzerOutput(
        analysis_path=str(round_dir / "analysis.md"),
        report="# 分析レポート\n\nデータの傾向分析結果",
    )


class TestFormatOutputContent:
    """_format_output_content() の単体テスト（FS ベース版）。"""

    def test_file_submitter_output_reads_from_file(
        self,
        agent: ClaudeCodeLocalCodeExecutorAgent,
        file_submitter_output: FileSubmitterOutput,
    ) -> None:
        """FileSubmitterOutput でファイルからコードを読み取り Markdown 形式にフォーマットされること。"""
        result = agent._format_output_content(file_submitter_output)

        assert "## Submissionの概要" in result
        assert SAMPLE_DESCRIPTION in result
        assert "```python" in result
        assert SAMPLE_CODE in result

    def test_file_submitter_output_evaluator_extractable(
        self,
        agent: ClaudeCodeLocalCodeExecutorAgent,
        file_submitter_output: FileSubmitterOutput,
    ) -> None:
        """フォーマット結果から Evaluator がコードを抽出できること。"""
        formatted = agent._format_output_content(file_submitter_output)

        extracted = extract_code_from_submission(formatted)
        assert "def generate_signal(" in extracted
        assert "import polars as pl" in extracted

    def test_file_analyzer_output_returns_report(
        self,
        agent: ClaudeCodeLocalCodeExecutorAgent,
        file_analyzer_output: FileAnalyzerOutput,
    ) -> None:
        """FileAnalyzerOutput で report フィールドをそのまま返すこと。"""
        result = agent._format_output_content(file_analyzer_output)

        assert result == "# 分析レポート\n\nデータの傾向分析結果"

    def test_non_file_basemodel_remains_json(
        self,
        agent: ClaudeCodeLocalCodeExecutorAgent,
    ) -> None:
        """FileSubmitterOutput/FileAnalyzerOutput 以外の BaseModel は JSON のまま返されること。"""

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


class TestExecuteOutputFormat:
    """execute() オーバーライドで FileSubmitterOutput が Markdown になることを検証。"""

    @pytest.mark.anyio
    async def test_execute_file_submitter_output_uses_markdown_format(
        self,
        agent: ClaudeCodeLocalCodeExecutorAgent,
        file_submitter_output: FileSubmitterOutput,
    ) -> None:
        """execute() が FileSubmitterOutput を Markdown 形式で返すこと。"""
        mock_result = MagicMock()
        mock_result.output = file_submitter_output
        mock_result.all_messages.return_value = []

        agent.agent.run = AsyncMock(return_value=mock_result)  # type: ignore[method-assign]
        agent._enrich_task_with_workspace_context = MagicMock(return_value="テスト用タスク")  # type: ignore[method-assign]

        result = await agent.execute("テスト用タスク", context=None)

        assert isinstance(result, MemberAgentResult)
        assert result.status == ResultStatus.SUCCESS
        assert "```python" in result.content
        assert SAMPLE_CODE in result.content
        assert "## Submissionの概要" in result.content

    @pytest.mark.anyio
    async def test_execute_error_returns_error_result(
        self,
        agent: ClaudeCodeLocalCodeExecutorAgent,
    ) -> None:
        """execute() で例外発生時に ERROR ステータスの MemberAgentResult を返すこと。"""
        agent.agent.run = AsyncMock(side_effect=RuntimeError("テストエラー"))  # type: ignore[method-assign]
        agent._enrich_task_with_workspace_context = MagicMock(return_value="テスト用タスク")  # type: ignore[method-assign]

        result = await agent.execute("テスト用タスク", context=None)

        assert isinstance(result, MemberAgentResult)
        assert result.status == ResultStatus.ERROR
        assert "テストエラー" in result.content


class TestParentExecuteDrift:
    """親クラス execute() のドリフト検出テスト。"""

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
