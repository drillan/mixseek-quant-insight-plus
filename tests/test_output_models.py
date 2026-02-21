"""FileSubmitterOutput・FileAnalyzerOutput のバリデーションテスト。

contracts/output_models.md に基づく:
- 絶対パス検証（field_validator）
- 必須フィールド
- 不正パス（相対パス）の拒否
"""

import pytest
from pydantic import ValidationError

from quant_insight_plus.agents.output_models import FileAnalyzerOutput, FileSubmitterOutput


class TestFileSubmitterOutput:
    """FileSubmitterOutput のバリデーション。"""

    def test_valid_absolute_path(self) -> None:
        """絶対パスで正常に生成されること。"""
        output = FileSubmitterOutput(
            submission_path="/workspace/submissions/round_1/submission.py",
            description="終値の前日比変化率をシグナルとして使用",
        )
        assert output.submission_path == "/workspace/submissions/round_1/submission.py"
        assert output.description == "終値の前日比変化率をシグナルとして使用"

    def test_rejects_relative_path(self) -> None:
        """相対パスで ValidationError が送出されること。"""
        with pytest.raises(ValidationError, match="submission_path"):
            FileSubmitterOutput(
                submission_path="submissions/round_1/submission.py",
                description="説明",
            )

    def test_rejects_empty_path(self) -> None:
        """空文字パスで ValidationError が送出されること。"""
        with pytest.raises(ValidationError, match="submission_path"):
            FileSubmitterOutput(
                submission_path="",
                description="説明",
            )

    def test_requires_submission_path(self) -> None:
        """submission_path が必須であること。"""
        with pytest.raises(ValidationError):
            FileSubmitterOutput(description="説明")  # type: ignore[call-arg]

    def test_requires_description(self) -> None:
        """description が必須であること。"""
        with pytest.raises(ValidationError):
            FileSubmitterOutput(submission_path="/abs/path.py")  # type: ignore[call-arg]


class TestFileAnalyzerOutput:
    """FileAnalyzerOutput のバリデーション。"""

    def test_valid_absolute_path(self) -> None:
        """絶対パスで正常に生成されること。"""
        output = FileAnalyzerOutput(
            analysis_path="/workspace/submissions/round_1/analysis.md",
            report="# 分析レポート\n\nデータの傾向分析結果",
        )
        assert output.analysis_path == "/workspace/submissions/round_1/analysis.md"
        assert output.report == "# 分析レポート\n\nデータの傾向分析結果"

    def test_rejects_relative_path(self) -> None:
        """相対パスで ValidationError が送出されること。"""
        with pytest.raises(ValidationError, match="analysis_path"):
            FileAnalyzerOutput(
                analysis_path="submissions/round_1/analysis.md",
                report="レポート",
            )

    def test_rejects_empty_path(self) -> None:
        """空文字パスで ValidationError が送出されること。"""
        with pytest.raises(ValidationError, match="analysis_path"):
            FileAnalyzerOutput(
                analysis_path="",
                report="レポート",
            )

    def test_requires_analysis_path(self) -> None:
        """analysis_path が必須であること。"""
        with pytest.raises(ValidationError):
            FileAnalyzerOutput(report="レポート")  # type: ignore[call-arg]

    def test_requires_report(self) -> None:
        """report が必須であること。"""
        with pytest.raises(ValidationError):
            FileAnalyzerOutput(analysis_path="/abs/path.md")  # type: ignore[call-arg]
