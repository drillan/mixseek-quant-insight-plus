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

    def test_examples_configs_has_judgment(self) -> None:
        """judgment.toml が存在し claudecode モデルを使用すること。"""
        from quant_insight_plus.cli import _PLUS_EXAMPLES_CONFIGS_DIR

        judgment = _PLUS_EXAMPLES_CONFIGS_DIR / "judgment.toml"
        assert judgment.exists()
        content = judgment.read_text()
        assert "claudecode:" in content

    def test_examples_configs_evaluator_has_default_model(self) -> None:
        """evaluator.toml に default_model が設定されていること。"""
        from quant_insight_plus.cli import _PLUS_EXAMPLES_CONFIGS_DIR

        evaluator = _PLUS_EXAMPLES_CONFIGS_DIR / "evaluator.toml"
        assert evaluator.exists()
        content = evaluator.read_text()
        assert "default_model" in content
        assert "claudecode:" in content


class TestOverlayClaudecodeConfigs:
    """_overlay_claudecode_configs のユニットテスト。

    conftest.py の mock_workspace_env fixture が tmp_path/workspace を
    自動作成するため、それを活用する。
    """

    @pytest.fixture(autouse=True)
    def _ensure_configs_dir(self, mock_workspace_env: Path) -> None:
        (mock_workspace_env / "configs").mkdir(exist_ok=True)

    def test_copies_toml_files_to_workspace(self, mock_workspace_env: Path) -> None:
        """toml ファイルがワークスペースにコピーされること。"""
        from quant_insight_plus.cli import _overlay_claudecode_configs

        copied = _overlay_claudecode_configs(mock_workspace_env)
        assert len(copied) > 0
        for rel_path in copied:
            assert (mock_workspace_env / "configs" / rel_path).exists()

    def test_copies_agent_configs(self, mock_workspace_env: Path) -> None:
        """3 つのエージェント設定ファイルがコピーされること。"""
        from quant_insight_plus.cli import _overlay_claudecode_configs

        _overlay_claudecode_configs(mock_workspace_env)

        agents_dir = mock_workspace_env / "configs" / "agents"
        assert (agents_dir / "teams" / "claudecode_team.toml").exists()
        assert (agents_dir / "members" / "train_analyzer_claudecode.toml").exists()
        assert (agents_dir / "members" / "submission_creator_claudecode.toml").exists()

    def test_copies_judgment_config(self, mock_workspace_env: Path) -> None:
        """judgment.toml がコピーされること。"""
        from quant_insight_plus.cli import _overlay_claudecode_configs

        _overlay_claudecode_configs(mock_workspace_env)

        judgment = mock_workspace_env / "configs" / "judgment.toml"
        assert judgment.exists()
        content = judgment.read_text()
        assert "claudecode:" in content

    def test_copies_evaluator_with_default_model(self, mock_workspace_env: Path) -> None:
        """evaluator.toml が default_model 付きでコピーされること。"""
        from quant_insight_plus.cli import _overlay_claudecode_configs

        _overlay_claudecode_configs(mock_workspace_env)

        evaluator = mock_workspace_env / "configs" / "evaluator.toml"
        assert evaluator.exists()
        content = evaluator.read_text()
        assert "default_model" in content
        assert "claudecode:" in content

    def test_creates_subdirectories(self, mock_workspace_env: Path) -> None:
        """サブディレクトリが自動作成されること。"""
        from quant_insight_plus.cli import _overlay_claudecode_configs

        _overlay_claudecode_configs(mock_workspace_env)

        assert (mock_workspace_env / "configs" / "agents" / "members").is_dir()
        assert (mock_workspace_env / "configs" / "agents" / "teams").is_dir()

    def test_overwrites_existing_files(self, mock_workspace_env: Path) -> None:
        """既存のファイルを上書きすること。"""
        from quant_insight_plus.cli import _overlay_claudecode_configs

        orchestrator = mock_workspace_env / "configs" / "orchestrator.toml"
        orchestrator.write_text('model = "google-gla:gemini-3-flash-preview"')

        _overlay_claudecode_configs(mock_workspace_env)

        content = orchestrator.read_text()
        assert "claudecode" in content

    def test_raises_on_missing_examples_dir(self, mock_workspace_env: Path) -> None:
        """examples/configs/ が存在しない場合に FileNotFoundError を送出すること。"""
        from quant_insight_plus.cli import _overlay_claudecode_configs

        with (
            patch(
                "quant_insight_plus.cli._PLUS_EXAMPLES_CONFIGS_DIR",
                mock_workspace_env / "nonexistent",
            ),
            pytest.raises(FileNotFoundError),
        ):
            _overlay_claudecode_configs(mock_workspace_env)


