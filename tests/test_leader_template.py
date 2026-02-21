"""claudecode_team.toml Leader system_instruction のテスト。

Leader がメンバーツールを正しく呼び出すために、
system_instruction に必要な情報が含まれていることを検証する。
"""

from __future__ import annotations

import tomllib

import pytest

MCP_TOOL_PREFIX = "mcp__team__"
DELEGATE_TOOL_PATTERN = "delegate_to_{agent_name}"


@pytest.fixture
def team_config() -> dict[str, object]:
    """claudecode_team.toml をパースして返す。"""
    from quant_insight_plus.cli import _TEMPLATES_DIR

    path = _TEMPLATES_DIR / "agents" / "teams" / "claudecode_team.toml"
    with path.open("rb") as f:
        return tomllib.load(f)


@pytest.fixture
def system_instruction(team_config: dict[str, object]) -> str:
    """Leader の system_instruction を取得。"""
    team = team_config["team"]
    assert isinstance(team, dict)
    leader = team["leader"]
    assert isinstance(leader, dict)
    instruction = leader["system_instruction"]
    assert isinstance(instruction, str)
    return instruction


@pytest.fixture
def member_agent_names() -> list[str]:
    """メンバー TOML から agent_name を読み取る。"""
    from quant_insight_plus.cli import _TEMPLATES_DIR

    members_dir = _TEMPLATES_DIR / "agents" / "members"
    names: list[str] = []
    for path in sorted(members_dir.glob("*_claudecode.toml")):
        with path.open("rb") as f:
            data = tomllib.load(f)
        agent = data["agent"]
        assert isinstance(agent, dict)
        name = agent["name"]
        assert isinstance(name, str)
        names.append(name)
    return names


class TestLeaderSystemInstructionMCPToolNames:
    """Leader の system_instruction が MCP ツール名を正しく記載していることを検証。"""

    def test_contains_mcp_tool_name_for_each_member(
        self,
        system_instruction: str,
        member_agent_names: list[str],
    ) -> None:
        """各メンバーの MCP ツール名が system_instruction に含まれること。"""
        assert len(member_agent_names) > 0, "メンバーが1つも見つからない"
        for agent_name in member_agent_names:
            expected_tool = f"{MCP_TOOL_PREFIX}{DELEGATE_TOOL_PATTERN.format(agent_name=agent_name)}"
            assert expected_tool in system_instruction, (
                f"MCP ツール名 '{expected_tool}' が system_instruction に見つからない"
            )

    def test_contains_task_parameter_description(
        self,
        system_instruction: str,
    ) -> None:
        """ツール呼び出しの task パラメータの説明が含まれること。"""
        assert "task" in system_instruction.lower(), "system_instruction に task パラメータの説明がない"

    def test_prohibits_direct_code_generation(
        self,
        system_instruction: str,
    ) -> None:
        """直接コード生成の禁止が明示されていること。"""
        assert "禁止" in system_instruction, "system_instruction にコード直接生成の禁止が明示されていない"


class TestLeaderPromptFSRelayGuidance:
    """Leader の system_instruction が FS Relay（FR-011）に対応していることを検証。"""

    def test_mentions_evaluator_auto_delivery(
        self,
        system_instruction: str,
    ) -> None:
        """Evaluator にコードが自動的に渡されることへの言及があること。"""
        assert "Evaluator" in system_instruction, "system_instruction に Evaluator への言及がない"
        assert "ファイルシステム" in system_instruction or "自動" in system_instruction, (
            "system_instruction に FS 経由の自動提出の説明がない"
        )

    def test_output_is_summary_and_strategy_only(
        self,
        system_instruction: str,
    ) -> None:
        """最終出力が概要・戦略のみであることが明示されていること。"""
        has_summary = "概要" in system_instruction or "戦略" in system_instruction
        assert has_summary, "system_instruction に概要・戦略のみの出力指示がない"
