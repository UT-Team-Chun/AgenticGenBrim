"""詳細 Bridge JSON を IFC に変換するスクリプト。"""

from __future__ import annotations

import json
from enum import StrEnum
from pathlib import Path
from typing import Any, Sequence

import fire

from src.bridge_agentic_generate.config import app_config
from src.bridge_agentic_generate.logger_config import logger
from src.bridge_json_to_ifc.ifc_utils import DefIFC
from src.bridge_json_to_ifc.models import DetailedBridgeJson, Partition

type Point2D = Sequence[float]
type Point3D = DefIFC.Point3D
type Profile2D = list[tuple[float, float]]

DEFAULT_ORIGIN = 0.0
PROFILE_ALIGNMENT_DELTA = 1.0
DEFAULT_DECK_TOP_Z = 0.0
DEFAULT_GIRDER_TOP_Z = 0.0
EXPERIMENT_DIR_NAME = "experiment"
DEFAULT_INPUT_FILENAME = "provisional_bridge.json"
DEFAULT_OUTPUT_FILENAME = "provisional_bridge.ifc"

experiment_dir = app_config.data_dir / EXPERIMENT_DIR_NAME
DEFAULT_INPUT_JSON = experiment_dir / DEFAULT_INPUT_FILENAME
DEFAULT_OUTPUT_IFC = experiment_dir / DEFAULT_OUTPUT_FILENAME


class IfcPrefixes(StrEnum):
    """IFC プレフィックス定義。"""

    SEGMENT = "Seg"
    ROW = "Row"
    GAP = "Gap"


class IfcMemberNames(StrEnum):
    """IFC メンバー名称の定義。"""

    DECK = "Deck"
    GIRDER = "Girder"
    CROSSBEAM = "Crossbeam"


class IfcRepresentation(StrEnum):
    """IFC 形状表現。"""

    BREP = "Brep"
    SWEPT_SOLID = "SweptSolid"
    BODY = "Body"


def load_detailed_bridge_json(json_path: Path) -> DetailedBridgeJson:
    """詳細 Bridge JSON を読み込んでバリデーションする。

    Args:
        json_path: 入力 JSON ファイルパス

    Returns:
        DetailedBridgeJson: IFC 生成用詳細モデル
    """
    with json_path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    return DetailedBridgeJson.model_validate(data)


def to_3d(point_2d: Point2D, z: float) -> Point3D:
    """2次元座標に高さを付与して3次元座標に変換する。

    Args:
        point_2d: X, Y を要素に持つ2次元座標
        z: 付与する高さ

    Returns:
        Point3D: X, Y, Z を含む3次元座標
    """
    return [float(point_2d[0]), float(point_2d[1]), float(z)]


def create_prism_from_2d(ifc_file: Any, vertices: Sequence[Point2D], thickness: float) -> object:
    """2D ポリゴンを押し出し、厚み方向に直方体ブレップを生成する。

    Args:
        ifc_file: IFC ファイルハンドル
        vertices: 反時計回りの2次元頂点列
        thickness: 押し出し厚さ

    Returns:
        生成された IFC ブレップオブジェクト
    """
    points_2d = vertices[:]
    if len(points_2d) > 2 and points_2d[0] == points_2d[-1]:
        points_2d = points_2d[:-1]

    top = [to_3d(point, thickness) for point in points_2d]
    bottom = [to_3d(point, DEFAULT_DECK_TOP_Z) for point in points_2d]
    return DefIFC.Create_brep_from_prism(ifc_file, top, bottom)


