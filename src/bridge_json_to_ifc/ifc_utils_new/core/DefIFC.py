"""
IFCモデル生成のためのモジュール
鋼橋の3DモデルをIFC形式で出力するための関数群
"""

import ifcopenshell
import ifcopenshell.api
import uuid
import numpy as np
import ifcopenshell.geom
from src.bridge_json_to_ifc.ifc_utils_new.core import DefMath
import math

# 生成された要素名を記録するグローバルリスト
_generated_element_names = []

# 損傷情報を格納するグローバル辞書（要素名をキーとする）
_damage_info_dict = {}

# グローバル変数: ログファイル出力関数（DefBridge.pyから設定される）
log_print_func = None


def _log_print(*args, **kwargs):
    """ログファイル出力関数（DEBUG_MODE時のみ出力）"""
    if log_print_func:
        log_print_func(*args, **kwargs)


def SetupIFC():
    """
    IFCファイルの基本構造をセットアップする
    プロジェクト、サイト、建物、階層、幾何表現コンテキストを作成する

    Returns:
        tuple: (ifc_file, bridge_span, geom_context)
            - ifc_file: IFCファイルオブジェクト
            - bridge_span: 橋梁スパン（BuildingStoreyとして表現）
            - geom_context: 幾何表現コンテキスト
    """
    # IFCファイルの作成
    # ifc_file = ifcopenshell.file(schema='IFC4')
    ifc_file = ifcopenshell.file(schema="IFC4x3")  # IFC4x3スキーマを使用

    # 測定単位をミリメートル（mm）に設定
    length_unit = ifc_file.createIfcSIUnit(UnitType="LENGTHUNIT", Prefix="MILLI")
    unit_assignment = ifc_file.createIfcUnitAssignment([length_unit])

    # プロジェクトの作成
    project = ifc_file.createIfcProject(
        GlobalId=new_guid(), OwnerHistory=None, Name="Bridge Project", UnitsInContext=unit_assignment
    )

    # サイト（区域）の作成
    site = ifc_file.createIfcSite(GlobalId=new_guid(), OwnerHistory=None, Name="Bridge Site")

    # 橋梁の作成
    # bridge = ifc_file.createIfcBridge(GlobalId=DefIFC.new_guid(),OwnerHistory=None,Name="Main Bridge")
    # IFC4では橋梁がサポートされていないため、Buildingとして表現
    bridge = ifc_file.createIfcBuilding(GlobalId=new_guid(), OwnerHistory=None, Name="Main Building")

    # 橋梁の部分（スパン）の作成
    # bridge_span = ifc_file.createIfcBridgePart(GlobalId=DefIFC.new_guid(),OwnerHistory=None,Name="Bridge Span")
    # IFC4では橋梁部材がサポートされていないため、BuildingStoreyとして表現
    bridge_span = ifc_file.createIfcBuildingStorey(GlobalId=new_guid(), OwnerHistory=None, Name="Building Storey")

    # サイトをプロジェクトに追加するリレーションの作成
    ifc_file.createIfcRelAggregates(
        GlobalId=new_guid(), OwnerHistory=None, RelatingObject=project, RelatedObjects=[site]
    )

    # 橋梁をサイトに追加するリレーションの作成
    ifc_file.createIfcRelAggregates(
        GlobalId=new_guid(), OwnerHistory=None, RelatingObject=site, RelatedObjects=[bridge]
    )

    # 橋梁スパンを橋梁に追加するリレーションの作成
    ifc_file.createIfcRelAggregates(
        GlobalId=new_guid(), OwnerHistory=None, RelatingObject=bridge, RelatedObjects=[bridge_span]
    )

    # 幾何表現コンテキストIfcGeometricRepresentationContextの作成
    geom_context = ifc_file.createIfcGeometricRepresentationContext(
        ContextIdentifier="Body",
        ContextType="Model",
        CoordinateSpaceDimension=3,
        Precision=0.1,
        WorldCoordinateSystem=ifc_file.createIfcAxis2Placement3D(
            Location=ifc_file.createIfcCartesianPoint((0.0, 0.0, 0.0)),
        ),
        TrueNorth=None,
    )

    return ifc_file, bridge_span, geom_context


def new_guid():
    """
    IFCエンティティ用の新しいGUID（Global Unique Identifier）を生成する

    Returns:
        str: UUID1形式のGUID文字列
    """
    return str(uuid.uuid1())


def create_cartesian_point(ifc_file, coordinates):
    """
    座標リストからIfcCartesianPointを作成する

    Args:
        ifc_file: IFCファイルオブジェクト
        coordinates: 座標のリスト [x, y, z] または [x, y]

    Returns:
        IfcCartesianPointエンティティ
    """
    # 各座標を文字列から実数に変換し、6桁で丸める
    coordinates_new = [round(float(coord), 6) for coord in coordinates]
    # IfcCartesianPointオブジェクトを作成
    return ifc_file.createIfcCartesianPoint(coordinates_new)


def create_face_from_points(ifc_file, face_points):
    vertices = [create_cartesian_point(ifc_file, point) for point in face_points]
    loop = ifc_file.createIfcPolyLoop(vertices)
    bound = ifc_file.createIfcFaceOuterBound(loop, True)
    face = ifc_file.createIfcFace([bound])
    return face


def Create_brep_from_polyline_list(ifc_file, polyline_list):
    """
    ポリラインのリストからB-Repソリッドを作成する
    複数のポリラインを側面として接続し、閉じたソリッド形状を生成する

    Args:
        ifc_file: IFCファイルオブジェクト
        polyline_list: ポリラインのリスト（各ポリラインは点のリスト）

    Returns:
        IfcFacetedBrepエンティティ
    """
    faces = []
    # 1. 側面（side faces）の作成
    for i in range(len(polyline_list) - 1):
        poly1 = polyline_list[i]
        poly2 = polyline_list[i + 1]
        n = min(len(poly1), len(poly2))
        for j in range(n - 1):
            quad = [poly1[j], poly1[j + 1], poly2[j + 1], poly2[j]]
            faces.append(quad)

    # 最初と最後のポリラインを接続
    poly1 = polyline_list[-1]
    poly2 = polyline_list[0]
    n = min(len(poly1), len(poly2))
    for j in range(n - 1):
        quad = [poly1[j], poly1[j + 1], poly2[j + 1], poly2[j]]
        faces.append(quad)

    # 2. 開始面（先端面）
    face_start = [poly[0] for poly in polyline_list]
    faces.append(face_start)

    # 3. 終了面（先端面）
    face_end = [poly[-1] for poly in polyline_list]
    faces.append(face_end)

    ifc_faces = [create_face_from_points(ifc_file, face) for face in faces]

    shell = ifc_file.createIfcClosedShell(ifc_faces)
    solid = ifc_file.createIfcFacetedBrep(shell)

    return solid


