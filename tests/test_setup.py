"""setup コマンドのオーバーレイ機能テスト。

qip setup 実行時に claudecode 版エージェント設定が
自動的にオーバーレイコピーされることを検証する。
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestPlusExamplesConfigsDir:
    """examples/configs/ ディレクトリの存在・内容を検証。"""

    def test_examples_configs_dir_exists(self) -> None:
        """examples/configs/ ディレクトリが実在すること。"""
        from quant_insight_plus.cli import _PLUS_EXAMPLES_CONFIGS_DIR

        assert _PLUS_EXAMPLES_CONFIGS_DIR.is_dir()

    def test_examples_configs_dir_contains_toml_files(self) -> None:
        """examples/configs/ に .toml ファイルが含まれること。"""
        from quant_insight_plus.cli import _PLUS_EXAMPLES_CONFIGS_DIR

        toml_files = list(_PLUS_EXAMPLES_CONFIGS_DIR.rglob("*.toml"))
        assert len(toml_files) > 0

    def test_examples_configs_has_orchestrator(self) -> None:
        """orchestrator.toml が claudecode_team を参照していること。"""
        from quant_insight_plus.cli import _PLUS_EXAMPLES_CONFIGS_DIR

        orchestrator = _PLUS_EXAMPLES_CONFIGS_DIR / "orchestrator.toml"
        assert orchestrator.exists()
        content = orchestrator.read_text()
        assert "claudecode_team" in content


class TestOverlayClaudecodeConfigs:
    """_overlay_claudecode_configs のユニットテスト。

    conftest.py の mock_workspace_env fixture が tmp_path/workspace を
    自動作成するため、それを活用する。
    """

    def test_copies_toml_files_to_workspace(self, mock_workspace_env: Path) -> None:
        """toml ファイルがワークスペースにコピーされること。"""
        from quant_insight_plus.cli import _overlay_claudecode_configs

        (mock_workspace_env / "configs").mkdir(exist_ok=True)

        copied = _overlay_claudecode_configs(mock_workspace_env)
        assert len(copied) > 0
        for rel_path in copied:
            assert (mock_workspace_env / "configs" / rel_path).exists()

    def test_copies_agent_configs(self, mock_workspace_env: Path) -> None:
        """3 つのエージェント設定ファイルがコピーされること。"""
        from quant_insight_plus.cli import _overlay_claudecode_configs

        (mock_workspace_env / "configs").mkdir(exist_ok=True)

        _overlay_claudecode_configs(mock_workspace_env)

        agents_dir = mock_workspace_env / "configs" / "agents"
        assert (agents_dir / "teams" / "claudecode_team.toml").exists()
        assert (agents_dir / "members" / "train_analyzer_claudecode.toml").exists()
        assert (agents_dir / "members" / "submission_creator_claudecode.toml").exists()

    def test_creates_subdirectories(self, mock_workspace_env: Path) -> None:
        """サブディレクトリが自動作成されること。"""
        from quant_insight_plus.cli import _overlay_claudecode_configs

        (mock_workspace_env / "configs").mkdir(exist_ok=True)

        _overlay_claudecode_configs(mock_workspace_env)

        assert (mock_workspace_env / "configs" / "agents" / "members").is_dir()
        assert (mock_workspace_env / "configs" / "agents" / "teams").is_dir()

    def test_overwrites_existing_files(self, mock_workspace_env: Path) -> None:
        """既存のファイルを上書きすること。"""
        from quant_insight_plus.cli import _overlay_claudecode_configs

        configs_dir = mock_workspace_env / "configs"
        configs_dir.mkdir(exist_ok=True)

        # 既存ファイルを作成（Gemini 設定を模倣）
        orchestrator = configs_dir / "orchestrator.toml"
        orchestrator.write_text('model = "google-gla:gemini-3-flash-preview"')

        _overlay_claudecode_configs(mock_workspace_env)

        # claudecode 版で上書きされていること
        content = orchestrator.read_text()
        assert "claudecode" in content

    def test_raises_on_missing_examples_dir(self, mock_workspace_env: Path) -> None:
        """examples/configs/ が存在しない場合に FileNotFoundError を送出すること。"""
        from quant_insight_plus.cli import _overlay_claudecode_configs

        (mock_workspace_env / "configs").mkdir(exist_ok=True)

        with (
            patch(
                "quant_insight_plus.cli._PLUS_EXAMPLES_CONFIGS_DIR",
                mock_workspace_env / "nonexistent",
            ),
            pytest.raises(FileNotFoundError),
        ):
            _overlay_claudecode_configs(mock_workspace_env)


class TestSetupCommand:
    """setup コマンドの統合テスト。"""

    @patch("quant_insight_plus.cli._overlay_claudecode_configs")
    @patch("quant_insight_plus.cli.quant_setup")
    def test_setup_calls_quant_setup_then_overlay(
        self,
        mock_quant_setup: MagicMock,
        mock_overlay: MagicMock,
        mock_workspace_env: Path,
    ) -> None:
        """quant_setup → _overlay_claudecode_configs の順で呼ばれること。"""
        from typer.testing import CliRunner

        from quant_insight_plus.cli import app

        call_order: list[str] = []

        def _track_quant_setup(**kw: object) -> None:
            call_order.append("quant_setup")

        def _track_overlay(ws: Path) -> list[Path]:
            call_order.append("overlay")
            return [Path("orchestrator.toml")]

        mock_quant_setup.side_effect = _track_quant_setup
        mock_overlay.side_effect = _track_overlay

        runner = CliRunner()
        result = runner.invoke(app, ["setup", "--workspace", str(mock_workspace_env)])

        assert result.exit_code == 0, result.output
        assert call_order == ["quant_setup", "overlay"]

    def test_setup_help_shows_workspace_option(self) -> None:
        """setup --help に --workspace が表示されること。"""
        from typer.testing import CliRunner

        from quant_insight_plus.cli import app

        runner = CliRunner()
        result = runner.invoke(app, ["setup", "--help"])
        assert result.exit_code == 0
        assert "--workspace" in result.output
