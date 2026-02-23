"""メンバーエージェントのプロンプトに実行制約が含まれることを検証するテスト。

Issue #56: メンバーエージェントが `find /` 等の長時間コマンドを実行し
タイムアウトを引き起こす問題を防止するため、プロンプトに制約を追加する。
"""

from pathlib import Path

import pytest

from quant_insight_plus.cli import _TEMPLATES_DIR

_MEMBERS_DIR = _TEMPLATES_DIR / "agents" / "members"
_MEMBER_TEMPLATES = sorted(_MEMBERS_DIR.glob("*_claudecode.toml"))


@pytest.fixture(params=_MEMBER_TEMPLATES)
def member_template_content(request: pytest.FixtureRequest) -> str:
    """各メンバーエージェントテンプレートの内容を返す。"""
    template_path = Path(request.param)
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


def _extract_constraint_block(content: str) -> str:
    """テンプレートから「コマンド実行の制約」セクションを抽出する。"""
    start = content.index("## コマンド実行の制約")
    end = content.index("## ガイドライン", start)
    return content[start:end]


class TestConstraintBlockConsistency:
    """全メンバーテンプレート間で制約ブロックが同一であることを検証。"""

    def test_constraint_blocks_are_identical(self) -> None:
        """全メンバーテンプレートの制約ブロックがドリフトしていないこと。"""
        assert len(_MEMBER_TEMPLATES) >= 2, "比較対象のテンプレートが不足"
        contents = [t.read_text(encoding="utf-8") for t in _MEMBER_TEMPLATES]
        blocks = [_extract_constraint_block(c) for c in contents]
        for i in range(1, len(blocks)):
            assert blocks[0] == blocks[i], (
                f"制約ブロックがドリフトしています: {_MEMBER_TEMPLATES[0].name} と {_MEMBER_TEMPLATES[i].name}"
            )
