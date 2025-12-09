"""IFC モデル生成のためのユーティリティ。"""

from __future__ import annotations

import uuid
from enum import StrEnum
from typing import Iterable, Literal, Sequence

import ifcopenshell
import numpy as np
from pydantic import BaseModel, ConfigDict, Field

from src.bridge_agentic_generate.logger_config import get_logger

logger = get_logger(__name__)

type Point2D = Sequence[float]
type Point3D = Sequence[float]
type FacePoints = Iterable[Point3D]
type ProfilePoints = Iterable[Point2D]

COORDINATE_DIMENSION = 3
COORDINATE_PRECISION = 0.1
EXTRUDE_AXIS = (0.0, 0.0, 1.0)
VECTOR_LENGTH_EPS = 1e-9

IFC_SCHEMA_LITERAL: Literal["IFC4X3"] = "IFC4X3"


class ProfileType(StrEnum):
    """IFC プロファイル種別の列挙。"""

    AREA = "AREA"


class LengthUnit(StrEnum):
    """長さ単位の関連値。"""

    LENGTH = "LENGTHUNIT"
    MILLI = "MILLI"


class GeometryContext(StrEnum):
    """ジオメトリコンテキスト関連値。"""

    BODY = "Body"
    MODEL = "Model"


class DefaultName(StrEnum):
    """デフォルト名称定義。"""

    PROJECT = "Bridge Project"
    SITE = "Bridge Site"
    BUILDING = "Main Building"
    STOREY = "Building Storey"


class IfcContext(BaseModel):
    """IFC ファイルと主要エンティティをまとめるモデル。"""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    ifc_file: ifcopenshell.file = Field(..., description="IFC ファイルオブジェクト")
    bridge_span: object = Field(..., description="ビルディングストーリー（橋梁スパン相当）")
    geom_context: object = Field(..., description="ジオメトリコンテキスト")


def new_guid() -> str:
    """IFC 用の GUID を生成する。

    Returns:
        str: UUID 文字列
    """
    return str(uuid.uuid1())


def create_cartesian_point(ifc_file: ifcopenshell.file, coordinates: Point3D) -> object:
    """IfcCartesianPoint を生成する。

    Args:
        ifc_file: IFC ファイルオブジェクト
        coordinates: 3次元座標

    Returns:
        生成された IfcCartesianPoint
    """
    return ifc_file.createIfcCartesianPoint([round(float(coord), 6) for coord in coordinates])


def create_face_from_points(ifc_file: ifcopenshell.file, face_points: FacePoints) -> object:
    """与えられた頂点群から IfcFace を生成する。

    Args:
        ifc_file: IFC ファイルオブジェクト
        face_points: 面を構成する頂点列

    Returns:
        生成された IfcFace
    """
    vertices = [create_cartesian_point(ifc_file, point) for point in face_points]
    loop = ifc_file.createIfcPolyLoop(vertices)
    bound = ifc_file.createIfcFaceOuterBound(loop, True)
    return ifc_file.createIfcFace([bound])


def _normalize_vector(vector: np.ndarray) -> np.ndarray:
    """ベクトルを正規化する。

    Args:
        vector: 正規化対象のベクトル

    Returns:
        np.ndarray: 正規化後のベクトル

    Raises:
        ValueError: ベクトル長が0の場合
    """
    norm = np.linalg.norm(vector)
    if norm < VECTOR_LENGTH_EPS:
        raise ValueError("ゼロ長ベクトルは正規化できません。")
    return vector / norm


def _ensure_3d(point: Sequence[float]) -> np.ndarray:
    """2次元/3次元の座標を3次元 numpy 配列へ正規化する。

    Args:
        point: 2要素または3要素の座標

    Returns:
        np.ndarray: 3次元座標
    """
    array = np.array(point, dtype=float)
    if array.shape[0] == 2:
        array = np.append(array, 0.0)
    return array


def SetupIFC() -> IfcContext:
    """IFC ファイルとジオメトリコンテキストを初期化する。

    Returns:
        IfcContext: IFC ファイル、ビルディングストーリー、ジオメトリコンテキストをまとめたモデル
    """
    ifc_file = ifcopenshell.file(schema=IFC_SCHEMA_LITERAL)

    length_unit = ifc_file.createIfcSIUnit(UnitType=LengthUnit.LENGTH, Prefix=LengthUnit.MILLI)
    unit_assignment = ifc_file.createIfcUnitAssignment([length_unit])

    project = ifc_file.createIfcProject(
        GlobalId=new_guid(), OwnerHistory=None, Name=DefaultName.PROJECT, UnitsInContext=unit_assignment
    )
    site = ifc_file.createIfcSite(GlobalId=new_guid(), OwnerHistory=None, Name=DefaultName.SITE)
    building = ifc_file.createIfcBuilding(GlobalId=new_guid(), OwnerHistory=None, Name=DefaultName.BUILDING)
    bridge_span = ifc_file.createIfcBuildingStorey(GlobalId=new_guid(), OwnerHistory=None, Name=DefaultName.STOREY)

    ifc_file.createIfcRelAggregates(
        GlobalId=new_guid(), OwnerHistory=None, RelatingObject=project, RelatedObjects=[site]
    )
    ifc_file.createIfcRelAggregates(
        GlobalId=new_guid(), OwnerHistory=None, RelatingObject=site, RelatedObjects=[building]
    )
    ifc_file.createIfcRelAggregates(
        GlobalId=new_guid(), OwnerHistory=None, RelatingObject=building, RelatedObjects=[bridge_span]
    )

    geom_context = ifc_file.createIfcGeometricRepresentationContext(
        ContextIdentifier=GeometryContext.BODY,
        ContextType=GeometryContext.MODEL,
        CoordinateSpaceDimension=COORDINATE_DIMENSION,
        Precision=COORDINATE_PRECISION,
        WorldCoordinateSystem=ifc_file.createIfcAxis2Placement3D(
            Location=ifc_file.createIfcCartesianPoint((0.0, 0.0, 0.0)),
        ),
        TrueNorth=None,
    )

    logger.debug("IFC を初期化しました（Schema=%s）", IFC_SCHEMA_LITERAL)
    return IfcContext(ifc_file=ifc_file, bridge_span=bridge_span, geom_context=geom_context)


