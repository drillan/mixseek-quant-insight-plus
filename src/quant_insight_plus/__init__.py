"""ClaudeCode integration for mixseek-quant-insight."""

from quant_insight_plus.agents.agent import (
    AGENT_TYPE_NAME,
    ClaudeCodeLocalCodeExecutorAgent,
    register_claudecode_quant_agents,
)

__all__ = [
    "AGENT_TYPE_NAME",
    "ClaudeCodeLocalCodeExecutorAgent",
    "register_claudecode_quant_agents",
]