class TestCreateDataDirs:
    """_create_data_dirs のユニットテスト。"""

    def test_creates_data_input_directories(self, mock_workspace_env: Path) -> None:
        """data/inputs/ 配下に ohlcv, returns, master ディレクトリが作成されること。"""
        from quant_insight_plus.cli import _create_data_dirs

        created = _create_data_dirs(mock_workspace_env)

        assert len(created) == 3
        assert (mock_workspace_env / "data" / "inputs" / "ohlcv").is_dir()
        assert (mock_workspace_env / "data" / "inputs" / "returns").is_dir()
        assert (mock_workspace_env / "data" / "inputs" / "master").is_dir()

    def test_idempotent(self, mock_workspace_env: Path) -> None:
        """既にディレクトリが存在する場合もエラーにならないこと。"""
        from quant_insight_plus.cli import _create_data_dirs

        _create_data_dirs(mock_workspace_env)
        created = _create_data_dirs(mock_workspace_env)

        assert len(created) == 3


class TestSetupCommand:
    """setup コマンドの統合テスト。"""

    @patch("quant_insight_plus.cli._print_next_steps")
    @patch("quant_insight_plus.cli._create_data_dirs")
    @patch("quant_insight_plus.cli._overlay_claudecode_configs")
    @patch("quant_insight_plus.cli.quant_setup")
    def test_setup_calls_all_steps_in_order(
        self,
        mock_quant_setup: MagicMock,
        mock_overlay: MagicMock,
        mock_data_dirs: MagicMock,
        mock_next_steps: MagicMock,
        mock_workspace_env: Path,
    ) -> None:
        """quant_setup → overlay → data_dirs → next_steps の順で呼ばれること。"""
        from typer.testing import CliRunner

        from quant_insight_plus.cli import app

        call_order: list[str] = []

        def _track_quant_setup(**kw: object) -> None:
            call_order.append("quant_setup")

        def _track_overlay(ws: Path) -> list[Path]:
            call_order.append("overlay")
            return [Path("orchestrator.toml")]

        def _track_data_dirs(ws: Path) -> list[Path]:
            call_order.append("data_dirs")
            return []

        def _track_next_steps(ws: Path) -> None:
            call_order.append("next_steps")

        mock_quant_setup.side_effect = _track_quant_setup
        mock_overlay.side_effect = _track_overlay
        mock_data_dirs.side_effect = _track_data_dirs
        mock_next_steps.side_effect = _track_next_steps

        runner = CliRunner()
        result = runner.invoke(app, ["setup", "--workspace", str(mock_workspace_env)])

        assert result.exit_code == 0, result.output
        assert call_order == ["quant_setup", "overlay", "data_dirs", "next_steps"]

    @patch("quant_insight_plus.cli._print_next_steps")
    @patch("quant_insight_plus.cli._create_data_dirs")
    @patch("quant_insight_plus.cli._overlay_claudecode_configs")
    @patch("quant_insight_plus.cli.quant_setup")
    def test_setup_output_contains_data_dir_message(
        self,
        mock_quant_setup: MagicMock,
        mock_overlay: MagicMock,
        mock_data_dirs: MagicMock,
        mock_next_steps: MagicMock,
        mock_workspace_env: Path,
    ) -> None:
        """setup の出力にデータディレクトリ作成メッセージが含まれること。"""
        from typer.testing import CliRunner

        from quant_insight_plus.cli import app

        mock_overlay.return_value = [Path("orchestrator.toml")]
        mock_data_dirs.return_value = []

        runner = CliRunner()
        result = runner.invoke(app, ["setup", "--workspace", str(mock_workspace_env)])

        assert result.exit_code == 0, result.output
        assert "データディレクトリを作成" in result.output

    def test_setup_help_shows_workspace_option(self) -> None:
        """setup --help に --workspace が表示されること。"""
        from typer.testing import CliRunner

        from quant_insight_plus.cli import app

        runner = CliRunner()
        result = runner.invoke(app, ["setup", "--help"])
        assert result.exit_code == 0
        assert "--workspace" in result.output
