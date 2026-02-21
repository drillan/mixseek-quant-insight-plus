"""Submission Relay: ファイルシステムベースのコード管理。

ラウンドディレクトリの管理と、RoundController への monkey-patch を提供する。
"""

from __future__ import annotations

import hashlib
import inspect
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine

    from mixseek.round_controller.controller import RoundController
    from mixseek.round_controller.models import RoundState

logger = logging.getLogger(__name__)

# --- 名前付き定数 ---
SUBMISSION_FILENAME = "submission.py"
ANALYSIS_FILENAME = "analysis.md"
SUBMISSIONS_DIR_NAME = "submissions"
EXPECTED_UPSTREAM_METHOD_HASH = "2a4f43ae89b3de20258933001ce370c249d8c48fa9a07d2840cf1c8422266bd7"


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


def get_submission_content(round_dir: Path) -> str:
    """submission.py を読み取り、Python コードブロックとして返す。

    Args:
        round_dir: ラウンドディレクトリのパス。

    Returns:
        ````` ```python\\n{code}\\n``` ````` 形式の文字列。

    Raises:
        SubmissionFileNotFoundError: submission.py が存在しないか空の場合。
    """
    submission_path = round_dir / SUBMISSION_FILENAME
    if not submission_path.is_file():
        msg = f"{SUBMISSION_FILENAME} が見つかりません: {submission_path}"
        raise SubmissionFileNotFoundError(msg)

    code = submission_path.read_text()
    if not code.strip():
        msg = f"{SUBMISSION_FILENAME} が空です: {submission_path}"
        raise SubmissionFileNotFoundError(msg)

    return f"```python\n{code}\n```"


# --- Monkey-Patch ---

_original_execute_single_round: Callable[..., Coroutine[Any, Any, RoundState]] | None = None


