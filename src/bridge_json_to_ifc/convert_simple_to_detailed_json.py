"""BridgeDesign JSON を IFC 生成用の詳細 JSON に変換するモジュール。"""

from __future__ import annotations

import json
from pathlib import Path

import fire

from src.bridge_agentic_generate.designer.models import BridgeDesign
from src.bridge_agentic_generate.logger_config import get_logger
from src.bridge_json_to_ifc.models import (
    Crossbeams,
    DeckGeometry,
    DetailedBridgeJson,
    Geometry,
    GirdersGeometry,
    Partition,
)

logger = get_logger(__name__)


def convert_simple_to_detailed(design: BridgeDesign) -> DetailedBridgeJson:
    """BridgeDesign を IFC 生成用の詳細 JSON に変換する。

    Args:
        design: LLM Designer が生成した BridgeDesign モデル

    Returns:
        IFC 生成用の詳細 JSON モデル
    """
    dims = design.dimensions
    bridge_length = dims.bridge_length
    total_width = dims.total_width
    num_girders = dims.num_girders
    girder_spacing = dims.girder_spacing
    panel_length = dims.panel_length

    num_panels = dims.num_panels
    if num_panels is None or num_panels == 0:
        num_panels = int(bridge_length / panel_length) if panel_length > 0 else 0

    # 断面情報の取得
    g_sec = design.sections.girder_standard
    cb_sec = design.sections.crossbeam_standard
    deck_comp = design.components.deck

    # 座標計算
    girders_total_span = (num_girders - 1) * girder_spacing
    x_offset = (total_width - girders_total_span) / 2

    # Y軸: 0から始まり、panel_lengthごとに増える
    y_positions = [float(i * panel_length) for i in range(num_panels + 1)]

    # X軸: 両端と各主桁の位置
    x_positions: list[float] = [0.0]
    current_x = x_offset
    for _ in range(num_girders):
        x_positions.append(current_x)
        current_x += girder_spacing
    x_positions.append(total_width)
    x_positions = sorted(set(x_positions))

    # 主桁断面情報
    web_height = g_sec.web_height
    web_thickness = g_sec.web_thickness
    top_flange_width = g_sec.top_flange_width
    top_flange_thickness = g_sec.top_flange_thickness
    bottom_flange_width = g_sec.bottom_flange_width
    bottom_flange_thickness = g_sec.bottom_flange_thickness

    # 床版厚み
    deck_thickness = deck_comp.thickness

    # 横桁断面情報
    cb_height = cb_sec.total_height
    cb_flange_width = cb_sec.flange_width
    cb_flange_thickness = cb_sec.flange_thickness
    cb_web_thickness = cb_sec.web_thickness

    # 詳細JSON の構築
    return DetailedBridgeJson(
        bridge_type="Steel Girder",
        geometry=Geometry(
            girders=GirdersGeometry(
                num_girders=num_girders,
                spacing_x=girder_spacing,
                spacing_z=0,
                length=bridge_length,
                x_offset=x_offset,
                web_height=web_height,
                web_thickness=web_thickness,
                top_flange_width=top_flange_width,
                top_flange_thickness=top_flange_thickness,
                bottom_flange_width=bottom_flange_width,
                bottom_flange_thickness=bottom_flange_thickness,
            ),
            deck=DeckGeometry(
                length=bridge_length,
                width=total_width,
                thickness=deck_thickness,
                points=[
                    [0, 0],
                    [total_width, 0],
                    [total_width, bridge_length],
                    [0, bridge_length],
                    [0, 0],
                ],
            ),
            partition=Partition(
                x_positions=x_positions,
                y_positions=y_positions,
            ),
        ),
        crossbeams=Crossbeams(
            use_crossbeams=True,
            use_i_section=True,
            num_cross_girders=max(0, num_panels - 1),
            spacing_z=panel_length,
            initial_position_z=panel_length,
            height=cb_height,
            flange_width=cb_flange_width,
            flange_thickness=cb_flange_thickness,
            web_thickness=cb_web_thickness,
            thickness=cb_web_thickness,
            length=girder_spacing,
        ),
    )


def load_bridge_design(filepath: Path) -> BridgeDesign:
    """BridgeDesign JSON ファイルを読み込む。

    Args:
        filepath: 入力 JSON ファイルパス

    Returns:
        BridgeDesign モデル
    """
    with filepath.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return BridgeDesign.model_validate(data)


def save_detailed_json(data: DetailedBridgeJson, filepath: Path) -> None:
    """詳細 JSON をファイルに保存する。

    Args:
        data: 詳細 JSON モデル
        filepath: 出力ファイルパス
    """
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with filepath.open("w", encoding="utf-8") as f:
        f.write(data.model_dump_json(indent=2))


def convert(input_path: str, output_path: str | None = None) -> None:
    """BridgeDesign JSON を詳細 JSON に変換する CLI コマンド。

    Args:
        input_path: 入力 BridgeDesign JSON ファイルパス
        output_path: 出力詳細 JSON ファイルパス（省略時は標準出力）
    """
    input_file = Path(input_path)
    design = load_bridge_design(input_file)
    detailed = convert_simple_to_detailed(design)

    if output_path is not None:
        output_file = Path(output_path)
        save_detailed_json(detailed, output_file)
        logger.info("Converted: %s -> %s", input_path, output_path)
    else:
        logger.info(detailed.model_dump_json(indent=2))


def main() -> None:
    """CLI エントリーポイント。"""
    fire.Fire(convert)


if __name__ == "__main__":
    main()
