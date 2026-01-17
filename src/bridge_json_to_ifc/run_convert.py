"""BridgeDesign JSON を詳細 JSON 経由で IFC に変換する統合スクリプト。"""

from __future__ import annotations

import json
from enum import StrEnum
from pathlib import Path

import fire

from src.bridge_agentic_generate.config import app_config
from src.bridge_agentic_generate.designer.models import BridgeDesign
from src.bridge_agentic_generate.logger_config import logger
from src.bridge_json_to_ifc.convert_detailed_json_to_ifc import build_ifc_from_spec
from src.bridge_json_to_ifc.convert_simple_to_detailed_json import convert_simple_to_detailed, save_detailed_json


class FileSuffixes(StrEnum):
    DETAILED = "_detailed.json"
    IFC = ".ifc"


def convert(
    bridge_design_path: str,
    detailed_json_path: str | None = None,
    ifc_output_path: str | None = None,
) -> None:
    """BridgeDesign JSON を詳細 JSON に変換し、IFC を出力する。

    Args:
        bridge_design_path:
            Designer が生成した BridgeDesign JSON パス（デフォルト想定は data/generated_simple_bridge_json）
        detailed_json_path:
            中間の詳細 JSON 出力パス（省略時は data/generated_detailed_bridge_json/<stem>_detailed.json）
        ifc_output_path:
            IFC 出力パス（省略時は data/generated_ifc/<stem>.ifc）
    """
    design_file = Path(bridge_design_path)
    if not design_file.is_absolute() and design_file.parent == Path("."):
        design_file = app_config.generated_simple_bridge_json_dir / design_file.name

    if not design_file.exists():
        raise FileNotFoundError(f"BridgeDesign JSON が見つかりません: {design_file}")
    detailed_file = (
        Path(detailed_json_path)
        if detailed_json_path is not None
        else app_config.generated_detailed_bridge_json_dir / f"{design_file.stem}{FileSuffixes.DETAILED}"
    )
    ifc_file = (
        Path(ifc_output_path)
        if ifc_output_path is not None
        else app_config.generated_ifc_dir / f"{design_file.stem}{FileSuffixes.IFC}"
    )

    with design_file.open("r", encoding="utf-8") as file:
        raw_data = json.load(file)

    design = BridgeDesign.model_validate(raw_data)
    detailed = convert_simple_to_detailed(design)
    save_detailed_json(detailed, detailed_file)
    build_ifc_from_spec(detailed, ifc_file)

    logger.info("BridgeDesign: %s", bridge_design_path)
    logger.info("Detailed JSON: %s", detailed_file)
    logger.info("IFC: %s", ifc_file)


def main() -> None:
    """Fire 経由の CLI エントリーポイント。"""
    fire.Fire(convert)


if __name__ == "__main__":
    main()
