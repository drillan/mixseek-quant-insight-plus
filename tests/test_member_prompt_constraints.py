"""メンバーエージェントのプロンプトに実行制約が含まれることを検証するテスト。

Issue #56: メンバーエージェントが `find /` 等の長時間コマンドを実行し
タイムアウトを引き起こす問題を防止するため、プロンプトに制約を追加する。
"""

from pathlib import Path

import pytest

_MEMBERS_DIR = (
    Path(__file__).resolve().parent.parent / "src" / "quant_insight_plus" / "templates" / "agents" / "members"
)

_MEMBER_TEMPLATES = [
    "train_analyzer_claudecode.toml",
    "submission_creator_claudecode.toml",
]


@pytest.fixture(params=_MEMBER_TEMPLATES)
def member_template_content(request: pytest.FixtureRequest) -> str:
    """各メンバーエージェントテンプレートの内容を返す。"""
    template_path = _MEMBERS_DIR / str(request.param)
    return template_path.read_text(encoding="utf-8")


class TestMemberPromptExecutionConstraints:
    """メンバーエージェントプロンプトの実行制約テスト。"""

    def test_prohibits_root_directory_search(self, member_template_content: str) -> None:
        """ルートディレクトリからのファイル探索を禁止していること。"""
        assert "find /" in member_template_content or "ルートディレクトリ" in member_template_content

    def test_recommends_glob_grep_tools(self, member_template_content: str) -> None:
        """ファイル探索に Glob / Grep ツールの使用を推奨していること。"""
        assert "Glob" in member_template_content
        assert "Grep" in member_template_content

    def test_prohibits_background_tasks(self, member_template_content: str) -> None:
        """バックグラウンドタスク実行を禁止していること。"""
        assert "run_in_background" in member_template_content

    def test_prohibits_long_running_commands(self, member_template_content: str) -> None:
        """長時間コマンドの実行を制限していること。"""
        assert "長時間" in member_template_content or "パッケージインストール" in member_template_content

    def test_restricts_to_provided_data(self, member_template_content: str) -> None:
        """提供データのみを対象とする制約があること。"""
        assert "外部データ" in member_template_content or "システム探索" in member_template_content
