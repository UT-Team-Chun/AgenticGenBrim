"""BridgeDesign（パラメトリックJSON）をSenkeiSpec形式に変換する。

BridgeDesignからjson_spec形式（Senkei, MainPanel, Yokogeta, Shouban等）への変換を行う。
"""

from __future__ import annotations

import json
from pathlib import Path

import fire

from src.bridge_agentic_generate.designer.models import (
    BridgeDesign,
    CrossbeamSection,
    Dimensions,
    GirderSection,
)
from src.bridge_agentic_generate.logger_config import logger
from src.bridge_json_to_ifc.senkei_models import (
    FlangeSpec,
    GirderBlockType,
    Infor,
    MainPanel,
    PanelBreak,
    PanelMaterial,
    PanelType,
    Senkei,
    SenkeiPoint,
    SenkeiSpec,
    Shouban,
    ShoubanBreak,
    ShoubanBreakX,
    ShoubanBreakY,
    WebSpec,
    Yokogeta,
    YokogetaBreak,
    YokogetaReference,
)

DEFAULT_MATERIAL = "SM400A"
DEFAULT_YOKOGETA_BREAK_COUNT = 2
DEFAULT_SHOUBAN_BREAK_THICK = 2


def _generate_section_names(num_panels: int) -> list[str]:
    """断面名リストを生成する。

    Args:
        num_panels: パネル数

    Returns:
        断面名リスト 例: ["S1", "C1", "C2", ..., "C9", "E1"]
    """
    sections = ["S1"]
    for i in range(1, num_panels):
        sections.append(f"C{i}")
    sections.append("E1")
    return sections


def _generate_senkei_list(
    dims: Dimensions,
    girder: GirderSection,
    sections: list[str],
) -> list[Senkei]:
    """全主桁の線形データを生成する。

    各主桁に対して6本の線形（TG*L, TG*, TG*R, BG*L, BG*, BG*R）を生成する。

    Args:
        dims: 橋梁寸法情報
        girder: 主桁断面情報
        sections: 断面名リスト

    Returns:
        線形リスト（主桁数×6本）
    """
    senkei_list: list[Senkei] = []

    # X座標（断面位置）を計算
    x_coords: dict[str, float] = {}
    for i, sec_name in enumerate(sections):
        if sec_name == "S1":
            x_coords[sec_name] = 0.0
        elif sec_name == "E1":
            x_coords[sec_name] = dims.bridge_length
        else:
            # C{n} の場合: panel_length × n
            panel_index = int(sec_name[1:])
            x_coords[sec_name] = dims.panel_length * panel_index

    # 各主桁について線形を生成
    for girder_idx in range(dims.num_girders):
        girder_num = girder_idx + 1
        y_center = dims.girder_spacing * girder_idx

        # 線形定義: (名前サフィックス, Y座標オフセット, Z座標)
        line_specs = [
            ("L", -girder.top_flange_width / 2, girder.web_height),  # TG*L
            ("", 0.0, girder.web_height),  # TG*
            ("R", girder.top_flange_width / 2, girder.web_height),  # TG*R
        ]
        bottom_line_specs = [
            ("L", -girder.bottom_flange_width / 2, 0.0),  # BG*L
            ("", 0.0, 0.0),  # BG*
            ("R", girder.bottom_flange_width / 2, 0.0),  # BG*R
        ]

        # 上フランジ線形（TG*）
        for suffix, y_offset, z in line_specs:
            line_name = f"TG{girder_num}{suffix}"
            points = [
                SenkeiPoint(
                    name=sec_name,
                    x=x_coords[sec_name],
                    y=y_center + y_offset,
                    z=z,
                )
                for sec_name in sections
            ]
            senkei_list.append(Senkei(name=line_name, point=points))

        # 下フランジ線形（BG*）
        for suffix, y_offset, z in bottom_line_specs:
            line_name = f"BG{girder_num}{suffix}"
            points = [
                SenkeiPoint(
                    name=sec_name,
                    x=x_coords[sec_name],
                    y=y_center + y_offset,
                    z=z,
                )
                for sec_name in sections
            ]
            senkei_list.append(Senkei(name=line_name, point=points))

    return senkei_list


