"""CLI wrapper for quant-insight-plus.

mixseek-plus CLI をラップし、ClaudeCode 版 quant-insight エージェントを
自動登録する CLI エントリーポイント。

インポート順序が重要:
1. patch_core() で claudecode: プレフィックスを有効化
2. mixseek-plus のエージェント登録
3. quant-insight-plus のエージェント登録
4. mixseek-core CLI アプリのインポート
5. quant-insight サブコマンド（setup, data, db, export）の統合
"""

import shutil
from pathlib import Path

import typer
from mixseek_plus.agents import register_claudecode_agents, register_groq_agents
from mixseek_plus.core_patch import patch_core

from quant_insight_plus.agents.agent import register_claudecode_quant_agents

patch_core()
register_groq_agents()
register_claudecode_agents()
register_claudecode_quant_agents()

from importlib.metadata import PackageNotFoundError, version  # noqa: E402

from mixseek.cli.main import app as core_app  # noqa: E402
from mixseek.models.workspace import WorkspaceStructure  # noqa: E402
from quant_insight.cli.commands import data_app, db_app, export_app  # noqa: E402
from quant_insight.storage import ImplementationStore  # noqa: E402
from quant_insight.utils.env import get_workspace  # noqa: E402

# quant-insight サブコマンドを core_app に統合
core_app.add_typer(data_app, name="data")
core_app.add_typer(db_app, name="db")
core_app.add_typer(export_app, name="export")

_TEMPLATES_DIR = Path(__file__).parent / "templates"


def _init_workspace(workspace: Path) -> None:
    """ワークスペースのディレクトリ構造を作成。

    mixseek_init() を使わず、WorkspaceStructure で
    必要なディレクトリのみ作成する（Gemini 設定ファイルは生成しない）。

    Args:
        workspace: ワークスペースパス
    """
    structure = WorkspaceStructure.create(workspace)

    if structure.exists:
        if not typer.confirm(
            f"ワークスペースが既に存在します: {workspace}。上書きしますか？",
            default=False,
        ):
            typer.echo("セットアップを中止しました。", err=True)
            raise typer.Exit(code=1)

    structure.create_directories()
    typer.echo(f"ワークスペースを初期化しました: {workspace}")


def _install_templates(workspace: Path) -> list[Path]:
    """テンプレート設定をワークスペースにコピー。

    Args:
        workspace: ワークスペースパス

    Returns:
        コピーされたファイルの相対パスリスト

    Raises:
        FileNotFoundError: templates ディレクトリが見つからない場合
    """
    if not _TEMPLATES_DIR.is_dir():
        msg = f"templates ディレクトリが見つかりません: {_TEMPLATES_DIR}"
        raise FileNotFoundError(msg)

    configs_dir = workspace / "configs"
    copied_files: list[Path] = []

    for src_file in _TEMPLATES_DIR.rglob("*.toml"):
        rel_path = src_file.relative_to(_TEMPLATES_DIR)
        dest_file = configs_dir / rel_path
        dest_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_file, dest_file)
        copied_files.append(rel_path)

    return copied_files


_DATA_INPUT_DIRS = ("ohlcv", "returns", "master")


def _create_data_dirs(workspace: Path) -> list[Path]:
    """data/inputs/ 配下のデータディレクトリを作成。

    Args:
        workspace: ワークスペースパス

    Returns:
        作成されたディレクトリのリスト
    """
    created: list[Path] = []
    for name in _DATA_INPUT_DIRS:
        d = workspace / "data" / "inputs" / name
        d.mkdir(parents=True, exist_ok=True)
        created.append(d)
    return created


def _print_next_steps(workspace: Path) -> None:
    """セットアップ完了後の次ステップ案内を出力。"""
    typer.echo(
        f"""
=== セットアップ完了 ===

次のステップ:
  1. データファイルを配置してください:
     {workspace}/data/inputs/ohlcv/  (ohlcv.parquet)
     {workspace}/data/inputs/returns/ (returns.parquet)
     {workspace}/data/inputs/master/  (master.parquet)

  2. データを分割:
     qip data split --config {workspace}/configs/competition.toml

  3. 環境変数を設定:
     export MIXSEEK_WORKSPACE={workspace}

  4. 実行:
     qip team "データ分析タスク" --config {workspace}/configs/agents/teams/claudecode_team.toml"""
    )


@core_app.command(name="setup")
def setup(
    workspace: Path | None = typer.Option(
        None,
        "--workspace",
        "-w",
        help="ワークスペースパス（未指定時は$MIXSEEK_WORKSPACE）",
    ),
) -> None:
    """環境を一括セットアップ（ワークスペース初期化 → テンプレートコピー → DB 初期化 → データディレクトリ作成）"""
    ws = workspace or get_workspace()

    # Step 1: ワークスペース構造を作成
    typer.echo("Step 1/4: ワークスペース構造を作成...")
    _init_workspace(ws)

    # Step 2: テンプレート設定をコピー
    typer.echo("Step 2/4: テンプレート設定をコピー...")
    copied = _install_templates(ws)
    typer.echo(f"  {len(copied)} ファイルをコピーしました")

    # Step 3: DB 初期化
    typer.echo("Step 3/4: データベースを初期化...")
    store = ImplementationStore(workspace=ws)
    store.initialize_schema()
    typer.echo(f"  {store.db_path}")

    # Step 4: データディレクトリ作成
    typer.echo("Step 4/4: データディレクトリを作成...")
    _create_data_dirs(ws)
    typer.echo("  data/inputs/{ohlcv,returns,master}")

    _print_next_steps(ws)


try:
    __version__ = version("mixseek-quant-insight-plus")
except PackageNotFoundError:
    __version__ = "0.0.0.dev0"

app = core_app


def version_callback(value: bool | None) -> None:
    """バージョン情報を表示。"""
    if value:
        typer.echo(f"quant-insight-plus version {__version__}")
        raise typer.Exit(code=0)


@app.callback()
def main_callback(
    _version: bool | None = typer.Option(
        None,
        "--version",
        "-v",
        help="Show version and exit",
        callback=version_callback,
        is_eager=True,
    ),
) -> None:
    """Quant-Insight-Plus CLI - ClaudeCode 対応 quant-insight エージェント。"""


def main() -> None:
    """CLI エントリーポイント。

    quant-insight-plus コマンドで呼び出される。
    """
    app()
