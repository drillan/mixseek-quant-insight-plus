"""ClaudeCode integration for mixseek-quant-insight."""

from quant_insight_plus.agents.agent import (
    AGENT_TYPE_NAME,
    ClaudeCodeLocalCodeExecutorAgent,
    register_claudecode_quant_agents,
)
from quant_insight_plus.agents.output_models import (
    FileAnalyzerOutput,
    FileSubmitterOutput,
)
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

__all__ = [
    "AGENT_TYPE_NAME",
    "ANALYSIS_FILENAME",
    "ClaudeCodeLocalCodeExecutorAgent",
    "FileAnalyzerOutput",
    "FileSubmitterOutput",
    "SUBMISSION_FILENAME",
    "SUBMISSIONS_DIR_NAME",
    "SubmissionFileNotFoundError",
    "ensure_round_dir",
    "get_round_dir",
    "get_submission_content",
    "get_upstream_method_hash",
    "patch_submission_relay",
    "register_claudecode_quant_agents",
    "reset_submission_relay_patch",
]