def _generate_main_panels(
    dims: Dimensions,
    girder: GirderSection,
    sections: list[str],
    num_panels: int,
) -> list[MainPanel]:
    """全主桁のパネルを生成する。

    各主桁に3パネル（W, UF, LF）を生成する。

    Args:
        dims: 橋梁寸法情報
        girder: 主桁断面情報
        sections: 断面名リスト
        num_panels: パネル数

    Returns:
        MainPanelリスト（主桁数×3パネル）
    """
    panels: list[MainPanel] = []

    for girder_idx in range(dims.num_girders):
        girder_num = girder_idx + 1
        girder_name = f"G{girder_num}"

        # パネル定義: (タイプ, Line, 厚さ, SplitThickness)
        panel_specs: list[tuple[PanelType, list[str], float, bool | None]] = [
            (
                PanelType.W,
                [f"TG{girder_num}", f"BG{girder_num}"],
                girder.web_thickness,
                None,
            ),
            (
                PanelType.UF,
                [f"TG{girder_num}L", f"TG{girder_num}R"],
                girder.top_flange_thickness,
                True,
            ),
            (
                PanelType.LF,
                [f"BG{girder_num}L", f"BG{girder_num}R"],
                girder.bottom_flange_thickness,
                True,
            ),
        ]

        for panel_type, line, thickness, split_thickness in panel_specs:
            panel_name = f"{girder_name}B1{panel_type.value}"

            # Break設定: 厚み2分割
            half_thick = thickness / 2
            break_info = PanelBreak(
                lenght=[dims.panel_length] * num_panels,
                extend=[0] * num_panels,
                thick=[f"{half_thick}/{half_thick}"] * num_panels,
            )

            panel = MainPanel(
                name=panel_name,
                line=line,
                sec=sections,
                type=GirderBlockType(
                    girder=girder_name,
                    block="B1",
                    type_panel=panel_type.value,
                ),
                material=PanelMaterial(
                    thick1=thickness,
                    thick2=thickness,
                    mat=DEFAULT_MATERIAL,
                    split_thickness=split_thickness,
                ),
                break_=break_info,
            )
            panels.append(panel)

    return panels


def _generate_yokogeta_list(
    dims: Dimensions,
    crossbeam: CrossbeamSection,
    sections: list[str],
) -> list[Yokogeta]:
    """横桁リストを生成する。

    横桁は各パネル境界（C1〜C{num_panels-1}）に、隣接主桁間で配置する。

    Args:
        dims: 橋梁寸法情報
        crossbeam: 横桁断面情報
        sections: 断面名リスト

    Returns:
        Yokogetaリスト（(num_girders - 1) × (num_panels - 1)本）
    """
    yokogeta_list: list[Yokogeta] = []

    # 中間断面のみ（S1, E1を除く）
    intermediate_sections = [s for s in sections if s.startswith("C")]

    for section in intermediate_sections:
        for girder_idx in range(dims.num_girders - 1):
            left_girder = f"G{girder_idx + 1}"
            right_girder = f"G{girder_idx + 2}"
            name = f"CB_{left_girder}_{right_girder}_{section}"

            yokogeta = Yokogeta(
                name=name,
                girder=[left_girder, right_girder],
                section=section,
                reference=YokogetaReference.TOP,
                height=crossbeam.total_height,
                z_offset=0,
                web=WebSpec(thick=crossbeam.web_thickness, mat=DEFAULT_MATERIAL),
                u_flange=FlangeSpec(
                    thick=crossbeam.flange_thickness,
                    width=crossbeam.flange_width,
                    mat=DEFAULT_MATERIAL,
                ),
                l_flange=FlangeSpec(
                    thick=crossbeam.flange_thickness,
                    width=crossbeam.flange_width,
                    mat=DEFAULT_MATERIAL,
                ),
                break_=YokogetaBreak(count=DEFAULT_YOKOGETA_BREAK_COUNT),
            )
            yokogeta_list.append(yokogeta)

    return yokogeta_list


