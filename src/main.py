"""プロジェクトの簡易エントリーポイント。"""

from __future__ import annotations

from fire import Fire

from src.bridge_llm_mvp.main import main as bridge_main


def cli() -> None:
    """CLI エントリーポイント。

    Returns:
        None: 返り値は利用しない。
    """
    Fire(bridge_main)


if __name__ == "__main__":
    cli()