def Create_brep_from_prism(ifc_file, top_points, bottom_points):
    """
    上面と下面の点リストからプリズム（角柱）形状のB-Repソリッドを作成する

    Args:
        ifc_file: IFCファイルオブジェクト
        top_points: 上面の点リスト
        bottom_points: 下面の点リスト（top_pointsと同じ数の点が必要）

    Returns:
        IfcFacetedBrepエンティティ
    """
    assert len(top_points) == len(bottom_points), "上面と下面の点の数は同じである必要があります"
    n = len(top_points)

    # 上面（top face）と下面（bottom face）
    face_top = top_points
    face_bottom = bottom_points[::-1]  # 法線ベクトルの向きを正しくするために反転

    # 側面の作成
    side_faces = []
    for i in range(n):
        pt_top1 = top_points[i]
        pt_top2 = top_points[(i + 1) % n]
        pt_bot2 = bottom_points[(i + 1) % n]
        pt_bot1 = bottom_points[i]
        side_faces.append([pt_top1, pt_top2, pt_bot2, pt_bot1])

    # すべての面をまとめる
    face_indices = [face_top, face_bottom] + side_faces

    # 各面を作成
    faces = [create_face_from_points(ifc_file, pts) for pts in face_indices]
    shell = ifc_file.createIfcClosedShell(faces)
    solid = ifc_file.createIfcFacetedBrep(shell)

    return solid


def Create_faces_from_prism(ifc_file, top_points, bottom_points):
    assert len(top_points) == len(bottom_points), "上面と下面の点の数は同じである必要があります"
    n = len(top_points)

    # 上面（top face）と下面（bottom face）
    face_top = top_points
    face_bottom = bottom_points[::-1]  # 法線方向を正しくするために反転

    # 側面
    side_faces = []
    for i in range(n):
        pt_top1 = top_points[i]
        pt_top2 = top_points[(i + 1) % n]
        pt_bot2 = bottom_points[(i + 1) % n]
        pt_bot1 = bottom_points[i]
        side_faces.append([pt_top1, pt_top2, pt_bot2, pt_bot1])

    # すべての面を統合
    face_indices = [face_top, face_bottom] + side_faces

    return face_indices


def Create_brep_from_box_8points(
    ifc_file, points1T, points2T, points3T, points4T, points1B, points2B, points3B, points4B
):
    face1 = [points1T, points2T, points3T, points4T]
    face2 = [points1B, points4B, points3B, points2B]
    face3 = [points1T, points1B, points2B, points2T]
    face4 = [points2T, points2B, points3B, points3T]
    face5 = [points4T, points3T, points3B, points4B]
    face6 = [points1T, points4T, points4B, points1B]
    face_indices = [face1, face2, face3, face4, face5, face6]
    faces = [create_face_from_points(ifc_file, indices) for indices in face_indices]
    shell = ifc_file.createIfcClosedShell(faces)
    # result = ifc_file.createIfcManifoldSolidBrep(shell)
    result = ifc_file.createIfcFacetedBrep(shell)
    return result


def Create_brep_from_box_8points_tamgiac(
    ifc_file, points1T, points2T, points3T, points4T, points1B, points2B, points3B, points4B
):
    face1A = [points1T, points2T, points3T]
    face1B = [points3T, points4T, points1T]
    face2A = [points1B, points4B, points3B]
    face2B = [points3B, points2B, points1B]
    face3A = [points1T, points1B, points2B]
    face3B = [points2B, points2T, points1T]
    face4A = [points2T, points2B, points3B]
    face4B = [points3B, points3T, points2T]
    face5A = [points4T, points3T, points3B]
    face5B = [points3B, points4B, points4T]
    face6A = [points1T, points4T, points4B]
    face6B = [points4B, points1B, points1T]

    face_indices = [face1A, face1B, face2A, face2B, face3A, face3B, face4A, face4B, face5A, face5B, face6A, face6B]

    faces = [create_face_from_points(ifc_file, indices) for indices in face_indices]
    shell = ifc_file.createIfcClosedShell(faces)
    # result = ifc_file.createIfcManifoldSolidBrep(shell)
    result = ifc_file.createIfcFacetedBrep(shell)
    return result


def Create_brep_from_box_8points_Devide(
    ifc_file, points1T, points2T, points3T, points4T, points1B, points2B, points3B, points4B
):
    result = None
    if DefMath.Calculate_distance_p2p(points1T, points2T) > 500:
        count = DefMath.Calculate_distance_p2p(points1T, points2T) // 500
        for i in range(int(count)):
            p1t = DefMath.Point_on_line(
                points1T, points2T, (DefMath.Calculate_distance_p2p(points1T, points2T) / count) * i
            )
            p2t = DefMath.Point_on_line(
                points1T, points2T, (DefMath.Calculate_distance_p2p(points1T, points2T) / count) * (i + 1)
            )

            p4t = DefMath.Point_on_line(
                points4T, points3T, (DefMath.Calculate_distance_p2p(points4T, points3T) / count) * i
            )
            p3t = DefMath.Point_on_line(
                points4T, points3T, (DefMath.Calculate_distance_p2p(points4T, points3T) / count) * (i + 1)
            )

            p1b = DefMath.Point_on_line(
                points1B, points2B, (DefMath.Calculate_distance_p2p(points1B, points2B) / count) * i
            )
            p2b = DefMath.Point_on_line(
                points1B, points2B, (DefMath.Calculate_distance_p2p(points1B, points2B) / count) * (i + 1)
            )

            p4b = DefMath.Point_on_line(
                points4B, points3B, (DefMath.Calculate_distance_p2p(points4B, points3B) / count) * i
            )
            p3b = DefMath.Point_on_line(
                points4B, points3B, (DefMath.Calculate_distance_p2p(points4B, points3B) / count) * (i + 1)
            )
            solid = Create_brep_from_box_8points(ifc_file, p1t, p2t, p3t, p4t, p1b, p2b, p3b, p4b)
            if result == None:
                result = solid
            else:
                result = ifc_file.createIfcBooleanResult("UNION", result, solid)
    else:
        result = Create_brep_from_box_8points(
            ifc_file, points1T, points2T, points3T, points4T, points1B, points2B, points3B, points4B
        )

    return result


