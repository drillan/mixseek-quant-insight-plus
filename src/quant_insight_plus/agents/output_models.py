"""エージェントの構造化出力モデル（ファイルシステムベース）。

コード本体はファイルに存在する。
構造化出力はファイルパスのみを含み、コードの二重管理を排除する（FR-003）。
"""

from pathlib import PurePosixPath

from pydantic import BaseModel, field_validator


class FileSubmitterOutput(BaseModel):
    """submission-creator の構造化出力。

    コード本体はファイルに存在する。
    構造化出力はファイルパスのみを含み、コードの二重管理を排除する。
    """

    submission_path: str
    description: str

    @field_validator("submission_path")
    @classmethod
    def validate_absolute_path(cls, v: str) -> str:
        """submission_path が絶対パスであることを検証。"""
        if not PurePosixPath(v).is_absolute():
            msg = f"submission_path must be an absolute path, got: {v!r}"
            raise ValueError(msg)
        return v


class FileAnalyzerOutput(BaseModel):
    """train-analyzer の構造化出力。

    分析レポートはファイルとモデルの両方に存在する
    （report はリーダーへの主要な報告内容として使用）。
    """

    analysis_path: str
    report: str

    @field_validator("analysis_path")
    @classmethod
    def validate_absolute_path(cls, v: str) -> str:
        """analysis_path が絶対パスであることを検証。"""
        if not PurePosixPath(v).is_absolute():
            msg = f"analysis_path must be an absolute path, got: {v!r}"
            raise ValueError(msg)
        return v
