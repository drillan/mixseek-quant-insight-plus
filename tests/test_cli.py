"""CLI ラッパーモジュールのユニットテスト。

quant-insight-plus CLI が以下を自動実行することを検証:
- patch_core() によるプロバイダー拡張
- register_claudecode_quant_agents() によるエージェント登録
- mixseek-core CLI コマンドへの委譲
"""

import importlib

import pytest
from typer.testing import CliRunner


@pytest.fixture
def cli_runner() -> CliRunner:
    """CLI テストランナー。"""
    return CliRunner()


class TestCLIWrapper:
    """CLI ラッパーの基本動作テスト。"""

    def test_cli_app_is_typer_instance(self) -> None:
        """app が Typer インスタンスであること。"""
        import typer

        from quant_insight_plus.cli import app

        assert isinstance(app, typer.Typer)

    def test_main_function_exists(self) -> None:
        """main 関数が存在し呼び出し可能であること。"""
        from quant_insight_plus.cli import main

        assert callable(main)


class TestCLIAutoRegistration:
    """CLI インポート時の自動登録テスト。"""

    def test_patch_core_applied_on_import(self) -> None:
        """CLI インポート時に patch_core() が適用されること。"""
        from mixseek_plus.core_patch import is_patched

        import quant_insight_plus.cli

        importlib.reload(quant_insight_plus.cli)

        assert is_patched() is True

    def test_agent_type_registered_on_import(self) -> None:
        """CLI インポート時に claudecode_local_code_executor が登録されること。"""
        from mixseek.agents.member.factory import MemberAgentFactory

        import quant_insight_plus.cli

        importlib.reload(quant_insight_plus.cli)

        supported_types = MemberAgentFactory.get_supported_types()
        assert "claudecode_local_code_executor" in supported_types


class TestMainFunction:
    """main() 関数のデッドコード不在テスト。"""

    def test_main_has_no_is_patched_check(self) -> None:
        """main() 内に is_patched() の冗長チェックがないこと。

        patch_core() はモジュールレベルで実行されるため、
        main() 内での is_patched() チェックは到達不能コード。
        """
        import inspect

        from quant_insight_plus.cli import main

        source = inspect.getsource(main)
        assert "is_patched" not in source


class TestCLICommands:
    """CLI コマンド委譲テスト。"""

    def test_help_command(self, cli_runner: CliRunner) -> None:
        """--help が正常に表示されること。"""
        from quant_insight_plus.cli import app

        result = cli_runner.invoke(app, ["--help"])
        assert result.exit_code == 0

    def test_version_command(self, cli_runner: CliRunner) -> None:
        """--version がバージョン情報を表示すること。"""
        from quant_insight_plus.cli import app

        result = cli_runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "quant-insight-plus" in result.output
