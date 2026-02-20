"""ClaudeCode プリセット設定の検証テスト。

delegate_only プリセットがメタツールを正しくブロックし、
Leader がメンバーツール以外を使用できないことを検証する。
"""

import tomllib

import pytest

# delegate_only でブロックすべきメタツール
_REQUIRED_META_TOOLS = [
    "EnterPlanMode",
    "ExitPlanMode",
    "AskUserQuestion",
]

# delegate_only でブロックすべきタスク・チーム管理ツール
_REQUIRED_TASK_TEAM_TOOLS = [
    "TodoWrite",
    "TaskCreate",
    "TaskUpdate",
    "TaskList",
    "TaskGet",
    "TeamCreate",
    "TeamDelete",
    "SendMessage",
]

# delegate_only でブロックすべきコーディングツール
_REQUIRED_CODING_TOOLS = [
    "Bash",
    "Write",
    "Edit",
    "Read",
    "Glob",
    "Grep",
    "WebFetch",
    "WebSearch",
    "NotebookEdit",
    "Task",
]

# delegate_only で許可すべきツール（ブロックリストに含まれてはいけない）
_ALLOWED_TOOLS = [
    "Skill",
]


@pytest.fixture
def presets() -> dict[str, object]:
    """templates/presets/claudecode.toml を読み込む。"""
    from quant_insight_plus.cli import _TEMPLATES_DIR

    with (_TEMPLATES_DIR / "presets" / "claudecode.toml").open("rb") as f:
        return tomllib.load(f)


class TestDelegateOnlyPreset:
    """delegate_only プリセットの検証。"""

    def test_preset_exists(self, presets: dict[str, object]) -> None:
        """delegate_only セクションが存在すること。"""
        assert "delegate_only" in presets

    def test_permission_mode(self, presets: dict[str, object]) -> None:
        """permission_mode が bypassPermissions であること。"""
        delegate_only = presets["delegate_only"]
        assert isinstance(delegate_only, dict)
        assert delegate_only["permission_mode"] == "bypassPermissions"

    def test_has_disallowed_tools(self, presets: dict[str, object]) -> None:
        """disallowed_tools が定義されていること。"""
        delegate_only = presets["delegate_only"]
        assert isinstance(delegate_only, dict)
        assert "disallowed_tools" in delegate_only
        assert isinstance(delegate_only["disallowed_tools"], list)
        assert len(delegate_only["disallowed_tools"]) > 0

    @pytest.mark.parametrize("tool_name", _REQUIRED_CODING_TOOLS)
    def test_blocks_coding_tools(self, presets: dict[str, object], tool_name: str) -> None:
        """コーディングツールがブロックされていること。"""
        delegate_only = presets["delegate_only"]
        assert isinstance(delegate_only, dict)
        disallowed = delegate_only["disallowed_tools"]
        assert tool_name in disallowed, f"{tool_name} が disallowed_tools に含まれていません"

    @pytest.mark.parametrize("tool_name", _REQUIRED_META_TOOLS)
    def test_blocks_meta_tools(self, presets: dict[str, object], tool_name: str) -> None:
        """メタツール（EnterPlanMode 等）がブロックされていること。"""
        delegate_only = presets["delegate_only"]
        assert isinstance(delegate_only, dict)
        disallowed = delegate_only["disallowed_tools"]
        assert tool_name in disallowed, (
            f"{tool_name} が disallowed_tools に含まれていません。承認者不在で無限ループを引き起こします。"
        )

    @pytest.mark.parametrize("tool_name", _REQUIRED_TASK_TEAM_TOOLS)
    def test_blocks_task_team_tools(self, presets: dict[str, object], tool_name: str) -> None:
        """タスク・チーム管理ツールがブロックされていること。"""
        delegate_only = presets["delegate_only"]
        assert isinstance(delegate_only, dict)
        disallowed = delegate_only["disallowed_tools"]
        assert tool_name in disallowed, f"{tool_name} が disallowed_tools に含まれていません"

    @pytest.mark.parametrize("tool_name", _ALLOWED_TOOLS)
    def test_allows_skill_tool(self, presets: dict[str, object], tool_name: str) -> None:
        """Skill ツールがブロックされていないこと。"""
        delegate_only = presets["delegate_only"]
        assert isinstance(delegate_only, dict)
        disallowed = delegate_only["disallowed_tools"]
        assert tool_name not in disallowed, (
            f"{tool_name} が disallowed_tools に含まれています。"
            "リーダーの能力拡張に必要なため、ブロックすべきではありません。"
        )


class TestPresetConsistency:
    """テンプレートプリセットファイルの一貫性を検証。"""

    def test_templates_preset_file_exists(self) -> None:
        """templates/presets/claudecode.toml が存在すること。"""
        from quant_insight_plus.cli import _TEMPLATES_DIR

        assert (_TEMPLATES_DIR / "presets" / "claudecode.toml").exists()

    def test_all_preset_sections_have_permission_mode(self, presets: dict[str, object]) -> None:
        """全プリセットセクションが permission_mode を持つこと。"""
        for section_name, section in presets.items():
            assert isinstance(section, dict)
            assert "permission_mode" in section, f"[{section_name}] に permission_mode がありません"
