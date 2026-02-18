"""pytest fixtures for mixseek-quant-insight-plus tests.

patch_core() はテストコレクション前に呼び出す必要がある。
pytest_configure フックで実行。
"""

from pathlib import Path

import pytest


def pytest_configure(config: pytest.Config) -> None:
    """Configure pytest: patch mixseek-core for claudecode: prefix support."""
    import mixseek_plus

    mixseek_plus.patch_core()


@pytest.fixture(autouse=True)
def mock_workspace_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """全テストで MIXSEEK_WORKSPACE 環境変数を設定。"""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    monkeypatch.setenv("MIXSEEK_WORKSPACE", str(workspace))
    return workspace