def create_i_section_profile(
    top_flange_width: float,
    web_height: float,
    bottom_flange_width: float,
    top_flange_thickness: float,
    web_thickness: float,
    bottom_flange_thickness: float,
) -> Profile2D:
    """I形断面の閉じた2Dポリゴンを生成する。

    Args:
        top_flange_width: 上フランジ幅
        web_height: 腹板高さ
        bottom_flange_width: 下フランジ幅
        top_flange_thickness: 上フランジ厚
        web_thickness: 腹板厚
        bottom_flange_thickness: 下フランジ厚

    Returns:
        Profile2D: I形断面の閉合ポリゴン座標
    """
    total_height = bottom_flange_thickness + web_height + top_flange_thickness
    half_top_width = top_flange_width / 2.0
    half_bottom_width = bottom_flange_width / 2.0
    half_web = web_thickness / 2.0

    y_bottom = DEFAULT_ORIGIN
    y_bottom_flange_top = bottom_flange_thickness
    y_web_top = bottom_flange_thickness + web_height
    y_top = total_height

    return [
        (-half_bottom_width, y_bottom),
        (half_bottom_width, y_bottom),
        (half_bottom_width, y_bottom_flange_top),
        (half_web, y_bottom_flange_top),
        (half_web, y_web_top),
        (half_top_width, y_web_top),
        (half_top_width, y_top),
        (-half_top_width, y_top),
        (-half_top_width, y_web_top),
        (-half_web, y_web_top),
        (-half_web, y_bottom_flange_top),
        (-half_bottom_width, y_bottom_flange_top),
        (-half_bottom_width, y_bottom),
    ]


def add_solid_as_beam(ifc_file: Any, bridge_span: object, geom_context: object, solid: Any, name: str) -> None:
    """ソリッドをIFC Beamエンティティとして追加する。

    Args:
        ifc_file: IFC ファイルハンドル
        bridge_span: 追加先の橋梁スパンエンティティ
        geom_context: 幾何コンテキスト
        solid: 追加するソリッドオブジェクト
        name: IFC エンティティ名
    """
    representation_type = IfcRepresentation.BREP
    try:
        if hasattr(solid, "is_a") and solid.is_a("IfcExtrudedAreaSolid"):
            representation_type = IfcRepresentation.SWEPT_SOLID
    except AttributeError:
        representation_type = IfcRepresentation.BREP

    shape_representation = ifc_file.createIfcShapeRepresentation(
        ContextOfItems=geom_context,
        RepresentationIdentifier=IfcRepresentation.BODY,
        RepresentationType=representation_type,
        Items=[solid],
    )
    DefIFC.Add_shape_representation_in_Beam(ifc_file, bridge_span, shape_representation, name)


def ensure_partition_y_positions(partition: Partition, girder_length: float) -> list[float]:
    """主桁長さを含むようにパーティションY座標を整備する。

    Args:
        partition: パーティションモデル
        girder_length: 主桁長さ

    Returns:
        list[float]: 0 と主桁長さを含む昇順ソート済み Y 座標列
    """
    positions = sorted({float(value) for value in partition.y_positions})
    if not positions:
        return [DEFAULT_ORIGIN, girder_length]

    if positions[0] > DEFAULT_ORIGIN:
        positions.insert(0, DEFAULT_ORIGIN)
    if positions[-1] < girder_length:
        positions.append(girder_length)
    return positions