def Create_brep_from_box_2linepoints(ifc_file, arCoord1B, arCoord2B, arCoord1T, arCoord2T):
    face_indices = []
    for i in range(len(arCoord1T) - 1):
        face1 = [arCoord2T[i], arCoord2T[i + 1], arCoord1T[i + 1], arCoord1T[i]]
        face_indices.append(face1)

    for i in range(len(arCoord1B) - 1):
        face1 = [arCoord1B[i], arCoord1B[i + 1], arCoord2B[i + 1], arCoord2B[i]]
        face_indices.append(face1)

    for i in range(len(arCoord1T) - 1):
        face1 = [arCoord1T[i], arCoord1T[i + 1], arCoord1B[i + 1], arCoord1B[i]]
        face_indices.append(face1)

    for i in range(len(arCoord2T) - 1):
        face1 = [arCoord2B[i], arCoord2B[i + 1], arCoord2T[i + 1], arCoord2T[i]]
        face_indices.append(face1)

    face5 = [arCoord1T[0], arCoord1B[0], arCoord2B[0], arCoord2T[0]]
    face_indices.append(face5)
    face6 = [arCoord1T[-1], arCoord2T[-1], arCoord2B[-1], arCoord1B[-1]]
    face_indices.append(face6)

    faces = [create_face_from_points(ifc_file, indices) for indices in face_indices]
    shell = ifc_file.createIfcClosedShell(faces)
    # result = ifc_file.createIfcManifoldSolidBrep(shell)
    result = ifc_file.createIfcFacetedBrep(shell)
    return result


def Create_brep_from_box_points_UF(ifc_file, arCoordB, arCoordT):
    result = None
    for i in range(0, len(arCoordB) - 1):
        arCoord1T = arCoordT[i]
        arCoord2T = arCoordT[i + 1]
        arCoord1B = arCoordB[i]
        arCoord2B = arCoordB[i + 1]
        solid = Create_brep_from_box_2linepoints(ifc_file, arCoord1B, arCoord2B, arCoord1T, arCoord2T)
        if result == None:
            result = solid
        else:
            result = ifc_file.createIfcBooleanResult("UNION", result, solid)

    return result


def Create_brep_from_box_points_old(ifc_file, arCoordB, arCoordT):
    result_all = None
    for i in range(0, len(arCoordB) - 1):
        arCoord1T = arCoordT[i]
        arCoord2T = arCoordT[i + 1]
        arCoord1B = arCoordB[i]
        arCoord2B = arCoordB[i + 1]
        result = None
        for i_1 in range(0, len(arCoord1T) - 1):
            solid = Create_brep_from_box_8points(
                ifc_file,
                arCoord2T[i_1],
                arCoord2T[i_1 + 1],
                arCoord1T[i_1 + 1],
                arCoord1T[i_1],
                arCoord2B[i_1],
                arCoord2B[i_1 + 1],
                arCoord1B[i_1 + 1],
                arCoord1B[i_1],
            )
            if result == None:
                result = solid
            else:
                result = ifc_file.createIfcBooleanResult("UNION", result, solid)

        if result_all == None:
            result_all = result
        else:
            result_all = ifc_file.createIfcBooleanResult("UNION", result_all, result)

    return result_all


def Create_brep_from_box_points(ifc_file, arCoordB, arCoordT):
    """
    上下2つの座標配列からBRep（境界表現）ソリッドを作成する

    Args:
        ifc_file: IFCファイルオブジェクト
        arCoordB: 下部座標配列（ボトム）
        arCoordT: 上部座標配列（トップ）

    Returns:
        IfcFacetedBrep: 作成されたソリッド
    """
    _log_print(
        f"      [BREP DEBUG] Create_brep_from_box_points開始: arCoordBの数={len(arCoordB)}, arCoordTの数={len(arCoordT)}"
    )
    if len(arCoordB) == 0 or len(arCoordT) == 0:
        _log_print(f"      [BREP DEBUG] 警告: 座標配列が空です")
        return None
    if len(arCoordB) != len(arCoordT):
        _log_print(f"      [BREP DEBUG] 警告: 座標配列の数が一致しません (B:{len(arCoordB)}, T:{len(arCoordT)})")

    face_indices = []
    for i in range(0, len(arCoordB) - 1):
        arCoord1T = arCoordT[i]
        arCoord2T = arCoordT[i + 1]
        arCoord1B = arCoordB[i]
        arCoord2B = arCoordB[i + 1]

        # 各配列が空でないことを確認
        if len(arCoord1T) == 0 or len(arCoord2T) == 0 or len(arCoord1B) == 0 or len(arCoord2B) == 0:
            _log_print(
                f"      [BREP DEBUG] 警告: 区間[{i}]で空の座標配列を検出 (arCoord1T:{len(arCoord1T)}, arCoord2T:{len(arCoord2T)}, arCoord1B:{len(arCoord1B)}, arCoord2B:{len(arCoord2B)})"
            )
            continue

        for i_1 in range(len(arCoord1T) - 1):
            face1 = [arCoord2T[i_1], arCoord2T[i_1 + 1], arCoord1T[i_1 + 1], arCoord1T[i_1]]
            face_indices.append(face1)

        for i_1 in range(len(arCoord1B) - 1):
            face1 = [arCoord1B[i_1], arCoord1B[i_1 + 1], arCoord2B[i_1 + 1], arCoord2B[i_1]]
            face_indices.append(face1)

        # 各配列に少なくとも1つの要素があることを確認
        if len(arCoord1T) > 0 and len(arCoord1B) > 0 and len(arCoord2B) > 0 and len(arCoord2T) > 0:
            face5 = [arCoord1T[0], arCoord1B[0], arCoord2B[0], arCoord2T[0]]
            face_indices.append(face5)
            face6 = [arCoord1T[-1], arCoord2T[-1], arCoord2B[-1], arCoord1B[-1]]
            face_indices.append(face6)

    # 最初の面と最後の面を追加（配列が存在し、十分な要素がある場合のみ）
    if len(arCoordT) >= 2 and len(arCoordB) >= 2:
        arCoord1T = arCoordT[0]
        arCoord2T = arCoordT[1]
        arCoord1B = arCoordB[0]
        arCoord2B = arCoordB[1]
        if len(arCoord1T) > 1 and len(arCoord1B) > 1:
            for i in range(len(arCoord1T) - 1):
                face1 = [arCoord1T[i], arCoord1T[i + 1], arCoord1B[i + 1], arCoord1B[i]]
                face_indices.append(face1)

        arCoord1T = arCoordT[-2]
        arCoord2T = arCoordT[-1]
        arCoord1B = arCoordB[-2]
        arCoord2B = arCoordB[-1]
        if len(arCoord2T) > 1 and len(arCoord2B) > 1:
            for i in range(len(arCoord2T) - 1):
                face1 = [arCoord2B[i], arCoord2B[i + 1], arCoord2T[i + 1], arCoord2T[i]]
                face_indices.append(face1)

    if len(face_indices) == 0:
        _log_print(f"      [BREP DEBUG] 警告: 面が作成されませんでした")
        return None

    _log_print(f"      [BREP DEBUG] 面の数: {len(face_indices)}")
    faces = [create_face_from_points(ifc_file, indices) for indices in face_indices]
    _log_print(f"      [BREP DEBUG] IfcFace作成完了: {len(faces)}個")
    shell = ifc_file.createIfcClosedShell(faces)
    _log_print(
        f"      [BREP DEBUG] IfcClosedShell作成完了: Faces数={len(shell.CfsFaces) if hasattr(shell, 'CfsFaces') else 'N/A'}"
    )
    # result = ifc_file.createIfcManifoldSolidBrep(shell)
    result = ifc_file.createIfcFacetedBrep(shell)
    _log_print(
        f"      [BREP DEBUG] IfcFacetedBrep作成完了: Outer={result.Outer if hasattr(result, 'Outer') else 'N/A'}"
    )

    return result


