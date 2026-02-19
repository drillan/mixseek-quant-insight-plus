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
from quant_insight.cli.commands import data_app, db_app, export_app  # noqa: E402
from quant_insight.cli.main import setup as quant_setup  # noqa: E402

# quant-insight サブコマンドを core_app に統合
core_app.add_typer(data_app, name="data")
core_app.add_typer(db_app, name="db")
core_app.add_typer(export_app, name="export")
core_app.command(name="setup")(quant_setup)

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
