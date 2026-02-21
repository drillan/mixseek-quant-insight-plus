"""エージェントの構造化出力モデル（ファイルシステムベース）。

コード本体はファイルに存在する。
構造化出力はファイルパスのみを含み、コードの二重管理を排除する（FR-003）。
"""

from pathlib import PurePosixPath
from typing import Annotated

from pydantic import AfterValidator, BaseModel


def _validate_absolute_path(v: str) -> str:
    """値が POSIX 絶対パスであることを検証する。"""
    if not PurePosixPath(v).is_absolute():
        msg = f"must be an absolute path, got: {v!r}"
        raise ValueError(msg)
    return v


AbsolutePosixPath = Annotated[str, AfterValidator(_validate_absolute_path)]


class FileSubmitterOutput(BaseModel):
    """submission-creator の構造化出力。

    コード本体はファイルに存在する。
    構造化出力はファイルパスのみを含み、コードの二重管理を排除する。
    """

    submission_path: AbsolutePosixPath
    description: str


class FileAnalyzerOutput(BaseModel):
    """train-analyzer の構造化出力。

    分析レポートはファイルとモデルの両方に存在する
    （report はリーダーへの主要な報告内容として使用）。
    """

    analysis_path: AbsolutePosixPath
    report: str