def Add_shape_representation_in_Beam(
    ifc_file, bridge_span, shape_representation, NameBeam, object_type=None, pset_name=None, properties=None
):
    # 形状表現をBeam（梁）エンティティとして追加し、橋梁スパンに配置する
    import uuid
    import ifcopenshell.api

    NameBeam_str = NameBeam
    metadata = {}
    if isinstance(NameBeam, (list, tuple)):
        if len(NameBeam) >= 1:
            NameBeam_str = NameBeam[0]
        if len(NameBeam) >= 2 and isinstance(NameBeam[1], dict):
            metadata = NameBeam[1]
    elif isinstance(NameBeam, dict):
        NameBeam_str = NameBeam.get("Name", "Component")
        metadata = NameBeam

    # UUIDを追加しない（呼び出し側で完全な名前を渡す）
    # ただし、名前が既に完全な形式（T_X_Yなど）を含む場合はそのまま使用
    unique_name = NameBeam_str
    _log_print(f"    [IFC DEBUG] Add_shape_representation_in_Beam: NameBeam={NameBeam_str}, unique_name={unique_name}")
    _log_print(
        f"    [IFC DEBUG] shape_representation type={type(shape_representation)}, Items数={len(shape_representation.Items) if hasattr(shape_representation, 'Items') else 'N/A'}"
    )

    # オブジェクトにリンクするIfcProductDefinitionShapeを作成
    product_definition_shape = ifc_file.createIfcProductDefinitionShape(
        Name=None,  # 製品定義の名前（不要な場合はNone）
        Description=None,  # 製品定義の説明（不要な場合はNone）
        Representations=[shape_representation],  # 形状表現のリスト
    )
    _log_print(f"    [IFC DEBUG] product_definition_shape作成完了: {product_definition_shape}")

    # オブジェクトの位置を定義するIfcLocalPlacementを作成
    # bridge_spanのObjectPlacementを取得して、それを参照にする
    try:
        parent_placement = bridge_span.ObjectPlacement if hasattr(bridge_span, "ObjectPlacement") else None
    except:
        parent_placement = None

    beam_placement = ifc_file.createIfcLocalPlacement(
        PlacementRelTo=parent_placement,  # 親オブジェクトの配置を参照
        RelativePlacement=ifc_file.createIfcAxis2Placement3D(
            Location=ifc_file.createIfcCartesianPoint((0.0, 0.0, 0.0)),  # オブジェクトの位置 (0, 0, 0)
            Axis=None,  # 軸（不要な場合はNone）
            RefDirection=None,  # 参照方向（不要な場合はNone）
        ),
    )
    _log_print(f"    [IFC DEBUG] beam_placement作成完了: parent_placement={parent_placement}")

    # IfcBeamを属性と形状で作成
    beam_guid = new_guid()
    beam = ifc_file.createIfcBeam(
        GlobalId=beam_guid,  # 梁のグローバルID（通常は新規生成）
        OwnerHistory=None,  # 所有者履歴（不要な場合はNone）
        Name=unique_name,  # 梁の名前（一意の名前に変更）
        ObjectPlacement=beam_placement,  # 梁の位置と方向
        Representation=product_definition_shape,  # 梁の形状
        Tag=None,  # タグ（不要な場合はNone）
        ObjectType=object_type,  # ObjectTypeを設定
    )

    # metadataからも取得（パラメータが指定されていない場合）
    if not object_type:
        object_type = metadata.get("ObjectType")
        if object_type:
            beam.ObjectType = object_type

    predefined_type = metadata.get("PredefinedType", "USERDEFINED")
    tag_value = metadata.get("Tag")
    if predefined_type:
        try:
            beam.PredefinedType = predefined_type
        except Exception:
            pass
    if tag_value:
        beam.Tag = tag_value
    _log_print(
        f"    [IFC DEBUG] IfcBeam作成完了: GlobalId={beam_guid}, Name={unique_name}, ObjectPlacement={beam_placement}"
    )

    # 生成された要素名を記録（アンダースコアを保持）
    # unique_nameは文字列としてそのまま記録されるため、アンダースコアは保持される
    _generated_element_names.append(str(unique_name))

    # プロパティセットを追加
    if pset_name and properties:
        try:
            ifcopenshell.api.run("pset.add_pset", ifc_file, product=beam, name=pset_name, properties=properties)
        except Exception as e:
            _log_print(f"    [IFC WARNING] プロパティセットの追加に失敗しました: {e}")
    else:
        # metadataからも取得（パラメータが指定されていない場合）
        props_dict = metadata.get("Properties")
        if props_dict:
            pset_name_from_metadata = metadata.get("PropertySetName", "Pset_CustomAttributes")
            try:
                pset = ifcopenshell.api.run("pset.add_pset", ifc_file, product=beam, name=pset_name_from_metadata)
                ifcopenshell.api.run("pset.edit_pset", ifc_file, pset=pset, properties=props_dict)
            except Exception as e:
                _log_print(f"    [IFC WARNING] プロパティセットの追加に失敗しました: {e}")

    # 損傷情報をプロパティセットとして追加
    _log_print(
        f"    [DAMAGE DEBUG] 要素名チェック: unique_name='{unique_name}', 損傷情報辞書のキー数={len(_damage_info_dict)}"
    )
    if len(_damage_info_dict) > 0:
        _log_print(f"    [DAMAGE DEBUG] 損傷情報辞書のキー一覧: {list(_damage_info_dict.keys())}")

    if unique_name in _damage_info_dict:
        damage_data = _damage_info_dict[unique_name]
        print(f"    [損傷] {unique_name} に損傷情報を適用中...")
        _log_print(f"    [DAMAGE DEBUG] 損傷情報が見つかりました: {unique_name}")

        # 新形式: DamageItemsとInspectionMetaを分離
        if isinstance(damage_data, dict) and "DamageItems" in damage_data:
            damage_items = damage_data.get("DamageItems", [])
            inspection_meta = damage_data.get("InspectionMeta", {})
        else:
            # 旧形式: damage_dataが直接DamageItemsのリスト
            damage_items = damage_data if isinstance(damage_data, list) else []
            inspection_meta = {}

        if damage_items:
            try:
                # 損傷情報をプロパティとして整理
                damage_properties = {}

                # 点検情報を追加
                if inspection_meta:
                    if inspection_meta.get("InspectionDate"):
                        damage_properties["点検日"] = inspection_meta["InspectionDate"]
                    if inspection_meta.get("InspectionYear"):
                        damage_properties["点検年度"] = str(inspection_meta["InspectionYear"])
                    if inspection_meta.get("Inspector"):
                        damage_properties["点検者"] = inspection_meta["Inspector"]
                    if inspection_meta.get("InspectionType"):
                        damage_properties["点検種別"] = inspection_meta["InspectionType"]
                    if inspection_meta.get("HistorySummary"):
                        damage_properties["経緯"] = inspection_meta["HistorySummary"]
                    if inspection_meta.get("RepairRecommendation"):
                        damage_properties["補修推奨"] = inspection_meta["RepairRecommendation"]
                    if inspection_meta.get("RepairHistory"):
                        damage_properties["補修履歴"] = inspection_meta["RepairHistory"]

                # 損傷項目を追加
                for i, damage_item in enumerate(damage_items):
                    damage_type = damage_item.get("DamageType", f"損傷{i + 1}")
                    damage_level = damage_item.get("DamageLevel", "")
                    notes = damage_item.get("Notes", "")

                    # プロパティ名: 損傷の種類、値: 評価レベル
                    damage_properties[damage_type] = damage_level
                    if notes:
                        damage_properties[f"{damage_type}_備考"] = notes
                    _log_print(
                        f"    [DAMAGE DEBUG] 損傷項目[{i}]: DamageType='{damage_type}', DamageLevel='{damage_level}'"
                    )

                _log_print(f"    [DAMAGE DEBUG] プロパティ辞書: {damage_properties}")

                # 損傷情報用のプロパティセットを作成
                _log_print(f"    [DAMAGE DEBUG] プロパティセット作成開始: name='Pset_DamageInformation'")
                pset_damage = ifcopenshell.api.run(
                    "pset.add_pset", ifc_file, product=beam, name="Pset_DamageInformation"
                )
                _log_print(f"    [DAMAGE DEBUG] プロパティセット作成完了: pset={pset_damage}")

                _log_print(f"    [DAMAGE DEBUG] プロパティ編集開始: properties={damage_properties}")
                # IFC4X3ではpset.edit_psetがサポートされていないため、直接プロパティを追加
                # 既存のプロパティを取得（HasPropertiesがNoneの場合は空リスト）
                if hasattr(pset_damage, "HasProperties") and pset_damage.HasProperties is not None:
                    existing_properties = list(pset_damage.HasProperties)
                else:
                    existing_properties = []

                _log_print(f"    [DAMAGE DEBUG] 既存プロパティ数: {len(existing_properties)}")

                # 新しいプロパティを作成
                new_properties = []
                for prop_name, prop_value in damage_properties.items():
                    # IfcPropertySingleValueを作成
                    prop = ifc_file.createIfcPropertySingleValue(
                        Name=prop_name, NominalValue=ifc_file.createIfcText(str(prop_value))
                    )
                    new_properties.append(prop)
                    _log_print(f"    [DAMAGE DEBUG] プロパティ作成: {prop_name} = {prop_value}")

                # 既存のプロパティと新しいプロパティを結合
                all_properties = existing_properties + new_properties

                # プロパティセットにプロパティを設定
                pset_damage.HasProperties = tuple(all_properties)
                print(f"    [損傷] プロパティ追加完了: {len(new_properties)}個")
                _log_print(
                    f"    [DAMAGE DEBUG] プロパティセットに{len(new_properties)}個のプロパティを追加しました（合計{len(all_properties)}個）"
                )

                _log_print(f"    [DAMAGE DEBUG] プロパティ編集完了: {len(new_properties)}個のプロパティを追加")
                _log_print(f"    [IFC DEBUG] 損傷情報を追加: {unique_name} -> {damage_properties}")

                # 損傷がある要素の色を変更（レベルEなら赤、それ以外は黄色）
                try:
                    # 損傷レベルEがあるかチェック
                    has_level_e = any(item.get("DamageLevel", "").upper() == "E" for item in damage_items)
                    _apply_damage_color_to_shape(ifc_file, shape_representation, is_severe=has_level_e)
                    color_name = "赤（重度）" if has_level_e else "黄色（警告）"
                    print(f"    [損傷] 色変更: {color_name}")
                    _log_print(f"    [DAMAGE DEBUG] 損傷要素の色を{color_name}に変更しました: {unique_name}")
                except Exception as color_e:
                    _log_print(f"    [DAMAGE DEBUG] 色の変更に失敗しました: {color_e}")

            except Exception as e:
                import traceback

                _log_print(f"    [IFC WARNING] 損傷情報のプロパティセット追加に失敗しました: {e}")
                _log_print(f"    [IFC WARNING] トレースバック: {traceback.format_exc()}")
    else:
        _log_print(f"    [DAMAGE DEBUG] 損傷情報が見つかりませんでした: '{unique_name}' は損傷情報辞書に存在しません")

    # 梁を橋梁スパンの一部としてリンクするIfcRelContainedInSpatialStructureを作成
    relation_guid = new_guid()
    relation = ifc_file.createIfcRelContainedInSpatialStructure(
        GlobalId=relation_guid,  # リレーションのグローバルID（通常は新規生成）
        OwnerHistory=None,  # 所有者履歴（不要な場合はNone）
        RelatingStructure=bridge_span,  # オブジェクトが含まれる橋梁スパン（スパン）
        RelatedElements=[beam],  # 橋梁スパン内のオブジェクト（梁など）
    )
    _log_print(
        f"    [IFC DEBUG] IfcRelContainedInSpatialStructure作成完了: GlobalId={relation_guid}, RelatedElements数={len(relation.RelatedElements)}"
    )
    _log_print(f"    [IFC DEBUG] {NameBeam}のIFCエンティティ追加完了")