def patch_submission_relay() -> None:
    """RoundController._execute_single_round() を monkey-patch する。

    パッチ適用済みなら何もしない（冪等）。
    Evaluator への submission_content をファイルシステムから直接読み取る。
    """
    global _original_execute_single_round  # noqa: PLW0603

    from mixseek.round_controller.controller import RoundController

    if _original_execute_single_round is not None:
        return

    _original_execute_single_round = RoundController._execute_single_round

    async def _patched_execute_single_round(
        self: RoundController,
        round_number: int,
        user_prompt: str,
        original_user_prompt: str,
        timeout_seconds: int,
    ) -> RoundState:
        """FS ベースの _execute_single_round 置換。

        Leader 実行後、submission_content をファイルから直接読み取り、
        Leader の出力テキストではなく原本コードを Evaluator に渡す。
        """
        from mixseek.agents.leader.agent import create_leader_agent
        from mixseek.agents.leader.dependencies import TeamDependencies
        from mixseek.agents.leader.models import MemberSubmissionsRecord
        from mixseek.agents.member.factory import MemberAgentFactory
        from mixseek.config.member_agent_loader import member_settings_to_config
        from mixseek.evaluator import Evaluator
        from mixseek.models.evaluation_request import EvaluationRequest
        from mixseek.round_controller.models import RoundState

        round_started_at = datetime.now(UTC)

        # 1. Create Member Agents
        member_agents: dict[str, object] = {}
        for member_settings in self.team_settings.members:
            member_config = member_settings_to_config(member_settings, agent_data=None, workspace=self.workspace)
            member_agent = MemberAgentFactory.create_agent(member_config)
            member_agents[member_settings.agent_name] = member_agent

        # 2. Execute Leader Agent
        self._write_progress_file(round_number, status="running", current_agent="leader")

        leader_agent = create_leader_agent(self.team_config, member_agents)
        deps = TeamDependencies(
            execution_id=self.task.execution_id,
            team_id=self.team_config.team_id,
            team_name=self.team_config.team_name,
            round_number=round_number,
        )

        result = await leader_agent.run(user_prompt, deps=deps)

        # --- FS RELAY: ファイルから直接読み取り ---
        workspace = self.workspace
        round_dir = get_round_dir(workspace, round_number)
        submission_content = get_submission_content(round_dir)
        logger.info("FS Relay: submission.py から直接読み取り (round=%d)", round_number)

        message_history = result.all_messages()

        self._write_progress_file(round_number, status="running", current_agent=None)

        # 3. Save round history
        member_record = MemberSubmissionsRecord(
            execution_id=self.task.execution_id,
            team_id=self.team_config.team_id,
            team_name=self.team_config.team_name,
            round_number=round_number,
            submissions=deps.submissions,
        )

        if self.store is not None:
            await self.store.save_aggregation(self.task.execution_id, member_record, message_history)

        # 4. Execute Evaluator
        self._write_progress_file(round_number, status="running", current_agent="evaluator")

        evaluator = Evaluator(
            settings=self.evaluator_settings,
            prompt_builder_settings=self.prompt_builder_settings,
        )
        request = EvaluationRequest(
            user_query=original_user_prompt,
            submission=submission_content,
            team_id=self.team_config.team_id,
        )

        evaluation_result = await evaluator.evaluate(request)
        evaluation_score = evaluation_result.overall_score

        self._write_progress_file(round_number, status="running", current_agent=None)

        score_details: dict[str, Any] = {
            "overall_score": evaluation_score,
            "metrics": [
                {
                    "metric_name": metric.metric_name,
                    "score": metric.score,
                    "evaluator_comment": metric.evaluator_comment,
                }
                for metric in evaluation_result.metrics
            ],
        }

        round_ended_at = datetime.now(UTC)

        # 5. Save to leader_board
        if self.store is not None:
            await self.store.save_to_leader_board(
                execution_id=self.task.execution_id,
                team_id=self.team_config.team_id,
                team_name=self.team_config.team_name,
                round_number=round_number,
                submission_content=submission_content,
                submission_format="md",
                score=evaluation_score,
                score_details=score_details,
                final_submission=False,
                exit_reason=None,
            )

        # 6. Save to round_status
        if self.store is not None:
            await self.store.save_round_status(
                execution_id=self.task.execution_id,
                team_id=self.team_config.team_id,
                team_name=self.team_config.team_name,
                round_number=round_number,
                should_continue=None,
                reasoning=None,
                confidence_score=None,
                round_started_at=round_started_at.isoformat(),
                round_ended_at=round_ended_at.isoformat(),
            )

        # 7. Create RoundState
        round_state = RoundState(
            round_number=round_number,
            submission_content=submission_content,
            evaluation_score=evaluation_score,
            score_details=score_details,
            improvement_judgment=None,
            round_started_at=round_started_at,
            round_ended_at=round_ended_at,
            message_history=[],
        )

        # 8. on_round_complete hook
        if self._on_round_complete:
            try:
                await self._on_round_complete(round_state, deps.submissions)
            except Exception as e:
                logger.warning("on_round_complete hook failed: %s", e, exc_info=True)

        return round_state

    RoundController._execute_single_round = _patched_execute_single_round  # type: ignore[method-assign]


def reset_submission_relay_patch() -> None:
    """パッチをリセットし、元のメソッドに戻す（テスト用）。"""
    global _original_execute_single_round  # noqa: PLW0603

    from mixseek.round_controller.controller import RoundController

    if _original_execute_single_round is not None:
        RoundController._execute_single_round = _original_execute_single_round  # type: ignore[method-assign]
        _original_execute_single_round = None


def get_upstream_method_hash() -> str:
    """パッチ対象メソッドの現在のソースコード SHA-256 ハッシュを返す。

    Returns:
        16進数のハッシュ文字列。
    """
    from mixseek.round_controller.controller import RoundController

    original = _original_execute_single_round or RoundController._execute_single_round
    src = inspect.getsource(original)
    return hashlib.sha256(src.encode()).hexdigest()
