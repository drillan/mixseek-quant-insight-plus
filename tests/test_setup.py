"""setup コマンドのテンプレートインストール機能テスト。

qip setup 実行時にワークスペース初期化とテンプレートコピーが
正しく実行されることを検証する。
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestTemplatesDir:
    """templates/ ディレクトリの存在・内容を検証。"""

    def test_templates_dir_exists(self) -> None:
        """templates/ ディレクトリが実在すること。"""
        from quant_insight_plus.cli import _TEMPLATES_DIR

        assert _TEMPLATES_DIR.is_dir()

    def test_templates_dir_contains_toml_files(self) -> None:
        """templates/ に .toml ファイルが含まれること。"""
        from quant_insight_plus.cli import _TEMPLATES_DIR

        toml_files = list(_TEMPLATES_DIR.rglob("*.toml"))
        assert len(toml_files) > 0

    @pytest.mark.parametrize(
        ("filename", "expected_strings"),
        [
            ("orchestrator.toml", ["claudecode_team"]),
            ("judgment.toml", ["claudecode:"]),
            ("evaluator.toml", ["default_model", "claudecode:"]),
        ],
    )
    def test_template_contains_expected_content(self, filename: str, expected_strings: list[str]) -> None:
        """各設定ファイルが存在し期待する内容を含むこと。"""
        from quant_insight_plus.cli import _TEMPLATES_DIR

        cfg = _TEMPLATES_DIR / filename
        assert cfg.exists()
        content = cfg.read_text()
        for s in expected_strings:
            assert s in content


class TestInstallTemplates:
    """_install_templates のユニットテスト。

    conftest.py の mock_workspace_env fixture が tmp_path/workspace を
    自動作成するため、それを活用する。
    """

    @pytest.fixture(autouse=True)
    def _ensure_configs_dir(self, mock_workspace_env: Path) -> None:
        (mock_workspace_env / "configs").mkdir(exist_ok=True)

    def test_copies_toml_files_to_workspace(self, mock_workspace_env: Path) -> None:
        """toml ファイルがワークスペースにコピーされること。"""
        from quant_insight_plus.cli import _install_templates

        copied = _install_templates(mock_workspace_env)
        assert len(copied) > 0
        for rel_path in copied:
            assert (mock_workspace_env / "configs" / rel_path).exists()

    def test_copies_agent_configs(self, mock_workspace_env: Path) -> None:
        """3 つのエージェント設定ファイルがコピーされること。"""
        from quant_insight_plus.cli import _install_templates

        _install_templates(mock_workspace_env)

        agents_dir = mock_workspace_env / "configs" / "agents"
        assert (agents_dir / "teams" / "claudecode_team.toml").exists()
        assert (agents_dir / "members" / "train_analyzer_claudecode.toml").exists()
        assert (agents_dir / "members" / "submission_creator_claudecode.toml").exists()

    @pytest.mark.parametrize(
        ("filename", "expected_strings"),
        [
            ("judgment.toml", ["claudecode:"]),
            ("evaluator.toml", ["default_model", "claudecode:"]),
        ],
    )
    def test_copies_config_with_expected_content(
        self, mock_workspace_env: Path, filename: str, expected_strings: list[str]
    ) -> None:
        """設定ファイルが期待する内容でコピーされること。"""
        from quant_insight_plus.cli import _install_templates

        _install_templates(mock_workspace_env)

        cfg = mock_workspace_env / "configs" / filename
        assert cfg.exists()
        content = cfg.read_text()
        for s in expected_strings:
            assert s in content

    def test_creates_subdirectories(self, mock_workspace_env: Path) -> None:
        """サブディレクトリが自動作成されること。"""
        from quant_insight_plus.cli import _install_templates

        _install_templates(mock_workspace_env)

        assert (mock_workspace_env / "configs" / "agents" / "members").is_dir()
        assert (mock_workspace_env / "configs" / "agents" / "teams").is_dir()

    def test_overwrites_existing_files(self, mock_workspace_env: Path) -> None:
        """既存のファイルを上書きすること。"""
        from quant_insight_plus.cli import _install_templates

        orchestrator = mock_workspace_env / "configs" / "orchestrator.toml"
        orchestrator.write_text('model = "google-gla:gemini-3-flash-preview"')

        _install_templates(mock_workspace_env)

        content = orchestrator.read_text()
        assert "claudecode" in content

    def test_raises_on_missing_templates_dir(self, mock_workspace_env: Path) -> None:
        """templates/ が存在しない場合に FileNotFoundError を送出すること。"""
        from quant_insight_plus.cli import _install_templates

        with (
            patch(
                "quant_insight_plus.cli._TEMPLATES_DIR",
                mock_workspace_env / "nonexistent",
            ),
            pytest.raises(FileNotFoundError),
        ):
            _install_templates(mock_workspace_env)


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
    @patch("quant_insight_plus.cli.ImplementationStore")
    @patch("quant_insight_plus.cli._install_templates")
    @patch("quant_insight_plus.cli._init_workspace")
    def test_setup_calls_all_steps_in_order(
        self,
        mock_init_workspace: MagicMock,
        mock_install_templates: MagicMock,
        mock_store_cls: MagicMock,
        mock_data_dirs: MagicMock,
        mock_next_steps: MagicMock,
        mock_workspace_env: Path,
    ) -> None:
        """init_workspace → install_templates → db_init → data_dirs → next_steps の順で呼ばれること。"""
        from typer.testing import CliRunner

        from quant_insight_plus.cli import app

        call_order: list[str] = []

        def _track_init_workspace(ws: Path) -> None:
            call_order.append("init_workspace")

        def _track_install_templates(ws: Path) -> list[Path]:
            call_order.append("install_templates")
            return [Path("orchestrator.toml")]

        def _track_db_init() -> None:
            call_order.append("db_init")

        def _track_data_dirs(ws: Path) -> list[Path]:
            call_order.append("data_dirs")
            return []

        def _track_next_steps(ws: Path) -> None:
            call_order.append("next_steps")

        mock_init_workspace.side_effect = _track_init_workspace
        mock_install_templates.side_effect = _track_install_templates
        mock_store = MagicMock()
        mock_store.initialize_schema.side_effect = _track_db_init
        mock_store_cls.return_value = mock_store
        mock_data_dirs.side_effect = _track_data_dirs
        mock_next_steps.side_effect = _track_next_steps

        runner = CliRunner()
        result = runner.invoke(app, ["setup", "--workspace", str(mock_workspace_env)])

        assert result.exit_code == 0, result.output
        assert call_order == ["init_workspace", "install_templates", "db_init", "data_dirs", "next_steps"]

    @patch("quant_insight_plus.cli._print_next_steps")
    @patch("quant_insight_plus.cli._create_data_dirs")
    @patch("quant_insight_plus.cli.ImplementationStore")
    @patch("quant_insight_plus.cli._install_templates")
    @patch("quant_insight_plus.cli._init_workspace")
    def test_setup_output_contains_data_dir_message(
        self,
        mock_init_workspace: MagicMock,
        mock_install_templates: MagicMock,
        mock_store_cls: MagicMock,
        mock_data_dirs: MagicMock,
        mock_next_steps: MagicMock,
        mock_workspace_env: Path,
    ) -> None:
        """setup の出力にデータディレクトリ作成メッセージが含まれること。"""
        from typer.testing import CliRunner

        from quant_insight_plus.cli import app

        mock_install_templates.return_value = [Path("orchestrator.toml")]
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
