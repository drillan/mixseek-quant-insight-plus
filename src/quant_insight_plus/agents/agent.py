"""ClaudeCode版 LocalCodeExecutorAgent。

ClaudeCode の組み込みツール（Bash, Read等）を活用し、
pydantic-ai のカスタムツールセットは登録しない。
"""

from typing import Any

from mixseek.agents.member.base import BaseMemberAgent
from mixseek.agents.member.factory import MemberAgentFactory
from mixseek.core.auth import create_authenticated_model
from mixseek.models.member_agent import MemberAgentConfig
from pydantic_ai import Agent
from quant_insight.agents.local_code_executor.agent import LocalCodeExecutorAgent
from quant_insight.agents.local_code_executor.models import LocalCodeExecutorConfig

AGENT_TYPE_NAME = "claudecode_local_code_executor"


class ClaudeCodeLocalCodeExecutorAgent(LocalCodeExecutorAgent):  # type: ignore[misc]
    """ClaudeCode版 LocalCodeExecutorAgent。

    LocalCodeExecutorAgent を継承し、__init__ のみオーバーライド。
    - create_authenticated_model() でモデルを解決（claudecode: プレフィックス対応）
    - pydantic-ai ツールセットは登録しない（Claude Code 組み込みツールに委ねる）
    - execute() 等のドメインロジックはすべて親クラスから継承
    """

    def __init__(self, config: MemberAgentConfig) -> None:
        """ClaudeCode版エージェントを初期化。

        Args:
            config: Member Agent設定。

        Raises:
            RuntimeError: DuckDBスキーマが初期化されていない場合。
            ValueError: 認証失敗またはTOML設定不足の場合。
        """
        # BaseMemberAgent.__init__ を直接呼び出し
        # （LocalCodeExecutorAgent.__init__ はスキップ）
        BaseMemberAgent.__init__(self, config)

        # 親クラスのヘルパーメソッドを再利用
        self.executor_config = self._build_executor_config(config)
        self._verify_database_schema()
        output_type = self._resolve_output_type()
        model_settings = self._create_model_settings()

        # create_authenticated_model で claudecode: プレフィックスを解決
        model = create_authenticated_model(self.config.model)

        # ツールセットなし — Claude Code の組み込みツールを使用
        self.agent: Agent[LocalCodeExecutorConfig, Any] = Agent(
            model=model,
            deps_type=LocalCodeExecutorConfig,
            output_type=output_type,
            instructions=self.config.system_instruction,
            model_settings=model_settings,
            retries=self.config.max_retries,
        )


def register_claudecode_quant_agents() -> None:
    """ClaudeCode quant-insight エージェントを MemberAgentFactory に登録。

    この関数を呼び出すと、TOML設定で type = "claudecode_local_code_executor" が使用可能になる。
    """
    MemberAgentFactory.register_agent(AGENT_TYPE_NAME, ClaudeCodeLocalCodeExecutorAgent)