def extrude_profile_and_align(ifc_file, profile_points, Thick, pal1, pal2, pal3):
    pal1 = np.array(pal1, dtype=float)
    pal2 = np.array(pal2, dtype=float)
    pal3 = np.array(pal3, dtype=float)
    pal2_vector = pal2 - pal1
    pal3_vector = pal3 - pal1
    pal1_list = pal1.tolist()
    pal2_list = pal2_vector.tolist()
    pal3_list = pal3_vector.tolist()

    polyline = ifc_file.createIfcPolyline([create_cartesian_point(ifc_file, point) for point in profile_points])
    profile = ifc_file.createIfcArbitraryClosedProfileDef("AREA", None, polyline)
    axis2placement = ifc_file.createIfcAxis2Placement3D(
        create_cartesian_point(ifc_file, pal1_list),
        ifc_file.createIfcDirection(pal2_list),
        ifc_file.createIfcDirection(pal3_list),
    )
    solid_obj = ifc_file.createIfcExtrudedAreaSolid(
        profile, axis2placement, ifc_file.createIfcDirection([0.0, 0.0, 1.0]), Thick
    )

    return solid_obj


def _pt2d(ifc, xy):
    return ifc.createIfcCartesianPoint([float(xy[0]), float(xy[1])])


def _pt3d(ifc, xyz):
    return ifc.createIfcCartesianPoint([float(xyz[0]), float(xyz[1]), float(xyz[2])])


