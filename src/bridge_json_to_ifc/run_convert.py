"""BridgeDesign JSON を詳細 JSON 経由で IFC に変換する統合スクリプト。"""

from __future__ import annotations

import json
from enum import StrEnum
from pathlib import Path

import fire

from src.bridge_agentic_generate.config import app_config
from src.bridge_agentic_generate.designer.models import BridgeDesign
from src.bridge_agentic_generate.logger_config import logger
from src.bridge_json_to_ifc.convert_senkei_json_to_ifc import convert_senkei_to_ifc
from src.bridge_json_to_ifc.convert_simple_to_senkei_json import convert_simple_to_senkei
from src.bridge_json_to_ifc.senkei_models import SenkeiSpec


class FileSuffixes(StrEnum):
    SENKEI = "_senkei.json"
    IFC = ".ifc"


def save_senkei_json(senkei_spec: SenkeiSpec, output_path: Path) -> None:
    """SenkeiSpec を JSON ファイルに保存する。

    Args:
        senkei_spec: 保存する SenkeiSpec オブジェクト。
        output_path: 出力先のファイルパス。
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    json_output = senkei_spec.model_dump_json(by_alias=True, indent=4, exclude_none=True)
    output_path.write_text(json_output, encoding="utf-8")


def convert(
    bridge_design_path: str,
    senkei_json_path: str | None = None,
    ifc_output_path: str | None = None,
) -> None:
    """BridgeDesign JSON を SenkeiSpec JSON に変換し、IFC を出力する。

    Args:
        bridge_design_path:
            Designer が生成した BridgeDesign JSON パス（デフォルト想定は data/generated_simple_bridge_json）
        senkei_json_path:
            中間の SenkeiSpec JSON 出力パス（省略時は data/generated_senkei_json/<stem>_senkei.json）
        ifc_output_path:
            IFC 出力パス（省略時は data/generated_ifc/<stem>.ifc）
    """
    design_file = Path(bridge_design_path)
    if not design_file.is_absolute() and design_file.parent == Path("."):
        design_file = app_config.generated_simple_bridge_json_dir / design_file.name

    if not design_file.exists():
        raise FileNotFoundError(f"BridgeDesign JSON が見つかりません: {design_file}")
    senkei_file = (
        Path(senkei_json_path)
        if senkei_json_path is not None
        else app_config.generated_senkei_json_dir / f"{design_file.stem}{FileSuffixes.SENKEI}"
    )
    ifc_file = (
        Path(ifc_output_path)
        if ifc_output_path is not None
        else app_config.generated_ifc_dir / f"{design_file.stem}{FileSuffixes.IFC}"
    )

    with design_file.open("r", encoding="utf-8") as file:
        raw_data = json.load(file)

    design = BridgeDesign.model_validate(raw_data)
    senkei = convert_simple_to_senkei(design)
    save_senkei_json(senkei, senkei_file)
    convert_senkei_to_ifc(senkei_file, ifc_file)

    logger.info("BridgeDesign: %s", bridge_design_path)
    logger.info("Senkei JSON: %s", senkei_file)
    logger.info("IFC: %s", ifc_file)


def main() -> None:
    """Fire 経由の CLI エントリーポイント。"""
    fire.Fire(convert)


if __name__ == "__main__":
    main()
