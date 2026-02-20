"""ClaudeCode版 LocalCodeExecutorAgent。

ClaudeCode の組み込みツール（Bash, Read等）を活用し、
pydantic-ai のカスタムツールセットは登録しない。
"""

from typing import Any

from mixseek.agents.member.base import BaseMemberAgent
from mixseek.agents.member.factory import MemberAgentFactory
from mixseek.core import auth
from mixseek.models.member_agent import AgentType, MemberAgentConfig, MemberAgentResult, ResultStatus
from pydantic import BaseModel
from pydantic_ai import Agent
from quant_insight.agents.local_code_executor.agent import LocalCodeExecutorAgent
from quant_insight.agents.local_code_executor.models import ImplementationContext, LocalCodeExecutorConfig
from quant_insight.agents.local_code_executor.output_models import SubmitterOutput
from quant_insight.storage import get_implementation_store

AGENT_TYPE_NAME = "claudecode_local_code_executor"


class ClaudeCodeLocalCodeExecutorAgent(LocalCodeExecutorAgent):  # type: ignore[misc]
    """ClaudeCode版 LocalCodeExecutorAgent。

    LocalCodeExecutorAgent を継承し、以下をオーバーライド:
    - __init__: create_authenticated_model() でモデルを解決（claudecode: プレフィックス対応）
    - _enrich_task_with_existing_scripts(): スクリプト内容をプロンプトに埋め込む
    - execute(): SubmitterOutput を Markdown 形式にフォーマットしてリーダーに返す
    - pydantic-ai ツールセットは登録しない（Claude Code 組み込みツールに委ねる）
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

    def _format_output_content(self, output: BaseModel | str) -> str:
        """構造化出力をリーダーエージェント向けにフォーマット。

        SubmitterOutput は Evaluator がコードブロックを正規表現で抽出できるよう、
        Markdown 形式（```python ブロック付き）にフォーマットする。
        その他の構造化出力は JSON のまま返す。

        Args:
            output: エージェントの出力（BaseModel または str）。

        Returns:
            フォーマットされた出力文字列。
        """
        if isinstance(output, SubmitterOutput):
            return (
                f"## Submissionの概要\n{output.description}\n\n"
                f"## Submissionスクリプト\n```python\n{output.submission}\n```"
            )
        if isinstance(output, BaseModel):
            return output.model_dump_json(indent=2)
        return output

    async def execute(
        self,
        task: str,
        context: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> MemberAgentResult:
        """エージェントタスクを実行（SubmitterOutput を Markdown 形式にフォーマット）。

        親クラスの execute() と同一のロジックだが、SubmitterOutput を
        JSON ではなく Markdown 形式にフォーマットする。これにより、
        リーダーが受け取る出力に ```python ブロックが含まれ、
        Evaluator がコードを正しく抽出できる。

        NOTE: 親クラス LocalCodeExecutorAgent.execute()
        (quant_insight==0.0.3) のロジックを複製し、シリアライズ部分のみ変更。
        依存ライブラリ更新時にドリフトする可能性があるため注意。

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
            enriched_task = await self._enrich_task_with_existing_scripts(task)
            result = await self.agent.run(enriched_task, deps=self.executor_config)
            all_messages = result.all_messages()

            if self.executor_config.implementation_context is not None:
                await self._save_output_scripts(result.output)

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

    async def _enrich_task_with_existing_scripts(self, task: str) -> str:
        """既存スクリプトの内容をタスクプロンプトに埋め込む。

        親クラスはファイル名のみ追加するが、ClaudeCode 版は read_script ツールを
        持たないため、スクリプト内容そのものをプロンプトに埋め込む。

        DatabaseReadError は呼び出し元に伝播する。エンリッチメントは補助的機能だが、
        DB エラー時にエンリッチなしで続行すると暗黙のデータ欠損となるため、
        明示的にエラーを伝播させる（フォールバック禁止ポリシー）。

        Args:
            task: 元のタスク文字列。

        Returns:
            既存スクリプト内容が追加されたタスク文字列。

        Raises:
            DatabaseReadError: list_scripts / read_script の DB 読み込み失敗時。
        """
        impl_ctx = self.executor_config.implementation_context
        if impl_ctx is None:
            return task

        store = get_implementation_store()
        existing_scripts = await store.list_scripts(
            execution_id=impl_ctx.execution_id,
            team_id=impl_ctx.team_id,
            round_number=impl_ctx.round_number,
        )

        if not existing_scripts:
            return task

        sections: list[str] = []
        for script_info in existing_scripts:
            file_name = script_info["file_name"]
            code = await store.read_script(
                execution_id=impl_ctx.execution_id,
                team_id=impl_ctx.team_id,
                round_number=impl_ctx.round_number,
                file_name=file_name,
            )
            if code is not None:
                sections.append(f"### {file_name}\n```python\n{code}\n```")

        if not sections:
            return task

        footer = "\n\n---\n## 既存スクリプト\n\n" + "\n\n".join(sections)
        return task + footer


def register_claudecode_quant_agents() -> None:
    """ClaudeCode quant-insight エージェントを MemberAgentFactory に登録。

    この関数を呼び出すと、TOML設定で type = "claudecode_local_code_executor" が使用可能になる。
    """
    MemberAgentFactory.register_agent(AGENT_TYPE_NAME, ClaudeCodeLocalCodeExecutorAgent)
