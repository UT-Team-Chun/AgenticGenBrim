"""SenkeiSpec JSON を IFC に変換するモジュール。"""

from __future__ import annotations

from pathlib import Path

import fire

from src.bridge_agentic_generate.logger_config import logger
from src.bridge_json_to_ifc.ifc_utils_new.core import DefBridge, DefIFC


def convert_senkei_to_ifc(input_path: Path, output_path: Path) -> int:
    """SenkeiSpec JSON を IFC に変換。

    Args:
        input_path: 入力JSONファイルパス
        output_path: 出力IFCファイルパス

    Returns:
        生成された要素数
    """
    DefIFC.clear_generated_element_names()

    DefBridge.RunBridge(
        str(input_path.parent) + "/",
        input_path.name,
        str(output_path),
    )

    element_count = len(DefIFC.get_generated_element_names())
    logger.info(f"IFC生成完了: {element_count}個の要素")
    return element_count


def convert(
    input_path: str,
    output_path: str | None = None,
) -> None:
    """CLI エントリーポイント。

    Args:
        input_path: 入力JSONファイルパス
        output_path: 出力IFCファイルパス（省略時は入力と同名.ifc）
    """
    input_p = Path(input_path)

    if output_path is None:
        output_p = input_p.with_suffix(".ifc")
    else:
        output_p = Path(output_path)

    output_p.parent.mkdir(parents=True, exist_ok=True)

    logger.info(f"入力: {input_p}")
    logger.info(f"出力: {output_p}")

    convert_senkei_to_ifc(input_p, output_p)


def main() -> None:
    fire.Fire(convert)


if __name__ == "__main__":
    main()
