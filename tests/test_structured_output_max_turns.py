"""構造化出力時の max_turns パッチのテスト。

claudecode_model.model.DEFAULT_MAX_TURNS_WITH_JSON_SCHEMA が
cli.py のインポート時に上書きされることを検証する。
"""

import claudecode_model.model as claudecode_model_module

# cli.py の定数
EXPECTED_MAX_TURNS = 10
_ORIGINAL_DEFAULT = 3


def _get_patched_value() -> int:
    """パッチ適用後の DEFAULT_MAX_TURNS_WITH_JSON_SCHEMA を取得。"""
    return claudecode_model_module.DEFAULT_MAX_TURNS_WITH_JSON_SCHEMA  # type: ignore[attr-defined]


class TestStructuredOutputMaxTurnsPatch:
    """DEFAULT_MAX_TURNS_WITH_JSON_SCHEMA のパッチテスト。"""

    def test_default_max_turns_patched_on_cli_import(self) -> None:
        """cli.py インポート後に DEFAULT_MAX_TURNS_WITH_JSON_SCHEMA が 10 であること。"""
        import quant_insight_plus.cli  # noqa: F401

        assert _get_patched_value() == EXPECTED_MAX_TURNS

    def test_default_max_turns_not_original_value(self) -> None:
        """パッチ後の値がオリジナルの 3 ではないこと。"""
        import quant_insight_plus.cli  # noqa: F401

        assert _get_patched_value() != _ORIGINAL_DEFAULT