def build_ifc_from_spec(spec: DetailedBridgeJson, output_path: Path) -> None:
    """詳細 Bridge JSON から IFC ファイルを生成する。

    Args:
        spec: 詳細 Bridge JSON モデル
        output_path: 出力 IFC ファイルパス
    """
    context = DefIFC.SetupIFC()
    ifc_file = context.ifc_file
    bridge_span = context.bridge_span
    geom_context = context.geom_context

    geometry = spec.geometry

    deck = geometry.deck
    if deck.points and deck.thickness > DEFAULT_ORIGIN:
        deck_solid = create_prism_from_2d(ifc_file, deck.points, deck.thickness)
        add_solid_as_beam(ifc_file, bridge_span, geom_context, deck_solid, IfcMemberNames.DECK)

    girders = geometry.girders
    y_positions = ensure_partition_y_positions(geometry.partition, girders.length)

    girder_x_positions: list[float] = []
    if girders.num_girders > 0 and girders.top_flange_width > DEFAULT_ORIGIN and girders.web_height > DEFAULT_ORIGIN:
        girder_profile = create_i_section_profile(
            girders.top_flange_width,
            girders.web_height,
            girders.bottom_flange_width,
            girders.top_flange_thickness,
            girders.web_thickness,
            girders.bottom_flange_thickness,
        )
        girder_total_height = girders.bottom_flange_thickness + girders.web_height + girders.top_flange_thickness
        girder_bottom_z = DEFAULT_GIRDER_TOP_Z - girder_total_height

        for index in range(girders.num_girders):
            girder_x = girders.x_offset + index * girders.spacing_x
            girder_x_positions.append(girder_x)

            for segment_index in range(len(y_positions) - 1):
                y_start = y_positions[segment_index]
                y_end = y_positions[segment_index + 1]
                segment_length = y_end - y_start
                if segment_length <= DEFAULT_ORIGIN:
                    continue

                pal1 = [girder_x, y_start, girder_bottom_z]
                pal2 = [girder_x, y_end, girder_bottom_z]
                pal3 = [girder_x - PROFILE_ALIGNMENT_DELTA, y_start, girder_bottom_z]

                girder_solid = DefIFC.extrude_profile_and_align(
                    ifc_file, girder_profile, segment_length, pal1, pal2, pal3
                )
                add_solid_as_beam(
                    ifc_file,
                    bridge_span,
                    geom_context,
                    girder_solid,
                    f"{IfcMemberNames.GIRDER}_{index + 1}_{IfcPrefixes.SEGMENT}_{segment_index + 1}",
                )

    crossbeams = spec.crossbeams
    if crossbeams.use_crossbeams and len(girder_x_positions) >= 2:
        crossbeam_web_height = max(DEFAULT_ORIGIN, crossbeams.height - 2 * crossbeams.flange_thickness)
        crossbeam_profile = None
        if crossbeams.use_i_section:
            crossbeam_profile = create_i_section_profile(
                crossbeams.flange_width,
                crossbeam_web_height,
                crossbeams.flange_width,
                crossbeams.flange_thickness,
                crossbeams.web_thickness,
                crossbeams.flange_thickness,
            )

        for row in range(crossbeams.num_cross_girders):
            y_pos = crossbeams.initial_position_z + row * crossbeams.spacing_z
            z_bottom = DEFAULT_GIRDER_TOP_Z - crossbeams.height

            for girder_index in range(len(girder_x_positions) - 1):
                x_left = girder_x_positions[girder_index]
                x_right = girder_x_positions[girder_index + 1]
                gap = x_right - x_left
                actual_length = crossbeams.length if crossbeams.length > DEFAULT_ORIGIN else gap
                center_x = (x_left + x_right) / 2.0

                x_start = center_x - actual_length / 2.0
                x_end = center_x + actual_length / 2.0

                if crossbeam_profile is None:
                    continue

                pal1 = [x_start, y_pos, z_bottom]
                pal2 = [x_end, y_pos, z_bottom]
                pal3 = [x_start, y_pos + PROFILE_ALIGNMENT_DELTA, z_bottom]

                solid_crossbeam = DefIFC.extrude_profile_and_align(
                    ifc_file, crossbeam_profile, actual_length, pal1, pal2, pal3
                )
                add_solid_as_beam(
                    ifc_file,
                    bridge_span,
                    geom_context,
                    solid_crossbeam,
                    f"{IfcMemberNames.CROSSBEAM}_{IfcPrefixes.ROW}{row + 1}_{IfcPrefixes.GAP}{girder_index + 1}",
                )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    ifc_file.write(str(output_path))
    logger.info("IFC generated at %s", output_path)


def convert(input_path: str = str(DEFAULT_INPUT_JSON), output_path: str | None = None) -> None:
    """詳細 Bridge JSON を IFC に変換する CLI エントリーポイント。

    Args:
        input_path: 入力となる詳細 Bridge JSON パス
        output_path: 出力 IFC パス（省略時は入力ファイルと同ディレクトリに出力）
    """
    input_file = Path(input_path)
    target_output = Path(output_path) if output_path is not None else input_file.with_suffix(".ifc")

    spec = load_detailed_bridge_json(input_file)
    build_ifc_from_spec(spec, target_output)


def main() -> None:
    """Fire 経由の CLI 呼び出しを行う。

    Returns:
        None
    """
    fire.Fire(convert)


if __name__ == "__main__":
    main()
