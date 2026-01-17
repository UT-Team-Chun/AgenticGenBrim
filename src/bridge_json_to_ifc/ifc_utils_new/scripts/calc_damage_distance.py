"""
損傷要素間の距離計算スクリプト
damage_info.jsonに記載された損傷要素間の距離をすべて計算して表示
"""

import os
import sys
import json
import argparse
import math
from itertools import combinations

# ifcopenshellのインポート
try:
    import ifcopenshell
    import ifcopenshell.geom
    import ifcopenshell.util.placement
except ImportError:
    print("エラー: ifcopenshellがインストールされていません")
    print("pip install ifcopenshell でインストールしてください")
    sys.exit(1)

try:
    import numpy as np
except ImportError:
    print("エラー: numpyがインストールされていません")
    sys.exit(1)


def get_element_centroid(ifc_file, element_name):
    """
    IFC要素の重心座標を取得

    Args:
        ifc_file: IFCファイルオブジェクト
        element_name: 要素名

    Returns:
        (x, y, z) タプル、または見つからない場合はNone
    """
    # 要素を名前で検索
    target_element = None
    for elem_type in ["IfcBeam", "IfcPlate", "IfcMember", "IfcBuildingElementProxy"]:
        try:
            elements = ifc_file.by_type(elem_type)
            for elem in elements:
                if elem.Name == element_name:
                    target_element = elem
                    break
            if target_element:
                break
        except:
            pass

    if not target_element:
        return None

    # 方法1: ifcopenshell.geom で形状を処理（グローバル座標で取得）
    try:
        settings = ifcopenshell.geom.settings()
        settings.set(settings.USE_WORLD_COORDS, True)  # グローバル座標を使用
        shape = ifcopenshell.geom.create_shape(settings, target_element)

        verts = shape.geometry.verts
        if verts:
            vertices = []
            for i in range(0, len(verts), 3):
                vertices.append([verts[i], verts[i + 1], verts[i + 2]])

            if vertices:
                vertices = np.array(vertices)
                centroid = np.mean(vertices, axis=0)
                return tuple(centroid)
    except Exception as e:
        print(f"  注意: 形状処理失敗、手動で座標変換を試みます")

    # 方法2: 形状定義のPositionとObjectPlacementの両方を考慮した変換
    try:
        if target_element.Representation:
            for rep in target_element.Representation.Representations:
                for item in rep.Items:
                    if item.is_a("IfcExtrudedAreaSolid") or item.is_a("IfcSweptAreaSolid"):
                        # 形状定義のPosition（IfcAxis2Placement3D）から変換行列を作成
                        shape_matrix = get_axis2placement3d_matrix(item.Position)

                        # ObjectPlacementの変換行列
                        placement_matrix = ifcopenshell.util.placement.get_local_placement(
                            target_element.ObjectPlacement
                        )

                        # 全体の変換行列 = ObjectPlacement * ShapePosition
                        total_matrix = placement_matrix @ shape_matrix

                        # 形状の中心点を計算（押出の場合）
                        if item.is_a("IfcExtrudedAreaSolid"):
                            depth = item.Depth
                            # ローカル座標系での中心点（押出方向の中心）
                            local_center = np.array([0.0, 0.0, depth / 2, 1.0])
                        else:
                            local_center = np.array([0.0, 0.0, 0.0, 1.0])

                        # グローバル座標に変換
                        global_center = total_matrix @ local_center
                        print(f"  (形状+配置の変換により取得)")
                        return tuple(global_center[:3])
    except Exception as e:
        print(f"  注意: 手動座標変換失敗: {e}")

    # 方法3: Representationのローカル座標のみ（フォールバック）
    try:
        if target_element.Representation:
            coords = extract_coords_from_representation(target_element.Representation)
            if coords is not None and len(coords) > 0:
                centroid = np.mean(coords, axis=0)
                print(f"  (ローカル座標から取得 - 不正確な可能性)")
                return tuple(centroid)
    except Exception as e:
        print(f"  警告: 座標抽出に失敗: {e}")

    return None