def sweep_profile_along_polyline(ifc_file, profile_points_2d, path_points_3d, fixed_reference=(0, 0, 1)):
    # 2Dプロファイルを3Dポリラインに沿ってスイープしてIfcFixedReferenceSweptAreaSolidを作成する
    # profile_points_2d: [(x, y), ...]  XY平面上の閉じたプロファイル
    # path_points_3d: [(x, y, z), ...]  グローバル座標系のポリライン
    # fixed_reference: ねじれ防止のための上方向ベクトル

    # --- 入力データの検証 ---
    if len(path_points_3d) < 2:
        raise ValueError("path_points_3dには最低2点必要です")

    # プロファイルが閉じていない場合は最初の点を最後に追加
    if not np.allclose(np.array(profile_points_2d[0]), np.array(profile_points_2d[-1])):
        profile_points_2d = list(profile_points_2d) + [profile_points_2d[0]]

    # --- 閉じた2Dプロファイルの作成 ---
    poly2d = ifc_file.createIfcPolyline([_pt2d(ifc_file, p) for p in profile_points_2d])
    profile = ifc_file.createIfcArbitraryClosedProfileDef("AREA", None, poly2d)

    # --- 3Dポリラインのパス（IfcPolyline 3D）を作成 ---
    directrix = ifc_file.createIfcPolyline([_pt3d(ifc_file, p) for p in path_points_3d])

    # --- プロファイルの固定方向（FixedReference） ---
    fixed_ref = ifc_file.createIfcDirection([float(x) for x in fixed_reference])

    # --- スイープソリッドの作成 ---
    swept = ifc_file.createIfcFixedReferenceSweptAreaSolid(
        SweptArea=profile, Directrix=directrix, FixedReference=fixed_ref
    )

    return swept


def create_color(ifc_file, red, green, blue):
    color = ifc_file.createIfcColourRgb(Red=red / 255.0, Green=green / 255.0, Blue=blue / 255.0)
    surface_style_shading = ifc_file.createIfcSurfaceStyleShading(SurfaceColour=color)
    surface_style = ifc_file.createIfcSurfaceStyle(Side="BOTH", Styles=[surface_style_shading])
    return surface_style


