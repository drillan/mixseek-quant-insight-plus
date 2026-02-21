"""Submission Relay: ファイルシステムベースのコード管理。

ラウンドディレクトリの管理と submission ファイルの読み取りを提供する。
"""

from pathlib import Path

# --- 名前付き定数 ---
SUBMISSION_FILENAME = "submission.py"
ANALYSIS_FILENAME = "analysis.md"
SUBMISSIONS_DIR_NAME = "submissions"


class SubmissionFileNotFoundError(FileNotFoundError):
    """submission.py がラウンドディレクトリに存在しない場合に送出。"""


def get_round_dir(workspace: Path, round_number: int) -> Path:
    """ラウンドディレクトリのパスを返す（作成しない）。

    Args:
        workspace: ワークスペースのルートパス。
        round_number: ラウンド番号（1-indexed）。

    Returns:
        ``{workspace}/submissions/round_{round_number}`` のパス。
    """
    return workspace / SUBMISSIONS_DIR_NAME / f"round_{round_number}"


def ensure_round_dir(workspace: Path, round_number: int) -> Path:
    """ラウンドディレクトリを作成して返す（冪等）。

    Args:
        workspace: ワークスペースのルートパス。
        round_number: ラウンド番号。

    Returns:
        作成（または既存）のラウンドディレクトリパス。

    Raises:
        OSError: ディレクトリ作成に失敗した場合。
    """
    round_dir = get_round_dir(workspace, round_number)
    round_dir.mkdir(parents=True, exist_ok=True)
    return round_dir