def get_axis2placement3d_matrix(placement):
    """IfcAxis2Placement3Dから4x4変換行列を作成"""
    if not placement:
        return np.eye(4)

    # 原点
    location = np.array([0.0, 0.0, 0.0])
    if hasattr(placement, "Location") and placement.Location:
        coords = placement.Location.Coordinates
        location = np.array([float(coords[0]), float(coords[1]), float(coords[2]) if len(coords) > 2 else 0.0])

    # Z軸（Axis）
    z_axis = np.array([0.0, 0.0, 1.0])
    if hasattr(placement, "Axis") and placement.Axis:
        ratios = placement.Axis.DirectionRatios
        z_axis = np.array([float(ratios[0]), float(ratios[1]), float(ratios[2]) if len(ratios) > 2 else 0.0])
        z_axis = z_axis / np.linalg.norm(z_axis)  # 正規化

    # X軸（RefDirection）
    x_axis = np.array([1.0, 0.0, 0.0])
    if hasattr(placement, "RefDirection") and placement.RefDirection:
        ratios = placement.RefDirection.DirectionRatios
        x_axis = np.array([float(ratios[0]), float(ratios[1]), float(ratios[2]) if len(ratios) > 2 else 0.0])
        x_axis = x_axis / np.linalg.norm(x_axis)  # 正規化

    # Y軸はZ×Xの外積
    y_axis = np.cross(z_axis, x_axis)
    y_axis = y_axis / np.linalg.norm(y_axis)  # 正規化

    # X軸を再計算（直交化）
    x_axis = np.cross(y_axis, z_axis)
    x_axis = x_axis / np.linalg.norm(x_axis)

    # 4x4変換行列を作成
    matrix = np.eye(4)
    matrix[0:3, 0] = x_axis
    matrix[0:3, 1] = y_axis
    matrix[0:3, 2] = z_axis
    matrix[0:3, 3] = location

    return matrix


def get_placement_location(placement):
    """ObjectPlacementから絶対座標を取得"""
    try:
        # 再帰的に親の配置を辿って絶対座標を計算
        location = np.array([0.0, 0.0, 0.0])

        current = placement
        while current:
            if hasattr(current, "RelativePlacement") and current.RelativePlacement:
                rel_place = current.RelativePlacement
                if hasattr(rel_place, "Location") and rel_place.Location:
                    coords = rel_place.Location.Coordinates
                    location += np.array([float(coords[0]), float(coords[1]), float(coords[2])])

            # 親の配置へ
            if hasattr(current, "PlacementRelTo"):
                current = current.PlacementRelTo
            else:
                break

        return tuple(location)
    except:
        return None


def extract_local_coords_from_representation(representation):
    """IfcProductDefinitionShapeからローカル座標を抽出（座標変換用）"""
    coords = []
    try:
        for rep in representation.Representations:
            for item in rep.Items:
                # IfcExtrudedAreaSolidの場合
                if item.is_a("IfcExtrudedAreaSolid"):
                    if hasattr(item, "Position") and item.Position:
                        # Position（ローカル座標系の原点）
                        loc = item.Position.Location
                        if loc:
                            base_point = list(loc.Coordinates)
                            if len(base_point) == 2:
                                base_point.append(0.0)

                            # Axis2Placement3Dの変換を適用
                            axis = None
                            ref_dir = None
                            if hasattr(item.Position, "Axis") and item.Position.Axis:
                                axis = item.Position.Axis.DirectionRatios
                            if hasattr(item.Position, "RefDirection") and item.Position.RefDirection:
                                ref_dir = item.Position.RefDirection.DirectionRatios

                            # 押出方向と長さを考慮
                            if hasattr(item, "ExtrudedDirection") and hasattr(item, "Depth"):
                                direction = item.ExtrudedDirection.DirectionRatios
                                depth = item.Depth

                                # ローカル座標系での中心点
                                local_center = [
                                    base_point[0],
                                    base_point[1],
                                    base_point[2] + depth / 2
                                    if len(direction) > 2 and direction[2] != 0
                                    else base_point[2],
                                ]
                                coords.append(local_center)
                            else:
                                coords.append(base_point)

                # IfcSweptAreaSolidの場合
                elif item.is_a("IfcSweptAreaSolid"):
                    if hasattr(item, "Position") and item.Position:
                        loc = item.Position.Location
                        if loc:
                            coord = list(loc.Coordinates)
                            if len(coord) == 2:
                                coord.append(0.0)
                            coords.append(coord)
    except Exception as e:
        pass

    return np.array(coords) if coords else None


