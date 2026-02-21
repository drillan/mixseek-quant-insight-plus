"""ClaudeCode版 LocalCodeExecutorAgent（FS ベース版）。

ClaudeCode の組み込みツール（Bash, Read等）を活用し、
pydantic-ai のカスタムツールセットは登録しない。
ファイルシステムを介してコードを管理する。
"""

import os
from pathlib import Path
from typing import Any

from mixseek.agents.member.base import BaseMemberAgent
from mixseek.agents.member.factory import MemberAgentFactory
from mixseek.core import auth
from mixseek.models.member_agent import AgentType, MemberAgentConfig, MemberAgentResult, ResultStatus
from pydantic import BaseModel
from pydantic_ai import Agent
from quant_insight.agents.local_code_executor.agent import LocalCodeExecutorAgent
from quant_insight.agents.local_code_executor.models import ImplementationContext, LocalCodeExecutorConfig

from quant_insight_plus.agents.output_models import FileAnalyzerOutput, FileSubmitterOutput
from quant_insight_plus.submission_relay import ensure_round_dir, get_round_dir

AGENT_TYPE_NAME = "claudecode_local_code_executor"

_WORKSPACE_ENV_VAR = "MIXSEEK_WORKSPACE"


class ClaudeCodeLocalCodeExecutorAgent(LocalCodeExecutorAgent):  # type: ignore[misc]
    """ClaudeCode版 LocalCodeExecutorAgent（FS ベース版）。

    LocalCodeExecutorAgent を継承し、以下をオーバーライド:
    - __init__: create_authenticated_model() でモデルを解決し、ツールセットなしで Agent を構築
    - _format_output_content(): FileSubmitterOutput/FileAnalyzerOutput をフォーマット
    - execute(): FS ベースのフロー（_ensure_round_directory + _enrich_task_with_workspace_context）
    """

    def __init__(self, config: MemberAgentConfig) -> None:
        """ClaudeCode版エージェントを初期化。

        Args:
            config: Member Agent設定。

        Raises:
            ValueError: 認証失敗またはTOML設定不足の場合。
        """
        # BaseMemberAgent.__init__ を直接呼び出し
        # （LocalCodeExecutorAgent.__init__ はスキップ）
        BaseMemberAgent.__init__(self, config)

        # 親クラスのヘルパーメソッドを再利用
        self.executor_config = self._build_executor_config(config)
        output_type = self._resolve_output_type()
        model_settings = self._create_model_settings()

        # create_authenticated_model で claudecode: プレフィックスを解決
        model = auth.create_authenticated_model(self.config.model)

        # ツールセットなし — Claude Code の組み込みツールを使用
        self.agent: Agent[LocalCodeExecutorConfig, Any] = Agent(
            model=model,
            deps_type=LocalCodeExecutorConfig,
            output_type=output_type,
            instructions=self.config.system_instruction,
            model_settings=model_settings,
            retries=self.config.max_retries,
        )

    def _get_workspace_path(self) -> Path:
        """MIXSEEK_WORKSPACE 環境変数からパスを取得。

        Returns:
            ワークスペースの Path。

        Raises:
            RuntimeError: 環境変数未設定時。
        """
        workspace = os.environ.get(_WORKSPACE_ENV_VAR)
        if workspace is None:
            msg = f"{_WORKSPACE_ENV_VAR} 環境変数が設定されていません"
            raise RuntimeError(msg)
        return Path(workspace)

    def _ensure_round_directory(self) -> None:
        """ラウンドディレクトリを作成。ImplementationContext 未設定時は何もしない。"""
        impl_ctx = self.executor_config.implementation_context
        if impl_ctx is None:
            return
        workspace = self._get_workspace_path()
        ensure_round_dir(workspace, impl_ctx.round_number)

    def _enrich_task_with_workspace_context(self, task: str) -> str:
        """ラウンドディレクトリ内のファイル内容をタスクプロンプトに埋め込む。

        Args:
            task: 元のタスク文字列。

        Returns:
            ファイル内容がフッタに埋め込まれたタスク文字列。

        Raises:
            RuntimeError: MIXSEEK_WORKSPACE 未設定時。
        """
        impl_ctx = self.executor_config.implementation_context
        if impl_ctx is None:
            return task

        workspace = self._get_workspace_path()
        round_dir = get_round_dir(workspace, impl_ctx.round_number)

        if not round_dir.is_dir():
            return task

        sections: list[str] = []
        for file_path in sorted(round_dir.iterdir()):
            if file_path.is_file():
                content = file_path.read_text()
                if content.strip():
                    sections.append(f"### {file_path.name}\n```\n{content}\n```")

        if not sections:
            return task

        footer = "\n\n---\n## ワークスペースファイル\n\n" + "\n\n".join(sections)
        return task + footer

    def _format_output_content(self, output: BaseModel | str) -> str:
        """構造化出力をリーダーエージェント向けにフォーマット。

        FileSubmitterOutput はファイルからコードを読み取り Markdown 形式にフォーマット。
        FileAnalyzerOutput は report フィールドをそのまま返す。
        その他の構造化出力は JSON のまま返す。

        Args:
            output: エージェントの出力（BaseModel または str）。

        Returns:
            フォーマットされた出力文字列。
        """
        if isinstance(output, FileSubmitterOutput):
            code = Path(output.submission_path).read_text()
            return f"## Submissionの概要\n{output.description}\n\n## Submissionスクリプト\n```python\n{code}\n```"
        if isinstance(output, FileAnalyzerOutput):
            return output.report
        if isinstance(output, BaseModel):
            return output.model_dump_json(indent=2)
        return output

    async def execute(
        self,
        task: str,
        context: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> MemberAgentResult:
        """エージェントタスクを実行（FS ベース版）。

        FS ベースのフロー:
        1. ImplementationContext を設定
        2. ラウンドディレクトリを作成
        3. ワークスペースコンテキストでタスクをエンリッチ
        4. エージェントを実行
        5. 出力をフォーマットして返す

        NOTE: 親クラス LocalCodeExecutorAgent.execute()
        (mixseek-quant-insight==0.1.0) のロジックを基に、
        DuckDB 依存を FS ベースに置き換え。

        Args:
            task: Leader Agentからのタスク説明。
            context: オプションの実行コンテキスト。
            **kwargs: 追加の実行パラメータ。

        Returns:
            実行結果を含むMemberAgentResult。
        """
        _ = kwargs

        if context is not None:
            self.executor_config.implementation_context = ImplementationContext(
                execution_id=context.get("execution_id", ""),
                team_id=context.get("team_id", ""),
                round_number=context.get("round_number", 0),
                member_agent_name=self.config.name,
            )

        try:
            self._ensure_round_directory()
            enriched_task = self._enrich_task_with_workspace_context(task)
            result = await self.agent.run(enriched_task, deps=self.executor_config)
            all_messages = result.all_messages()

            content = self._format_output_content(result.output)

            return MemberAgentResult(
                status=ResultStatus.SUCCESS,
                content=content,
                agent_name=self.config.name,
                agent_type=str(AgentType.CUSTOM),
                all_messages=all_messages,
            )

        except Exception as e:
            return MemberAgentResult(
                status=ResultStatus.ERROR,
                content=f"タスク実行エラー: {e!s}",
                agent_name=self.config.name,
                agent_type=str(AgentType.CUSTOM),
                error_message=str(e),
            )


def register_claudecode_quant_agents() -> None:
    """ClaudeCode quant-insight エージェントを MemberAgentFactory に登録。

    この関数を呼び出すと、TOML設定で type = "claudecode_local_code_executor" が使用可能になる。
    """
    MemberAgentFactory.register_agent(AGENT_TYPE_NAME, ClaudeCodeLocalCodeExecutorAgent)
