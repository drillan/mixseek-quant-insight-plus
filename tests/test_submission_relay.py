"""submission_relay モジュールのテスト。

contracts/submission_relay.md に基づく:
- get_round_dir: パス生成（作成しない）
- ensure_round_dir: 冪等なディレクトリ作成
- get_submission_content: submission.py の読み取り
- patch_submission_relay / reset_submission_relay_patch: monkey-patch
- SubmissionFileNotFoundError: 専用例外の定義
- 名前付き定数: SUBMISSION_FILENAME, ANALYSIS_FILENAME, SUBMISSIONS_DIR_NAME
"""

from pathlib import Path

import pytest

from quant_insight_plus.submission_relay import (
    ANALYSIS_FILENAME,
    SUBMISSION_FILENAME,
    SUBMISSIONS_DIR_NAME,
    SubmissionFileNotFoundError,
    ensure_round_dir,
    get_round_dir,
    get_submission_content,
    get_upstream_method_hash,
    patch_submission_relay,
    reset_submission_relay_patch,
)


class TestNamedConstants:
    """名前付き定数が仕様通りに定義されていること。"""

    def test_submission_filename(self) -> None:
        """SUBMISSION_FILENAME が 'submission.py' であること。"""
        assert SUBMISSION_FILENAME == "submission.py"

    def test_analysis_filename(self) -> None:
        """ANALYSIS_FILENAME が 'analysis.md' であること。"""
        assert ANALYSIS_FILENAME == "analysis.md"

    def test_submissions_dir_name(self) -> None:
        """SUBMISSIONS_DIR_NAME が 'submissions' であること。"""
        assert SUBMISSIONS_DIR_NAME == "submissions"


class TestSubmissionFileNotFoundError:
    """SubmissionFileNotFoundError の定義を検証。"""

    def test_inherits_file_not_found_error(self) -> None:
        """FileNotFoundError を継承していること。"""
        assert issubclass(SubmissionFileNotFoundError, FileNotFoundError)

    def test_can_be_raised_and_caught(self) -> None:
        """raise/except で正常に動作すること。"""
        with pytest.raises(SubmissionFileNotFoundError):
            raise SubmissionFileNotFoundError("submission.py not found")

    def test_caught_by_file_not_found_error(self) -> None:
        """FileNotFoundError としても捕捉できること。"""
        with pytest.raises(FileNotFoundError):
            raise SubmissionFileNotFoundError("submission.py not found")


class TestGetRoundDir:
    """get_round_dir のパス生成テスト。"""

    def test_returns_correct_path(self, tmp_path: Path) -> None:
        """workspace/submissions/round_{N} のパスを返すこと。"""
        result = get_round_dir(tmp_path, 1)
        assert result == tmp_path / "submissions" / "round_1"

    def test_round_number_in_path(self, tmp_path: Path) -> None:
        """ラウンド番号がパスに反映されること。"""
        result = get_round_dir(tmp_path, 42)
        assert result == tmp_path / "submissions" / "round_42"

    def test_does_not_create_directory(self, tmp_path: Path) -> None:
        """ディレクトリを作成しないこと（パスを返すだけ）。"""
        result = get_round_dir(tmp_path, 1)
        assert not result.exists()


class TestEnsureRoundDir:
    """ensure_round_dir の冪等ディレクトリ作成テスト。"""

    def test_creates_directory(self, tmp_path: Path) -> None:
        """ディレクトリが作成されること。"""
        result = ensure_round_dir(tmp_path, 1)
        assert result.is_dir()
        assert result == tmp_path / "submissions" / "round_1"

    def test_creates_parent_directories(self, tmp_path: Path) -> None:
        """親ディレクトリ（submissions/）も作成されること。"""
        ensure_round_dir(tmp_path, 1)
        assert (tmp_path / "submissions").is_dir()

    def test_idempotent(self, tmp_path: Path) -> None:
        """複数回呼び出してもエラーにならないこと（冪等）。"""
        first = ensure_round_dir(tmp_path, 1)
        second = ensure_round_dir(tmp_path, 1)
        assert first == second
        assert first.is_dir()

    def test_returns_path(self, tmp_path: Path) -> None:
        """作成されたディレクトリのパスを返すこと。"""
        result = ensure_round_dir(tmp_path, 3)
        assert isinstance(result, Path)
        assert result == tmp_path / "submissions" / "round_3"


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


class TestGetSubmissionContent:
    """get_submission_content のテスト。"""

    def test_reads_submission_as_python_code_block(self, tmp_path: Path) -> None:
        """submission.py を ```python コードブロック形式で返すこと。"""
        round_dir = tmp_path / "submissions" / "round_1"
        round_dir.mkdir(parents=True)
        (round_dir / SUBMISSION_FILENAME).write_text(SAMPLE_CODE)

        result = get_submission_content(round_dir)

        assert result == f"```python\n{SAMPLE_CODE}\n```"

    def test_raises_submission_file_not_found_error(self, tmp_path: Path) -> None:
        """submission.py が存在しない場合に SubmissionFileNotFoundError を送出すること。"""
        round_dir = tmp_path / "submissions" / "round_1"
        round_dir.mkdir(parents=True)

        with pytest.raises(SubmissionFileNotFoundError):
            get_submission_content(round_dir)

    def test_empty_file_raises_submission_file_not_found_error(self, tmp_path: Path) -> None:
        """空ファイルの場合に SubmissionFileNotFoundError を送出すること。"""
        round_dir = tmp_path / "submissions" / "round_1"
        round_dir.mkdir(parents=True)
        (round_dir / SUBMISSION_FILENAME).write_text("")

        with pytest.raises(SubmissionFileNotFoundError):
            get_submission_content(round_dir)


class TestPatchSubmissionRelay:
    """patch_submission_relay / reset_submission_relay_patch のテスト。"""

    def setup_method(self) -> None:
        """各テストメソッド前にパッチをリセット。"""
        reset_submission_relay_patch()

    def teardown_method(self) -> None:
        """各テストメソッド後にパッチをリセット。"""
        reset_submission_relay_patch()

    def test_patch_replaces_method(self) -> None:
        """パッチ適用後に _execute_single_round が置換されること。"""
        from mixseek.round_controller.controller import RoundController

        original = RoundController._execute_single_round
        patch_submission_relay()
        assert RoundController._execute_single_round is not original

    def test_patch_is_idempotent(self) -> None:
        """パッチを複数回適用してもエラーにならないこと。"""
        patch_submission_relay()
        patch_submission_relay()  # 2回目もエラーなし

    def test_reset_restores_original(self) -> None:
        """reset でオリジナルメソッドに戻ること。"""
        from mixseek.round_controller.controller import RoundController

        original = RoundController._execute_single_round
        patch_submission_relay()
        reset_submission_relay_patch()
        assert RoundController._execute_single_round is original


class TestGetUpstreamMethodHash:
    """get_upstream_method_hash のテスト。"""

    def test_returns_hex_string(self) -> None:
        """16進数のハッシュ文字列を返すこと。"""
        result = get_upstream_method_hash()
        assert isinstance(result, str)
        assert len(result) == 64  # SHA-256 hex digest
        int(result, 16)  # valid hex

    def test_deterministic(self) -> None:
        """同じ結果を返すこと（決定論的）。"""
        assert get_upstream_method_hash() == get_upstream_method_hash()