def extract_coords_from_representation(representation):
    """IfcProductDefinitionShapeから座標を抽出（グローバル座標として）"""
    coords = []
    try:
        for rep in representation.Representations:
            for item in rep.Items:
                # IfcFacetedBrepの場合
                if item.is_a("IfcFacetedBrep"):
                    shell = item.Outer
                    for face in shell.CfsFaces:
                        for bound in face.Bounds:
                            loop = bound.Bound
                            if hasattr(loop, "Polygon"):
                                for point in loop.Polygon:
                                    coords.append(list(point.Coordinates))

                # IfcExtrudedAreaSolidの場合
                elif item.is_a("IfcExtrudedAreaSolid"):
                    if hasattr(item, "Position") and item.Position:
                        loc = item.Position.Location
                        if loc:
                            base_point = list(loc.Coordinates)
                            if len(base_point) == 2:
                                base_point.append(0.0)
                            # 押出方向と長さを考慮して中心を計算
                            if hasattr(item, "ExtrudedDirection") and hasattr(item, "Depth"):
                                direction = item.ExtrudedDirection.DirectionRatios
                                depth = item.Depth
                                # 押出の中心点を計算
                                center = [
                                    base_point[0] + direction[0] * depth / 2 if len(direction) > 0 else base_point[0],
                                    base_point[1] + direction[1] * depth / 2 if len(direction) > 1 else base_point[1],
                                    base_point[2] + direction[2] * depth / 2 if len(direction) > 2 else base_point[2],
                                ]
                                coords.append(center)
                            else:
                                coords.append(base_point)

                # IfcSweptAreaSolidの場合
                elif item.is_a("IfcSweptAreaSolid"):
                    if hasattr(item, "Position") and item.Position:
                        loc = item.Position.Location
                        if loc:
                            coord = list(loc.Coordinates)
                            if len(coord) == 2:
                                coord.append(0.0)
                            coords.append(coord)

                # IfcPolylineの場合
                elif item.is_a("IfcPolyline"):
                    for point in item.Points:
                        coord = list(point.Coordinates)
                        if len(coord) == 2:
                            coord.append(0.0)
                        coords.append(coord)
    except Exception as e:
        print(f"  座標抽出エラー: {e}")

    return np.array(coords) if coords else None


def get_element_bounding_box(ifc_file, element_name):
    """
    IFC要素のバウンディングボックスを取得

    Returns:
        (min_point, max_point) タプル、または見つからない場合はNone
    """
    target_element = None
    for elem_type in ["IfcBeam", "IfcPlate", "IfcMember", "IfcBuildingElementProxy"]:
        try:
            elements = ifc_file.by_type(elem_type)
            for elem in elements:
                if elem.Name == element_name:
                    target_element = elem
                    break
            if target_element:
                break
        except:
            pass

    if not target_element:
        return None

    # 方法1: 形状から計算
    try:
        settings = ifcopenshell.geom.settings()
        shape = ifcopenshell.geom.create_shape(settings, target_element)

        verts = shape.geometry.verts
        if verts:
            vertices = []
            for i in range(0, len(verts), 3):
                vertices.append([verts[i], verts[i + 1], verts[i + 2]])

            vertices = np.array(vertices)
            min_point = np.min(vertices, axis=0)
            max_point = np.max(vertices, axis=0)
            return (tuple(min_point), tuple(max_point))
    except:
        pass

    # 方法2: Representationから座標を抽出
    try:
        if target_element.Representation:
            coords = extract_coords_from_representation(target_element.Representation)
            if coords is not None and len(coords) > 0:
                min_point = np.min(coords, axis=0)
                max_point = np.max(coords, axis=0)
                return (tuple(min_point), tuple(max_point))
    except:
        pass

    return None


def calculate_distance(p1, p2):
    """2点間の距離を計算"""
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    dz = p2[2] - p1[2]
    distance = math.sqrt(dx**2 + dy**2 + dz**2)
    return dx, dy, dz, distance