def Create_brep_from_prism(
    ifc_file: ifcopenshell.file, top_points: Sequence[Point3D], bottom_points: Sequence[Point3D]
) -> object:
    """上面と下面の輪郭から角柱状の BREP を生成する。

    Args:
        ifc_file: IFC ファイルオブジェクト
        top_points: 上面頂点列（反時計回り）
        bottom_points: 下面頂点列（反時計回り）

    Returns:
        Faceted BREP オブジェクト

    Raises:
        ValueError: 上下面の頂点数が一致しない場合
    """
    if len(top_points) != len(bottom_points):
        raise ValueError("上下面の頂点数が一致しません。")

    face_top = top_points
    face_bottom = bottom_points[::-1]
    side_faces = []
    for index in range(len(top_points)):
        pt_top1 = top_points[index]
        pt_top2 = top_points[(index + 1) % len(top_points)]
        pt_bot2 = bottom_points[(index + 1) % len(bottom_points)]
        pt_bot1 = bottom_points[index]
        side_faces.append([pt_top1, pt_top2, pt_bot2, pt_bot1])

    faces = [create_face_from_points(ifc_file, pts) for pts in [face_top, face_bottom] + side_faces]
    shell = ifc_file.createIfcClosedShell(faces)
    return ifc_file.createIfcFacetedBrep(shell)


def Add_shape_representation_in_Beam(
    ifc_file: ifcopenshell.file, bridge_span: object, shape_representation: object, name_beam: str
) -> None:
    """IfcBeam を生成し空間階層にぶら下げる。

    Args:
        ifc_file: IFC ファイルオブジェクト
        bridge_span: ぶら下げ先の階層（BuildingStorey）
        shape_representation: 生成済み ShapeRepresentation
        name_beam: 要素名
    """
    product_definition_shape = ifc_file.createIfcProductDefinitionShape(
        Name=None, Description=None, Representations=[shape_representation]
    )
    beam_placement = ifc_file.createIfcLocalPlacement(
        PlacementRelTo=None,
        RelativePlacement=ifc_file.createIfcAxis2Placement3D(
            Location=ifc_file.createIfcCartesianPoint((0.0, 0.0, 0.0)), Axis=None, RefDirection=None
        ),
    )
    beam = ifc_file.createIfcBeam(
        GlobalId=new_guid(),
        OwnerHistory=None,
        Name=name_beam,
        ObjectPlacement=beam_placement,
        Representation=product_definition_shape,
        Tag=None,
    )
    ifc_file.createIfcRelContainedInSpatialStructure(
        GlobalId=new_guid(), OwnerHistory=None, RelatingStructure=bridge_span, RelatedElements=[beam]
    )


def extrude_profile_and_align(
    ifc_file: ifcopenshell.file,
    profile_points: ProfilePoints,
    thickness: float,
    pal1: Point3D,
    pal2: Point3D,
    pal3: Point3D,
) -> object:
    """任意断面を指定方向に押し出してソリッドを作成する。

    Args:
        ifc_file: IFC ファイルオブジェクト
        profile_points: 断面プロファイルの頂点列（2D）
        thickness: 押し出し長さ
        pal1: 押し出し開始点
        pal2: 押し出し方向を示す点
        pal3: 押し出し基準となる第3点

    Returns:
        生成された IfcExtrudedAreaSolid
    """
    pal1_vec = _ensure_3d(pal1)
    pal2_vec = _ensure_3d(pal2)
    pal3_vec = _ensure_3d(pal3)

    pal2_direction = _normalize_vector(pal2_vec - pal1_vec)
    pal3_direction = _normalize_vector(pal3_vec - pal1_vec)

    polyline = ifc_file.createIfcPolyline(
        [create_cartesian_point(ifc_file, _ensure_3d(point).tolist()) for point in profile_points]
    )
    profile = ifc_file.createIfcArbitraryClosedProfileDef(ProfileType.AREA, None, polyline)
    axis2placement = ifc_file.createIfcAxis2Placement3D(
        create_cartesian_point(ifc_file, pal1_vec.tolist()),
        ifc_file.createIfcDirection(pal2_direction.tolist()),
        ifc_file.createIfcDirection(pal3_direction.tolist()),
    )
    return ifc_file.createIfcExtrudedAreaSolid(
        profile, axis2placement, ifc_file.createIfcDirection(EXTRUDE_AXIS), thickness
    )