def _generate_shouban(
    dims: Dimensions,
    deck_thickness: float,
    sections: list[str],
) -> Shouban:
    """床版を生成する。

    Args:
        dims: 橋梁寸法情報
        deck_thickness: 床版厚 [mm]
        sections: 断面名リスト

    Returns:
        Shoubanオブジェクト
    """
    # 張り出し（Overhang）計算
    girders_total_span = dims.girder_spacing * (dims.num_girders - 1)
    overhang = (dims.total_width - girders_total_span) / 2

    # Line: 床版4隅を定義
    # 最左主桁の上フランジ左端、右端、最右主桁の上フランジ右端、左端
    last_girder_num = dims.num_girders
    line = [
        "TG1L",
        "TG1R",
        f"TG{last_girder_num}R",
        f"TG{last_girder_num}L",
    ]

    # 桁リスト（G1, G2, ..., G{n}）
    girders = [f"G{i + 1}" for i in range(dims.num_girders)]

    # Break設定
    break_info = ShoubanBreak(
        thick=DEFAULT_SHOUBAN_BREAK_THICK,
        x=ShoubanBreakX(type="sections", sections=sections),
        y=ShoubanBreakY(type="webs", girders=girders),
    )

    return Shouban(
        name="Deck_Main",
        line=line,
        sec=sections,
        thick=deck_thickness,
        overhang_left=overhang,
        overhang_right=overhang,
        break_=break_info,
    )


def convert_simple_to_senkei(
    design: BridgeDesign,
    bridge_name: str = "Bridge",
) -> SenkeiSpec:
    """BridgeDesignをSenkeiSpec形式に変換する。

    Args:
        design: LLM Designerが生成したBridgeDesign
        bridge_name: 橋梁名（デフォルト: "Bridge"）

    Returns:
        json_spec形式のSenkeiSpec
    """
    dims = design.dimensions
    girder = design.sections.girder_standard
    crossbeam = design.sections.crossbeam_standard
    deck = design.components.deck

    # num_panelsの補完
    num_panels = dims.num_panels
    if num_panels is None:
        num_panels = int(dims.bridge_length / dims.panel_length)

    # 断面名生成
    sections = _generate_section_names(num_panels)

    logger.info(f"変換開始: 橋長={dims.bridge_length}mm, 主桁数={dims.num_girders}, パネル数={num_panels}")

    senkei_list = _generate_senkei_list(dims, girder, sections)
    main_panels = _generate_main_panels(dims, girder, sections, num_panels)
    yokogeta_list = _generate_yokogeta_list(dims, crossbeam, sections)
    shouban = _generate_shouban(dims, deck.thickness, sections)

    logger.info(
        f"生成完了: Senkei={len(senkei_list)}本, "
        f"MainPanel={len(main_panels)}枚, "
        f"Yokogeta={len(yokogeta_list)}本, "
        f"Shouban=1枚"
    )

    return SenkeiSpec(
        infor=Infor(name_bridge=bridge_name, side_export=2),
        senkei=senkei_list,
        main_panel=main_panels,
        yokogeta=yokogeta_list,
        shouban=[shouban],
    )


def load_bridge_design(input_path: Path) -> BridgeDesign:
    """BridgeDesign JSONファイルを読み込む。

    Args:
        input_path: 入力ファイルパス

    Returns:
        BridgeDesignオブジェクト
    """
    with input_path.open(encoding="utf-8") as f:
        data = json.load(f)

    # BridgeDesignがトップレベルにある場合とネストされている場合に対応
    if "dimensions" in data:
        return BridgeDesign.model_validate(data)
    elif "design" in data:
        return BridgeDesign.model_validate(data["design"])
    elif "bridge_design" in data:
        return BridgeDesign.model_validate(data["bridge_design"])
    else:
        msg = f"BridgeDesignが見つかりません: {input_path}"
        raise ValueError(msg)


def convert(
    input_path: str,
    output_path: str | None = None,
    bridge_name: str = "Bridge",
) -> None:
    """BridgeDesign JSONをSenkeiSpec形式に変換するCLIコマンド。

    Args:
        input_path: 入力BridgeDesign JSONファイルパス
        output_path: 出力SenkeiSpec JSONファイルパス（省略時は標準出力）
        bridge_name: 橋梁名
    """
    input_file = Path(input_path)
    if not input_file.exists():
        logger.error(f"入力ファイルが見つかりません: {input_path}")
        raise FileNotFoundError(input_path)

    design = load_bridge_design(input_file)
    senkei_spec = convert_simple_to_senkei(design, bridge_name)

    # model_dump(by_alias=True) でPascalCase出力
    json_output = senkei_spec.model_dump_json(by_alias=True, indent=4, exclude_none=True)

    if output_path:
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(json_output, encoding="utf-8")
        logger.info(f"出力完了: {output_path}")
    else:
        print(json_output)  # noqa: T201


def main() -> None:
    """CLIエントリポイント。"""
    fire.Fire(convert)


if __name__ == "__main__":
    main()