def _apply_damage_color_to_shape(ifc_file, shape_representation, is_severe=False):
    """
    損傷がある要素の色を変更する

    Args:
        ifc_file: IFCファイルオブジェクト
        shape_representation: IfcShapeRepresentation
        is_severe: True=重度損傷（赤）、False=警告（黄色）
    """
    if is_severe:
        # 赤色（重度損傷：レベルE）
        # RGB: 220, 50, 50 (鮮やかな赤)
        damage_color = ifc_file.createIfcColourRgb(Red=220.0 / 255.0, Green=50.0 / 255.0, Blue=50.0 / 255.0)
    else:
        # 黄色（警告色：レベルC, Dなど）
        # RGB: 255, 200, 0 (鮮やかな黄色/オレンジ寄り)
        damage_color = ifc_file.createIfcColourRgb(Red=255.0 / 255.0, Green=200.0 / 255.0, Blue=0.0 / 255.0)

    damage_surface_style_shading = ifc_file.createIfcSurfaceStyleShading(SurfaceColour=damage_color)
    damage_surface_style = ifc_file.createIfcSurfaceStyle(Side="BOTH", Styles=[damage_surface_style_shading])

    # shape_representationのItemsに対してスタイルを適用
    if hasattr(shape_representation, "Items") and shape_representation.Items:
        for item in shape_representation.Items:
            # 既存のIfcStyledItemを探して削除または更新
            existing_styled_items = []
            try:
                # IFCファイル内のすべてのIfcStyledItemを検索
                for styled_item in ifc_file.by_type("IfcStyledItem"):
                    if styled_item.Item == item:
                        existing_styled_items.append(styled_item)
            except:
                pass

            # 既存のスタイルを削除
            for existing_styled_item in existing_styled_items:
                try:
                    ifc_file.remove(existing_styled_item)
                except:
                    pass

            # 新しい黄色のスタイルを適用
            ifc_file.createIfcStyledItem(Item=item, Styles=[damage_surface_style])


def Draw_Solid_Circle(ifc_file, pcen, dcir, pal1, pal2, pal3, Distance_extrude=50.1):
    Rcir = float(dcir) / 2

    pcen = np.array(pcen, dtype=float)
    circle_profile = ifc_file.createIfcCircleProfileDef(
        ProfileType="AREA",
        ProfileName=None,
        Position=ifc_file.createIfcAxis2Placement2D(create_cartesian_point(ifc_file, (pcen[0], pcen[1]))),
        Radius=Rcir,
    )

    pal1 = np.array(pal1, dtype=float)
    pal2 = np.array(pal2, dtype=float)
    pal3 = np.array(pal3, dtype=float)
    pal2_vector = pal2 - pal1
    pal3_vector = pal3 - pal1
    pal1_list = pal1.tolist()
    pal2_list = pal2_vector.tolist()
    pal3_list = pal3_vector.tolist()

    void_position1 = np.array(pal1)
    void_axis2placement1 = ifc_file.createIfcAxis2Placement3D(
        create_cartesian_point(ifc_file, void_position1),
        ifc_file.createIfcDirection(pal2_list),
        ifc_file.createIfcDirection(pal3_list),
    )

    if Distance_extrude == 50.1:
        SolidHole1 = ifc_file.createIfcExtrudedAreaSolid(
            circle_profile, void_axis2placement1, ifc_file.createIfcDirection([0.0, 0.0, 1.0]), 50
        )
        SolidHole2 = ifc_file.createIfcExtrudedAreaSolid(
            circle_profile, void_axis2placement1, ifc_file.createIfcDirection([0.0, 0.0, 1.0]), -50
        )
        main_solid = ifc_file.createIfcBooleanResult("UNION", SolidHole1, SolidHole2)
    else:
        main_solid = ifc_file.createIfcExtrudedAreaSolid(
            circle_profile, void_axis2placement1, ifc_file.createIfcDirection([0.0, 0.0, 1.0]), Distance_extrude
        )

    return main_solid