def load_damage_elements(damage_file):
    """damage_info.jsonから損傷要素名を取得"""
    with open(damage_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    elements = []
    for entry in data.get("DamageInformation", []):
        element_name = entry.get("ElementName", "")
        if element_name:
            # 最新の損傷レベルを取得
            inspection_history = entry.get("InspectionHistory", [])
            if inspection_history:
                latest = inspection_history[0]
                damage_items = latest.get("DamageItems", [])
                # 最も深刻な損傷レベルを取得
                levels = [item.get("DamageLevel", "") for item in damage_items]
                max_level = max(levels) if levels else ""
            else:
                # 旧形式
                damage_items = entry.get("DamageItems", [])
                levels = [item.get("DamageLevel", "") for item in damage_items]
                max_level = max(levels) if levels else ""

            elements.append({"name": element_name, "level": max_level})

    return elements


def main():
    parser = argparse.ArgumentParser(description="損傷要素間の距離を計算")
    parser.add_argument("-i", "--ifc", default="Girder.ifc", help="入力IFCファイル")
    parser.add_argument("-d", "--damage", default="damage_info.json", help="損傷情報JSONファイル")
    args = parser.parse_args()

    current_dir = os.path.dirname(os.path.abspath(__file__))

    # IFCファイルのパス
    ifc_path = args.ifc
    if not os.path.isabs(ifc_path):
        ifc_path = os.path.join(current_dir, ifc_path)

    # damage_info.jsonのパス
    damage_path = args.damage
    if not os.path.isabs(damage_path):
        damage_path = os.path.join(current_dir, damage_path)

    # ファイル存在チェック
    if not os.path.exists(ifc_path):
        print(f"エラー: IFCファイルが見つかりません: {ifc_path}")
        sys.exit(1)

    if not os.path.exists(damage_path):
        print(f"エラー: 損傷情報ファイルが見つかりません: {damage_path}")
        sys.exit(1)

    print("=" * 70)
    print("損傷要素間距離計算")
    print("=" * 70)
    print(f"IFCファイル: {os.path.basename(ifc_path)}")
    print(f"損傷情報: {os.path.basename(damage_path)}")
    print()

    # 損傷要素を読み込み
    damage_elements = load_damage_elements(damage_path)
    print(f"損傷要素数: {len(damage_elements)}")
    print()

    # IFCファイルを読み込み
    print("IFCファイルを読み込み中...")
    ifc_file = ifcopenshell.open(ifc_path)
    print(f"読み込み完了")
    print()

    # 各要素の重心を計算
    print("=" * 70)
    print("各損傷要素の位置")
    print("=" * 70)

    element_centroids = {}
    for elem in damage_elements:
        name = elem["name"]
        level = elem["level"]
        print(f"\n{name} (レベル: {level})")

        centroid = get_element_centroid(ifc_file, name)
        if centroid:
            print(f"  重心: X={centroid[0]:.1f}, Y={centroid[1]:.1f}, Z={centroid[2]:.1f} mm")
            element_centroids[name] = {"centroid": centroid, "level": level}

            # バウンディングボックスも取得
            bbox = get_element_bounding_box(ifc_file, name)
            if bbox:
                min_p, max_p = bbox
                print(
                    f"  範囲: X=[{min_p[0]:.1f}, {max_p[0]:.1f}], Y=[{min_p[1]:.1f}, {max_p[1]:.1f}], Z=[{min_p[2]:.1f}, {max_p[2]:.1f}]"
                )
        else:
            print(f"  警告: 要素が見つかりませんでした")

    # すべての組み合わせの距離を計算
    print()
    print("=" * 70)
    print("損傷要素間の距離（すべての組み合わせ）")
    print("=" * 70)

    element_names = list(element_centroids.keys())

    if len(element_names) < 2:
        print("距離を計算するには2つ以上の要素が必要です")
        return

    # 距離を計算して結果を保存
    distances = []
    for name1, name2 in combinations(element_names, 2):
        c1 = element_centroids[name1]["centroid"]
        c2 = element_centroids[name2]["centroid"]
        level1 = element_centroids[name1]["level"]
        level2 = element_centroids[name2]["level"]

        dx, dy, dz, dist = calculate_distance(c1, c2)

        distances.append(
            {
                "elem1": name1,
                "elem2": name2,
                "level1": level1,
                "level2": level2,
                "dx": dx,
                "dy": dy,
                "dz": dz,
                "distance": dist,
            }
        )

    # 距離順にソート
    distances.sort(key=lambda x: x["distance"])

    print(f"\n組み合わせ数: {len(distances)}")
    print()

    for i, d in enumerate(distances, 1):
        print(f"[{i}] {d['elem1']} ({d['level1']}) ↔ {d['elem2']} ({d['level2']})")
        print(f"    ΔX: {d['dx']:+.1f} mm")
        print(f"    ΔY: {d['dy']:+.1f} mm")
        print(f"    ΔZ: {d['dz']:+.1f} mm")
        print(f"    距離: {d['distance']:.1f} mm ({d['distance'] / 1000:.2f} m)")
        print()

    # サマリー
    print("=" * 70)
    print("サマリー")
    print("=" * 70)
    if distances:
        min_dist = min(distances, key=lambda x: x["distance"])
        max_dist = max(distances, key=lambda x: x["distance"])
        avg_dist = sum(d["distance"] for d in distances) / len(distances)

        print(f"最短距離: {min_dist['distance']:.1f} mm ({min_dist['distance'] / 1000:.2f} m)")
        print(f"  {min_dist['elem1']} ↔ {min_dist['elem2']}")
        print()
        print(f"最長距離: {max_dist['distance']:.1f} mm ({max_dist['distance'] / 1000:.2f} m)")
        print(f"  {max_dist['elem1']} ↔ {max_dist['elem2']}")
        print()
        print(f"平均距離: {avg_dist:.1f} mm ({avg_dist / 1000:.2f} m)")


if __name__ == "__main__":
    main()