def Draw_Solid_Bolt(ifc_file, pcen, dhole, gap_cen_to_head, gap_cen_to_nut, pal1, pal2, pal3):
    # ボルトのソリッドを生成する

    dhead = 40
    hhead = 15
    dshaft = 20
    dnut = 35
    hnut = 10
    hshaft = abs(gap_cen_to_head + gap_cen_to_nut) + hnut + 10

    pcen = np.array(pcen, dtype=float)
    if pcen.shape[0] == 2:
        pcen = np.append(pcen, 0.0)

    Rhead = float(dhead) / 2
    circle_head_profile = create_hexagon_profile(ifc_file, (pcen[0], pcen[1]), Rhead)

    # ボルトのシャフト部分のプロファイルを作成
    Rshaft = float(dshaft) / 2
    circle_shaft_profile = ifc_file.createIfcCircleProfileDef(
        ProfileType="AREA",
        ProfileName=None,
        Position=ifc_file.createIfcAxis2Placement2D(create_cartesian_point(ifc_file, (pcen[0], pcen[1]))),
        Radius=Rshaft,
    )

    # ナット部分のプロファイルを作成
    Rnut = float(dnut) / 2
    circle_nut_profile = circle_head_profile = create_hexagon_profile(ifc_file, (pcen[0], pcen[1]), Rnut)

    # ボルトの座標系を定義
    pal1 = np.array(pal1, dtype=float)
    pal2 = np.array(pal2, dtype=float)
    pal3 = np.array(pal3, dtype=float)

    if gap_cen_to_head > 0:
        pal1_head = DefMath.Point_on_parallel_line(pal1, pal1, pal2, gap_cen_to_head)
        pal2_head = pal2.copy()
        pal3_head = DefMath.Point_on_parallel_line(pal3, pal1, pal2, gap_cen_to_head)
        pal2_head_vector = pal2_head - pal1_head
        pal3_head_vector = pal3_head - pal1_head
        pal1_head_list = pal1_head.tolist()
        pal2_head_list = pal2_head_vector.tolist()
        pal3_head_list = pal3_head_vector.tolist()
        bolt_axis2placement = ifc_file.createIfcAxis2Placement3D(
            create_cartesian_point(ifc_file, pal1_head_list),
            ifc_file.createIfcDirection(pal2_head_list),
            ifc_file.createIfcDirection(pal3_head_list),
        )
        # ボルトの頭部
        solid_head = ifc_file.createIfcExtrudedAreaSolid(
            circle_head_profile, bolt_axis2placement, ifc_file.createIfcDirection([0.0, 0.0, 1.0]), hhead
        )
        solid_shaft = ifc_file.createIfcExtrudedAreaSolid(
            circle_shaft_profile, bolt_axis2placement, ifc_file.createIfcDirection([0.0, 0.0, -1.0]), hshaft
        )

        pal1_nut = DefMath.Point_on_parallel_line(pal1, pal1, pal2, -gap_cen_to_nut)
        pal2_nut = pal2.copy()
        pal3_nut = DefMath.Point_on_parallel_line(pal3, pal1, pal2, -gap_cen_to_nut)
        pal2_nut_vector = pal2_nut - pal1_nut
        pal3_nut_vector = pal3_nut - pal1_nut
        pal1_nut_list = pal1_nut.tolist()
        pal2_nut_list = pal2_nut_vector.tolist()
        pal3_nut_list = pal3_nut_vector.tolist()
        # 下側のナット
        nut_axis2placement = ifc_file.createIfcAxis2Placement3D(
            create_cartesian_point(ifc_file, pal1_nut_list),
            ifc_file.createIfcDirection(pal2_nut_list),
            ifc_file.createIfcDirection(pal3_nut_list),
        )
        solid_nut = ifc_file.createIfcExtrudedAreaSolid(
            circle_nut_profile, nut_axis2placement, ifc_file.createIfcDirection([0.0, 0.0, -1.0]), hnut
        )

        # 各部分を結合
        head_shaft = ifc_file.createIfcBooleanResult("UNION", solid_head, solid_shaft)
        complete_bolt = ifc_file.createIfcBooleanResult("UNION", head_shaft, solid_nut)
    else:
        pal1_head = DefMath.Point_on_parallel_line(pal1, pal1, pal2, gap_cen_to_head)
        pal2_head = pal2.copy()
        pal3_head = DefMath.Point_on_parallel_line(pal3, pal1, pal2, gap_cen_to_head)
        pal2_head_vector = pal2_head - pal1_head
        pal3_head_vector = pal3_head - pal1_head
        pal1_head_list = pal1_head.tolist()
        pal2_head_list = pal2_head_vector.tolist()
        pal3_head_list = pal3_head_vector.tolist()
        bolt_axis2placement = ifc_file.createIfcAxis2Placement3D(
            create_cartesian_point(ifc_file, pal1_head_list),
            ifc_file.createIfcDirection(pal2_head_list),
            ifc_file.createIfcDirection(pal3_head_list),
        )
        # ボルトの頭部
        solid_head = ifc_file.createIfcExtrudedAreaSolid(
            circle_head_profile, bolt_axis2placement, ifc_file.createIfcDirection([0.0, 0.0, 1.0]), -hhead
        )
        solid_shaft = ifc_file.createIfcExtrudedAreaSolid(
            circle_shaft_profile, bolt_axis2placement, ifc_file.createIfcDirection([0.0, 0.0, -1.0]), -hshaft
        )

        pal1_nut = DefMath.Point_on_parallel_line(pal1, pal1, pal2, -gap_cen_to_nut)
        pal2_nut = pal2.copy()
        pal3_nut = DefMath.Point_on_parallel_line(pal3, pal1, pal2, -gap_cen_to_nut)
        pal2_nut_vector = pal2_nut - pal1_nut
        pal3_nut_vector = pal3_nut - pal1_nut
        pal1_nut_list = pal1_nut.tolist()
        pal2_nut_list = pal2_nut_vector.tolist()
        pal3_nut_list = pal3_nut_vector.tolist()
        # 下側のナット
        nut_axis2placement = ifc_file.createIfcAxis2Placement3D(
            create_cartesian_point(ifc_file, pal1_nut_list),
            ifc_file.createIfcDirection(pal2_nut_list),
            ifc_file.createIfcDirection(pal3_nut_list),
        )
        solid_nut = ifc_file.createIfcExtrudedAreaSolid(
            circle_nut_profile, nut_axis2placement, ifc_file.createIfcDirection([0.0, 0.0, -1.0]), -hnut
        )

        # 各部分を結合
        head_shaft = ifc_file.createIfcBooleanResult("UNION", solid_head, solid_shaft)
        complete_bolt = ifc_file.createIfcBooleanResult("UNION", head_shaft, solid_nut)

    return complete_bolt


def create_ifc_polyline(ifc_file, points):
    # 点のリストから IfcPolyline を作成する
    # IfcCartesianPoint を作成
    ifc_points = []
    for p in points:
        # x, y のみの場合は z = 0.0 を追加
        if len(p) == 2:
            p = [p[0], p[1], 0.0]

        pt = create_cartesian_point(ifc_file, p)
        ifc_points.append(pt)
    # polyline を作成
    polyline = ifc_file.createIfcPolyline(ifc_points)
    return polyline


def create_hexagon_profile(ifc_file, center, radius):
    # 正六角形のプロファイルを作成する
    # ボルトの頭部やナットの形状に使用される
    points = []
    for i in range(6):
        angle = math.radians(i * 60)  # 360度を6等分して角度を計算
        x = center[0] + radius * math.cos(angle)
        y = center[1] + radius * math.sin(angle)
        points.append(create_cartesian_point(ifc_file, (x, y)))

    # 点から六角形プロファイルを作成
    return ifc_file.createIfcArbitraryClosedProfileDef(
        ProfileType="AREA", OuterCurve=ifc_file.createIfcPolyline(points)
    )


def union_all_solids(ifc_file, solids):
    if not solids:
        return None  # 空の配列

    result = solids[0]  # 最初のソリッドから開始

    for solid in solids[1:]:
        result = ifc_file.createIfcBooleanResult("UNION", result, solid)

    return result


def get_generated_element_names():
    """
    生成された要素名のリストを取得する

    Returns:
        list: 生成された要素名のリスト
    """
    return _generated_element_names.copy()


def clear_generated_element_names():
    """
    生成された要素名のリストをクリアする
    """
    global _generated_element_names
    _generated_element_names = []


def load_damage_info(damage_info_dict):
    """
    損傷情報を読み込む

    Args:
        damage_info_dict: 要素名をキーとした損傷情報の辞書
            {
                "ElementName": [
                    {"DamageType": "腐食損傷", "DamageLevel": "C"},
                    ...
                ],
                ...
            }
    """
    global _damage_info_dict
    _damage_info_dict = damage_info_dict.copy()


def clear_damage_info():
    """
    損傷情報をクリアする
    """
    global _damage_info_dict
    _damage_info_dict = {}
