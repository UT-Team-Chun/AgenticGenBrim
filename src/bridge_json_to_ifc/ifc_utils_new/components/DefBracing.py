"""
鋼橋IFCモデル生成 - 対傾構・横構生成モジュール
対傾構（Yokokou）・横構（Taikeikou）生成関連関数
"""

# mathモジュールをインポート（math.isnan用）
import math

import numpy as np

# DefStiffener.pyの関数は循環依存を避けるため、関数内で遅延インポートします
# from src.bridge_json_to_ifc.ifc_utils_new.components.DefStiffener import Devide_Pitch_Vstiff
# DefGusset.pyの関数をインポート
from src.bridge_json_to_ifc.ifc_utils_new.components.DefGusset import Calculate_edge_Guss_Constant

# DefSlot.pyの関数をインポート
from src.bridge_json_to_ifc.ifc_utils_new.components.DefSlot import Draw_3Dsolid_Slot
from src.bridge_json_to_ifc.ifc_utils_new.core import DefIFC, DefMath
from src.bridge_json_to_ifc.ifc_utils_new.io import DefStrings

# DefBridgeUtils.pyの関数をインポート
from src.bridge_json_to_ifc.ifc_utils_new.utils.DefBridgeUtils import (
    Calculate_Extend_Coord,
    Combined_Sort_Coord_And_NameSec,
    Load_Coordinate_Panel,
    Load_Coordinate_Point,
    Load_Coordinate_PolLine,
)

# グローバル変数: ログファイル出力関数（DefBridge.pyから設定される）
log_print_func = None


def _log_print(*args, **kwargs):
    """ログファイル出力関数（DEBUG_MODE時のみ出力）"""
    if log_print_func:
        try:
            log_print_func(*args, **kwargs)
        except Exception:
            pass  # ログ出力エラーは無視


def Find_number_block_MainPanel_Have_Vstiff(Senkei_data, Data_MainPanel, Sec_SubPanel):
    """
    垂直補剛材を持つメインパネルのブロック番号を取得する（DefBracing用）

    Args:
        Senkei_data: 線形データ
        Data_MainPanel: メインパネルデータ
        Sec_SubPanel: 点名称（文字列）または断面範囲（リスト）

    Returns:
        ブロック番号（文字列）
    """
    # 循環依存を避けるため、関数内で遅延インポート
    from src.bridge_json_to_ifc.ifc_utils_new.components.DefStiffener import Devide_Pitch_Vstiff
    from src.bridge_json_to_ifc.ifc_utils_new.core import DefMath
    from src.bridge_json_to_ifc.ifc_utils_new.io import DefStrings

    stt_exit = False
    number_block = ""
    for panel in Data_MainPanel:
        Name_panel = panel["Name"]
        Line_panel = panel["Line"]
        Sec_panel = panel["Sec"]
        Vstiff_panel = panel["Vstiff"]
        arCoordLines_Mod = Load_Coordinate_Panel(Senkei_data, Line_panel, Sec_panel)
        if Vstiff_panel:
            if Vstiff_panel[0]:
                type_devide, pitch_top, pitch_bot, namepoint = Vstiff_panel[0]
                namepoint = DefStrings.Chuyen_Name_LRib_thanh_Array(namepoint)
                arCoord_Vstiff, PosVstiff = Devide_Pitch_Vstiff(arCoordLines_Mod, Vstiff_panel[0])
                arCoordLines_Mod, Sec_panel = Combined_Sort_Coord_And_NameSec(
                    arCoord_Vstiff, namepoint, arCoordLines_Mod, Sec_panel
                )

        # Sec_SubPanelが文字列の場合（点名称）、Sec_panelに含まれているかチェック
        if isinstance(Sec_SubPanel, str):
            if Sec_SubPanel in Sec_panel:
                atc = Name_panel.split("B")
                for i_2 in range(len(atc[1])):
                    if DefMath.is_number(atc[1][i_2]) == True:
                        number_block += atc[1][i_2]
                    else:
                        stt_exit = True
                        break
                if stt_exit == True:
                    break
        # Sec_SubPanelがリストの場合（断面範囲）
        else:
            if Sec_panel[0] == Sec_SubPanel[0] and Sec_panel[-1] == Sec_SubPanel[-1]:
                if Vstiff_panel:
                    atc = Name_panel.split("B")
                    for i_2 in range(len(atc[1])):
                        if DefMath.is_number(atc[1][i_2]) == True:
                            number_block += atc[1][i_2]
                        else:
                            stt_exit = True
                            break
                    if stt_exit == True:
                        break
    return number_block


# 注: Extend_Yokoketa_Face と Extend_Yokoketa_Face_FLG は DefPanel.py に移動しました
# from src.bridge_json_to_ifc.ifc_utils_new.components.DefPanel import Extend_Yokoketa_Face, Extend_Yokoketa_Face_FLG


# -----------------------------Yokokou（横構）------------------------------------------------------------
def Calculate_Yokokou(
    ifc_all, Senkei_data, MainPanel_data, SubPanel_data, Taikeiko_data, Member_data, Mem_Rib_data, infor_yokokou
):
    try:
        ifc_file, bridge_span, geom_context = ifc_all
        name_yokokou, type_yokokou, girder_yokokou, point_yokokou, shape_yokokou, guss_yokokou = infor_yokokou

        _log_print("    [Yokokou] 座標点の計算を開始")
        arCoordPoint_Yokokou = Calculate_Point_Yokokou(
            Senkei_data, MainPanel_data, type_yokokou, girder_yokokou, point_yokokou
        )

        if len(arCoordPoint_Yokokou) == 0:
            _log_print("    [Yokokou] 警告: 座標点が0個です。形状の生成をスキップします。")
            return

        _log_print("    [Yokokou] 形状の生成を開始")
        Draw_Shape_Yokokou(ifc_all, arCoordPoint_Yokokou, shape_yokokou, type_yokokou, name_yokokou, girder_yokokou)

        _log_print("    [Yokokou] ガセットの生成を開始")
        Draw_Guss_Yokokou(
            ifc_all,
            Senkei_data,
            MainPanel_data,
            SubPanel_data,
            Taikeiko_data,
            Member_data,
            Mem_Rib_data,
            arCoordPoint_Yokokou,
            infor_yokokou,
        )
    except Exception as e:
        import traceback

        _log_print(f"    [Yokokou] エラーが発生しました: {e}")
        _log_print(f"    [Yokokou] トレースバック:\n{traceback.format_exc()}")
        raise


def Calculate_Point_Yokokou(Senkei_data, MainPanel_data, type_yokokou, girder_yokokou, point_yokokou):
    # 循環依存を避けるため、関数内で遅延インポート
    try:
        from src.bridge_json_to_ifc.ifc_utils_new.components.DefStiffener import Devide_Pitch_Vstiff
    except ImportError as e:
        _log_print(f"    [Yokokou Point] 警告: DefStiffenerのインポートに失敗しました: {e}")
        # Devide_Pitch_Vstiffが使われない場合は続行

    arCoordPoint_Yokokou = []
    try:
        g1 = girder_yokokou[0].split("/")[0]
        w1 = girder_yokokou[0].split("/")[1]
        g2 = girder_yokokou[1].split("/")[0]
        w2 = girder_yokokou[1].split("/")[1]
    except (IndexError, AttributeError) as e:
        _log_print(f"    [Yokokou Point] エラー: girder_yokokouの解析に失敗しました: {girder_yokokou}, エラー: {e}")
        return arCoordPoint_Yokokou

    _log_print(f"    [Yokokou Point] 桁情報: g1={g1}, w1={w1}, g2={g2}, w2={w2}")
    _log_print(f"    [Yokokou Point] Point配列: {point_yokokou}")

    for i in range(0, len(point_yokokou), 3):
        try:
            if i + 2 >= len(point_yokokou):
                _log_print(f"    [Yokokou Point] 警告: Point配列のインデックス範囲外 (i={i}, len={len(point_yokokou)})")
                break

            name_point = point_yokokou[i]
            distz_point = point_yokokou[i + 1]
            distx_point = point_yokokou[i + 2]

            _log_print(
                f"    [Yokokou Point] 処理中: name_point={name_point}, distz={distz_point}, distx={distx_point}, i={i}"
            )

            try:
                number_block = Find_number_block_MainPanel_Have_Vstiff(Senkei_data, MainPanel_data, name_point)
                _log_print(f"    [Yokokou Point] ブロック番号: {number_block}")
            except Exception as e:
                _log_print(f"    [Yokokou Point] エラー: Find_number_block_MainPanel_Have_Vstiffでエラー: {e}")
                import traceback

                _log_print(f"    [Yokokou Point] トレースバック:\n{traceback.format_exc()}")
                continue

            name_mainpanel = None
            if type_yokokou[0] == "R" or type_yokokou[0] == "L":
                # point_yokokouの構造: [name1, distz1, distx1, name2, distz2, distx2, ...]
                # 同じ断面名の点を両方の桁から取得する必要がある
                # 例: ['S1', 0, 0, 'E1', 0, 0] → S1をg1とg2から、E1をg1とg2から取得
                point_index = i // 3  # 何番目の点か（0, 1, 2, ...）
                # 最初の点（point_index=0）はg1から、次の点（point_index=1）はg2から取得
                # その後、同じ断面名の点を交互に取得
                if point_index == 0:
                    # 最初の点はg1から取得
                    name_mainpanel = g1 + "B" + number_block + w1
                elif point_index == 1:
                    # 2番目の点はg2から取得（同じ断面名）
                    name_mainpanel = g2 + "B" + number_block + w2
                else:
                    # 3番目以降は、point_indexが偶数のときg1、奇数のときg2
                    if point_index % 2 == 0:
                        name_mainpanel = g1 + "B" + number_block + w1
                    else:
                        name_mainpanel = g2 + "B" + number_block + w2
            elif type_yokokou[0] == "CR" or type_yokokou[0] == "CL":
                if i == 0 or i == 3:
                    name_mainpanel = g1 + "B" + number_block + w1
                elif i == 6 or i == 9:
                    name_mainpanel = g2 + "B" + number_block + w2
            else:
                _log_print(f"    [Yokokou Point] 警告: Type {type_yokokou[0]} は未対応です")

            if name_mainpanel is None:
                _log_print(
                    f"    [Yokokou Point] エラー: name_mainpanelが決定できませんでした (type={type_yokokou[0]}, i={i})"
                )
                continue

            _log_print(f"    [Yokokou Point] 検索パネル名: {name_mainpanel}")

            panel_found = False
            for panel in MainPanel_data:
                if panel["Name"] == name_mainpanel:
                    panel_found = True
                    Line_mainpanel = panel["Line"]
                    Sec_mainpanel = panel["Sec"]
                    Vstiff_panel = panel["Vstiff"]
                    _log_print(
                        f"    [Yokokou Point] パネル発見: {name_mainpanel}, Line={Line_mainpanel}, Sec={Sec_mainpanel}"
                    )

                    arCoordLines_Mod = Load_Coordinate_Panel(Senkei_data, Line_mainpanel, Sec_mainpanel)
                    if Vstiff_panel:
                        if Vstiff_panel[0]:
                            type_devide, pitch_top, pitch_bot, namepoint = Vstiff_panel[0]
                            namepoint = DefStrings.Chuyen_Name_LRib_thanh_Array(namepoint)
                            arCoord_Vstiff, PosVstiff = Devide_Pitch_Vstiff(arCoordLines_Mod, Vstiff_panel[0])
                            arCoordLines_Mod, Sec_mainpanel = Combined_Sort_Coord_And_NameSec(
                                arCoord_Vstiff, namepoint, arCoordLines_Mod, Sec_mainpanel
                            )

                    if name_point not in Sec_mainpanel:
                        _log_print(
                            f"    [Yokokou Point] エラー: 点 {name_point} がSec_mainpanelに存在しません。利用可能な点: {Sec_mainpanel}"
                        )
                        break

                    idx = Sec_mainpanel.index(name_point)
                    pt = arCoordLines_Mod[0][idx]
                    pb = arCoordLines_Mod[-1][idx]

                    # Webパネルの場合、中央（高さ方向）から点を取得
                    # パネル名の最後の文字が"W"の場合はWebパネル
                    is_web_panel = name_mainpanel[-1] == "W"

                    if is_web_panel:
                        # Webパネルの中央（ptとpbの中点）を計算
                        mid_point = [(pt[0] + pb[0]) / 2, (pt[1] + pb[1]) / 2, (pt[2] + pb[2]) / 2]
                        _log_print(f"    [Yokokou Point] Webパネル検出: 中点={mid_point}")
                        # 中点からdistz_pointだけオフセット（distz_pointが0の場合は中点を使用）
                        if distz_point == 0:
                            p = mid_point
                        else:
                            # ptからpbへの方向でdistz_pointだけオフセット
                            p = DefMath.Point_on_parallel_line(mid_point, pt, pb, distz_point)
                    else:
                        # フランジパネルの場合、従来通り
                        if type_yokokou[1] == "T":
                            p = DefMath.Point_on_parallel_line(pt, pt, pb, distz_point)
                        else:
                            p = DefMath.Point_on_parallel_line(pb, pb, pt, distz_point)

                    if distx_point != 0:
                        if distx_point > 0:
                            if idx + 1 >= len(arCoordLines_Mod[0]):
                                _log_print(
                                    f"    [Yokokou Point] 警告: インデックス範囲外 (idx+1={idx + 1}, len={len(arCoordLines_Mod[0])})"
                                )
                                break
                            pt1 = arCoordLines_Mod[0][idx + 1]
                            pb1 = arCoordLines_Mod[-1][idx + 1]
                        else:
                            if idx - 1 < 0:
                                _log_print(f"    [Yokokou Point] 警告: インデックス範囲外 (idx-1={idx - 1})")
                                break
                            pt1 = arCoordLines_Mod[0][idx - 1]
                            pb1 = arCoordLines_Mod[-1][idx - 1]

                        pp = DefMath.point_per_line(p, pt1, pb1)

                        p = DefMath.Point_on_parallel_line(p, p, pp, distx_point)

                    data = {"Name": name_point, "X": p[0], "Y": p[1], "Z": p[2]}
                    _log_print(f"    [Yokokou Point] 計算完了: {name_point} = [{p[0]:.2f}, {p[1]:.2f}, {p[2]:.2f}]")

                    arCoordPoint_Yokokou.append(data)
                    break

            if not panel_found:
                _log_print(f"    [Yokokou Point] エラー: パネル {name_mainpanel} が見つかりませんでした")
        except Exception as e:
            _log_print(f"    [Yokokou Point] エラー: 点の計算中にエラーが発生しました: {e}")
            import traceback

            _log_print(f"    [Yokokou Point] トレースバック:\n{traceback.format_exc()}")
            continue

    _log_print(f"    [Yokokou Point] 計算完了: {len(arCoordPoint_Yokokou)}個の点を取得")
    return arCoordPoint_Yokokou


def Draw_Shape_Yokokou(
    ifc_all, arCoordPoint_Yokokou, shape_yokokou, type_yokokou, name_yokokou=None, girder_yokokou=None
):
    ifc_file, bridge_span, geom_context = ifc_all

    for shape in shape_yokokou:
        _log_print(f"    Shape - {shape['Name']} : Starting the export.")
        name_shape = shape["Name"]
        infor_shape = shape["Infor"]
        point_shape = shape["Point"]
        pitch_shape = shape["Pitch"]
        hole_shape = shape["Hole"]

        _log_print(f"    [Shape] point_shape: {point_shape}, 長さ: {len(point_shape)}")

        if type_yokokou[0] == "L" or type_yokokou[0] == "R":
            pbs_shape = None
            pbe_shape = None
            pplan_shape = None

            # point_shape[0]とpoint_shape[1]が同じ名前の場合、インデックスで直接取得
            if point_shape[0] == point_shape[1] and len(arCoordPoint_Yokokou) >= 2:
                # インデックス0をpbs_shape、インデックス1をpbe_shapeに割り当て
                pbs_shape = [arCoordPoint_Yokokou[0]["X"], arCoordPoint_Yokokou[0]["Y"], arCoordPoint_Yokokou[0]["Z"]]
                pbe_shape = [arCoordPoint_Yokokou[1]["X"], arCoordPoint_Yokokou[1]["Y"], arCoordPoint_Yokokou[1]["Z"]]
                _log_print(f"    [Shape] 同じ点名のため、インデックスで取得: pbs={pbs_shape}, pbe={pbe_shape}")
                # 距離を計算してログ出力
                distance = DefMath.Calculate_distance_p2p(pbs_shape, pbe_shape)
                _log_print(f"    [Shape] 横桁の距離: {distance:.2f}mm")
            else:
                # 異なる名前の場合は、名前で検索
                for point in arCoordPoint_Yokokou:
                    if point["Name"] == point_shape[0]:
                        pbs_shape = [point["X"], point["Y"], point["Z"]]
                        break
                for point in arCoordPoint_Yokokou:
                    if point["Name"] == point_shape[1]:
                        pbe_shape = [point["X"], point["Y"], point["Z"]]
                        break

            # point_shape[2]が存在する場合のみ処理
            if len(point_shape) >= 3:
                for point in arCoordPoint_Yokokou:
                    if point["Name"] == point_shape[2]:
                        pplan_shape = [point["X"], point["Y"], point["Z"]]
                        break
            else:
                # point_shapeが2点のみの場合、中間点を計算
                if pbs_shape is not None and pbe_shape is not None:
                    pplan_shape = [
                        (pbs_shape[0] + pbe_shape[0]) / 2,
                        (pbs_shape[1] + pbe_shape[1]) / 2,
                        (pbs_shape[2] + pbe_shape[2]) / 2,
                    ]
                    _log_print(f"    [Shape] point_shapeが2点のみのため、中間点を計算: {pplan_shape}")
                else:
                    _log_print("    [Shape] エラー: pbs_shapeまたはpbe_shapeがNoneです")
                    continue
        elif type_yokokou[0] == "CL" or type_yokokou[0] == "CR":
            namepoint = point_shape[0]
            if DefMath.is_number(namepoint) == True:
                index = int(namepoint) - 1
                point = arCoordPoint_Yokokou[index]

                pbs_shape = [point["X"], point["Y"], point["Z"]]
            elif namepoint == "Cross":
                pbs_shape = Calculate_Point_Cross_Yokokou(arCoordPoint_Yokokou, type_yokokou)
            else:
                print(f"Chưa khai bảo điểm {namepoint} trong hệ thông yokokou")
                pbs_shape = None

            namepoint = point_shape[1]
            if DefMath.is_number(namepoint) == True:
                index = int(namepoint) - 1
                point = arCoordPoint_Yokokou[index]
                pbe_shape = [point["X"], point["Y"], point["Z"]]
            elif namepoint == "Cross":
                pbe_shape = Calculate_Point_Cross_Yokokou(arCoordPoint_Yokokou, type_yokokou)
            else:
                print(f"Chưa khai bảo điểm {namepoint} trong hệ thông yokokou")
                pbe_shape = None

            namepoint = point_shape[2]
            if DefMath.is_number(namepoint) == True:
                index = int(namepoint) - 1
                point = arCoordPoint_Yokokou[index]
                pplan_shape = [point["X"], point["Y"], point["Z"]]
            elif namepoint == "Cross":
                pplan_shape = Calculate_Point_Cross_Yokokou(arCoordPoint_Yokokou, type_yokokou)
            else:
                print(f"Chưa khai bảo điểm {namepoint} trong hệ thông yokokou")
                pplan_shape = None
        else:
            print(f"Trường hợp type của  yokoko là : {type_yokokou[0]} chưa phát triển.")
            pbs_shape = None
            pbe_shape = None
            pplan_shape = None

        # pbs_shape, pbe_shape, pplan_shapeの検証
        if pbs_shape is None or pbe_shape is None or pplan_shape is None:
            _log_print(
                f"    [Shape] エラー: 形状点が不足しています (pbs={pbs_shape}, pbe={pbe_shape}, pplan={pplan_shape})"
            )
            continue

        _log_print(f"    [Shape] 形状点: pbs={pbs_shape}, pbe={pbe_shape}, pplan={pplan_shape}")

        result_pitch_shape = "/".join(str(x) for x in pitch_shape)

        ps_shape, pe_shape = Calculate_Pse_Shape(result_pitch_shape, pbs_shape, pbe_shape)

        # 横桁の実際の長さを計算してログ出力
        length_shape = DefMath.Calculate_distance_p2p(ps_shape, pe_shape)
        _log_print(f"    [Shape] 横桁の実際の長さ（ps-pe間）: {length_shape:.2f}mm")
        if type_yokokou[0] == "L":
            normal_shape = -1 * DefMath.Normal_vector(pbs_shape, pbe_shape, pplan_shape)
        elif type_yokokou[0] == "R":
            normal_shape = +1 * DefMath.Normal_vector(pbs_shape, pbe_shape, pplan_shape)
        else:
            normal_shape = -1 * DefMath.Normal_vector(pbs_shape, pbe_shape, pplan_shape)
            if normal_shape[2] < 0:
                normal_shape = +1 * DefMath.Normal_vector(pbs_shape, pbe_shape, pplan_shape)

        if infor_shape[0] == "CT":
            if type_yokokou[1] == "T":
                pal_shape = ps_shape + 100 * normal_shape
                pal_shape = ps_shape - 100 * DefMath.Normal_vector(ps_shape, pe_shape, pal_shape)
            else:
                pal_shape = ps_shape + 100 * normal_shape
                pal_shape = ps_shape + 100 * DefMath.Normal_vector(ps_shape, pe_shape, pal_shape)

            ar_size_shape = infor_shape[1].split("x")
            _log_print(f"    [Shape] 形状名: {infor_shape[1]}, サイズ配列: {ar_size_shape}")
            arCoor_profile = DefMath.profile2D_shapCT(infor_shape[1], [0, -float(ar_size_shape[0])])

            if arCoor_profile is None:
                _log_print(f"    [Shape] エラー: 形状名 '{infor_shape[1]}' がprofile2D_shapCTのリストに存在しません。")
                _log_print(
                    "    [Shape] 利用可能な形状: 95x152x8x8, 118x176x8x8, 119x177x9x9, 118x178x10x8, 142x200x8x8, 144x204x12x10, 165x251x10x10"
                )
                continue

            _log_print(f"    [Shape] プロファイル座標数: {len(arCoor_profile)}")
            solid_shape = DefIFC.extrude_profile_and_align(
                ifc_file,
                arCoor_profile,
                DefMath.Calculate_distance_p2p(ps_shape, pe_shape),
                ps_shape,
                pe_shape,
                pal_shape,
            )
            color_style = DefIFC.create_color(ifc_file, 70.0, 100.0, 150.0)  # スチールブルー
            styled_item = ifc_file.createIfcStyledItem(Item=solid_shape, Styles=[color_style])
            shape_representation = ifc_file.createIfcShapeRepresentation(
                ContextOfItems=geom_context,
                RepresentationIdentifier="Body",
                RepresentationType="Brep",
                Items=[solid_shape],
            )

            # 位置情報を含む名前を生成: {Name}_G{Girder1}_G{Girder2}_S{Section}
            # 名前から既存の桁情報を削除して重複を避ける
            if name_yokokou and girder_yokokou and len(girder_yokokou) >= 2 and len(point_shape) >= 2:
                try:
                    girder1_raw = girder_yokokou[0].split("/")[0] if "/" in girder_yokokou[0] else girder_yokokou[0]
                    girder2_raw = girder_yokokou[1].split("/")[0] if "/" in girder_yokokou[1] else girder_yokokou[1]
                    section_raw = (
                        point_shape[0] if point_shape[0] == point_shape[1] else point_shape[0]
                    )  # 同じセクション名を使用

                    # G1 -> 1, S1 -> 1 のように数字部分だけを抽出
                    import re

                    girder1_num = re.sub(r"^G", "", girder1_raw) if girder1_raw.startswith("G") else girder1_raw
                    girder2_num = re.sub(r"^G", "", girder2_raw) if girder2_raw.startswith("G") else girder2_raw
                    section_num = re.sub(r"^S", "", section_raw) if section_raw.startswith("S") else section_raw

                    # 名前から既存の桁情報パターンを削除（例: _G1_G2, _G1, _G2など）
                    base_name = name_yokokou
                    # _G{桁名}のパターンを削除
                    base_name = re.sub(r"_G\d+(_G\d+)?", "", base_name)
                    # 末尾の_S{セクション}も削除（既にある場合）
                    base_name = re.sub(r"_S\w+$", "", base_name)

                    shape_name = f"{base_name}_G{girder1_num}_G{girder2_num}_S{section_num}"
                except Exception as e:
                    _log_print(f"    [Shape] 警告: 名前生成エラー: {e}, 元の名前を使用: {name_shape}")
                    shape_name = name_shape
            else:
                shape_name = name_shape

            DefIFC.Add_shape_representation_in_Beam(ifc_file, bridge_span, shape_representation, shape_name)

            # -------------------Bolt（ボルト）-------------------------------------------------------------------
            hole_s, hole_e = hole_shape["S"], hole_shape["E"]
            arCoord_hole_s = Caculate_Coord_Hole_Yokokou(hole_s, [0, 0, 0], "S")
            Draw_3DSolid_Bolt_Yokokou(
                ifc_all, arCoord_hole_s, float(ar_size_shape[2]), 9, ps_shape, pe_shape, pal_shape
            )

            arCoord_hole_e = Caculate_Coord_Hole_Yokokou(hole_e, [0, 0, 0], "E")
            Draw_3DSolid_Bolt_Yokokou(
                ifc_all, arCoord_hole_e, float(ar_size_shape[2]), 9, pe_shape, ps_shape, pal_shape
            )

        _log_print(f"    Shape - {shape['Name']} : Export completed.")


def Calculate_Point_Cross_Yokokou(arCoordPoint_Yokokou, type_yokokou):
    if type_yokokou[0] == "CL":
        point = arCoordPoint_Yokokou[0]
        p1_line = [point["X"], point["Y"], point["Z"]]
        point = arCoordPoint_Yokokou[3]
        p2_line = [point["X"], point["Y"], point["Z"]]

        point = arCoordPoint_Yokokou[1]
        p1_plan = [point["X"], point["Y"], point["Z"]]
        point = arCoordPoint_Yokokou[2]
        p2_plan = [point["X"], point["Y"], point["Z"]]
        point = arCoordPoint_Yokokou[1]
        p3_plan = [point["X"], point["Y"], point["Z"]]
        p3_plan[2] += 1000

        point_cross = DefMath.Intersection_line_plane(p1_plan, p2_plan, p3_plan, p1_line, p2_line)

    elif type_yokokou[0] == "CR":
        point = arCoordPoint_Yokokou[2]
        p1_line = [point["X"], point["Y"], point["Z"]]
        point = arCoordPoint_Yokokou[1]
        p2_line = [point["X"], point["Y"], point["Z"]]

        point = arCoordPoint_Yokokou[0]
        p1_plan = [point["X"], point["Y"], point["Z"]]
        point = arCoordPoint_Yokokou[3]
        p2_plan = [point["X"], point["Y"], point["Z"]]
        point = arCoordPoint_Yokokou[0]
        p3_plan = [point["X"], point["Y"], point["Z"]]
        p3_plan[2] += 1000

        point_cross = DefMath.Intersection_line_plane(p1_plan, p2_plan, p3_plan, p1_line, p2_line)

    else:
        print(f"Đang khai báo sai Type của Yokokou : {type_yokokou[0]}")
        point_cross = None

    return point_cross


def Draw_3DSolid_Bolt_Yokokou(ifc_all, arCoord_hole, gap_cen_to_head, gap_cen_to_nut, p1_3d, p2_3d, p3_3d):
    ifc_file, bridge_span, geom_context = ifc_all

    pz = p1_3d + 100 * DefMath.Normal_vector(p1_3d, p2_3d, p3_3d)
    if pz[2] < p1_3d[2]:
        pz = p1_3d - 100 * DefMath.Normal_vector(p1_3d, p2_3d, p3_3d)

    for i in range(len(arCoord_hole)):
        for i_1 in range(len(arCoord_hole[i])):
            solid_bolt = DefIFC.Draw_Solid_Bolt(
                ifc_file, arCoord_hole[i][i_1], 26.5, gap_cen_to_head, gap_cen_to_nut, p1_3d, pz, p2_3d
            )
            shape_representation = ifc_file.createIfcShapeRepresentation(
                ContextOfItems=geom_context,
                RepresentationIdentifier="Body",
                RepresentationType="Brep",
                Items=[solid_bolt],
            )
            DefIFC.Add_shape_representation_in_Beam(ifc_file, bridge_span, shape_representation, "Bolt")


def Caculate_Coord_Hole_Yokokou(infor_hole, pointbase_hole, pos):
    d_hole, pitchX_hole, pitchY_hole = infor_hole
    pointdirX_hole = pointbase_hole.copy()
    pointdirX_hole[0] += 100
    pointdirY_hole = pointbase_hole.copy()
    pointdirY_hole[1] += 100

    arpitchX_hole = str(pitchX_hole).split("/")
    arpitchX_hole = DefStrings.process_array(arpitchX_hole)
    arpitchY_hole = str(pitchY_hole).split("/")
    arpitchY_hole = DefStrings.process_array(arpitchY_hole)
    total_pitchY = sum(arpitchY_hole)
    ps_linebH, pe_linebH = DefMath.Offset_Line(pointbase_hole[:2], pointdirX_hole[:2], total_pitchY / 2)
    arCoor_hole = []
    sumx = 0
    for i in range(len(arpitchX_hole)):
        sumx += float(arpitchX_hole[i])
        if pos == "S":
            ps_lineV, pe_lineV = DefMath.Offset_Line(pointbase_hole[:2], pointdirY_hole[:2], -sumx)
        elif pos == "E":
            ps_lineV, pe_lineV = DefMath.Offset_Line(pointbase_hole[:2], pointdirY_hole[:2], -sumx)
        arCoor_hole_Y = []
        sumy = 0
        for i_1 in range(len(arpitchY_hole) - 1):
            sumy += arpitchY_hole[i_1]
            ps_lineH, pe_lineH = DefMath.Offset_Line(ps_linebH, pe_linebH, -sumy)

            p = DefMath.Intersec_line_line(ps_lineV, pe_lineV, ps_lineH, pe_lineH)

            arCoor_hole_Y.append(p)

        arCoor_hole.append(arCoor_hole_Y)

    return arCoor_hole


def Calculate_Pse_Shape(pitchmod_shape, psmod, pemod, dirpitch="XY"):
    if dirpitch == "XY":
        import math

        pitchmod_shape_X = DefStrings.Xu_Ly_Pitch_va_Tim_X(
            pitchmod_shape, math.hypot(pemod[0] - psmod[0], pemod[1] - psmod[1])
        )
        pitchmod_shape_XY = DefStrings.Xu_Ly_Pitch_va_Tim_X(
            pitchmod_shape_X, DefMath.Calculate_distance_p2p(psmod, pemod)
        )
    else:
        pitchmod_shape_XY = DefStrings.Xu_Ly_Pitch_va_Tim_X(
            pitchmod_shape, DefMath.Calculate_distance_p2p(psmod, pemod)
        )

    arpitchmod_shape_XY = pitchmod_shape_XY.split("/")

    ps_shape = DefMath.Point_on_line(psmod, pemod, float(arpitchmod_shape_XY[0]))
    pe_shape = DefMath.Point_on_line(pemod, psmod, float(arpitchmod_shape_XY[-1]))

    return ps_shape, pe_shape


# グローバル変数（DefBridge.pyから設定される）
start_point_bridge = None
unit_vector_bridge = None


def Calculate_edge_Guss_P(MainPanel_data, Senkei_data, nameWeb_mainpanel, pbase, pplan1, pplan2):
    for panel in MainPanel_data:
        if panel["Name"] == nameWeb_mainpanel:
            Line_mainpanel = panel["Line"]
            Sec_mainpanel = panel["Sec"]
            Type_mainpanel = panel["Type"]
            Mat_mainpanel = panel["Material"]
            Expand_mainpanel = panel["Expand"]
            break
    thick1_panel, thick2_panel, mat_panel = Mat_mainpanel["Thick1"], Mat_mainpanel["Thick2"], Mat_mainpanel["Mat"]
    arCoordLines_mod = Load_Coordinate_Panel(Senkei_data, Line_mainpanel, Sec_mainpanel)
    # ------------------cut face 1-----------------------------
    arCoordLines_Out = DefMath.Offset_Face(arCoordLines_mod, -thick2_panel)
    arCoordLines_Out = Calculate_Extend_Coord(arCoordLines_Out, 5, "L")
    arCoordLines_Out = Calculate_Extend_Coord(arCoordLines_Out, 5, "R")
    arCoordLines_Out_1 = arCoordLines_Out[0]
    for i_1 in range(len(arCoordLines_Out_1) - 1):
        ps_line = arCoordLines_Out_1[i_1]
        ps_line[2] = 0
        pe_line = arCoordLines_Out_1[i_1 + 1]
        pe_line[2] = 0
        pbase2d = pbase.copy()
        pbase2d[2] = 0
        p1 = DefMath.point_per_line(pbase2d, ps_line, pe_line)
        if DefMath.is_point_on_line(p1, ps_line, pe_line) == True:
            break
    # ------------------cut face 2-----------------------------
    arCoordLines_Out = DefMath.Offset_Face(arCoordLines_mod, thick1_panel)
    arCoordLines_Out = Calculate_Extend_Coord(arCoordLines_Out, 5, "L")
    arCoordLines_Out = Calculate_Extend_Coord(arCoordLines_Out, 5, "R")
    arCoordLines_Out_1 = arCoordLines_Out[0]
    for i_1 in range(len(arCoordLines_Out_1) - 1):
        ps_line = arCoordLines_Out_1[i_1]
        ps_line[2] = 0
        pe_line = arCoordLines_Out_1[i_1 + 1]
        pe_line[2] = 0
        pbase2d = pbase.copy()
        pbase2d[2] = 0
        p2 = DefMath.point_per_line(pbase2d, ps_line, pe_line)
        if DefMath.is_point_on_line(p2, ps_line, pe_line) == True:
            break

    pbase2d = pbase.copy()
    pbase2d[2] = 0
    if DefMath.Calculate_distance_p2p(pbase2d, p1) < DefMath.Calculate_distance_p2p(pbase2d, p2):
        p = p1
    else:
        p = p2
    pp = p.copy()
    pp[2] = 1000
    resut = DefMath.Intersection_line_plane(pbase, pplan1, pplan2, p, pp)

    return resut


def Calculate_PointMod_Guss_follow_Yokokou(shape_yokokou, arCoordPoint_Yokokou, namepoint_guss, distedge_face, pos):
    for shape in shape_yokokou:
        name_shape = shape["Name"]
        infor_shape = shape["Infor"]
        point_shape = shape["Point"]
        pitch_shape = shape["Pitch"]
        hole_shape = shape["Hole"]
        hole_s, hole_e = hole_shape["S"], hole_shape["E"]
        ar_size_shape = infor_shape[1].split("x")

        for point in arCoordPoint_Yokokou:
            if point["Name"] == point_shape[0]:
                pbs_shape = [point["X"], point["Y"], point["Z"]]
                break
        for point in arCoordPoint_Yokokou:
            if point["Name"] == point_shape[1]:
                pbe_shape = [point["X"], point["Y"], point["Z"]]
                break
        for point in arCoordPoint_Yokokou:
            if point["Name"] == point_shape[2]:
                pplan_shape = [point["X"], point["Y"], point["Z"]]
                break
        result_pitch_shape = "/".join(str(x) for x in pitch_shape)
        ps_shape, pe_shape = Calculate_Pse_Shape(result_pitch_shape, pbs_shape, pbe_shape)

        if pos == "S":
            if point_shape[0] == namepoint_guss:
                if (
                    distedge_face.startswith("O")
                    or distedge_face.startswith("A")
                    or distedge_face.startswith("F")
                    or distedge_face.startswith("B")
                    or distedge_face.startswith("C")
                ):
                    numberoffset = float(distedge_face[1:])
                    if hole_s:
                        d_hole, pitchX_hole, pitchY_hole = hole_s
                        arpitchX_hole = str(pitchX_hole).split("/")
                        arpitchX_hole = DefStrings.process_array(arpitchX_hole)
                        numberoffset += sum(arpitchX_hole)
                    ps_shape = DefMath.Point_on_parallel_line(ps_shape, ps_shape, pe_shape, numberoffset)
                preturn = ps_shape
                break
        elif pos == "E":
            if point_shape[1] == namepoint_guss:
                if (
                    distedge_face.startswith("O")
                    or distedge_face.startswith("A")
                    or distedge_face.startswith("F")
                    or distedge_face.startswith("B")
                    or distedge_face.startswith("C")
                ):
                    numberoffset = float(distedge_face[1:])
                    if hole_e:
                        d_hole, pitchX_hole, pitchY_hole = hole_e
                        arpitchX_hole = str(pitchX_hole).split("/")
                        arpitchX_hole = DefStrings.process_array(arpitchX_hole)
                        numberoffset += sum(arpitchX_hole)
                    pe_shape = DefMath.Point_on_parallel_line(pe_shape, pe_shape, ps_shape, numberoffset)
                preturn = pe_shape
                break

    return preturn


def Calculate_Face_Guss_follow_Yokokou(
    shape_yokokou, arCoordPoint_Yokokou, type_yokokou, namepoint_guss, distedge_face, p1_fb, p2_fb, pos
):
    for shape in shape_yokokou:
        name_shape = shape["Name"]
        infor_shape = shape["Infor"]
        point_shape = shape["Point"]
        pitch_shape = shape["Pitch"]
        hole_shape = shape["Hole"]
        hole_s, hole_e = hole_shape["S"], hole_shape["E"]
        ar_size_shape = infor_shape[1].split("x")
        bc = float(ar_size_shape[1]) / 2

        if type_yokokou[0] == "L" or type_yokokou[0] == "R":
            for point in arCoordPoint_Yokokou:
                if point["Name"] == point_shape[0]:
                    pbs_shape = [point["X"], point["Y"], point["Z"]]
                    break
            for point in arCoordPoint_Yokokou:
                if point["Name"] == point_shape[1]:
                    pbe_shape = [point["X"], point["Y"], point["Z"]]
                    break
            for point in arCoordPoint_Yokokou:
                if point["Name"] == point_shape[2]:
                    pplan_shape = [point["X"], point["Y"], point["Z"]]
                    break
        elif type_yokokou[0] == "CL" or type_yokokou[0] == "CR":
            namepoint = point_shape[0]
            if DefMath.is_number(namepoint) == True:
                index = int(namepoint) - 1
                point = arCoordPoint_Yokokou[index]

                pbs_shape = [point["X"], point["Y"], point["Z"]]
            elif namepoint == "Cross":
                pbs_shape = Calculate_Point_Cross_Yokokou(arCoordPoint_Yokokou, type_yokokou)
            else:
                print(f"Chưa khai bảo điểm {namepoint} trong hệ thông yokokou")
                pbs_shape = None

            namepoint = point_shape[1]
            if DefMath.is_number(namepoint) == True:
                index = int(namepoint) - 1
                point = arCoordPoint_Yokokou[index]
                pbe_shape = [point["X"], point["Y"], point["Z"]]
            elif namepoint == "Cross":
                pbe_shape = Calculate_Point_Cross_Yokokou(arCoordPoint_Yokokou, type_yokokou)
            else:
                print(f"Chưa khai bảo điểm {namepoint} trong hệ thông yokokou")
                pbe_shape = None

            namepoint = point_shape[2]
            if DefMath.is_number(namepoint) == True:
                index = int(namepoint) - 1
                point = arCoordPoint_Yokokou[index]
                pplan_shape = [point["X"], point["Y"], point["Z"]]
            elif namepoint == "Cross":
                pplan_shape = Calculate_Point_Cross_Yokokou(arCoordPoint_Yokokou, type_yokokou)
            else:
                print(f"Chưa khai bảo điểm {namepoint} trong hệ thông yokokou")
                pplan_shape = None
        else:
            print(f"Trường hợp type của  yokoko là : {type_yokokou[0]} chưa phát triển.")
            pbs_shape = None
            pbe_shape = None
            pplan_shape = None

        result_pitch_shape = "/".join(str(x) for x in pitch_shape)
        ps_shape, pe_shape = Calculate_Pse_Shape(result_pitch_shape, pbs_shape, pbe_shape)

        if pos == "S":
            if point_shape[0] == namepoint_guss:
                if (
                    distedge_face.startswith("O")
                    or distedge_face.startswith("A")
                    or distedge_face.startswith("F")
                    or distedge_face.startswith("B")
                    or distedge_face.startswith("C")
                ):
                    numberoffset = float(distedge_face[1:])
                    if hole_s:
                        d_hole, pitchX_hole, pitchY_hole = hole_s
                        arpitchX_hole = str(pitchX_hole).split("/")
                        arpitchX_hole = DefStrings.process_array(arpitchX_hole)
                        numberoffset += sum(arpitchX_hole)
                    ps_shape = DefMath.Point_on_parallel_line(ps_shape, ps_shape, pe_shape, numberoffset)
                pp_shape = ps_shape + 100 * DefMath.Normal_vector(p1_fb, p2_fb, ps_shape)
                if pp_shape[2] < ps_shape[2]:
                    pp_shape = ps_shape - 100 * DefMath.Normal_vector(p1_fb, p2_fb, ps_shape)

                normal_shape = DefMath.Normal_vector(ps_shape, pe_shape, pp_shape)
                pT_fn = ps_shape + bc * normal_shape
                pS_fn = ps_shape - bc * normal_shape
                if start_point_bridge is not None and unit_vector_bridge is not None:
                    if np.dot(pT_fn - start_point_bridge, unit_vector_bridge) > np.dot(
                        ps_shape - start_point_bridge, unit_vector_bridge
                    ):
                        pT_fn = ps_shape - bc * normal_shape
                        pS_fn = ps_shape + bc * normal_shape

                break
        elif pos == "E":
            if point_shape[1] == namepoint_guss:
                if (
                    distedge_face.startswith("O")
                    or distedge_face.startswith("A")
                    or distedge_face.startswith("F")
                    or distedge_face.startswith("B")
                    or distedge_face.startswith("C")
                ):
                    numberoffset = float(distedge_face[1:])
                    if hole_e:
                        d_hole, pitchX_hole, pitchY_hole = hole_e
                        arpitchX_hole = str(pitchX_hole).split("/")
                        arpitchX_hole = DefStrings.process_array(arpitchX_hole)
                        numberoffset += sum(arpitchX_hole)
                    pe_shape = DefMath.Point_on_parallel_line(pe_shape, pe_shape, ps_shape, numberoffset)
                pp_shape = pe_shape + 100 * DefMath.Normal_vector(p1_fb, p2_fb, pe_shape)
                if pp_shape[2] < pe_shape[2]:
                    pp_shape = pe_shape - 100 * DefMath.Normal_vector(p1_fb, p2_fb, pe_shape)
                normal_shape = DefMath.Normal_vector(ps_shape, pe_shape, pp_shape)
                pT_fn = pe_shape + bc * normal_shape
                pS_fn = pe_shape - bc * normal_shape
                if start_point_bridge is not None and unit_vector_bridge is not None:
                    if np.dot(pT_fn - start_point_bridge, unit_vector_bridge) > np.dot(
                        pe_shape - start_point_bridge, unit_vector_bridge
                    ):
                        pT_fn = pe_shape - bc * normal_shape
                        pS_fn = pe_shape + bc * normal_shape
                break

    return pT_fn, pS_fn


def Calculate_Point_Vstiff_Taikeikou(width_vstiff, pb1_tai, pb2_tai, pb3_tai, pb4_tai, pos="R"):
    if pos == "L":
        p1mod_vs = pb1_tai.copy()
        p2mod_vs = pb4_tai.copy()

        p1_2d = pb1_tai.copy()
        p1_2d[2] = 0
        p2_2d = pb2_tai.copy()
        p2_2d[2] = 0
        distance = float(width_vstiff)
        p = DefMath.Point_on_line(p1_2d, p2_2d, distance)
        ppl1 = p.copy()
        ppl2 = p.copy()
        ppl2[0] += 100
        ppl3 = p.copy()
        ppl3[2] += 100
        p1modw_vs = DefMath.Intersection_line_plane(ppl1, ppl2, ppl3, pb1_tai, pb2_tai)

        p1_2d = pb4_tai.copy()
        p1_2d[2] = 0
        p2_2d = pb3_tai.copy()
        p2_2d[2] = 0
        distance = float(width_vstiff)
        p = DefMath.Point_on_line(p1_2d, p2_2d, distance)
        ppl1 = p.copy()
        ppl2 = p.copy()
        ppl2[0] += 100
        ppl3 = p.copy()
        ppl3[2] += 100
        p2modw_vs = DefMath.Intersection_line_plane(ppl1, ppl2, ppl3, pb4_tai, pb3_tai)

        p1mod_vs = DefMath.Point_on_line(p1mod_vs, p2mod_vs, -100)
        p1modw_vs = DefMath.Point_on_line(p1modw_vs, p2modw_vs, -100)
        p2mod_vs = DefMath.Point_on_line(p2mod_vs, p1mod_vs, -100)
        p2modw_vs = DefMath.Point_on_line(p2modw_vs, p1modw_vs, -100)

        arCoord_Top = [p1modw_vs, p1mod_vs]
        arCoord_Bot = [p2mod_vs, p2modw_vs]
        arCoord_Left = [p1mod_vs, p2mod_vs]
        arCoord_Right = [p2modw_vs, p1modw_vs]

    else:  # "R"
        p1mod_vs = pb2_tai.copy()
        p2mod_vs = pb3_tai.copy()
        p1_2d = pb2_tai.copy()
        p1_2d[2] = 0
        p2_2d = pb1_tai.copy()
        p2_2d[2] = 0
        distance = float(width_vstiff)
        p = DefMath.Point_on_line(p1_2d, p2_2d, distance)
        ppl1 = p.copy()
        ppl2 = p.copy()
        ppl2[0] += 100
        ppl3 = p.copy()
        ppl3[2] += 100
        p1modw_vs = DefMath.Intersection_line_plane(ppl1, ppl2, ppl3, pb1_tai, pb2_tai)

        p1_2d = pb3_tai.copy()
        p1_2d[2] = 0
        p2_2d = pb4_tai.copy()
        p2_2d[2] = 0
        distance = float(width_vstiff)
        p = DefMath.Point_on_line(p1_2d, p2_2d, distance)
        ppl1 = p.copy()
        ppl2 = p.copy()
        ppl2[0] += 100
        ppl3 = p.copy()
        ppl3[2] += 100
        p2modw_vs = DefMath.Intersection_line_plane(ppl1, ppl2, ppl3, pb4_tai, pb3_tai)

        p1mod_vs = DefMath.Point_on_line(p1mod_vs, p2mod_vs, -100)
        p1modw_vs = DefMath.Point_on_line(p1modw_vs, p2modw_vs, -100)
        p2mod_vs = DefMath.Point_on_line(p2mod_vs, p1mod_vs, -100)
        p2modw_vs = DefMath.Point_on_line(p2modw_vs, p1modw_vs, -100)

        arCoord_Top = [p1mod_vs, p1modw_vs]
        arCoord_Bot = [p2modw_vs, p2mod_vs]
        arCoord_Left = [p1modw_vs, p2modw_vs]
        arCoord_Right = [p2mod_vs, p1mod_vs]

    return arCoord_Top, arCoord_Bot, arCoord_Left, arCoord_Right


def Calculate_Face_Base_Guss_follow_Yokokou(
    shape_yokokou, arCoordPoint_Yokokou, type_yokokou, coordpoint_guss, distedge_face
):
    psL_shape = psR_shape = peL_shape = peR_shape = None

    for shape in shape_yokokou:
        name_shape = shape["Name"]
        infor_shape = shape["Infor"]
        point_shape = shape["Point"]
        pitch_shape = shape["Pitch"]
        hole_shape = shape["Hole"]
        hole_s, hole_e = hole_shape["S"], hole_shape["E"]
        ar_size_shape = infor_shape[1].split("x")
        bc = float(ar_size_shape[1]) / 2

        def get_point_by_name(name):
            for point in arCoordPoint_Yokokou:
                if point["Name"] == name:
                    return [point["X"], point["Y"], point["Z"]]
            print(f"⚠️ Không tìm thấy điểm: {name}")
            return None

        def get_point_by_index_or_cross(namepoint):
            if DefMath.is_number(namepoint):
                index = int(namepoint) - 1
                if 0 <= index < len(arCoordPoint_Yokokou):
                    point = arCoordPoint_Yokokou[index]
                    return [point["X"], point["Y"], point["Z"]]
                else:
                    print(f"⚠️ Index {index} vượt quá giới hạn danh sách.")
            elif namepoint == "Cross":
                return Calculate_Point_Cross_Yokokou(arCoordPoint_Yokokou, type_yokokou)
            else:
                print(f"⚠️ Không rõ điểm {namepoint} trong hệ thống yokokou.")
            return None

        if type_yokokou[0] == "L" or type_yokokou[0] == "R":
            pbs_shape = get_point_by_name(point_shape[0])
            pbe_shape = get_point_by_name(point_shape[1])
            pplan_shape = get_point_by_name(point_shape[2])
        elif type_yokokou[0] == "CL" or type_yokokou[0] == "CR":
            pbs_shape = get_point_by_index_or_cross(point_shape[0])
            pbe_shape = get_point_by_index_or_cross(point_shape[1])
            pplan_shape = get_point_by_index_or_cross(point_shape[2])
        else:
            print(f"⚠️ Type yokokou [{type_yokokou[0]}] chưa được hỗ trợ.")
            pbs_shape = None
            pbe_shape = None
            pplan_shape = None
            continue

        result_pitch_shape = "/".join(str(x) for x in pitch_shape)
        ps_shape, pe_shape = Calculate_Pse_Shape(result_pitch_shape, pbs_shape, pbe_shape)
        if start_point_bridge is not None and unit_vector_bridge is not None:
            if np.dot(ps_shape - start_point_bridge, unit_vector_bridge) > np.dot(
                pe_shape - start_point_bridge, unit_vector_bridge
            ):
                pe_shape, ps_shape = Calculate_Pse_Shape(result_pitch_shape, pbs_shape, pbe_shape)

        if type_yokokou[0] == "CL":
            if (point_shape[0] == 3 and point_shape[1] == 2) or (point_shape[0] == 2 and point_shape[1] == 3):
                if (
                    distedge_face.startswith("O")
                    or distedge_face.startswith("A")
                    or distedge_face.startswith("F")
                    or distedge_face.startswith("B")
                    or distedge_face.startswith("C")
                ):
                    numberoffset = float(distedge_face[1:])
                    ps_shape = DefMath.Point_on_parallel_line(coordpoint_guss, pe_shape, ps_shape, numberoffset)
                    pe_shape = DefMath.Point_on_parallel_line(coordpoint_guss, ps_shape, pe_shape, numberoffset)

                normal_shape = -1 * DefMath.Normal_vector(pbs_shape, pbe_shape, pplan_shape)
                if normal_shape[2] < 0:
                    normal_shape = +1 * DefMath.Normal_vector(pbs_shape, pbe_shape, pplan_shape)

                pp_shape = ps_shape + 100 * normal_shape
                normal_shape = +1 * DefMath.Normal_vector(ps_shape, pe_shape, pp_shape)

                psL_shape = ps_shape - bc * normal_shape
                psR_shape = ps_shape + bc * normal_shape

                peL_shape = pe_shape - bc * normal_shape
                peR_shape = pe_shape + bc * normal_shape

                break
        elif type_yokokou[0] == "CR":
            if (point_shape[0] == 1 and point_shape[1] == 4) or (point_shape[0] == 4 and point_shape[1] == 1):
                if (
                    distedge_face.startswith("O")
                    or distedge_face.startswith("A")
                    or distedge_face.startswith("F")
                    or distedge_face.startswith("B")
                    or distedge_face.startswith("C")
                ):
                    numberoffset = float(distedge_face[1:])

                    ps_shape = DefMath.Point_on_parallel_line(coordpoint_guss, pe_shape, ps_shape, numberoffset)
                    pe_shape = DefMath.Point_on_parallel_line(coordpoint_guss, ps_shape, pe_shape, numberoffset)

                normal_shape = -1 * DefMath.Normal_vector(pbs_shape, pbe_shape, pplan_shape)
                if normal_shape[2] < 0:
                    normal_shape = +1 * DefMath.Normal_vector(pbs_shape, pbe_shape, pplan_shape)

                pp_shape = ps_shape + 100 * normal_shape
                normal_shape = +1 * DefMath.Normal_vector(ps_shape, pe_shape, pp_shape)

                psR_shape = ps_shape - bc * normal_shape
                psL_shape = ps_shape + bc * normal_shape

                peR_shape = pe_shape - bc * normal_shape
                peL_shape = pe_shape + bc * normal_shape

                break

    return psL_shape, psR_shape, peL_shape, peR_shape


def Draw_3DSlot_For_Guss_Yokokou(
    ifc_all,
    Senkei_data,
    MainPanel_data,
    Member_data,
    Mem_Rib_data,
    Taikeiko_data,
    name_slot,
    namepoint_guss,
    typefacefollow,
    nameWeb_mainpanel,
    pos,
    p1_guss,
    p2_guss,
    p3_guss,
):
    # 循環依存を避けるため、関数内で遅延インポート
    from src.bridge_json_to_ifc.ifc_utils_new.components.DefStiffener import Devide_Pitch_Vstiff

    ifc_file, bridge_span, geom_context = ifc_all

    solid_slot = None
    if typefacefollow == "TK":
        for taikeikou in Taikeiko_data:
            if taikeikou["Name"] == namepoint_guss:
                # ----------Infor Taikeikou------------------------------------------------------------
                name_taikeikou = taikeikou["Name"]
                type_taikeikou = taikeikou["Type"]
                girder_taikeikou = taikeikou["Girder"]
                point_taikeikou = taikeikou["Point"]
                distmod_taikeikou = taikeikou["Distmod"]
                hole_taikeikou = taikeikou["Hole"]
                vstiff_taikeikou = taikeikou["Vstiff"]
                shape_taikeikou = taikeikou["Shape"]
                guss_taikeikou = taikeikou["Guss"]
                infor_Taikeikou = (
                    name_taikeikou,
                    type_taikeikou,
                    girder_taikeikou,
                    point_taikeikou,
                    distmod_taikeikou,
                    hole_taikeikou,
                    vstiff_taikeikou,
                    shape_taikeikou,
                    guss_taikeikou,
                )
                if vstiff_taikeikou:
                    vstiff_left, vstiff_right = vstiff_taikeikou["L"], vstiff_taikeikou["R"]
                    if pos == "L":
                        if vstiff_left:
                            thick_vstiff, mat_vstiff, width_vstiff = vstiff_left
                            solid_slot = Draw_3DSlot_follow_Stiff_Taikeikou_For_Guss(
                                ifc_all,
                                Senkei_data,
                                Member_data,
                                infor_Taikeikou,
                                name_slot,
                                pos,
                                p1_guss,
                                p2_guss,
                                p3_guss,
                            )
                    elif pos == "R":
                        if vstiff_right:
                            thick_vstiff, mat_vstiff, width_vstiff = vstiff_right
                            solid_slot = Draw_3DSlot_follow_Stiff_Taikeikou_For_Guss(
                                ifc_all,
                                Senkei_data,
                                Member_data,
                                infor_Taikeikou,
                                name_slot,
                                pos,
                                p1_guss,
                                p2_guss,
                                p3_guss,
                            )
    else:
        stt = False
        for panel in MainPanel_data:
            if panel["Name"] == nameWeb_mainpanel:
                # -----------------------パネル情報------------------------------------------------------------
                Name_panel = panel["Name"]
                Line_panel = panel["Line"]
                Sec_panel = panel["Sec"]
                Type_panel = panel["Type"]
                Mat_panel = panel["Material"]
                Expand_panel = panel["Expand"]
                Jbut_panel = panel["Jbut"]
                Corner_panel = panel["Corner"]
                Lrib_panel = panel["Lrib"]
                Vstiff_panel = panel["Vstiff"]
                Hstiff_panel = panel["Hstiff"]
                Atm_panel = panel["Atm"]
                Cutout_panel = panel["Cutout"]
                Stud_panel = panel["Stud"]
                arCoordLines_Mod = Load_Coordinate_Panel(Senkei_data, Line_panel, Sec_panel)
                Thick1, Thick2, Mat = Mat_panel["Thick1"], Mat_panel["Thick2"], Mat_panel["Mat"]
                if Vstiff_panel:
                    if Vstiff_panel[0]:
                        type_devide, pitch_top, pitch_bot, namepoint = Vstiff_panel[0]
                        namepoint = DefStrings.Chuyen_Name_LRib_thanh_Array(namepoint)
                        arCoord_Vstiff, PosVstiff = Devide_Pitch_Vstiff(arCoordLines_Mod, Vstiff_panel[0])
                        arCoordLines_Mod_new, sec_panel_new = Combined_Sort_Coord_And_NameSec(
                            arCoord_Vstiff, namepoint, arCoordLines_Mod, Sec_panel
                        )
                    else:
                        arCoordLines_Mod_new = arCoordLines_Mod
                        sec_panel_new = Sec_panel
                    solid_slot = None
                    for i_1 in range(1, len(Vstiff_panel)):
                        solid_slot = Draw_3DSlot_follow_VStiff_MainPanel_For_Guss(
                            ifc_all,
                            Mem_Rib_data,
                            Member_data,
                            Vstiff_panel[i_1],
                            arCoordLines_Mod_new,
                            sec_panel_new,
                            Thick1,
                            Thick2,
                            name_slot,
                            pos,
                            p1_guss,
                            p2_guss,
                            p3_guss,
                        )
                        if solid_slot is not None:
                            stt = True
                            break

                if stt == True:
                    break

    return solid_slot


def Draw_3DSlot_follow_VStiff_MainPanel_For_Guss(
    ifc_all,
    Mem_Rib_data,
    Member_data,
    infor_vstiff,
    arCoord_mod_panel,
    sec_panel,
    thick1_panel,
    thick2_panel,
    name_slot,
    pos,
    p1_guss,
    p2_guss,
    p3_guss,
):
    if pos == "L":
        pos = "R"
    else:
        pos = "L"

    solid_slot_original = None
    ifc_file, bridge_span, geom_context = ifc_all

    name_point_line_vstiff, name_point_sec_vstiff, face_vstiff, name_vstiff, name_ref_vstiff = (
        infor_vstiff["Line"],
        infor_vstiff["Point"],
        infor_vstiff["Face"],
        infor_vstiff["Name"],
        infor_vstiff["Ref"],
    )
    name_point_line_vstiff = DefStrings.Chuyen_Name_LRib_thanh_Array(name_point_line_vstiff)
    name_vstiff = DefStrings.Chuyen_Name_LRib_thanh_Array(name_vstiff)
    arface_vstiff = []
    if face_vstiff == "ALL":
        arface_vstiff = ["L", "R"]
    else:
        arface_vstiff = [face_vstiff]

    # --------参照リブ----------------------------------------
    for rib in Mem_Rib_data:
        if rib["Name"] == name_ref_vstiff:
            infor = rib["Infor"]
            ang = rib["Ang"]
            extend = rib["Extend"]
            corner = rib["Corner"]
            spl_s = rib["JointS"]
            spl_e = rib["JointE"]
            break

    thick1_rib, thick2_rib, mat_rib, height_rib = infor["Thick1"], infor["Thick2"], infor["Mat"], infor["Width"]
    angs_rib, ange_rib, anga_rib = ang
    extendT_rib, extendB_rib, extendL_rib, extendR_rib = extend
    corner1, corner2, corner3, corner4 = corner
    # --------------------------------------------------------------
    for i in range(len(name_point_line_vstiff)):
        for side in arface_vstiff:
            if side == pos:
                if side == "L":
                    arCoord_Base_Offset = DefMath.Offset_Face(arCoord_mod_panel, -thick1_panel)
                elif side == "R":
                    arCoord_Base_Offset = DefMath.Offset_Face(arCoord_mod_panel, thick2_panel)

                index = sec_panel.index(name_point_line_vstiff[i])
                P1Mod = arCoord_Base_Offset[0][index]
                P2Mod = arCoord_Base_Offset[-1][index]

                p1al = P2Mod.copy()
                if side == "L":
                    p3al = DefMath.Offset_point(P2Mod, P1Mod, arCoord_Base_Offset[0][index - 1], -100)
                    p2al = DefMath.Offset_point(P2Mod, P1Mod, p3al, -100)

                    P3Mod = DefMath.Offset_point(P1Mod, P2Mod, arCoord_Base_Offset[0][index - 1], height_rib)
                    P4Mod = DefMath.Offset_point(P2Mod, P1Mod, arCoord_Base_Offset[0][index - 1], -height_rib)
                elif side == "R":
                    p3al = DefMath.Offset_point(P2Mod, P1Mod, arCoord_Base_Offset[0][index - 1], 100)
                    p2al = DefMath.Offset_point(P2Mod, P1Mod, p3al, -100)

                    P3Mod = DefMath.Offset_point(P1Mod, P2Mod, arCoord_Base_Offset[0][index - 1], -height_rib)
                    P4Mod = DefMath.Offset_point(P2Mod, P1Mod, arCoord_Base_Offset[0][index - 1], height_rib)

                p1_slot = None
                p1_slot = DefMath.Intersection_line_plane(p1_guss, p2_guss, p3_guss, P1Mod, P2Mod)
                p2_slot = None
                p2_slot = DefMath.Intersection_line_plane(p1_guss, p2_guss, p3_guss, P3Mod, P4Mod)

                if p1_slot is not None and p2_slot is not None:
                    pal1_slot = p1_slot.copy()
                    normal_p1p2p3 = DefMath.Normal_vector(p1_guss, p2_guss, p3_guss)

                    if side == "L":
                        pal2_slot = p1_slot - 100 * normal_p1p2p3
                    elif side == "R":
                        pal2_slot = p1_slot + 100 * normal_p1p2p3

                    pal3_slot = DefMath.rotate_point_around_axis(p1_slot, pal2_slot, p2_slot, 90)
                    # --------参照スロット----------------------------------------
                    for slot in Member_data:
                        if slot["Name"] == name_slot:
                            infor_slot = slot["Infor"]
                            wides_slot = slot["Wide"]
                            radius_slot = slot["Radius"]
                            break
                    type_slot = infor_slot[0]
                    wideL_slot = wides_slot[0]
                    wideR_slot = wides_slot[1]
                    r_slot = radius_slot[0]

                    solid_slot = Draw_3Dsolid_Slot(
                        ifc_file, p1_slot, p2_slot, wideL_slot, wideR_slot, r_slot, pal1_slot, pal2_slot, pal3_slot
                    )

                    if solid_slot_original is not None:
                        if solid_slot is not None:
                            solid_slot_original = ifc_file.createIfcBooleanResult(
                                "UNION", solid_slot_original, solid_slot
                            )
                    else:
                        if solid_slot is not None:
                            solid_slot_original = solid_slot

    return solid_slot_original


def Draw_Guss_Yokokou(
    ifc_all,
    Senkei_data,
    MainPanel_data,
    SubPanel_data,
    Taikeiko_data,
    Member_data,
    Mem_Rib_data,
    arCoordPoint_Yokokou,
    infor_yokokou,
):
    ifc_file, bridge_span, geom_context = ifc_all
    name_yokokou, type_yokokou, girder_yokokou, point_yokokou, shape_yokokou, guss_yokokou = infor_yokokou
    g1 = girder_yokokou[0].split("/")[0]
    w1 = girder_yokokou[0].split("/")[1]
    g2 = girder_yokokou[1].split("/")[0]
    w2 = girder_yokokou[1].split("/")[1]
    girder_guss = [g1, g2]
    for guss in guss_yokokou:
        print(f"    Guss - {guss['Name']} : Starting the export.")
        name_guss = guss["Name"]
        infor_guss = guss["Infor"]
        point_guss = guss["Point"]
        face_guss = guss["Face"]
        Edge_guss = guss["Edge"]
        KL_guss = guss["KL"]
        slot = guss["Slot"]

        if DefMath.is_number(point_guss) == True:
            index = int(point_guss) - 1
            name_sec = point_yokokou[index * 3]
            point = arCoordPoint_Yokokou[index]
            pb_guss = [point["X"], point["Y"], point["Z"]]
            number_block = Find_number_block_MainPanel_Have_Vstiff(Senkei_data, MainPanel_data, name_sec)
            if index == 0 or index == 1:
                nameWeb_mainpanel = g1 + "B" + number_block + w1
            elif index == 2 or index == 3:
                nameWeb_mainpanel = g2 + "B" + number_block + w2

        elif point_guss == "Cross":
            name_sec = point_guss
            nameWeb_mainpanel = ""
            if type_yokokou[0] == "CL":
                pb_guss = Calculate_Point_Cross_Yokokou(arCoordPoint_Yokokou, ["CR", "B"])
            else:
                pb_guss = Calculate_Point_Cross_Yokokou(arCoordPoint_Yokokou, ["CL", "B"])

        else:
            name_sec = point_guss
            for index, point in enumerate(arCoordPoint_Yokokou):
                number_block = Find_number_block_MainPanel_Have_Vstiff(Senkei_data, MainPanel_data, point_guss)
                if point["Name"] == point_guss:
                    pb_guss = [point["X"], point["Y"], point["Z"]]
                    if type_yokokou[0] == "R" or type_yokokou[0] == "L":
                        if index % 2 == 0:
                            if type_yokokou[0] == "R":
                                nameWeb_mainpanel = g1 + "B" + number_block + w1
                            else:
                                nameWeb_mainpanel = g2 + "B" + number_block + w2
                        else:
                            if type_yokokou[0] == "R":
                                nameWeb_mainpanel = g2 + "B" + number_block + w2
                            else:
                                nameWeb_mainpanel = g1 + "B" + number_block + w1
                    break

        arCoord_Face_Guss = []
        if KL_guss:
            # ---------------face base guss-------------------
            if not all(math.isnan(x) for x in KL_guss):
                index_faceKL = (int(KL_guss[0]) - 1) * 2
                distKL1_face = float(KL_guss[1])
                distKL2_face = float(KL_guss[2])

                typefacefollow = face_guss[index_faceKL]
                distedge_fb = face_guss[index_faceKL + 1]
                if typefacefollow == "TK":
                    # TODO: Calculate_Face_Base_Guss_follow_Taikeikouを追加する必要があります
                    p1T_fb, p1S_fb, p2T_fb, p2S_fb = Calculate_Face_Base_Guss_follow_Taikeikou(
                        Senkei_data,
                        MainPanel_data,
                        Taikeiko_data,
                        name_sec,
                        pb_guss,
                        type_yokokou[1],
                        nameWeb_mainpanel,
                        girder_guss,
                        distedge_fb,
                        distKL1_face,
                        distKL2_face,
                    )
                elif typefacefollow == "SP":
                    # TODO: Calculate_Face_Base_Guss_follow_SubPanelを追加する必要があります
                    p1T_fb, p1S_fb, p2T_fb, p2S_fb = Calculate_Face_Base_Guss_follow_SubPanel(
                        Senkei_data,
                        MainPanel_data,
                        SubPanel_data,
                        Mem_Rib_data,
                        name_sec,
                        pb_guss,
                        type_yokokou[1],
                        girder_guss,
                        distedge_fb,
                        distKL1_face,
                        distKL2_face,
                        Edge_guss[0],
                        Edge_guss[1],
                    )
                elif typefacefollow == "YK":
                    p1T_fb, p1S_fb, p2T_fb, p2S_fb = Calculate_Face_Base_Guss_follow_Yokokou(
                        shape_yokokou, arCoordPoint_Yokokou, type_yokokou, pb_guss, distedge_fb
                    )

                else:
                    print(f"⚠️ Trường hợp mặt base của face guss là {typefacefollow} chưa phát triển")

                if index_faceKL == 0:
                    if Edge_guss[0] != "P" and DefMath.is_real_number(Edge_guss[0]):
                        p2T_fb = Calculate_edge_Guss_Constant(
                            MainPanel_data,
                            Senkei_data,
                            nameWeb_mainpanel,
                            name_sec,
                            pb_guss,
                            float(Edge_guss[0]),
                            p1T_fb,
                            p1S_fb,
                            p2S_fb,
                        )
                elif index_faceKL == len(face_guss) - 2:
                    if Edge_guss[1] != "P" and DefMath.is_real_number(Edge_guss[1]):
                        p2S_fb = Calculate_edge_Guss_Constant(
                            MainPanel_data,
                            Senkei_data,
                            nameWeb_mainpanel,
                            name_sec,
                            pb_guss,
                            float(Edge_guss[1]),
                            p1T_fb,
                            p1S_fb,
                            p2T_fb,
                        )
            else:
                print("⚠️ Lỗi mặt KL của Guss")
            # ---------------face guss-------------------
            stt_F = False
            stt_A = False
            for i in range(0, len(face_guss), 2):
                if i != index_faceKL and i > index_faceKL:
                    stt_F = True
                    p1_fF = p1S_fb
                    p2_fF = p2S_fb
                    typefacefollow = face_guss[i]
                    distedge_face = face_guss[i + 1]
                    if typefacefollow == "YK":
                        p3T_fF, p3S_fF = Calculate_Face_Guss_follow_Yokokou(
                            shape_yokokou,
                            arCoordPoint_Yokokou,
                            type_yokokou,
                            point_guss,
                            distedge_face,
                            p1_fF,
                            p2_fF,
                            "S",
                        )
                        if Edge_guss[1] == "P":
                            p_edge_fF = Calculate_edge_Guss_P(
                                MainPanel_data, Senkei_data, nameWeb_mainpanel, p3S_fF, p1_fF, p2_fF
                            )
                        elif DefMath.is_real_number(Edge_guss[1]) == True:
                            p_edge_fF = Calculate_edge_Guss_Constant(
                                MainPanel_data,
                                Senkei_data,
                                nameWeb_mainpanel,
                                name_sec,
                                pb_guss,
                                float(Edge_guss[1]),
                                p3S_fF,
                                p1_fF,
                                p2_fF,
                            )
                        else:
                            p_edge_fF = None

                        if distedge_fb.startswith("A"):
                            p_pl = np.array(p1T_fb).copy()
                            p_pl[2] += 100
                            p1S_fb = DefMath.Intersection_line_plane(p1T_fb, p3T_fF, p_pl, p1_fF, p2_fF)
                            p1_fF = p1S_fb
                        elif distedge_fb.startswith("B"):
                            p1_pl = p3T_fF

                elif i != index_faceKL and i < index_faceKL:
                    stt_A = True
                    p1_fA = p1T_fb
                    p2_fA = p2T_fb
                    typefacefollow = face_guss[i]
                    distedge_face = face_guss[i + 1]
                    if typefacefollow == "YK":
                        p3T_fA, p3S_fA = Calculate_Face_Guss_follow_Yokokou(
                            shape_yokokou,
                            arCoordPoint_Yokokou,
                            type_yokokou,
                            point_guss,
                            distedge_face,
                            p1_fA,
                            p2_fA,
                            "E",
                        )

                        if Edge_guss[0] == "P":
                            p_edge_fA = Calculate_edge_Guss_P(
                                MainPanel_data, Senkei_data, nameWeb_mainpanel, p3T_fA, p1_fA, p2_fA
                            )
                        elif DefMath.is_real_number(Edge_guss[0]) == True:
                            p_edge_fA = Calculate_edge_Guss_Constant(
                                MainPanel_data,
                                Senkei_data,
                                nameWeb_mainpanel,
                                name_sec,
                                pb_guss,
                                float(Edge_guss[0]),
                                p3T_fA,
                                p1_fA,
                                p2_fA,
                            )
                        else:
                            p_edge_fA = None

                        if distedge_fb.startswith("F"):
                            p_pl = np.array(p1S_fb).copy()
                            p_pl[2] += 100
                            p1T_fb = DefMath.Intersection_line_plane(p1S_fb, p3S_fA, p_pl, p1_fA, p2_fA)
                            p1_fA = p1T_fb
                        elif distedge_fb.startswith("B"):
                            p2_pl = p3S_fA

            # ---------------Recal face base------------
            if distedge_fb.startswith("B"):
                p3_pl = np.array(p1_pl).copy()
                p3_pl[2] += 100
                p1T_fb = DefMath.Intersection_line_plane(p1_pl, p2_pl, p3_pl, p1T_fb, p2T_fb)
                p1S_fb = DefMath.Intersection_line_plane(p1_pl, p2_pl, p3_pl, p1S_fb, p2S_fb)
                p1_fF = p1S_fb
                p2_fF = p2S_fb
                p1_fA = p1T_fb
                p2_fA = p2T_fb
            if distedge_fb.startswith("C"):
                p1_pl = p3T_fF
                p2_pl = p3T_fA
                p3_pl = np.array(p1_pl).copy()
                p3_pl[2] += 100
                p1T_fb = DefMath.Intersection_line_plane(p1_pl, p2_pl, p3_pl, p1T_fb, p2T_fb)
                p1S_fb = DefMath.Intersection_line_plane(p1_pl, p2_pl, p3_pl, p1S_fb, p2S_fb)
                p1_fF = p1S_fb
                p2_fF = p2S_fb
                p1_fA = p1T_fb
                p2_fA = p2T_fb

                p1_pl = p3S_fF
                p2_pl = p3S_fA
                p3_pl = np.array(p1_pl).copy()
                p3_pl[2] += 100
                p2T_fb = DefMath.Intersection_line_plane(p1_pl, p2_pl, p3_pl, p1T_fb, p2T_fb)
                p2S_fb = DefMath.Intersection_line_plane(p1_pl, p2_pl, p3_pl, p1S_fb, p2S_fb)
                p1_fF = p1S_fb
                p2_fF = p2S_fb
                p1_fA = p1T_fb
                p2_fA = p2T_fb

            # ---------------Draw Solid -------------------------------
            # --Face base
            normal_fb = DefMath.Normal_vector(p1T_fb, p1S_fb, p2T_fb)
            p1T_fb_thick = p1T_fb + float(infor_guss[0]) * normal_fb
            p1S_fb_thick = p1S_fb + float(infor_guss[0]) * normal_fb
            p2T_fb_thick = p2T_fb + float(infor_guss[0]) * normal_fb
            p2S_fb_thick = p2S_fb + float(infor_guss[0]) * normal_fb
            if p1T_fb_thick[2] > p1T_fb[2]:
                p1T_fb_thick = p1T_fb - float(infor_guss[0]) * normal_fb
                p1S_fb_thick = p1S_fb - float(infor_guss[0]) * normal_fb
                p2T_fb_thick = p2T_fb - float(infor_guss[0]) * normal_fb
                p2S_fb_thick = p2S_fb - float(infor_guss[0]) * normal_fb

            arCoordT = [p1T_fb, p1S_fb, p2S_fb, p2T_fb]
            arCoordB = [p1T_fb_thick, p1S_fb_thick, p2S_fb_thick, p2T_fb_thick]
            arCoordT = DefMath.sort_points_clockwise(arCoordT)
            arCoordB = DefMath.sort_points_clockwise(arCoordB)
            arCoord_Face_Guss.append((arCoordT, arCoordB))

            # --Face F------
            if stt_F == True:
                normal_face = DefMath.Normal_vector(p1_fF, p2_fF, p3T_fF)
                p3T_fF_thick = p3T_fF + float(infor_guss[0]) * normal_face
                p3S_fF_thick = p3S_fF + float(infor_guss[0]) * normal_face
                if p_edge_fF is not None:
                    p_edge_fF_thick = p_edge_fF + float(infor_guss[0]) * normal_face
                if p3T_fF_thick[2] > p3T_fF[2]:
                    p3T_fF_thick = p3T_fF - float(infor_guss[0]) * normal_face
                    p3S_fF_thick = p3S_fF - float(infor_guss[0]) * normal_face
                    if p_edge_fF is not None:
                        p_edge_fF_thick = p_edge_fF - float(infor_guss[0]) * normal_face

                if p_edge_fF is not None:
                    arCoordT = [p1_fF, p2_fF, p3T_fF, p3S_fF, p_edge_fF]
                    arCoordB = [p1S_fb_thick, p2S_fb_thick, p3T_fF_thick, p3S_fF_thick, p_edge_fF_thick]
                else:
                    arCoordT = [p1_fF, p2_fF, p3T_fF, p3S_fF]
                    arCoordB = [p1S_fb_thick, p2S_fb_thick, p3T_fF_thick, p3S_fF_thick]

                arCoordT = DefMath.sort_points_clockwise(arCoordT)
                arCoordB = DefMath.sort_points_clockwise(arCoordB)
                arCoord_Face_Guss.append((arCoordT, arCoordB))
            # -Face A------
            if stt_A == True:
                normal_face = DefMath.Normal_vector(p1_fA, p2_fA, p3T_fA)
                p3T_fn_thick = p3T_fA + float(infor_guss[0]) * normal_face
                p3S_fn_thick = p3S_fA + float(infor_guss[0]) * normal_face
                if p_edge_fA is not None:
                    p_edge_fA_thick = p_edge_fA + float(infor_guss[0]) * normal_face
                if p3T_fn_thick[2] > p3T_fA[2]:
                    p3T_fn_thick = p3T_fA - float(infor_guss[0]) * normal_face
                    p3S_fn_thick = p3S_fA - float(infor_guss[0]) * normal_face
                    if p_edge_fA is not None:
                        p_edge_fA_thick = p_edge_fA - float(infor_guss[0]) * normal_face

                if p_edge_fA is not None:
                    arCoordT = [p1_fA, p2_fA, p3T_fA, p3S_fA, p_edge_fA]
                    arCoordB = [p1T_fb_thick, p2T_fb_thick, p3T_fn_thick, p3S_fn_thick, p_edge_fA_thick]
                else:
                    arCoordT = [p1_fA, p2_fA, p3T_fA, p3S_fA]
                    arCoordB = [p1T_fb_thick, p2T_fb_thick, p3T_fn_thick, p3S_fn_thick]

                arCoordT = DefMath.sort_points_clockwise(arCoordT)
                arCoordB = DefMath.sort_points_clockwise(arCoordB)
                arCoord_Face_Guss.append((arCoordT, arCoordB))
        else:
            # ---------------face guss-------------------
            arCoordT = []
            arCoordB = []
            for i in range(0, len(face_guss), 2):
                if i == 0:
                    typefacefollow_1 = face_guss[i]
                    distedge_face_1 = face_guss[i + 1]
                    if typefacefollow_1 == "YK":
                        pmod1_face = Calculate_PointMod_Guss_follow_Yokokou(
                            shape_yokokou, arCoordPoint_Yokokou, point_guss, distedge_face_1, "E"
                        )
                elif i == 2:
                    typefacefollow_2 = face_guss[i]
                    distedge_face_2 = face_guss[i + 1]
                    if typefacefollow_2 == "YK":
                        pmod2_face = Calculate_PointMod_Guss_follow_Yokokou(
                            shape_yokokou, arCoordPoint_Yokokou, point_guss, distedge_face_2, "S"
                        )

            normal_face = DefMath.Normal_vector(pb_guss, pmod1_face, pmod2_face)

            if typefacefollow_1 == "YK":
                pmod1T_face, pmod1S_face = Calculate_Face_Guss_follow_Yokokou(
                    shape_yokokou,
                    arCoordPoint_Yokokou,
                    type_yokokou,
                    point_guss,
                    distedge_face_1,
                    pb_guss,
                    pmod2_face,
                    "E",
                )
                if Edge_guss[0] == "P":
                    p_edge_guss = Calculate_edge_Guss_P(
                        MainPanel_data, Senkei_data, nameWeb_mainpanel, pmod1T_face, pb_guss, pmod2_face
                    )
                else:
                    p_edge_guss = Calculate_edge_Guss_Constant(
                        MainPanel_data,
                        Senkei_data,
                        nameWeb_mainpanel,
                        name_sec,
                        pb_guss,
                        float(Edge_guss[0]),
                        pmod1T_face,
                        pb_guss,
                        pmod2_face,
                    )
                if pmod1T_face[1] < p_edge_guss[1]:
                    pos = "L"
                else:
                    pos = "R"
                pmod1T_face_thick = pmod1T_face + float(infor_guss[0]) * normal_face
                pmod1S_face_thick = pmod1S_face + float(infor_guss[0]) * normal_face
                p_edge_guss_thick = p_edge_guss + float(infor_guss[0]) * normal_face
                if pmod1T_face_thick[2] > pmod1T_face[2]:
                    pmod1T_face_thick = pmod1T_face - float(infor_guss[0]) * normal_face
                    pmod1S_face_thick = pmod1S_face - float(infor_guss[0]) * normal_face
                    p_edge_guss_thick = p_edge_guss - float(infor_guss[0]) * normal_face

                arCoordT.append(pmod1T_face)
                arCoordT.append(pmod1S_face)
                arCoordT.append(p_edge_guss)
                arCoordB.append(pmod1T_face_thick)
                arCoordB.append(pmod1S_face_thick)
                arCoordB.append(p_edge_guss_thick)

            if typefacefollow_2 == "YK":
                pmod2T_face, pmod2S_face = Calculate_Face_Guss_follow_Yokokou(
                    shape_yokokou,
                    arCoordPoint_Yokokou,
                    type_yokokou,
                    point_guss,
                    distedge_face_2,
                    pb_guss,
                    pmod1_face,
                    "S",
                )
                if Edge_guss[1] == "P":
                    p_edge_guss = Calculate_edge_Guss_P(
                        MainPanel_data, Senkei_data, nameWeb_mainpanel, pmod2S_face, pb_guss, pmod1_face
                    )
                else:
                    p_edge_guss = Calculate_edge_Guss_Constant(
                        MainPanel_data,
                        Senkei_data,
                        nameWeb_mainpanel,
                        name_sec,
                        pb_guss,
                        float(Edge_guss[1]),
                        pmod2S_face,
                        pb_guss,
                        pmod1_face,
                    )

                pmod2T_face_thick = pmod2T_face + float(infor_guss[0]) * normal_face
                pmod2S_face_thick = pmod2S_face + float(infor_guss[0]) * normal_face
                p_edge_guss_thick = p_edge_guss + float(infor_guss[0]) * normal_face
                if pmod2T_face_thick[2] > pmod2T_face[2]:
                    pmod2T_face_thick = pmod2T_face - float(infor_guss[0]) * normal_face
                    pmod2S_face_thick = pmod2S_face - float(infor_guss[0]) * normal_face
                    p_edge_guss_thick = p_edge_guss - float(infor_guss[0]) * normal_face

                arCoordT.append(pmod2T_face)
                arCoordT.append(pmod2S_face)
                arCoordT.append(p_edge_guss)
                arCoordB.append(pmod2T_face_thick)
                arCoordB.append(pmod2S_face_thick)
                arCoordB.append(p_edge_guss_thick)

            arCoordT = DefMath.sort_points_clockwise(arCoordT)
            arCoordB = DefMath.sort_points_clockwise(arCoordB)
            arCoord_Face_Guss.append((arCoordT, arCoordB))

        if arCoord_Face_Guss:
            all_faces = []
            for top_pts, bot_pts in arCoord_Face_Guss:
                face_indices = DefIFC.Create_faces_from_prism(ifc_file, top_pts, bot_pts)
                faces = [DefIFC.create_face_from_points(ifc_file, pts) for pts in face_indices]
                all_faces.extend(faces)
            shell = ifc_file.createIfcClosedShell(all_faces)
            solid_guss = ifc_file.createIfcFacetedBrep(shell)
            if slot != "N":
                solid_slot = Draw_3DSlot_For_Guss_Yokokou(
                    ifc_all,
                    Senkei_data,
                    MainPanel_data,
                    Member_data,
                    Mem_Rib_data,
                    Taikeiko_data,
                    slot,
                    name_sec,
                    "",
                    nameWeb_mainpanel,
                    pos,
                    pb_guss,
                    pmod1T_face,
                    pmod2T_face,
                )
                if solid_slot is not None:
                    solid_guss = ifc_file.createIfcBooleanResult("DIFFERENCE", solid_guss, solid_slot)

            color_style = DefIFC.create_color(ifc_file, 174.0, 249.0, 240.0)
            styled_item = ifc_file.createIfcStyledItem(Item=solid_guss, Styles=[color_style])
            shape_representation = ifc_file.createIfcShapeRepresentation(
                ContextOfItems=geom_context,
                RepresentationIdentifier="Body",
                RepresentationType="Brep",
                Items=[solid_guss],
            )
            DefIFC.Add_shape_representation_in_Beam(ifc_file, bridge_span, shape_representation, name_guss)

        print(f"    Guss - {guss['Name']} : Export completed.")


# -----------------------------Taikeikou（対傾構）------------------------------------------------------------
def Calculate_Taikeikou(ifc_all, Data_Panel, Senkei_data, number_mainblock, infor_Taikeikou):
    """
    対傾構（Taikeikou）を計算して描画する

    対傾構の位置、サイズ、形状を計算し、IFCソリッドとして生成する。
    穴、補剛材、形状、ガセットプレートなどの処理も含む。

    Args:
        ifc_all: (ifc_file, bridge_span, geom_context)のタプル
        Data_Panel: パネルデータ
        Senkei_data: 線形データ
        number_mainblock: メインブロック番号
        infor_Taikeikou: 対傾構情報（名称、タイプ、桁、点、距離修正、穴、補剛材、形状、ガセットなど）
    """
    ifc_file, bridge_span, geom_context = ifc_all
    # infor_Taikeikouから全要素を取得（セクション情報を含む）
    if len(infor_Taikeikou) >= 10:
        (
            name_taikeikou,
            type_taikeikou,
            girder_taikeikou,
            point_taikeikou,
            distmod_taikeikou,
            hole_taikeikou,
            vstiff_taikeikou,
            shape_taikeikou,
            guss_taikeikou,
            section_taikeikou,
        ) = infor_Taikeikou
    else:
        # 後方互換性のため、セクション情報がない場合はデフォルト値を使用
        (
            name_taikeikou,
            type_taikeikou,
            girder_taikeikou,
            point_taikeikou,
            distmod_taikeikou,
            hole_taikeikou,
            vstiff_taikeikou,
            shape_taikeikou,
            guss_taikeikou,
        ) = infor_Taikeikou
        section_taikeikou = "C1"

    _log_print(
        f"    [Taikeikou] 開始: name={name_taikeikou}, セクション名ベース: section={section_taikeikou}, shape_taikeikou={shape_taikeikou}, type(shape_taikeikou)={type(shape_taikeikou)}"
    )
    typ_taikeikou, gau_gus, gau_shape = type_taikeikou

    # number_mainblockがリストの場合は最初の要素を使用
    if isinstance(number_mainblock, list):
        if len(number_mainblock) > 0:
            number_mainblock = number_mainblock[0]
        else:
            _log_print("    [Taikeikou] 警告: ブロック番号が見つかりません。デフォルト値 '1' を使用します。")
            number_mainblock = "1"
    # 数値の場合は文字列に変換
    elif not isinstance(number_mainblock, str):
        number_mainblock = str(number_mainblock)

    headname1_block_mainpanel = girder_taikeikou[0] + "B" + number_mainblock
    headname2_block_mainpanel = girder_taikeikou[1] + "B" + number_mainblock
    basepoint, modpoint = Calculate_Point_Taikeikou(
        Data_Panel,
        Senkei_data,
        name_taikeikou,
        point_taikeikou,
        distmod_taikeikou,
        girder_taikeikou,
        number_mainblock,
        section_taikeikou,
    )
    BasePoint1, BasePoint2, BasePoint3, BasePoint4 = basepoint
    ModPoint1, ModPoint2, ModPoint3, ModPoint4 = modpoint
    if typ_taikeikou == "Type1D":
        CenPoint = (ModPoint3 + ModPoint4) / 2
    elif typ_taikeikou == "Type1U":
        CenPoint = (ModPoint1 + ModPoint2) / 2
    else:
        print(f"対傾構のタイプ {typ_taikeikou} はまだ開発されていません")

    p1_3d = BasePoint4
    p2_3d = DefMath.point_per_line(p1_3d, BasePoint2, BasePoint3)
    p3_3d = BasePoint1
    normal_taikeikou = -DefMath.Normal_vector(p1_3d, p2_3d, p3_3d)
    p1_2d = [0, 0, 0]
    p2_2d = [100, 0, 0]
    p3_2d = [0, 100, 0]
    BasePoint1_2D = DefMath.Transform_point_face2face(BasePoint1, p1_3d, p2_3d, p3_3d, p1_2d, p2_2d, p3_2d)
    BasePoint1_2D[2] = 0
    BasePoint2_2D = DefMath.Transform_point_face2face(BasePoint2, p1_3d, p2_3d, p3_3d, p1_2d, p2_2d, p3_2d)
    BasePoint2_2D[2] = 0
    BasePoint3_2D = DefMath.Transform_point_face2face(BasePoint3, p1_3d, p2_3d, p3_3d, p1_2d, p2_2d, p3_2d)
    BasePoint3_2D[2] = 0
    BasePoint4_2D = DefMath.Transform_point_face2face(BasePoint4, p1_3d, p2_3d, p3_3d, p1_2d, p2_2d, p3_2d)
    BasePoint4_2D[2] = 0
    ModPoint1_2D = DefMath.Transform_point_face2face(ModPoint1, p1_3d, p2_3d, p3_3d, p1_2d, p2_2d, p3_2d)
    ModPoint1_2D[2] = 0
    ModPoint2_2D = DefMath.Transform_point_face2face(ModPoint2, p1_3d, p2_3d, p3_3d, p1_2d, p2_2d, p3_2d)
    ModPoint2_2D[2] = 0
    ModPoint3_2D = DefMath.Transform_point_face2face(ModPoint3, p1_3d, p2_3d, p3_3d, p1_2d, p2_2d, p3_2d)
    ModPoint3_2D[2] = 0
    ModPoint4_2D = DefMath.Transform_point_face2face(ModPoint4, p1_3d, p2_3d, p3_3d, p1_2d, p2_2d, p3_2d)
    ModPoint4_2D[2] = 0
    CenPoint_2D = DefMath.Transform_point_face2face(CenPoint, p1_3d, p2_3d, p3_3d, p1_2d, p2_2d, p3_2d)
    CenPoint_2D[2] = 0

    # -------------------Bolt（ボルト）-------------------------------------------------------------------
    hole_tl, hole_tr, hole_bl, hole_br = (
        hole_taikeikou["TL"],
        hole_taikeikou["TR"],
        hole_taikeikou["BL"],
        hole_taikeikou["BR"],
    )

    arCoord_hole_tl = Caculate_Coord_Hole_Taikeikou(hole_tl, ModPoint1_2D, "TL")
    gap_cen_to_head, gap_cen_to_nut = Calculate_Length_Bolt_Taikeikou(gau_gus, vstiff_taikeikou, guss_taikeikou, "TL")
    Draw_3DSolid_Bolt_Taikeikou(ifc_all, arCoord_hole_tl, gap_cen_to_head, gap_cen_to_nut, p1_3d, p2_3d, p3_3d)

    arCoord_hole_tr = Caculate_Coord_Hole_Taikeikou(hole_tr, ModPoint2_2D, "TR")
    gap_cen_to_head, gap_cen_to_nut = Calculate_Length_Bolt_Taikeikou(gau_gus, vstiff_taikeikou, guss_taikeikou, "TR")
    Draw_3DSolid_Bolt_Taikeikou(ifc_all, arCoord_hole_tr, gap_cen_to_head, gap_cen_to_nut, p1_3d, p2_3d, p3_3d)

    arCoord_hole_bl = Caculate_Coord_Hole_Taikeikou(hole_bl, ModPoint4_2D, "BL")
    gap_cen_to_head, gap_cen_to_nut = Calculate_Length_Bolt_Taikeikou(gau_gus, vstiff_taikeikou, guss_taikeikou, "BL")
    Draw_3DSolid_Bolt_Taikeikou(ifc_all, arCoord_hole_bl, gap_cen_to_head, gap_cen_to_nut, p1_3d, p2_3d, p3_3d)

    arCoord_hole_br = Caculate_Coord_Hole_Taikeikou(hole_br, ModPoint3_2D, "BR")
    gap_cen_to_head, gap_cen_to_nut = Calculate_Length_Bolt_Taikeikou(gau_gus, vstiff_taikeikou, guss_taikeikou, "BR")
    Draw_3DSolid_Bolt_Taikeikou(ifc_all, arCoord_hole_br, gap_cen_to_head, gap_cen_to_nut, p1_3d, p2_3d, p3_3d)

    # -------------------Vstiff（垂直補剛材）-------------------------------------------------------------------
    if vstiff_taikeikou:
        vstiff_left, vstiff_right = vstiff_taikeikou["L"], vstiff_taikeikou["R"]
        if vstiff_left:
            thick_vstiff, mat_vstiff, width_vstiff = vstiff_left
            from src.bridge_json_to_ifc.ifc_utils_new.components.DefStiffener import Draw_3DSolid_Vstiff_Taikeikou

            Solid_vstiff_left = Draw_3DSolid_Vstiff_Taikeikou(
                ifc_all,
                Data_Panel,
                Senkei_data,
                headname1_block_mainpanel,
                thick_vstiff,
                width_vstiff,
                BasePoint1,
                BasePoint2,
                BasePoint3,
                BasePoint4,
                pos="L",
            )
            color_style = DefIFC.create_color(ifc_file, 174.0, 249.0, 240.0)
            styled_item = ifc_file.createIfcStyledItem(Item=Solid_vstiff_left, Styles=[color_style])
            shape_representation = ifc_file.createIfcShapeRepresentation(
                ContextOfItems=geom_context,
                RepresentationIdentifier="Body",
                RepresentationType="Brep",
                Items=[Solid_vstiff_left],
            )
            # 位置情報を含む名前を生成: {Name}_G{Girder1}_G{Girder2}_C1_VL
            # 対傾構は通常中間点（C1）を使用
            girder1_raw = girder_taikeikou[0] if len(girder_taikeikou) > 0 else ""
            girder2_raw = girder_taikeikou[1] if len(girder_taikeikou) > 1 else ""
            import re

            girder1_num = re.sub(r"^G", "", girder1_raw) if girder1_raw.startswith("G") else girder1_raw
            girder2_num = re.sub(r"^G", "", girder2_raw) if girder2_raw.startswith("G") else girder2_raw
            vstiff_name = f"{name_taikeikou}_G{girder1_num}_G{girder2_num}_C1_VL"
            DefIFC.Add_shape_representation_in_Beam(ifc_file, bridge_span, shape_representation, vstiff_name)

        if vstiff_right:
            thick_vstiff, mat_vstiff, width_vstiff = vstiff_right
            from src.bridge_json_to_ifc.ifc_utils_new.components.DefStiffener import Draw_3DSolid_Vstiff_Taikeikou

            Solid_vstiff_right = Draw_3DSolid_Vstiff_Taikeikou(
                ifc_all,
                Data_Panel,
                Senkei_data,
                headname2_block_mainpanel,
                thick_vstiff,
                width_vstiff,
                BasePoint1,
                BasePoint2,
                BasePoint3,
                BasePoint4,
                pos="R",
            )
            color_style = DefIFC.create_color(ifc_file, 174.0, 249.0, 240.0)
            styled_item = ifc_file.createIfcStyledItem(Item=Solid_vstiff_right, Styles=[color_style])
            shape_representation = ifc_file.createIfcShapeRepresentation(
                ContextOfItems=geom_context,
                RepresentationIdentifier="Body",
                RepresentationType="Brep",
                Items=[Solid_vstiff_right],
            )
            # 位置情報を含む名前を生成: {Name}_G{Girder1}_G{Girder2}_C1_VR
            # 対傾構は通常中間点（C1）を使用
            girder1_raw = girder_taikeikou[0] if len(girder_taikeikou) > 0 else ""
            girder2_raw = girder_taikeikou[1] if len(girder_taikeikou) > 1 else ""
            import re

            girder1_num = re.sub(r"^G", "", girder1_raw) if girder1_raw.startswith("G") else girder1_raw
            girder2_num = re.sub(r"^G", "", girder2_raw) if girder2_raw.startswith("G") else girder2_raw
            vstiff_name = f"{name_taikeikou}_G{girder1_num}_G{girder2_num}_C1_VR"
            DefIFC.Add_shape_representation_in_Beam(ifc_file, bridge_span, shape_representation, vstiff_name)

    # -------------------Shape（形状部材）-------------------------------------------------------------------
    _log_print(
        f"    [Taikeikou] Shapeチェック: shape_taikeikou={shape_taikeikou}, bool(shape_taikeikou)={bool(shape_taikeikou)}"
    )
    if shape_taikeikou:
        _log_print(f"    [Taikeikou] Shape処理開始: shape_taikeikou={shape_taikeikou}")
        shapeT, shapeB, shapeL, shapeR = (
            shape_taikeikou["T"],
            shape_taikeikou["B"],
            shape_taikeikou["L"],
            shape_taikeikou["R"],
        )
        _log_print(f"    [Taikeikou] shapeT={shapeT}, shapeB={shapeB}, shapeL={shapeL}, shapeR={shapeR}")
        if guss_taikeikou:
            tl_guss, tr_guss, bl_guss, br_guss, mid_guss = (
                guss_taikeikou["TL"],
                guss_taikeikou["TR"],
                guss_taikeikou["BL"],
                guss_taikeikou["BR"],
                guss_taikeikou["Mid"],
            )
        else:
            tl_guss, tr_guss, bl_guss, br_guss, mid_guss = [], [], [], [], []

        if shapeT:
            _log_print(f"    [Taikeikou ShapeT] 処理開始: shapeT={shapeT}")
            type_shape, size_shape, mat_shape, dir_shape, distmodY_shape, pitchmod_shape = shapeT
            ar_size_shape = size_shape.split("x")
            # shapeTは上フランジの下に配置するため、BasePoint1_2DとBasePoint2_2Dを使用
            _log_print(f"    [Taikeikou ShapeT] BasePoint1_2D={BasePoint1_2D}, BasePoint2_2D={BasePoint2_2D}")
            p1mod_shape, p2mod_shape = Calculate_Pse_Shape(pitchmod_shape, BasePoint1_2D, BasePoint2_2D)
            _log_print(f"    [Taikeikou ShapeT] p1mod_shape={p1mod_shape}, p2mod_shape={p2mod_shape}")
            if type_shape == "CT":
                distmodX_shape = Calculate_DistModX_Shape(
                    vstiff_taikeikou, guss_taikeikou, gau_gus, gau_shape, size_shape, "CT"
                )
                p1mod_shape_3D_al = np.array(
                    DefMath.Transform_point_face2face(p1mod_shape, p1_2d, p2_2d, p3_2d, p1_3d, p2_3d, p3_3d)
                    + distmodX_shape * normal_taikeikou,
                    dtype=float,
                )
                p2mod_shape_3D_al = np.array(
                    DefMath.Transform_point_face2face(p2mod_shape, p1_2d, p2_2d, p3_2d, p1_3d, p2_3d, p3_3d)
                    + distmodX_shape * normal_taikeikou,
                    dtype=float,
                )

                # 断面高さ・中心位置を計算（センター基準）
                shape_height = float(ar_size_shape[0])  # 部材高さ（mm）
                half_shape_height = shape_height / 2.0
                y_base_profile = -half_shape_height
                arCoor_profile = DefMath.profile2D_shapCT(size_shape, [0, y_base_profile])
                _log_print(
                    f"    [Taikeikou ShapeT] shape_height={shape_height}, half={half_shape_height}, profile_base_y={y_base_profile}"
                )
                _log_print(
                    f"    [Taikeikou ShapeT] arCoor_profile生成: {arCoor_profile is not None}, 座標数={len(arCoor_profile) if arCoor_profile else 0}"
                )
                if arCoor_profile is None:
                    print(f"    [Taikeikou] エラー: 形状名 '{size_shape}' がprofile2D_shapCTのリストに存在しません。")
                else:
                    # 上側水平材の中心を上フランジ直下に合わせる
                    try:
                        distmodY_value = float(distmodY_shape)
                    except (TypeError, ValueError):
                        distmodY_value = 0.0
                    dir_vertical = np.array(BasePoint1) - np.array(BasePoint4)
                    if np.linalg.norm(dir_vertical) < 1e-6:
                        dir_vertical = np.array(BasePoint2) - np.array(BasePoint3)
                    if np.linalg.norm(dir_vertical) < 1e-6:
                        dir_vertical = np.array([0.0, 0.0, 1.0])
                    dir_vertical = dir_vertical / np.linalg.norm(dir_vertical)
                    target_center = np.array(BasePoint1) - dir_vertical * (half_shape_height + distmodY_value)
                    shift_vec = target_center - p1mod_shape_3D_al
                    p1mod_shape_3D_al = p1mod_shape_3D_al + shift_vec
                    p2mod_shape_3D_al = p2mod_shape_3D_al + shift_vec
                    _log_print(f"    [Taikeikou ShapeT] dir_vertical={dir_vertical}, distmodY={distmodY_value}")
                    _log_print(
                        f"    [Taikeikou ShapeT] target_center={target_center.tolist()}, shift_vec={shift_vec.tolist()}"
                    )
                    _log_print(
                        f"    [Taikeikou ShapeT] p1mod(after)={p1mod_shape_3D_al.tolist()}, p2mod(after)={p2mod_shape_3D_al.tolist()}"
                    )

                    if dir_shape == "U":
                        if gau_shape == "A":
                            p3mod_shape_3D_al = p2mod_shape_3D_al - 100 * normal_taikeikou
                            solid_shape = DefIFC.extrude_profile_and_align(
                                ifc_file,
                                arCoor_profile,
                                DefMath.Calculate_distance_p2p(p1mod_shape, p2mod_shape),
                                p1mod_shape_3D_al,
                                p2mod_shape_3D_al,
                                p3mod_shape_3D_al,
                            )
                        else:
                            p3mod_shape_3D_al = p1mod_shape_3D_al + 100 * normal_taikeikou
                            solid_shape = DefIFC.extrude_profile_and_align(
                                ifc_file,
                                arCoor_profile,
                                DefMath.Calculate_distance_p2p(p1mod_shape, p2mod_shape),
                                p2mod_shape_3D_al,
                                p1mod_shape_3D_al,
                                p3mod_shape_3D_al,
                            )
                    else:
                        if gau_shape == "A":
                            p3mod_shape_3D_al = p1mod_shape_3D_al - 100 * normal_taikeikou
                            solid_shape = DefIFC.extrude_profile_and_align(
                                ifc_file,
                                arCoor_profile,
                                DefMath.Calculate_distance_p2p(p1mod_shape, p2mod_shape),
                                p2mod_shape_3D_al,
                                p1mod_shape_3D_al,
                                p3mod_shape_3D_al,
                            )
                        else:
                            p3mod_shape_3D_al = p2mod_shape_3D_al + 100 * normal_taikeikou
                            solid_shape = DefIFC.extrude_profile_and_align(
                                ifc_file,
                                arCoor_profile,
                                DefMath.Calculate_distance_p2p(p1mod_shape, p2mod_shape),
                                p1mod_shape_3D_al,
                                p2mod_shape_3D_al,
                                p3mod_shape_3D_al,
                            )

                    color_style = DefIFC.create_color(ifc_file, 70.0, 100.0, 150.0)  # スチールブルー
                    styled_item = ifc_file.createIfcStyledItem(Item=solid_shape, Styles=[color_style])
                    shape_representation = ifc_file.createIfcShapeRepresentation(
                        ContextOfItems=geom_context,
                        RepresentationIdentifier="Body",
                        RepresentationType="Brep",
                        Items=[solid_shape],
                    )
                    # 位置情報を含む名前を生成: {Name}_G{Girder1}_G{Girder2}_C1_CT{Size}
                    # 対傾構は通常中間点（C1）を使用
                    girder1_raw = girder_taikeikou[0] if len(girder_taikeikou) > 0 else ""
                    girder2_raw = girder_taikeikou[1] if len(girder_taikeikou) > 1 else ""
                    import re

                    girder1_num = re.sub(r"^G", "", girder1_raw) if girder1_raw.startswith("G") else girder1_raw
                    girder2_num = re.sub(r"^G", "", girder2_raw) if girder2_raw.startswith("G") else girder2_raw
                    shape_name = f"{name_taikeikou}_G{girder1_num}_G{girder2_num}_C1_CT{size_shape}"
                    DefIFC.Add_shape_representation_in_Beam(ifc_file, bridge_span, shape_representation, shape_name)
            elif type_shape == "L":
                distmodX_shape = Calculate_DistModX_Shape(
                    vstiff_taikeikou, guss_taikeikou, gau_gus, gau_shape, size_shape, "L"
                )
                p1mod_shape_3D_al = (
                    DefMath.Transform_point_face2face(p1mod_shape, p1_2d, p2_2d, p3_2d, p1_3d, p2_3d, p3_3d)
                    + distmodX_shape * normal_taikeikou
                )
                p2mod_shape_3D_al = (
                    DefMath.Transform_point_face2face(p2mod_shape, p1_2d, p2_2d, p3_2d, p1_3d, p2_3d, p3_3d)
                    + distmodX_shape * normal_taikeikou
                )
                if dir_shape == "U":
                    if gau_shape == "A":
                        p3mod_shape_3D_al = p2mod_shape_3D_al - 100 * normal_taikeikou
                        arCoor_profile = DefMath.profile2D_shapL(size_shape, [0, -distmodY_shape])
                        if arCoor_profile is None:
                            print(
                                f"    [Taikeikou] エラー: 形状名 '{size_shape}' がprofile2D_shapLのリストに存在しません。"
                            )
                        else:
                            solid_shape = DefIFC.extrude_profile_and_align(
                                ifc_file,
                                arCoor_profile,
                                DefMath.Calculate_distance_p2p(p1mod_shape, p2mod_shape),
                                p1mod_shape_3D_al,
                                p2mod_shape_3D_al,
                                p3mod_shape_3D_al,
                            )
                    else:
                        p3mod_shape_3D_al = p1mod_shape_3D_al + 100 * normal_taikeikou
                        arCoor_profile = DefMath.profile2D_shapL(size_shape, [0, -distmodY_shape])
                        solid_shape = DefIFC.extrude_profile_and_align(
                            ifc_file,
                            arCoor_profile,
                            DefMath.Calculate_distance_p2p(p1mod_shape, p2mod_shape),
                            p2mod_shape_3D_al,
                            p1mod_shape_3D_al,
                            p3mod_shape_3D_al,
                        )
                else:
                    if gau_shape == "A":
                        p3mod_shape_3D_al = p1mod_shape_3D_al - 100 * normal_taikeikou
                        arCoor_profile = DefMath.profile2D_shapL(size_shape, [0, -distmodY_shape])
                        solid_shape = DefIFC.extrude_profile_and_align(
                            ifc_file,
                            arCoor_profile,
                            DefMath.Calculate_distance_p2p(p1mod_shape, p2mod_shape),
                            p2mod_shape_3D_al,
                            p1mod_shape_3D_al,
                            p3mod_shape_3D_al,
                        )
                    else:
                        p3mod_shape_3D_al = p2mod_shape_3D_al + 100 * normal_taikeikou
                        arCoor_profile = DefMath.profile2D_shapL(size_shape, [0, -distmodY_shape])
                        if arCoor_profile is None:
                            print(
                                f"    [Taikeikou] エラー: 形状名 '{size_shape}' がprofile2D_shapLのリストに存在しません。"
                            )
                        else:
                            solid_shape = DefIFC.extrude_profile_and_align(
                                ifc_file,
                                arCoor_profile,
                                DefMath.Calculate_distance_p2p(p1mod_shape, p2mod_shape),
                                p1mod_shape_3D_al,
                                p2mod_shape_3D_al,
                                p3mod_shape_3D_al,
                            )

                color_style = DefIFC.create_color(ifc_file, 70.0, 100.0, 150.0)  # スチールブルー
                styled_item = ifc_file.createIfcStyledItem(Item=solid_shape, Styles=[color_style])
                shape_representation = ifc_file.createIfcShapeRepresentation(
                    ContextOfItems=geom_context,
                    RepresentationIdentifier="Body",
                    RepresentationType="Brep",
                    Items=[solid_shape],
                )
                # 位置情報を含む名前を生成: {Name}_G{Girder1}_G{Girder2}_C1_L{Size}
                # 対傾構は通常中間点（C1）を使用
                girder1_raw = girder_taikeikou[0] if len(girder_taikeikou) > 0 else ""
                girder2_raw = girder_taikeikou[1] if len(girder_taikeikou) > 1 else ""
                import re

                girder1_num = re.sub(r"^G", "", girder1_raw) if girder1_raw.startswith("G") else girder1_raw
                girder2_num = re.sub(r"^G", "", girder2_raw) if girder2_raw.startswith("G") else girder2_raw
                shape_name = f"{name_taikeikou}_G{girder1_num}_G{girder2_num}_C1_L{size_shape}"
                DefIFC.Add_shape_representation_in_Beam(ifc_file, bridge_span, shape_representation, shape_name)
            elif type_shape == "C":
                distmodX_shape = Calculate_DistModX_Shape(
                    vstiff_taikeikou, guss_taikeikou, gau_gus, gau_shape, size_shape, "L"
                )
                p1mod_shape_3D_al = (
                    DefMath.Transform_point_face2face(p1mod_shape, p1_2d, p2_2d, p3_2d, p1_3d, p2_3d, p3_3d)
                    + distmodX_shape * normal_taikeikou
                )
                p2mod_shape_3D_al = (
                    DefMath.Transform_point_face2face(p2mod_shape, p1_2d, p2_2d, p3_2d, p1_3d, p2_3d, p3_3d)
                    + distmodX_shape * normal_taikeikou
                )
                arCoor_profile = DefMath.profile2D_shapC(size_shape, [0, distmodY_shape - float(ar_size_shape[0])])
                if arCoor_profile is None:
                    print(f"    [Taikeikou] エラー: 形状名 '{size_shape}' がprofile2D_shapCのリストに存在しません。")
                else:
                    if dir_shape == "U":
                        if gau_shape == "A":
                            p3mod_shape_3D_al = p2mod_shape_3D_al - 100 * normal_taikeikou
                            solid_shape = DefIFC.extrude_profile_and_align(
                                ifc_file,
                                arCoor_profile,
                                DefMath.Calculate_distance_p2p(p1mod_shape, p2mod_shape),
                                p1mod_shape_3D_al,
                                p2mod_shape_3D_al,
                                p3mod_shape_3D_al,
                            )
                        else:
                            p3mod_shape_3D_al = p1mod_shape_3D_al + 100 * normal_taikeikou
                            solid_shape = DefIFC.extrude_profile_and_align(
                                ifc_file,
                                arCoor_profile,
                                DefMath.Calculate_distance_p2p(p1mod_shape, p2mod_shape),
                                p2mod_shape_3D_al,
                                p1mod_shape_3D_al,
                                p3mod_shape_3D_al,
                            )
                    else:
                        if gau_shape == "A":
                            p3mod_shape_3D_al = p1mod_shape_3D_al - 100 * normal_taikeikou
                            solid_shape = DefIFC.extrude_profile_and_align(
                                ifc_file,
                                arCoor_profile,
                                DefMath.Calculate_distance_p2p(p1mod_shape, p2mod_shape),
                                p2mod_shape_3D_al,
                                p1mod_shape_3D_al,
                                p3mod_shape_3D_al,
                            )
                        else:
                            p3mod_shape_3D_al = p2mod_shape_3D_al + 100 * normal_taikeikou
                            solid_shape = DefIFC.extrude_profile_and_align(
                                ifc_file,
                                arCoor_profile,
                                DefMath.Calculate_distance_p2p(p1mod_shape, p2mod_shape),
                                p1mod_shape_3D_al,
                                p2mod_shape_3D_al,
                                p3mod_shape_3D_al,
                            )

                color_style = DefIFC.create_color(ifc_file, 70.0, 100.0, 150.0)  # スチールブルー
                styled_item = ifc_file.createIfcStyledItem(Item=solid_shape, Styles=[color_style])
                shape_representation = ifc_file.createIfcShapeRepresentation(
                    ContextOfItems=geom_context,
                    RepresentationIdentifier="Body",
                    RepresentationType="Brep",
                    Items=[solid_shape],
                )
                # 位置情報を含む名前を生成: {Name}_G{Girder1}_G{Girder2}_C1_C{Size}
                # 対傾構は通常中間点（C1）を使用
                girder1_raw = girder_taikeikou[0] if len(girder_taikeikou) > 0 else ""
                girder2_raw = girder_taikeikou[1] if len(girder_taikeikou) > 1 else ""
                import re

                girder1_num = re.sub(r"^G", "", girder1_raw) if girder1_raw.startswith("G") else girder1_raw
                girder2_num = re.sub(r"^G", "", girder2_raw) if girder2_raw.startswith("G") else girder2_raw
                shape_name = f"{name_taikeikou}_G{girder1_num}_G{girder2_num}_C1_C{size_shape}"
                DefIFC.Add_shape_representation_in_Beam(ifc_file, bridge_span, shape_representation, shape_name)

        if shapeB:
            _log_print(f"    [Taikeikou ShapeB] 処理開始: shapeB={shapeB}")
            type_shape, size_shape, mat_shape, dir_shape, distmodY_shape, pitchmod_shape = shapeB
            ar_size_shape = size_shape.split("x")
            # shapeBは下フランジの上に配置するため、BasePoint4_2DとBasePoint3_2Dを使用
            _log_print(f"    [Taikeikou ShapeB] BasePoint4_2D={BasePoint4_2D}, BasePoint3_2D={BasePoint3_2D}")
            p1mod_shape, p2mod_shape = Calculate_Pse_Shape(pitchmod_shape, BasePoint4_2D, BasePoint3_2D)
            _log_print(f"    [Taikeikou ShapeB] p1mod_shape={p1mod_shape}, p2mod_shape={p2mod_shape}")
            if type_shape == "CT":
                distmodX_shape = Calculate_DistModX_Shape(
                    vstiff_taikeikou, guss_taikeikou, gau_gus, gau_shape, size_shape, "CT"
                )
                p1mod_shape_3D_al = np.array(
                    DefMath.Transform_point_face2face(p1mod_shape, p1_2d, p2_2d, p3_2d, p1_3d, p2_3d, p3_3d)
                    + distmodX_shape * normal_taikeikou,
                    dtype=float,
                )
                p2mod_shape_3D_al = np.array(
                    DefMath.Transform_point_face2face(p2mod_shape, p1_2d, p2_2d, p3_2d, p1_3d, p2_3d, p3_3d)
                    + distmodX_shape * normal_taikeikou,
                    dtype=float,
                )
                if dir_shape == "U":
                    p3mod_shape_3D_al = p1mod_shape_3D_al - 100 * normal_taikeikou
                else:
                    p3mod_shape_3D_al = p1mod_shape_3D_al + 100 * normal_taikeikou
                shape_height = float(ar_size_shape[0])
                half_shape_height = shape_height / 2.0
                y_base_profile = -half_shape_height
                arCoor_profile = DefMath.profile2D_shapCT(size_shape, [0, y_base_profile])
                _log_print(
                    f"    [Taikeikou ShapeB] shape_height={shape_height}, half={half_shape_height}, profile_base_y={y_base_profile}"
                )
                _log_print(
                    f"    [Taikeikou ShapeB] arCoor_profile生成: {arCoor_profile is not None}, 座標数={len(arCoor_profile) if arCoor_profile else 0}"
                )
                if arCoor_profile is None:
                    print(f"    [Taikeikou] エラー: 形状名 '{size_shape}' がprofile2D_shapCTのリストに存在しません。")
                else:
                    try:
                        distmodY_value = float(distmodY_shape)
                    except (TypeError, ValueError):
                        distmodY_value = 0.0
                    dir_vertical = np.array(BasePoint1) - np.array(BasePoint4)
                    if np.linalg.norm(dir_vertical) < 1e-6:
                        dir_vertical = np.array(BasePoint2) - np.array(BasePoint3)
                    if np.linalg.norm(dir_vertical) < 1e-6:
                        dir_vertical = np.array([0.0, 0.0, 1.0])
                    dir_vertical = dir_vertical / np.linalg.norm(dir_vertical)
                    target_center = np.array(BasePoint4) + dir_vertical * (half_shape_height + distmodY_value)
                    shift_vec = target_center - p1mod_shape_3D_al
                    p1mod_shape_3D_al = p1mod_shape_3D_al + shift_vec
                    p2mod_shape_3D_al = p2mod_shape_3D_al + shift_vec
                    _log_print(f"    [Taikeikou ShapeB] dir_vertical={dir_vertical}, distmodY={distmodY_value}")
                    _log_print(
                        f"    [Taikeikou ShapeB] target_center={target_center.tolist()}, shift_vec={shift_vec.tolist()}"
                    )
                    _log_print(
                        f"    [Taikeikou ShapeB] p1mod(after)={p1mod_shape_3D_al.tolist()}, p2mod(after)={p2mod_shape_3D_al.tolist()}"
                    )

                    solid_shape = DefIFC.extrude_profile_and_align(
                        ifc_file,
                        arCoor_profile,
                        DefMath.Calculate_distance_p2p(p1mod_shape, p2mod_shape),
                        p1mod_shape_3D_al,
                        p2mod_shape_3D_al,
                        p3mod_shape_3D_al,
                    )
                    color_style = DefIFC.create_color(ifc_file, 70.0, 100.0, 150.0)  # スチールブルー
                    styled_item = ifc_file.createIfcStyledItem(Item=solid_shape, Styles=[color_style])
                    shape_representation = ifc_file.createIfcShapeRepresentation(
                        ContextOfItems=geom_context,
                        RepresentationIdentifier="Body",
                        RepresentationType="Brep",
                        Items=[solid_shape],
                    )
                    # 位置情報を含む名前を生成: {Name}_G{Girder1}_G{Girder2}_C1_CT{Size}
                    # 対傾構は通常中間点（C1）を使用
                    girder1_raw = girder_taikeikou[0] if len(girder_taikeikou) > 0 else ""
                    girder2_raw = girder_taikeikou[1] if len(girder_taikeikou) > 1 else ""
                    import re

                    girder1_num = re.sub(r"^G", "", girder1_raw) if girder1_raw.startswith("G") else girder1_raw
                    girder2_num = re.sub(r"^G", "", girder2_raw) if girder2_raw.startswith("G") else girder2_raw
                    shape_name = f"{name_taikeikou}_G{girder1_num}_G{girder2_num}_C1_CT{size_shape}"
                    DefIFC.Add_shape_representation_in_Beam(ifc_file, bridge_span, shape_representation, shape_name)
            elif type_shape == "L":
                distmodX_shape = Calculate_DistModX_Shape(
                    vstiff_taikeikou, guss_taikeikou, gau_gus, gau_shape, size_shape, "L"
                )
                p1mod_shape_3D_al = (
                    DefMath.Transform_point_face2face(p1mod_shape, p1_2d, p2_2d, p3_2d, p1_3d, p2_3d, p3_3d)
                    + distmodX_shape * normal_taikeikou
                )
                p2mod_shape_3D_al = (
                    DefMath.Transform_point_face2face(p2mod_shape, p1_2d, p2_2d, p3_2d, p1_3d, p2_3d, p3_3d)
                    + distmodX_shape * normal_taikeikou
                )
                if dir_shape == "U":
                    if gau_shape == "A":
                        p3mod_shape_3D_al = p2mod_shape_3D_al - 100 * normal_taikeikou
                        arCoor_profile = DefMath.profile2D_shapL(size_shape, [0, -distmodY_shape])
                        if arCoor_profile is None:
                            print(
                                f"    [Taikeikou] エラー: 形状名 '{size_shape}' がprofile2D_shapLのリストに存在しません。"
                            )
                        else:
                            solid_shape = DefIFC.extrude_profile_and_align(
                                ifc_file,
                                arCoor_profile,
                                DefMath.Calculate_distance_p2p(p1mod_shape, p2mod_shape),
                                p1mod_shape_3D_al,
                                p2mod_shape_3D_al,
                                p3mod_shape_3D_al,
                            )
                    else:
                        p3mod_shape_3D_al = p1mod_shape_3D_al + 100 * normal_taikeikou
                        arCoor_profile = DefMath.profile2D_shapL(size_shape, [0, -distmodY_shape])
                        solid_shape = DefIFC.extrude_profile_and_align(
                            ifc_file,
                            arCoor_profile,
                            DefMath.Calculate_distance_p2p(p1mod_shape, p2mod_shape),
                            p2mod_shape_3D_al,
                            p1mod_shape_3D_al,
                            p3mod_shape_3D_al,
                        )
                else:
                    if gau_shape == "A":
                        p3mod_shape_3D_al = p1mod_shape_3D_al - 100 * normal_taikeikou
                        arCoor_profile = DefMath.profile2D_shapL(size_shape, [0, -distmodY_shape])
                        solid_shape = DefIFC.extrude_profile_and_align(
                            ifc_file,
                            arCoor_profile,
                            DefMath.Calculate_distance_p2p(p1mod_shape, p2mod_shape),
                            p2mod_shape_3D_al,
                            p1mod_shape_3D_al,
                            p3mod_shape_3D_al,
                        )
                    else:
                        p3mod_shape_3D_al = p2mod_shape_3D_al + 100 * normal_taikeikou
                        arCoor_profile = DefMath.profile2D_shapL(size_shape, [0, -distmodY_shape])
                        if arCoor_profile is None:
                            print(
                                f"    [Taikeikou] エラー: 形状名 '{size_shape}' がprofile2D_shapLのリストに存在しません。"
                            )
                        else:
                            solid_shape = DefIFC.extrude_profile_and_align(
                                ifc_file,
                                arCoor_profile,
                                DefMath.Calculate_distance_p2p(p1mod_shape, p2mod_shape),
                                p1mod_shape_3D_al,
                                p2mod_shape_3D_al,
                                p3mod_shape_3D_al,
                            )

                color_style = DefIFC.create_color(ifc_file, 70.0, 100.0, 150.0)  # スチールブルー
                styled_item = ifc_file.createIfcStyledItem(Item=solid_shape, Styles=[color_style])
                shape_representation = ifc_file.createIfcShapeRepresentation(
                    ContextOfItems=geom_context,
                    RepresentationIdentifier="Body",
                    RepresentationType="Brep",
                    Items=[solid_shape],
                )
                # 位置情報を含む名前を生成: {Name}_G{Girder1}_G{Girder2}_C1_L{Size}
                # 対傾構は通常中間点（C1）を使用
                girder1_raw = girder_taikeikou[0] if len(girder_taikeikou) > 0 else ""
                girder2_raw = girder_taikeikou[1] if len(girder_taikeikou) > 1 else ""
                import re

                girder1_num = re.sub(r"^G", "", girder1_raw) if girder1_raw.startswith("G") else girder1_raw
                girder2_num = re.sub(r"^G", "", girder2_raw) if girder2_raw.startswith("G") else girder2_raw
                shape_name = f"{name_taikeikou}_G{girder1_num}_G{girder2_num}_C1_L{size_shape}"
                DefIFC.Add_shape_representation_in_Beam(ifc_file, bridge_span, shape_representation, shape_name)

        if shapeL:
            _log_print(f"    [Taikeikou ShapeL] 処理開始: shapeL={shapeL}")
            type_shape, size_shape, mat_shape, dir_shape, distmodY_shape, pitchmod_shape = shapeL
            ar_size_shape = size_shape.split("x")
            distmodX_shape = Calculate_DistModX_Shape(
                vstiff_taikeikou, guss_taikeikou, gau_gus, gau_shape, size_shape, "L"
            )
            # 対角線の斜め配置: 左上から右下へ（ModPoint1からModPoint3へ）
            _log_print(f"    [Taikeikou ShapeL] ModPoint1_2D={ModPoint1_2D}, ModPoint3_2D={ModPoint3_2D}")
            if typ_taikeikou == "Type1D":
                p1mod_shape, p2mod_shape = Calculate_Pse_Shape(pitchmod_shape, ModPoint1_2D, ModPoint3_2D, "XYZ")
            elif typ_taikeikou == "Type1U":
                p1mod_shape, p2mod_shape = Calculate_Pse_Shape(pitchmod_shape, ModPoint1_2D, ModPoint3_2D, "XYZ")
            else:
                print(f"Trường hợp type taikeikou là {typ_taikeikou} chưa phát triển")
            _log_print(
                f"    [Taikeikou ShapeL] 計算後: p1mod_shape={p1mod_shape}, p2mod_shape={p2mod_shape}, type_shape={type_shape}"
            )

            if type_shape == "CT":
                distmodX_shape = Calculate_DistModX_Shape(
                    vstiff_taikeikou, guss_taikeikou, gau_gus, gau_shape, size_shape, "CT"
                )
                p1mod_shape_3D_al = (
                    DefMath.Transform_point_face2face(p1mod_shape, p1_2d, p2_2d, p3_2d, p1_3d, p2_3d, p3_3d)
                    + distmodX_shape * normal_taikeikou
                )
                p2mod_shape_3D_al = (
                    DefMath.Transform_point_face2face(p2mod_shape, p1_2d, p2_2d, p3_2d, p1_3d, p2_3d, p3_3d)
                    + distmodX_shape * normal_taikeikou
                )
                arCoor_profile = DefMath.profile2D_shapCT(size_shape, [0, distmodY_shape - float(ar_size_shape[0])])
                if arCoor_profile is None:
                    print(f"    [Taikeikou] エラー: 形状名 '{size_shape}' がprofile2D_shapCTのリストに存在しません。")
                else:
                    if dir_shape == "U":
                        p3mod_shape_3D_al = p1mod_shape_3D_al - 100 * normal_taikeikou
                    else:
                        p3mod_shape_3D_al = p1mod_shape_3D_al + 100 * normal_taikeikou
                    solid_shape = DefIFC.extrude_profile_and_align(
                        ifc_file,
                        arCoor_profile,
                        DefMath.Calculate_distance_p2p(p1mod_shape, p2mod_shape),
                        p1mod_shape_3D_al,
                        p2mod_shape_3D_al,
                        p3mod_shape_3D_al,
                    )
                    color_style = DefIFC.create_color(ifc_file, 70.0, 100.0, 150.0)  # スチールブルー
                    styled_item = ifc_file.createIfcStyledItem(Item=solid_shape, Styles=[color_style])
                    shape_representation = ifc_file.createIfcShapeRepresentation(
                        ContextOfItems=geom_context,
                        RepresentationIdentifier="Body",
                        RepresentationType="Brep",
                        Items=[solid_shape],
                    )
                    # 位置情報を含む名前を生成: {Name}_G{Girder1}_G{Girder2}_C1_CT{Size}
                    # 対傾構は通常中間点（C1）を使用
                    girder1_raw = girder_taikeikou[0] if len(girder_taikeikou) > 0 else ""
                    girder2_raw = girder_taikeikou[1] if len(girder_taikeikou) > 1 else ""
                    import re

                    girder1_num = re.sub(r"^G", "", girder1_raw) if girder1_raw.startswith("G") else girder1_raw
                    girder2_num = re.sub(r"^G", "", girder2_raw) if girder2_raw.startswith("G") else girder2_raw
                    shape_name = f"{name_taikeikou}_G{girder1_num}_G{girder2_num}_C1_CT{size_shape}"
                    DefIFC.Add_shape_representation_in_Beam(ifc_file, bridge_span, shape_representation, shape_name)
            elif type_shape == "L":
                p1mod_shape_3D_al = (
                    DefMath.Transform_point_face2face(p1mod_shape, p1_2d, p2_2d, p3_2d, p1_3d, p2_3d, p3_3d)
                    + distmodX_shape * normal_taikeikou
                )
                p2mod_shape_3D_al = (
                    DefMath.Transform_point_face2face(p2mod_shape, p1_2d, p2_2d, p3_2d, p1_3d, p2_3d, p3_3d)
                    + distmodX_shape * normal_taikeikou
                )
                if dir_shape == "U":
                    if gau_shape == "A":
                        p3mod_shape_3D_al = p2mod_shape_3D_al - 100 * normal_taikeikou
                        arCoor_profile = DefMath.profile2D_shapL(size_shape, [0, -distmodY_shape])
                        if arCoor_profile is None:
                            print(
                                f"    [Taikeikou] エラー: 形状名 '{size_shape}' がprofile2D_shapLのリストに存在しません。"
                            )
                        else:
                            solid_shape = DefIFC.extrude_profile_and_align(
                                ifc_file,
                                arCoor_profile,
                                DefMath.Calculate_distance_p2p(p1mod_shape, p2mod_shape),
                                p1mod_shape_3D_al,
                                p2mod_shape_3D_al,
                                p3mod_shape_3D_al,
                            )
                    else:
                        p3mod_shape_3D_al = p1mod_shape_3D_al + 100 * normal_taikeikou
                        arCoor_profile = DefMath.profile2D_shapL(size_shape, [0, -distmodY_shape])
                        solid_shape = DefIFC.extrude_profile_and_align(
                            ifc_file,
                            arCoor_profile,
                            DefMath.Calculate_distance_p2p(p1mod_shape, p2mod_shape),
                            p2mod_shape_3D_al,
                            p1mod_shape_3D_al,
                            p3mod_shape_3D_al,
                        )
                else:
                    if gau_shape == "A":
                        p3mod_shape_3D_al = p1mod_shape_3D_al - 100 * normal_taikeikou
                        arCoor_profile = DefMath.profile2D_shapL(size_shape, [0, -distmodY_shape])
                        solid_shape = DefIFC.extrude_profile_and_align(
                            ifc_file,
                            arCoor_profile,
                            DefMath.Calculate_distance_p2p(p1mod_shape, p2mod_shape),
                            p2mod_shape_3D_al,
                            p1mod_shape_3D_al,
                            p3mod_shape_3D_al,
                        )
                    else:
                        p3mod_shape_3D_al = p2mod_shape_3D_al + 100 * normal_taikeikou
                        arCoor_profile = DefMath.profile2D_shapL(size_shape, [0, -distmodY_shape])
                        if arCoor_profile is None:
                            print(
                                f"    [Taikeikou] エラー: 形状名 '{size_shape}' がprofile2D_shapLのリストに存在しません。"
                            )
                        else:
                            solid_shape = DefIFC.extrude_profile_and_align(
                                ifc_file,
                                arCoor_profile,
                                DefMath.Calculate_distance_p2p(p1mod_shape, p2mod_shape),
                                p1mod_shape_3D_al,
                                p2mod_shape_3D_al,
                                p3mod_shape_3D_al,
                            )

                color_style = DefIFC.create_color(ifc_file, 70.0, 100.0, 150.0)  # スチールブルー
                styled_item = ifc_file.createIfcStyledItem(Item=solid_shape, Styles=[color_style])
                shape_representation = ifc_file.createIfcShapeRepresentation(
                    ContextOfItems=geom_context,
                    RepresentationIdentifier="Body",
                    RepresentationType="Brep",
                    Items=[solid_shape],
                )
                # 位置情報を含む名前を生成: {Name}_G{Girder1}_G{Girder2}_C1_L{Size}
                # 対傾構は通常中間点（C1）を使用
                girder1_raw = girder_taikeikou[0] if len(girder_taikeikou) > 0 else ""
                girder2_raw = girder_taikeikou[1] if len(girder_taikeikou) > 1 else ""
                import re

                girder1_num = re.sub(r"^G", "", girder1_raw) if girder1_raw.startswith("G") else girder1_raw
                girder2_num = re.sub(r"^G", "", girder2_raw) if girder2_raw.startswith("G") else girder2_raw
                shape_name = f"{name_taikeikou}_G{girder1_num}_G{girder2_num}_C1_L{size_shape}"
                DefIFC.Add_shape_representation_in_Beam(ifc_file, bridge_span, shape_representation, shape_name)

        if shapeR:
            _log_print(f"    [Taikeikou ShapeR] 処理開始: shapeR={shapeR}")
            type_shape, size_shape, mat_shape, dir_shape, distmodY_shape, pitchmod_shape = shapeR
            ar_size_shape = size_shape.split("x")
            distmodX_shape = Calculate_DistModX_Shape(
                vstiff_taikeikou, guss_taikeikou, gau_gus, gau_shape, size_shape, "L"
            )
            # 対角線の斜め配置: 右上から左下へ（ModPoint2からModPoint4へ）
            _log_print(f"    [Taikeikou ShapeR] ModPoint2_2D={ModPoint2_2D}, ModPoint4_2D={ModPoint4_2D}")
            if typ_taikeikou == "Type1D":
                p1mod_shape, p2mod_shape = Calculate_Pse_Shape(pitchmod_shape, ModPoint2_2D, ModPoint4_2D, "XYZ")
            elif typ_taikeikou == "Type1U":
                p1mod_shape, p2mod_shape = Calculate_Pse_Shape(pitchmod_shape, ModPoint2_2D, ModPoint4_2D, "XYZ")
            else:
                print(f"Trường hợp type taikeikou là {typ_taikeikou} chưa phát triển")
            _log_print(
                f"    [Taikeikou ShapeR] 計算後: p1mod_shape={p1mod_shape}, p2mod_shape={p2mod_shape}, type_shape={type_shape}"
            )

            if type_shape == "CT":
                distmodX_shape = Calculate_DistModX_Shape(
                    vstiff_taikeikou, guss_taikeikou, gau_gus, gau_shape, size_shape, "CT"
                )
                p1mod_shape_3D_al = (
                    DefMath.Transform_point_face2face(p1mod_shape, p1_2d, p2_2d, p3_2d, p1_3d, p2_3d, p3_3d)
                    + distmodX_shape * normal_taikeikou
                )
                p2mod_shape_3D_al = (
                    DefMath.Transform_point_face2face(p2mod_shape, p1_2d, p2_2d, p3_2d, p1_3d, p2_3d, p3_3d)
                    + distmodX_shape * normal_taikeikou
                )
                arCoor_profile = DefMath.profile2D_shapCT(size_shape, [0, distmodY_shape - float(ar_size_shape[0])])
                if arCoor_profile is None:
                    print(f"    [Taikeikou] エラー: 形状名 '{size_shape}' がprofile2D_shapCTのリストに存在しません。")
                else:
                    if dir_shape == "U":
                        p3mod_shape_3D_al = p1mod_shape_3D_al - 100 * normal_taikeikou
                    else:
                        p3mod_shape_3D_al = p1mod_shape_3D_al + 100 * normal_taikeikou
                    solid_shape = DefIFC.extrude_profile_and_align(
                        ifc_file,
                        arCoor_profile,
                        DefMath.Calculate_distance_p2p(p1mod_shape, p2mod_shape),
                        p1mod_shape_3D_al,
                        p2mod_shape_3D_al,
                        p3mod_shape_3D_al,
                    )
                    color_style = DefIFC.create_color(ifc_file, 70.0, 100.0, 150.0)  # スチールブルー
                    styled_item = ifc_file.createIfcStyledItem(Item=solid_shape, Styles=[color_style])
                    shape_representation = ifc_file.createIfcShapeRepresentation(
                        ContextOfItems=geom_context,
                        RepresentationIdentifier="Body",
                        RepresentationType="Brep",
                        Items=[solid_shape],
                    )
                    # 位置情報を含む名前を生成: {Name}_G{Girder1}_G{Girder2}_C1_CT{Size}
                    # 対傾構は通常中間点（C1）を使用
                    girder1_raw = girder_taikeikou[0] if len(girder_taikeikou) > 0 else ""
                    girder2_raw = girder_taikeikou[1] if len(girder_taikeikou) > 1 else ""
                    import re

                    girder1_num = re.sub(r"^G", "", girder1_raw) if girder1_raw.startswith("G") else girder1_raw
                    girder2_num = re.sub(r"^G", "", girder2_raw) if girder2_raw.startswith("G") else girder2_raw
                    shape_name = f"{name_taikeikou}_G{girder1_num}_G{girder2_num}_C1_CT{size_shape}"
                    DefIFC.Add_shape_representation_in_Beam(ifc_file, bridge_span, shape_representation, shape_name)
            elif type_shape == "L":
                p1mod_shape_3D_al = (
                    DefMath.Transform_point_face2face(p1mod_shape, p1_2d, p2_2d, p3_2d, p1_3d, p2_3d, p3_3d)
                    + distmodX_shape * normal_taikeikou
                )
                p2mod_shape_3D_al = (
                    DefMath.Transform_point_face2face(p2mod_shape, p1_2d, p2_2d, p3_2d, p1_3d, p2_3d, p3_3d)
                    + distmodX_shape * normal_taikeikou
                )
                if dir_shape == "U":
                    if gau_shape == "A":
                        p3mod_shape_3D_al = p2mod_shape_3D_al - 100 * normal_taikeikou
                        arCoor_profile = DefMath.profile2D_shapL(size_shape, [0, -distmodY_shape])
                        if arCoor_profile is None:
                            print(
                                f"    [Taikeikou] エラー: 形状名 '{size_shape}' がprofile2D_shapLのリストに存在しません。"
                            )
                        else:
                            solid_shape = DefIFC.extrude_profile_and_align(
                                ifc_file,
                                arCoor_profile,
                                DefMath.Calculate_distance_p2p(p1mod_shape, p2mod_shape),
                                p1mod_shape_3D_al,
                                p2mod_shape_3D_al,
                                p3mod_shape_3D_al,
                            )
                    else:
                        p3mod_shape_3D_al = p1mod_shape_3D_al + 100 * normal_taikeikou
                        arCoor_profile = DefMath.profile2D_shapL(size_shape, [0, -distmodY_shape])
                        solid_shape = DefIFC.extrude_profile_and_align(
                            ifc_file,
                            arCoor_profile,
                            DefMath.Calculate_distance_p2p(p1mod_shape, p2mod_shape),
                            p2mod_shape_3D_al,
                            p1mod_shape_3D_al,
                            p3mod_shape_3D_al,
                        )
                else:
                    if gau_shape == "A":
                        p3mod_shape_3D_al = p1mod_shape_3D_al - 100 * normal_taikeikou
                        arCoor_profile = DefMath.profile2D_shapL(size_shape, [0, -distmodY_shape])
                        solid_shape = DefIFC.extrude_profile_and_align(
                            ifc_file,
                            arCoor_profile,
                            DefMath.Calculate_distance_p2p(p1mod_shape, p2mod_shape),
                            p2mod_shape_3D_al,
                            p1mod_shape_3D_al,
                            p3mod_shape_3D_al,
                        )
                    else:
                        p3mod_shape_3D_al = p2mod_shape_3D_al + 100 * normal_taikeikou
                        arCoor_profile = DefMath.profile2D_shapL(size_shape, [0, -distmodY_shape])
                        if arCoor_profile is None:
                            print(
                                f"    [Taikeikou] エラー: 形状名 '{size_shape}' がprofile2D_shapLのリストに存在しません。"
                            )
                        else:
                            solid_shape = DefIFC.extrude_profile_and_align(
                                ifc_file,
                                arCoor_profile,
                                DefMath.Calculate_distance_p2p(p1mod_shape, p2mod_shape),
                                p1mod_shape_3D_al,
                                p2mod_shape_3D_al,
                                p3mod_shape_3D_al,
                            )

                color_style = DefIFC.create_color(ifc_file, 70.0, 100.0, 150.0)  # スチールブルー
                styled_item = ifc_file.createIfcStyledItem(Item=solid_shape, Styles=[color_style])
                shape_representation = ifc_file.createIfcShapeRepresentation(
                    ContextOfItems=geom_context,
                    RepresentationIdentifier="Body",
                    RepresentationType="Brep",
                    Items=[solid_shape],
                )
                # 位置情報を含む名前を生成: {Name}_G{Girder1}_G{Girder2}_C1_L{Size}
                # 対傾構は通常中間点（C1）を使用
                girder1_raw = girder_taikeikou[0] if len(girder_taikeikou) > 0 else ""
                girder2_raw = girder_taikeikou[1] if len(girder_taikeikou) > 1 else ""
                import re

                girder1_num = re.sub(r"^G", "", girder1_raw) if girder1_raw.startswith("G") else girder1_raw
                girder2_num = re.sub(r"^G", "", girder2_raw) if girder2_raw.startswith("G") else girder2_raw
                shape_name = f"{name_taikeikou}_G{girder1_num}_G{girder2_num}_C1_L{size_shape}"
                DefIFC.Add_shape_representation_in_Beam(ifc_file, bridge_span, shape_representation, shape_name)
    else:
        _log_print("    [Taikeikou] 警告: shape_taikeikouが空またはNoneです。")

    # -------------------Guss（ガセットプレート）-------------------------------------------------------------------
    if guss_taikeikou:
        tl_guss, tr_guss, bl_guss, br_guss, mid_guss = (
            guss_taikeikou["TL"],
            guss_taikeikou["TR"],
            guss_taikeikou["BL"],
            guss_taikeikou["BR"],
            guss_taikeikou["Mid"],
        )
        if tl_guss:
            from src.bridge_json_to_ifc.ifc_utils_new.components.DefGusset import Draw_3DSolid_Guss

            solid_guss_tl = Draw_3DSolid_Guss(
                ifc_all,
                shape_taikeikou,
                vstiff_taikeikou,
                type_taikeikou,
                ModPoint1_2D,
                ModPoint2_2D,
                ModPoint3_2D,
                ModPoint4_2D,
                CenPoint_2D,
                arCoord_hole_tl,
                tl_guss,
                "TL",
                p1_3d,
                p2_3d,
                p3_3d,
            )
            color_style = DefIFC.create_color(ifc_file, 90.0, 120.0, 170.0)  # ライトスチールブルー
            styled_item = ifc_file.createIfcStyledItem(Item=solid_guss_tl, Styles=[color_style])
            shape_representation = ifc_file.createIfcShapeRepresentation(
                ContextOfItems=geom_context,
                RepresentationIdentifier="Body",
                RepresentationType="Brep",
                Items=[solid_guss_tl],
            )
            # 位置情報を含む名前を生成: {Name}_G{Girder1}_G{Girder2}_C1_GussTL
            # 対傾構は通常中間点（C1）を使用
            girder1_raw = girder_taikeikou[0] if len(girder_taikeikou) > 0 else ""
            girder2_raw = girder_taikeikou[1] if len(girder_taikeikou) > 1 else ""
            import re

            girder1_num = re.sub(r"^G", "", girder1_raw) if girder1_raw.startswith("G") else girder1_raw
            girder2_num = re.sub(r"^G", "", girder2_raw) if girder2_raw.startswith("G") else girder2_raw
            guss_name = f"{name_taikeikou}_G{girder1_num}_G{girder2_num}_C1_GussTL"
            DefIFC.Add_shape_representation_in_Beam(ifc_file, bridge_span, shape_representation, guss_name)

        if tr_guss:
            from src.bridge_json_to_ifc.ifc_utils_new.components.DefGusset import Draw_3DSolid_Guss

            solid_guss_tr = Draw_3DSolid_Guss(
                ifc_all,
                shape_taikeikou,
                vstiff_taikeikou,
                type_taikeikou,
                ModPoint1_2D,
                ModPoint2_2D,
                ModPoint3_2D,
                ModPoint4_2D,
                CenPoint_2D,
                arCoord_hole_tr,
                tr_guss,
                "TR",
                p1_3d,
                p2_3d,
                p3_3d,
            )
            color_style = DefIFC.create_color(ifc_file, 90.0, 120.0, 170.0)  # ライトスチールブルー
            styled_item = ifc_file.createIfcStyledItem(Item=solid_guss_tr, Styles=[color_style])
            shape_representation = ifc_file.createIfcShapeRepresentation(
                ContextOfItems=geom_context,
                RepresentationIdentifier="Body",
                RepresentationType="Brep",
                Items=[solid_guss_tr],
            )
            # 位置情報を含む名前を生成: {Name}_G{Girder1}_G{Girder2}_C1_GussTR
            # 対傾構は通常中間点（C1）を使用
            girder1_raw = girder_taikeikou[0] if len(girder_taikeikou) > 0 else ""
            girder2_raw = girder_taikeikou[1] if len(girder_taikeikou) > 1 else ""
            import re

            girder1_num = re.sub(r"^G", "", girder1_raw) if girder1_raw.startswith("G") else girder1_raw
            girder2_num = re.sub(r"^G", "", girder2_raw) if girder2_raw.startswith("G") else girder2_raw
            guss_name = f"{name_taikeikou}_G{girder1_num}_G{girder2_num}_C1_GussTR"
            DefIFC.Add_shape_representation_in_Beam(ifc_file, bridge_span, shape_representation, guss_name)

        if bl_guss:
            from src.bridge_json_to_ifc.ifc_utils_new.components.DefGusset import Draw_3DSolid_Guss

            solid_guss_bl = Draw_3DSolid_Guss(
                ifc_all,
                shape_taikeikou,
                vstiff_taikeikou,
                type_taikeikou,
                ModPoint1_2D,
                ModPoint2_2D,
                ModPoint3_2D,
                ModPoint4_2D,
                CenPoint_2D,
                arCoord_hole_bl,
                bl_guss,
                "BL",
                p1_3d,
                p2_3d,
                p3_3d,
            )
            color_style = DefIFC.create_color(ifc_file, 90.0, 120.0, 170.0)  # ライトスチールブルー
            styled_item = ifc_file.createIfcStyledItem(Item=solid_guss_bl, Styles=[color_style])
            shape_representation = ifc_file.createIfcShapeRepresentation(
                ContextOfItems=geom_context,
                RepresentationIdentifier="Body",
                RepresentationType="Brep",
                Items=[solid_guss_bl],
            )
            # 位置情報を含む名前を生成: {Name}_G{Girder1}_G{Girder2}_C1_GussBL
            # 対傾構は通常中間点（C1）を使用
            girder1_raw = girder_taikeikou[0] if len(girder_taikeikou) > 0 else ""
            girder2_raw = girder_taikeikou[1] if len(girder_taikeikou) > 1 else ""
            import re

            girder1_num = re.sub(r"^G", "", girder1_raw) if girder1_raw.startswith("G") else girder1_raw
            girder2_num = re.sub(r"^G", "", girder2_raw) if girder2_raw.startswith("G") else girder2_raw
            guss_name = f"{name_taikeikou}_G{girder1_num}_G{girder2_num}_C1_GussBL"
            DefIFC.Add_shape_representation_in_Beam(ifc_file, bridge_span, shape_representation, guss_name)

        if br_guss:
            from src.bridge_json_to_ifc.ifc_utils_new.components.DefGusset import Draw_3DSolid_Guss

            solid_guss_br = Draw_3DSolid_Guss(
                ifc_all,
                shape_taikeikou,
                vstiff_taikeikou,
                type_taikeikou,
                ModPoint1_2D,
                ModPoint2_2D,
                ModPoint3_2D,
                ModPoint4_2D,
                CenPoint_2D,
                arCoord_hole_br,
                br_guss,
                "BR",
                p1_3d,
                p2_3d,
                p3_3d,
            )
            color_style = DefIFC.create_color(ifc_file, 90.0, 120.0, 170.0)  # ライトスチールブルー
            styled_item = ifc_file.createIfcStyledItem(Item=solid_guss_br, Styles=[color_style])
            shape_representation = ifc_file.createIfcShapeRepresentation(
                ContextOfItems=geom_context,
                RepresentationIdentifier="Body",
                RepresentationType="Brep",
                Items=[solid_guss_br],
            )
            # 位置情報を含む名前を生成: {Name}_G{Girder1}_G{Girder2}_C1_GussBR
            # 対傾構は通常中間点（C1）を使用
            girder1_raw = girder_taikeikou[0] if len(girder_taikeikou) > 0 else ""
            girder2_raw = girder_taikeikou[1] if len(girder_taikeikou) > 1 else ""
            import re

            girder1_num = re.sub(r"^G", "", girder1_raw) if girder1_raw.startswith("G") else girder1_raw
            girder2_num = re.sub(r"^G", "", girder2_raw) if girder2_raw.startswith("G") else girder2_raw
            guss_name = f"{name_taikeikou}_G{girder1_num}_G{girder2_num}_C1_GussBR"
            DefIFC.Add_shape_representation_in_Beam(ifc_file, bridge_span, shape_representation, guss_name)

        if mid_guss:
            from src.bridge_json_to_ifc.ifc_utils_new.components.DefGusset import Draw_3DSolid_Guss

            solid_guss_mid = Draw_3DSolid_Guss(
                ifc_all,
                shape_taikeikou,
                vstiff_taikeikou,
                type_taikeikou,
                ModPoint1_2D,
                ModPoint2_2D,
                ModPoint3_2D,
                ModPoint4_2D,
                CenPoint_2D,
                arCoord_hole_br,
                mid_guss,
                "MID",
                p1_3d,
                p2_3d,
                p3_3d,
            )
            color_style = DefIFC.create_color(ifc_file, 90.0, 120.0, 170.0)  # ライトスチールブルー
            styled_item = ifc_file.createIfcStyledItem(Item=solid_guss_mid, Styles=[color_style])
            shape_representation = ifc_file.createIfcShapeRepresentation(
                ContextOfItems=geom_context,
                RepresentationIdentifier="Body",
                RepresentationType="Brep",
                Items=[solid_guss_mid],
            )
            # 位置情報を含む名前を生成: {Name}_G{Girder1}_G{Girder2}_C1_GussMID
            # 対傾構は通常中間点（C1）を使用
            girder1_raw = girder_taikeikou[0] if len(girder_taikeikou) > 0 else ""
            girder2_raw = girder_taikeikou[1] if len(girder_taikeikou) > 1 else ""
            import re

            girder1_num = re.sub(r"^G", "", girder1_raw) if girder1_raw.startswith("G") else girder1_raw
            girder2_num = re.sub(r"^G", "", girder2_raw) if girder2_raw.startswith("G") else girder2_raw
            guss_name = f"{name_taikeikou}_G{girder1_num}_G{girder2_num}_C1_GussMID"
            DefIFC.Add_shape_representation_in_Beam(ifc_file, bridge_span, shape_representation, guss_name)


def Calculate_Point_Taikeikou(
    Data_Panel,
    Senkei_data,
    name_taikeikou,
    point_taikeikou,
    distmod_taikeikou,
    girder_taikeikou=None,
    number_mainblock=None,
    section_taikeikou="C1",
):
    # 対傾構のPointは線形名のリストなので、各線形上の指定セクション（デフォルトは"C1"）を使用
    # 指定セクションがない場合は最初の点（"S1"）を使用
    # 接続点をWebパネルの端に調整するため、Webパネルの座標を使用（Data_Panelが利用可能な場合）

    from src.bridge_json_to_ifc.ifc_utils_new.utils.DefBridgeUtils import (
        Load_Coordinate_Panel,
    )

    # Webパネルの座標を取得して接続点を計算（Data_Panelが利用可能な場合）
    web1_coords = None
    web2_coords = None
    if Data_Panel is not None and girder_taikeikou is not None and number_mainblock is not None:
        # number_mainblockがリストの場合は最初の要素を使用
        if isinstance(number_mainblock, list):
            if len(number_mainblock) > 0:
                number_mainblock = number_mainblock[0]
            else:
                number_mainblock = "1"
        elif not isinstance(number_mainblock, str):
            number_mainblock = str(number_mainblock)

        # G1のWebパネル: G1B1W
        name_web1 = girder_taikeikou[0] + "B" + number_mainblock + "W"
        name_web2 = girder_taikeikou[1] + "B" + number_mainblock + "W"

        # Webパネルの座標を取得
        Line_web1 = None
        Line_web2 = None
        Sec_web1 = None
        Sec_web2 = None
        web1_coords = None
        web2_coords = None
        for panel in Data_Panel:
            if panel["Name"] == name_web1:
                Line_web1 = panel["Line"]
                Sec_web1 = panel["Sec"]
                web1_coords = Load_Coordinate_Panel(Senkei_data, Line_web1, Sec_web1)
                break
        for panel in Data_Panel:
            if panel["Name"] == name_web2:
                Line_web2 = panel["Line"]
                Sec_web2 = panel["Sec"]
                web2_coords = Load_Coordinate_Panel(Senkei_data, Line_web2, Sec_web2)
                break

    # 指定セクション（デフォルトはC1）を取得
    # BasePoint1: G1の上フランジ（TG1）の指定セクション
    # BasePoint2: G2の上フランジ（TG2）の指定セクション
    # BasePoint3: G2の下フランジ（BG2）の指定セクション
    # BasePoint4: G1の下フランジ（BG1）の指定セクション

    _log_print(f"    [Calculate_Point_Taikeikou] セクション名ベース: {section_taikeikou}, 線形: {point_taikeikou}")
    BasePoint1 = Load_Coordinate_Point(Senkei_data, point_taikeikou[0], section_taikeikou)
    if BasePoint1 is None:
        coordLine1 = Load_Coordinate_PolLine(Senkei_data, point_taikeikou[0])
        if len(coordLine1) == 0:
            raise ValueError(f"対傾構 '{name_taikeikou}': 線形 '{point_taikeikou[0]}' が見つかりません")
        BasePoint1 = coordLine1[0]
        _log_print(
            f"    [Calculate_Point_Taikeikou] 警告: セクション '{section_taikeikou}' が線形 '{point_taikeikou[0]}' に見つかりません。最初の点を使用します: {BasePoint1}"
        )
    else:
        _log_print(
            f"    [Calculate_Point_Taikeikou] BasePoint1 ({point_taikeikou[0]}, {section_taikeikou}): {BasePoint1}"
        )

    BasePoint2 = Load_Coordinate_Point(Senkei_data, point_taikeikou[1], section_taikeikou)
    if BasePoint2 is None:
        coordLine2 = Load_Coordinate_PolLine(Senkei_data, point_taikeikou[1])
        if len(coordLine2) == 0:
            raise ValueError(f"対傾構 '{name_taikeikou}': 線形 '{point_taikeikou[1]}' が見つかりません")
        BasePoint2 = coordLine2[0]
        _log_print(
            f"    [Calculate_Point_Taikeikou] 警告: セクション '{section_taikeikou}' が線形 '{point_taikeikou[1]}' に見つかりません。最初の点を使用します: {BasePoint2}"
        )
    else:
        _log_print(
            f"    [Calculate_Point_Taikeikou] BasePoint2 ({point_taikeikou[1]}, {section_taikeikou}): {BasePoint2}"
        )

    BasePoint3 = Load_Coordinate_Point(Senkei_data, point_taikeikou[2], section_taikeikou)
    if BasePoint3 is None:
        coordLine3 = Load_Coordinate_PolLine(Senkei_data, point_taikeikou[2])
        if len(coordLine3) == 0:
            raise ValueError(f"対傾構 '{name_taikeikou}': 線形 '{point_taikeikou[2]}' が見つかりません")
        BasePoint3 = coordLine3[0]
        _log_print(
            f"    [Calculate_Point_Taikeikou] 警告: セクション '{section_taikeikou}' が線形 '{point_taikeikou[2]}' に見つかりません。最初の点を使用します: {BasePoint3}"
        )
    else:
        _log_print(
            f"    [Calculate_Point_Taikeikou] BasePoint3 ({point_taikeikou[2]}, {section_taikeikou}): {BasePoint3}"
        )

    BasePoint4 = Load_Coordinate_Point(Senkei_data, point_taikeikou[3], section_taikeikou)
    if BasePoint4 is None:
        coordLine4 = Load_Coordinate_PolLine(Senkei_data, point_taikeikou[3])
        if len(coordLine4) == 0:
            raise ValueError(f"対傾構 '{name_taikeikou}': 線形 '{point_taikeikou[3]}' が見つかりません")
        BasePoint4 = coordLine4[0]
        _log_print(
            f"    [Calculate_Point_Taikeikou] 警告: セクション '{section_taikeikou}' が線形 '{point_taikeikou[3]}' に見つかりません。最初の点を使用します: {BasePoint4}"
        )
    else:
        _log_print(
            f"    [Calculate_Point_Taikeikou] BasePoint4 ({point_taikeikou[3]}, {section_taikeikou}): {BasePoint4}"
        )

    # Webパネルの座標を使用して接続点を調整
    # Webパネルは通常、TGとBGの2本の線形を持つ
    # 指定セクションに対応するWebパネルの座標を取得
    if Data_Panel and girder_taikeikou and number_mainblock:
        if web1_coords and len(web1_coords) >= 2 and len(web1_coords[0]) >= 2:
            # セクション名ベースの場合
            if Sec_web1 and section_taikeikou in Sec_web1:
                idx_section = Sec_web1.index(section_taikeikou)
                BasePoint1 = web1_coords[0][idx_section]  # 上端
                BasePoint4 = web1_coords[-1][idx_section]  # 下端
            else:
                # 指定セクションのX座標に最も近い点を探す
                target_x = BasePoint1[0]  # 指定セクションのX座標
                closest_idx = 0
                min_dist = abs(web1_coords[0][0][0] - target_x)
                for i, pt in enumerate(web1_coords[0]):
                    dist = abs(pt[0] - target_x)
                    if dist < min_dist:
                        min_dist = dist
                        closest_idx = i
                # Webパネルの上端と下端の座標を使用
                BasePoint1 = web1_coords[0][closest_idx]  # 上端
                BasePoint4 = web1_coords[-1][closest_idx]  # 下端

        if web2_coords and len(web2_coords) >= 2 and len(web2_coords[0]) >= 2:
            # セクション名ベースの場合
            if Sec_web2 and section_taikeikou in Sec_web2:
                idx_section = Sec_web2.index(section_taikeikou)
                BasePoint2 = web2_coords[0][idx_section]  # 上端
                BasePoint3 = web2_coords[-1][idx_section]  # 下端
            else:
                target_x = BasePoint2[0]
                closest_idx = 0
                min_dist = abs(web2_coords[0][0][0] - target_x)
                for i, pt in enumerate(web2_coords[0]):
                    dist = abs(pt[0] - target_x)
                    if dist < min_dist:
                        min_dist = dist
                        closest_idx = i
                BasePoint2 = web2_coords[0][closest_idx]  # 上端
                BasePoint3 = web2_coords[-1][closest_idx]  # 下端

    tl, tr, bl, br = distmod_taikeikou["TL"], distmod_taikeikou["TR"], distmod_taikeikou["BL"], distmod_taikeikou["BR"]

    p1_2d = BasePoint1.copy()
    p1_2d[2] = 0
    p2_2d = BasePoint2.copy()
    p2_2d[2] = 0
    distance = float(tl[0])
    p = DefMath.Point_on_line(p1_2d, p2_2d, distance)
    ppl1 = p.copy()
    ppl2 = p.copy()
    ppl2[0] += 100
    ppl3 = p.copy()
    ppl3[2] += 100
    pp = DefMath.point_per_line(BasePoint1, BasePoint2, BasePoint3)
    p1 = DefMath.Intersection_line_plane(ppl1, ppl2, ppl3, BasePoint1, pp)

    distance = float(tr[0])
    p = DefMath.Point_on_line(p2_2d, p1_2d, distance)
    ppl1 = p.copy()
    ppl2 = p.copy()
    ppl2[0] += 100
    ppl3 = p.copy()
    ppl3[2] += 100
    pp = DefMath.point_per_line(BasePoint2, BasePoint1, BasePoint4)
    p2 = DefMath.Intersection_line_plane(ppl1, ppl2, ppl3, BasePoint2, pp)

    p1_2d = BasePoint4.copy()
    p1_2d[2] = 0
    p2_2d = BasePoint3.copy()
    p2_2d[2] = 0
    distance = float(bl[0])
    p = DefMath.Point_on_line(p1_2d, p2_2d, distance)
    ppl1 = p.copy()
    ppl2 = p.copy()
    ppl2[0] += 100
    ppl3 = p.copy()
    ppl3[2] += 100
    pp = DefMath.point_per_line(BasePoint4, BasePoint2, BasePoint3)
    p4 = DefMath.Intersection_line_plane(ppl1, ppl2, ppl3, BasePoint4, pp)

    distance = float(br[0])
    p = DefMath.Point_on_line(p2_2d, p1_2d, distance)
    ppl1 = p.copy()
    ppl2 = p.copy()
    ppl2[0] += 100
    ppl3 = p.copy()
    ppl3[2] += 100
    pp = DefMath.point_per_line(BasePoint3, BasePoint1, BasePoint4)
    p3 = DefMath.Intersection_line_plane(ppl1, ppl2, ppl3, BasePoint3, pp)

    ModPoint1 = DefMath.Point_on_parallel_line(p1, p1, p4, float(tl[1]))
    ModPoint2 = DefMath.Point_on_parallel_line(p2, p2, p3, float(tr[1]))
    ModPoint3 = DefMath.Point_on_parallel_line(p3, p3, p2, float(br[1]))
    ModPoint4 = DefMath.Point_on_parallel_line(p4, p4, p1, float(bl[1]))

    basepoint = [BasePoint1, BasePoint2, BasePoint3, BasePoint4]
    modpoint = [ModPoint1, ModPoint2, ModPoint3, ModPoint4]

    return basepoint, modpoint


def Draw_3DSolid_Bolt_Taikeikou(ifc_all, arCoord_hole, gap_cen_to_head, gap_cen_to_nut, p1_3d, p2_3d, p3_3d):
    ifc_file, bridge_span, geom_context = ifc_all
    # 穴の座標が空の場合はボルトを生成しない
    if not arCoord_hole or len(arCoord_hole) == 0:
        return
    for i in range(len(arCoord_hole)):
        if not arCoord_hole[i] or len(arCoord_hole[i]) == 0:
            continue
        for i_1 in range(len(arCoord_hole[i])):
            solid_bolt = DefIFC.Draw_Solid_Bolt(
                ifc_file,
                arCoord_hole[i][i_1],
                26.5,
                gap_cen_to_head,
                gap_cen_to_nut,
                p1_3d,
                p1_3d + 100 * DefMath.Normal_vector(p1_3d, p2_3d, p3_3d),
                p2_3d,
            )
            shape_representation = ifc_file.createIfcShapeRepresentation(
                ContextOfItems=geom_context,
                RepresentationIdentifier="Body",
                RepresentationType="Brep",
                Items=[solid_bolt],
            )
            DefIFC.Add_shape_representation_in_Beam(ifc_file, bridge_span, shape_representation, "Bolt")


def Calculate_Length_Bolt_Taikeikou(gau_guss, vstiff_taikeikou, guss_taikeikou, pos):
    gap_cen_to_head = 0
    gap_cen_to_nut = 0

    # vstiff_taikeikouが空の場合はデフォルト値を返す
    if not vstiff_taikeikou or (isinstance(vstiff_taikeikou, dict) and len(vstiff_taikeikou) == 0):
        return gap_cen_to_head, gap_cen_to_nut

    # guss_taikeikouが空の場合はデフォルト値を返す
    if not guss_taikeikou or (isinstance(guss_taikeikou, dict) and len(guss_taikeikou) == 0):
        return gap_cen_to_head, gap_cen_to_nut

    # 必要なキーが存在しない場合はデフォルト値を返す
    if "L" not in vstiff_taikeikou or "R" not in vstiff_taikeikou:
        return gap_cen_to_head, gap_cen_to_nut

    if (
        "TL" not in guss_taikeikou
        or "TR" not in guss_taikeikou
        or "BL" not in guss_taikeikou
        or "BR" not in guss_taikeikou
    ):
        return gap_cen_to_head, gap_cen_to_nut

    vstiff_left = vstiff_taikeikou.get("L", [])
    vstiff_right = vstiff_taikeikou.get("R", [])
    tl_guss = guss_taikeikou.get("TL", [])
    tr_guss = guss_taikeikou.get("TR", [])
    bl_guss = guss_taikeikou.get("BL", [])
    br_guss = guss_taikeikou.get("BR", [])

    # 空のリストの場合はデフォルト値を返す
    if pos == "TL":
        if not vstiff_left or len(vstiff_left) == 0 or not tl_guss or len(tl_guss) == 0:
            return gap_cen_to_head, gap_cen_to_nut
        thick_vstiff, mat_vstiff, width_vstiff = vstiff_left
        thick_guss, mat_guss, distMep, DistShape1, DistShape2 = tl_guss
    elif pos == "TR":
        if not vstiff_right or len(vstiff_right) == 0 or not tr_guss or len(tr_guss) == 0:
            return gap_cen_to_head, gap_cen_to_nut
        thick_vstiff, mat_vstiff, width_vstiff = vstiff_right
        thick_guss, mat_guss, distMep, DistShape1, DistShape2 = tr_guss
    elif pos == "BL":
        if not vstiff_left or len(vstiff_left) == 0 or not bl_guss or len(bl_guss) == 0:
            return gap_cen_to_head, gap_cen_to_nut
        thick_vstiff, mat_vstiff, width_vstiff = vstiff_left
        thick_guss, mat_guss, distMep, DistShape1, DistShape2 = bl_guss
    else:  # pos == "BR":
        if not vstiff_right or len(vstiff_right) == 0 or not br_guss or len(br_guss) == 0:
            return gap_cen_to_head, gap_cen_to_nut
        thick_vstiff, mat_vstiff, width_vstiff = vstiff_right
        thick_guss, mat_guss, distMep, DistShape1, DistShape2 = br_guss

    if gau_guss == "A":
        gap_cen_to_head = thick_vstiff / 2 + thick_guss
        gap_cen_to_nut = thick_vstiff / 2
    else:
        gap_cen_to_nut = thick_vstiff / 2 + thick_guss
        gap_cen_to_head = thick_vstiff / 2

    return gap_cen_to_head, gap_cen_to_nut


def Caculate_Coord_Hole_Taikeikou(infor_hole, pointbase_hole, pos):
    d_hole, pitchY_hole, pitchX_hole = infor_hole

    # 穴が無い場合（d_hole=0、pitchY_hole="0"または空、pitchX_hole=0）は空の配列を返す
    if (
        d_hole == 0
        or (isinstance(pitchY_hole, str) and (pitchY_hole == "0" or pitchY_hole == ""))
        or (isinstance(pitchY_hole, (int, float)) and pitchY_hole == 0)
        or pitchX_hole == 0
    ):
        return []

    pointdirX_hole = pointbase_hole.copy()
    pointdirX_hole[0] += 100
    pointdirY_hole = pointbase_hole.copy()
    pointdirY_hole[1] += 100

    arpitchX_hole = str(pitchX_hole).split("/")
    arpitchX_hole = DefStrings.process_array(arpitchX_hole)
    arpitchY_hole = str(pitchY_hole).split("/")
    arpitchY_hole = DefStrings.process_array(arpitchY_hole)

    arCoor_hole = []
    sumx = 0
    for i in range(len(arpitchX_hole)):
        sumx += float(arpitchX_hole[i])
        if pos == "TL" or pos == "BL":
            ps_lineV, pe_lineV = DefMath.Offset_Line(pointbase_hole[:2], pointdirY_hole[:2], sumx)
        elif pos == "TR" or pos == "BR":
            ps_lineV, pe_lineV = DefMath.Offset_Line(pointbase_hole[:2], pointdirY_hole[:2], -sumx)

        arCoor_hole_Y = []
        sumy = 0
        for i_1 in range(len(arpitchY_hole)):
            sumy += arpitchY_hole[i_1]
            if pos == "TL" or pos == "TR":
                ps_lineH, pe_lineH = DefMath.Offset_Line(pointbase_hole[:2], pointdirX_hole[:2], -sumy)
            elif pos == "BL" or pos == "BR":
                ps_lineH, pe_lineH = DefMath.Offset_Line(pointbase_hole[:2], pointdirX_hole[:2], sumy)

            p = DefMath.Intersec_line_line(ps_lineV, pe_lineV, ps_lineH, pe_lineH)
            arCoor_hole_Y.append(p)

        arCoor_hole.append(arCoor_hole_Y)

    return arCoor_hole


def Calculate_DistModX_Shape(vstiff_taikeikou, guss_taikeikou, gau_guss, gau_shape, size_shape, type_shape):
    arsize_shape = size_shape.split("x")
    if type_shape == "CT":
        thick_shape = float(arsize_shape[2]) / 2
    else:
        thick_shape = 0

    if guss_taikeikou:
        tl_guss, tr_guss, bl_guss, br_guss, mid_guss = (
            guss_taikeikou["TL"],
            guss_taikeikou["TR"],
            guss_taikeikou["BL"],
            guss_taikeikou["BR"],
            guss_taikeikou["Mid"],
        )
        if tl_guss:
            thick_guss = float(tl_guss[0])
        elif tr_guss:
            thick_guss = float(tr_guss[0])
        elif bl_guss:
            thick_guss = float(bl_guss[0])
        elif br_guss:
            thick_guss = float(br_guss[0])
        elif mid_guss:
            thick_guss = float(mid_guss[0])
        else:
            thick_guss = 0
    else:
        thick_guss = 0

    if vstiff_taikeikou:
        vstiff_left, vstiff_right = vstiff_taikeikou["L"], vstiff_taikeikou["R"]
        if vstiff_left:
            thick_vstiff = float(vstiff_left[0])
        elif vstiff_right:
            thick_vstiff = float(vstiff_right[0])
        else:
            thick_vstiff = 0
    else:
        thick_vstiff = 0

    if gau_guss == "A":
        if gau_shape == "A":
            distmodX_shape = -thick_vstiff / 2 - thick_guss - thick_shape
        else:
            distmodX_shape = -thick_vstiff / 2 + thick_shape
    else:
        if gau_shape == "A":
            distmodX_shape = thick_vstiff / 2 - thick_shape
        else:
            distmodX_shape = thick_vstiff / 2 + thick_guss + thick_shape

    return distmodX_shape


def Calculate_Shape_Taikeikou_For_Yokokou(Senkei_data, infor_Taikeikou, pos):
    # infor_Taikeikouから全要素を取得（セクション情報を含む）
    if len(infor_Taikeikou) >= 10:
        (
            name_taikeikou,
            type_taikeikou,
            girder_taikeikou,
            point_taikeikou,
            distmod_taikeikou,
            hole_taikeikou,
            vstiff_taikeikou,
            shape_taikeikou,
            guss_taikeikou,
            section_taikeikou,
        ) = infor_Taikeikou
    else:
        (
            name_taikeikou,
            type_taikeikou,
            girder_taikeikou,
            point_taikeikou,
            distmod_taikeikou,
            hole_taikeikou,
            vstiff_taikeikou,
            shape_taikeikou,
            guss_taikeikou,
        ) = infor_Taikeikou
        section_taikeikou = "C1"
    typ_taikeikou, gau_guss, gau_shape = type_taikeikou

    basepoint, modpoint = Calculate_Point_Taikeikou(
        None, Senkei_data, name_taikeikou, point_taikeikou, distmod_taikeikou, None, None, section_taikeikou
    )
    BasePoint1, BasePoint2, BasePoint3, BasePoint4 = basepoint
    ModPoint1, ModPoint2, ModPoint3, ModPoint4 = modpoint
    if typ_taikeikou == "Type1D":
        CenPoint = (ModPoint3 + ModPoint4) / 2
    elif typ_taikeikou == "Type1U":
        CenPoint = (ModPoint1 + ModPoint2) / 2
    else:
        print(f"Trường hợp type taikeikou là {typ_taikeikou} chưa phát triển")

    p1_3d = BasePoint4
    p2_3d = DefMath.point_per_line(p1_3d, BasePoint2, BasePoint3)
    p3_3d = BasePoint1
    normal_taikeikou = -DefMath.Normal_vector(p1_3d, p2_3d, p3_3d)
    p1_2d = [0, 0, 0]
    p2_2d = [100, 0, 0]
    p3_2d = [0, 100, 0]
    BasePoint1_2D = DefMath.Transform_point_face2face(BasePoint1, p1_3d, p2_3d, p3_3d, p1_2d, p2_2d, p3_2d)
    BasePoint1_2D[2] = 0
    BasePoint2_2D = DefMath.Transform_point_face2face(BasePoint2, p1_3d, p2_3d, p3_3d, p1_2d, p2_2d, p3_2d)
    BasePoint2_2D[2] = 0
    BasePoint3_2D = DefMath.Transform_point_face2face(BasePoint3, p1_3d, p2_3d, p3_3d, p1_2d, p2_2d, p3_2d)
    BasePoint3_2D[2] = 0
    BasePoint4_2D = DefMath.Transform_point_face2face(BasePoint4, p1_3d, p2_3d, p3_3d, p1_2d, p2_2d, p3_2d)
    BasePoint4_2D[2] = 0
    ModPoint1_2D = DefMath.Transform_point_face2face(ModPoint1, p1_3d, p2_3d, p3_3d, p1_2d, p2_2d, p3_2d)
    ModPoint1_2D[2] = 0
    ModPoint2_2D = DefMath.Transform_point_face2face(ModPoint2, p1_3d, p2_3d, p3_3d, p1_2d, p2_2d, p3_2d)
    ModPoint2_2D[2] = 0
    ModPoint3_2D = DefMath.Transform_point_face2face(ModPoint3, p1_3d, p2_3d, p3_3d, p1_2d, p2_2d, p3_2d)
    ModPoint3_2D[2] = 0
    ModPoint4_2D = DefMath.Transform_point_face2face(ModPoint4, p1_3d, p2_3d, p3_3d, p1_2d, p2_2d, p3_2d)
    ModPoint4_2D[2] = 0
    CenPoint_2D = DefMath.Transform_point_face2face(CenPoint, p1_3d, p2_3d, p3_3d, p1_2d, p2_2d, p3_2d)
    CenPoint_2D[2] = 0

    # -------------------Shape（形状部材）-------------------------------------------------------------------
    if shape_taikeikou:
        shapeT, shapeB, shapeL, shapeR = (
            shape_taikeikou["T"],
            shape_taikeikou["B"],
            shape_taikeikou["L"],
            shape_taikeikou["R"],
        )
        if pos == "T":
            type_shape, size_shape, mat_shape, dir_shape, distmodY_shape, pitchmod_shape = shapeT
            ar_size_shape = size_shape.split("x")
            p1mod_shape, p2mod_shape = Calculate_Pse_Shape(pitchmod_shape, ModPoint1_2D, ModPoint2_2D)
            if type_shape == "CT":
                distmodX_shape = Calculate_DistModX_Shape(
                    vstiff_taikeikou, guss_taikeikou, gau_guss, gau_shape, size_shape, "CT"
                )
                p1mod_shape_3D_al = (
                    DefMath.Transform_point_face2face(p1mod_shape, p1_2d, p2_2d, p3_2d, p1_3d, p2_3d, p3_3d)
                    + distmodX_shape * normal_taikeikou
                )
                p2mod_shape_3D_al = (
                    DefMath.Transform_point_face2face(p2mod_shape, p1_2d, p2_2d, p3_2d, p1_3d, p2_3d, p3_3d)
                    + distmodX_shape * normal_taikeikou
                )
                if dir_shape == "U":
                    if gau_shape == "A":
                        p3mod_shape_3D_al = p2mod_shape_3D_al - 100 * normal_taikeikou
                    else:
                        p3mod_shape_3D_al = p1mod_shape_3D_al + 100 * normal_taikeikou
                else:
                    if gau_shape == "A":
                        p3mod_shape_3D_al = p1mod_shape_3D_al - 100 * normal_taikeikou
                    else:
                        p3mod_shape_3D_al = p2mod_shape_3D_al + 100 * normal_taikeikou
            elif type_shape == "L":
                distmodX_shape = Calculate_DistModX_Shape(
                    vstiff_taikeikou, guss_taikeikou, gau_guss, gau_shape, size_shape, "L"
                )
                p1mod_shape_3D_al = (
                    DefMath.Transform_point_face2face(p1mod_shape, p1_2d, p2_2d, p3_2d, p1_3d, p2_3d, p3_3d)
                    + distmodX_shape * normal_taikeikou
                )
                p2mod_shape_3D_al = (
                    DefMath.Transform_point_face2face(p2mod_shape, p1_2d, p2_2d, p3_2d, p1_3d, p2_3d, p3_3d)
                    + distmodX_shape * normal_taikeikou
                )
                if dir_shape == "U":
                    if gau_shape == "A":
                        p3mod_shape_3D_al = p2mod_shape_3D_al - 100 * normal_taikeikou
                    else:
                        p3mod_shape_3D_al = p1mod_shape_3D_al + 100 * normal_taikeikou
                else:
                    if gau_shape == "A":
                        p3mod_shape_3D_al = p1mod_shape_3D_al - 100 * normal_taikeikou
                    else:
                        p3mod_shape_3D_al = p2mod_shape_3D_al + 100 * normal_taikeikou

            normal_face = DefMath.Normal_vector(p1mod_shape_3D_al, p2mod_shape_3D_al, p3mod_shape_3D_al)
            p1_shape = p1mod_shape_3D_al + distmodY_shape * normal_face
            if p1_shape[2] < p1mod_shape_3D_al[2]:
                p1_shape = p1mod_shape_3D_al - distmodY_shape * normal_face
            p2_shape = p2mod_shape_3D_al + distmodY_shape * normal_face
            if p2_shape[2] < p1mod_shape_3D_al[2]:
                p2_shape = p2mod_shape_3D_al - distmodY_shape * normal_face

            if type_shape == "CT":
                p1T_shape = p1_shape + (float(ar_size_shape[1]) / 2) * normal_taikeikou
                p1S_shape = p1_shape - (float(ar_size_shape[1]) / 2) * normal_taikeikou
                if p1T_shape[0] > p1_shape[0]:
                    p1T_shape = p1_shape - (float(ar_size_shape[1]) / 2) * normal_taikeikou
                    p1S_shape = p1_shape + (float(ar_size_shape[1]) / 2) * normal_taikeikou
                p2T_shape = p2_shape + (float(ar_size_shape[1]) / 2) * normal_taikeikou
                p2S_shape = p2_shape - (float(ar_size_shape[1]) / 2) * normal_taikeikou
                if p2T_shape[0] > p2_shape[0]:
                    p2T_shape = p2_shape - (float(ar_size_shape[1]) / 2) * normal_taikeikou
                    p2S_shape = p2_shape + (float(ar_size_shape[1]) / 2) * normal_taikeikou
            elif type_shape == "L":
                if gau_shape == "F":
                    p1T_shape = p1_shape
                    p1S_shape = p1_shape - (float(ar_size_shape[1])) * normal_taikeikou
                    if p1S_shape[0] < p1_shape[0]:
                        p1S_shape = p1_shape + (float(ar_size_shape[1])) * normal_taikeikou

                    p2T_shape = p2_shape
                    p2S_shape = p2_shape - (float(ar_size_shape[1])) * normal_taikeikou
                    if p2S_shape[0] < p2_shape[0]:
                        p2S_shape = p2_shape + (float(ar_size_shape[1])) * normal_taikeikou
                elif gau_shape == "A":
                    p1T_shape = p1_shape + (float(ar_size_shape[1])) * normal_taikeikou
                    p1S_shape = p1_shape
                    if p1T_shape[0] > p1_shape[0]:
                        p1T_shape = p1_shape - (float(ar_size_shape[1])) * normal_taikeikou

                    p2T_shape = p2_shape + (float(ar_size_shape[1])) * normal_taikeikou
                    p2S_shape = p2_shape
                    if p2T_shape[0] > p2_shape[0]:
                        p2T_shape = p2_shape - (float(ar_size_shape[1])) * normal_taikeikou

        if pos == "B":
            type_shape, size_shape, mat_shape, dir_shape, distmodY_shape, pitchmod_shape = shapeB
            ar_size_shape = size_shape.split("x")
            p1mod_shape, p2mod_shape = Calculate_Pse_Shape(pitchmod_shape, ModPoint4_2D, ModPoint3_2D)
            if type_shape == "CT":
                distmodX_shape = Calculate_DistModX_Shape(
                    vstiff_taikeikou, guss_taikeikou, gau_guss, gau_shape, size_shape, "CT"
                )
                p1mod_shape_3D_al = (
                    DefMath.Transform_point_face2face(p1mod_shape, p1_2d, p2_2d, p3_2d, p1_3d, p2_3d, p3_3d)
                    + distmodX_shape * normal_taikeikou
                )
                p2mod_shape_3D_al = (
                    DefMath.Transform_point_face2face(p2mod_shape, p1_2d, p2_2d, p3_2d, p1_3d, p2_3d, p3_3d)
                    + distmodX_shape * normal_taikeikou
                )
                if dir_shape == "U":
                    if gau_shape == "A":
                        p3mod_shape_3D_al = p2mod_shape_3D_al - 100 * normal_taikeikou
                    else:
                        p3mod_shape_3D_al = p1mod_shape_3D_al + 100 * normal_taikeikou
                else:
                    if gau_shape == "A":
                        p3mod_shape_3D_al = p1mod_shape_3D_al - 100 * normal_taikeikou
                    else:
                        p3mod_shape_3D_al = p2mod_shape_3D_al + 100 * normal_taikeikou
            elif type_shape == "L":
                distmodX_shape = Calculate_DistModX_Shape(
                    vstiff_taikeikou, guss_taikeikou, gau_guss, gau_shape, size_shape, "L"
                )
                p1mod_shape_3D_al = (
                    DefMath.Transform_point_face2face(p1mod_shape, p1_2d, p2_2d, p3_2d, p1_3d, p2_3d, p3_3d)
                    + distmodX_shape * normal_taikeikou
                )
                p2mod_shape_3D_al = (
                    DefMath.Transform_point_face2face(p2mod_shape, p1_2d, p2_2d, p3_2d, p1_3d, p2_3d, p3_3d)
                    + distmodX_shape * normal_taikeikou
                )
                if dir_shape == "U":
                    if gau_shape == "A":
                        p3mod_shape_3D_al = p2mod_shape_3D_al - 100 * normal_taikeikou
                    else:
                        p3mod_shape_3D_al = p1mod_shape_3D_al + 100 * normal_taikeikou
                else:
                    if gau_shape == "A":
                        p3mod_shape_3D_al = p1mod_shape_3D_al - 100 * normal_taikeikou
                    else:
                        p3mod_shape_3D_al = p2mod_shape_3D_al + 100 * normal_taikeikou

            normal_face = DefMath.Normal_vector(p1mod_shape_3D_al, p2mod_shape_3D_al, p3mod_shape_3D_al)
            p1_shape = p1mod_shape_3D_al + distmodY_shape * normal_face
            if p1_shape[2] > p1mod_shape_3D_al[2]:
                p1_shape = p1mod_shape_3D_al - distmodY_shape * normal_face
            p2_shape = p2mod_shape_3D_al + distmodY_shape * normal_face
            if p2_shape[2] > p1mod_shape_3D_al[2]:
                p2_shape = p2mod_shape_3D_al - distmodY_shape * normal_face

            if type_shape == "CT":
                p1T_shape = p1_shape + (float(ar_size_shape[1]) / 2) * normal_taikeikou
                p1S_shape = p1_shape - (float(ar_size_shape[1]) / 2) * normal_taikeikou
                if p1T_shape[0] > p1_shape[0]:
                    p1T_shape = p1_shape - (float(ar_size_shape[1]) / 2) * normal_taikeikou
                    p1S_shape = p1_shape + (float(ar_size_shape[1]) / 2) * normal_taikeikou
                p2T_shape = p2_shape + (float(ar_size_shape[1]) / 2) * normal_taikeikou
                p2S_shape = p2_shape - (float(ar_size_shape[1]) / 2) * normal_taikeikou
                if p2T_shape[0] > p2_shape[0]:
                    p2T_shape = p2_shape - (float(ar_size_shape[1]) / 2) * normal_taikeikou
                    p2S_shape = p2_shape + (float(ar_size_shape[1]) / 2) * normal_taikeikou
            elif type_shape == "L":
                if gau_shape == "F":
                    p1T_shape = p1_shape
                    p1S_shape = p1_shape - (float(ar_size_shape[1])) * normal_taikeikou
                    if p1S_shape[0] < p1_shape[0]:
                        p1S_shape = p1_shape + (float(ar_size_shape[1])) * normal_taikeikou

                    p2T_shape = p2_shape
                    p2S_shape = p2_shape - (float(ar_size_shape[1])) * normal_taikeikou
                    if p2S_shape[0] < p2_shape[0]:
                        p2S_shape = p2_shape + (float(ar_size_shape[1])) * normal_taikeikou
                elif gau_shape == "A":
                    p1T_shape = p1_shape + (float(ar_size_shape[1])) * normal_taikeikou
                    p1S_shape = p1_shape
                    if p1T_shape[0] > p1_shape[0]:
                        p1T_shape = p1_shape - (float(ar_size_shape[1])) * normal_taikeikou

                    p2T_shape = p2_shape + (float(ar_size_shape[1])) * normal_taikeikou
                    p2S_shape = p2_shape
                    if p2T_shape[0] > p2_shape[0]:
                        p2T_shape = p2_shape - (float(ar_size_shape[1])) * normal_taikeikou

    return p1_shape, p1T_shape, p1S_shape, p2_shape, p2T_shape, p2S_shape


def Calculate_Face_Base_Guss_follow_Taikeikou(
    Senkei_data,
    MainPanel_data,
    Taikeiko_data,
    namepoint_guss,
    coordpoint_guss,
    typeTB_yokokou,
    nameWeb_mainpanel,
    girder_ykk,
    distedge_face,
    distKL1_face,
    distKL2_face,
):
    for taikeikou in Taikeiko_data:
        if taikeikou["Name"] == namepoint_guss and girder_ykk == taikeikou["Girder"]:
            # ----------Infor Taikeikou------------------------------------------------------------
            name_taikeikou = taikeikou["Name"]
            type_taikeikou = taikeikou["Type"]
            girder_taikeikou = taikeikou["Girder"]
            point_taikeikou = taikeikou["Point"]
            distmod_taikeikou = taikeikou["Distmod"]
            hole_taikeikou = taikeikou["Hole"]
            vstiff_taikeikou = taikeikou["Vstiff"]
            shape_taikeikou = taikeikou["Shape"]
            guss_taikeikou = taikeikou["Guss"]
            infor_Taikeikou = (
                name_taikeikou,
                type_taikeikou,
                girder_taikeikou,
                point_taikeikou,
                distmod_taikeikou,
                hole_taikeikou,
                vstiff_taikeikou,
                shape_taikeikou,
                guss_taikeikou,
            )

            p1mod_shape, p1Tmod_shape, p1Smod_shape, p2mod_shape, p2Tmod_shape, p2Smod_shape = (
                Calculate_Shape_Taikeikou_For_Yokokou(Senkei_data, infor_Taikeikou, typeTB_yokokou)
            )

            if (
                distedge_face.startswith("O")
                or distedge_face.startswith("A")
                or distedge_face.startswith("F")
                or distedge_face.startswith("B")
                or distedge_face.startswith("C")
            ):
                numberoffset = float(distedge_face[1:])
                p1Tmod_shape = DefMath.Point_on_parallel_line(p1Tmod_shape, p1Tmod_shape, p2Tmod_shape, numberoffset)
                p1Smod_shape = DefMath.Point_on_parallel_line(p1Smod_shape, p1Smod_shape, p2Smod_shape, numberoffset)
                p2Tmod_shape = DefMath.Point_on_parallel_line(p2Tmod_shape, p2Tmod_shape, p1Tmod_shape, numberoffset)
                p2Smod_shape = DefMath.Point_on_parallel_line(p2Smod_shape, p2Smod_shape, p1Smod_shape, numberoffset)

            if distKL1_face != 0:
                p1Tmod_shape = DefMath.Point_on_parallel_line(p1Tmod_shape, p1Tmod_shape, p1Smod_shape, -distKL1_face)
                p2Tmod_shape = DefMath.Point_on_parallel_line(p2Tmod_shape, p2Tmod_shape, p2Smod_shape, -distKL1_face)

            if distKL2_face != 0:
                p1Smod_shape = DefMath.Point_on_parallel_line(p1Smod_shape, p1Smod_shape, p1Tmod_shape, -distKL2_face)
                p2Smod_shape = DefMath.Point_on_parallel_line(p2Smod_shape, p2Smod_shape, p2Tmod_shape, -distKL2_face)

            if DefMath.Calculate_distance_p2p(coordpoint_guss, p1mod_shape) < DefMath.Calculate_distance_p2p(
                coordpoint_guss, p2mod_shape
            ):
                p1T_guss = p1Tmod_shape
                p1S_guss = p1Smod_shape
            else:
                p1T_guss = p2Tmod_shape
                p1S_guss = p2Smod_shape

            # ----------------cut web-----------------------------------------
            for panel in MainPanel_data:
                if panel["Name"] == nameWeb_mainpanel:
                    Line_mainpanel = panel["Line"]
                    Sec_mainpanel = panel["Sec"]
                    Type_mainpanel = panel["Type"]
                    Mat_mainpanel = panel["Material"]
                    Expand_mainpanel = panel["Expand"]
                    break
            thick1_panel, thick2_panel, mat_panel = (
                Mat_mainpanel["Thick1"],
                Mat_mainpanel["Thick2"],
                Mat_mainpanel["Mat"],
            )
            arCoordLines_mod = Load_Coordinate_Panel(Senkei_data, Line_mainpanel, Sec_mainpanel)
            # ------------------cut face 1-----------------------------
            arCoordLines_Out = DefMath.Offset_Face(arCoordLines_mod, -thick2_panel)
            arCoordLines_Out = Calculate_Extend_Coord(arCoordLines_Out, 5, "L")
            arCoordLines_Out = Calculate_Extend_Coord(arCoordLines_Out, 5, "R")
            for i_1 in range(len(arCoordLines_Out) - 1):
                status_exit = False
                arCoordLines_Out_1 = arCoordLines_Out[i_1]
                arCoordLines_Out_2 = arCoordLines_Out[i_1 + 1]
                for i_2 in range(len(arCoordLines_Out_1) - 1):
                    p1_plan = arCoordLines_Out_1[i_2]
                    p2_plan = arCoordLines_Out_1[i_2 + 1]
                    p3_plan = arCoordLines_Out_2[i_2]
                    p4_plan = arCoordLines_Out_2[i_2 + 1]
                    p = DefMath.Intersection_line_plane(p1_plan, p2_plan, p3_plan, p1Tmod_shape, p2Tmod_shape)
                    if p is not None:
                        polygon3d = [p1_plan, p2_plan, p3_plan, p4_plan]
                        polygon3d = DefMath.sort_points_clockwise(polygon3d)
                        if DefMath.is_point_in_polygon_3d(p, polygon3d, p1_plan, p2_plan, p3_plan) == True:
                            int_T1 = p
                            status_exit = True
                            break
                if status_exit == True:
                    break
            for i_1 in range(len(arCoordLines_Out) - 1):
                status_exit = False
                arCoordLines_Out_1 = arCoordLines_Out[i_1]
                arCoordLines_Out_2 = arCoordLines_Out[i_1 + 1]
                for i_2 in range(len(arCoordLines_Out_1) - 1):
                    p1_plan = arCoordLines_Out_1[i_2]
                    p2_plan = arCoordLines_Out_1[i_2 + 1]
                    p3_plan = arCoordLines_Out_2[i_2]
                    p4_plan = arCoordLines_Out_2[i_2 + 1]
                    p = DefMath.Intersection_line_plane(p1_plan, p2_plan, p3_plan, p1Smod_shape, p2Smod_shape)
                    if p is not None:
                        polygon3d = [p1_plan, p2_plan, p3_plan, p4_plan]
                        polygon3d = DefMath.sort_points_clockwise(polygon3d)
                        if DefMath.is_point_in_polygon_3d(p, polygon3d, p1_plan, p2_plan, p3_plan) == True:
                            int_S1 = p
                            status_exit = True
                            break
                if status_exit == True:
                    break

            # ------------------cut face 2------------------------------
            arCoordLines_Out = DefMath.Offset_Face(arCoordLines_mod, thick1_panel)
            arCoordLines_Out = Calculate_Extend_Coord(arCoordLines_Out, 5, "L")
            arCoordLines_Out = Calculate_Extend_Coord(arCoordLines_Out, 5, "R")
            for i_1 in range(len(arCoordLines_Out) - 1):
                status_exit = False
                arCoordLines_Out_1 = arCoordLines_Out[i_1]
                arCoordLines_Out_2 = arCoordLines_Out[i_1 + 1]
                for i_2 in range(len(arCoordLines_Out_1) - 1):
                    p1_plan = arCoordLines_Out_1[i_2]
                    p2_plan = arCoordLines_Out_1[i_2 + 1]
                    p3_plan = arCoordLines_Out_2[i_2]
                    p4_plan = arCoordLines_Out_2[i_2 + 1]
                    p = DefMath.Intersection_line_plane(p1_plan, p2_plan, p3_plan, p1Tmod_shape, p2Tmod_shape)
                    if p is not None:
                        polygon3d = [p1_plan, p2_plan, p3_plan, p4_plan]
                        polygon3d = DefMath.sort_points_clockwise(polygon3d)
                        if DefMath.is_point_in_polygon_3d(p, polygon3d, p1_plan, p2_plan, p3_plan) == True:
                            int_T2 = p
                            status_exit = True
                            break
                if status_exit == True:
                    break
            for i_1 in range(len(arCoordLines_Out) - 1):
                status_exit = False
                arCoordLines_Out_1 = arCoordLines_Out[i_1]
                arCoordLines_Out_2 = arCoordLines_Out[i_1 + 1]
                for i_2 in range(len(arCoordLines_Out_1) - 1):
                    p1_plan = arCoordLines_Out_1[i_2]
                    p2_plan = arCoordLines_Out_1[i_2 + 1]
                    p3_plan = arCoordLines_Out_2[i_2]
                    p4_plan = arCoordLines_Out_2[i_2 + 1]
                    p = DefMath.Intersection_line_plane(p1_plan, p2_plan, p3_plan, p1Smod_shape, p2Smod_shape)
                    if p is not None:
                        polygon3d = [p1_plan, p2_plan, p3_plan, p4_plan]
                        polygon3d = DefMath.sort_points_clockwise(polygon3d)
                        if DefMath.is_point_in_polygon_3d(p, polygon3d, p1_plan, p2_plan, p3_plan) == True:
                            int_S2 = p
                            status_exit = True
                            break
                if status_exit == True:
                    break

            if DefMath.Calculate_distance_p2p(p1T_guss, int_T1) < DefMath.Calculate_distance_p2p(p1T_guss, int_T2):
                p2T_guss = int_T1
                p2S_guss = int_S1
            else:
                p2T_guss = int_T2
                p2S_guss = int_S2

            break

    return p1T_guss, p1S_guss, p2T_guss, p2S_guss


def Draw_3DSlot_follow_Stiff_Taikeikou_For_Guss(
    ifc_all, Senkei_data, Member_data, infor_Taikeikou, name_slot, pos, p1_guss, p2_guss, p3_guss
):
    ifc_file, bridge_span, geom_context = ifc_all
    (
        name_taikeikou,
        type_taikeikou,
        girder_taikeikou,
        point_taikeikou,
        distmod_taikeikou,
        hole_taikeikou,
        vstiff_taikeikou,
        shape_taikeikou,
        guss_taikeikou,
    ) = infor_Taikeikou
    typ_taikeikou, gau_guss, gau_shape = type_taikeikou
    solid_slot_original = None

    basepoint, modpoint = Calculate_Point_Taikeikou(
        None, Senkei_data, name_taikeikou, point_taikeikou, distmod_taikeikou
    )
    BasePoint1, BasePoint2, BasePoint3, BasePoint4 = basepoint
    ModPoint1, ModPoint2, ModPoint3, ModPoint4 = modpoint
    if typ_taikeikou == "Type1D":
        CenPoint = (ModPoint3 + ModPoint4) / 2
    elif typ_taikeikou == "Type1U":
        CenPoint = (ModPoint1 + ModPoint2) / 2
    else:
        print(f"Trường hợp type taikeikou là {typ_taikeikou} chưa phát triển")

    p1_3d = BasePoint4
    p2_3d = DefMath.point_per_line(p1_3d, BasePoint2, BasePoint3)
    p3_3d = BasePoint1
    normal_taikeikou = DefMath.Normal_vector(p1_3d, p2_3d, p3_3d)
    p1_2d = [0, 0, 0]
    p2_2d = [100, 0, 0]
    p3_2d = [0, 100, 0]
    BasePoint1_2D = DefMath.Transform_point_face2face(BasePoint1, p1_3d, p2_3d, p3_3d, p1_2d, p2_2d, p3_2d)
    BasePoint1_2D[2] = 0
    BasePoint2_2D = DefMath.Transform_point_face2face(BasePoint2, p1_3d, p2_3d, p3_3d, p1_2d, p2_2d, p3_2d)
    BasePoint2_2D[2] = 0
    BasePoint3_2D = DefMath.Transform_point_face2face(BasePoint3, p1_3d, p2_3d, p3_3d, p1_2d, p2_2d, p3_2d)
    BasePoint3_2D[2] = 0
    BasePoint4_2D = DefMath.Transform_point_face2face(BasePoint4, p1_3d, p2_3d, p3_3d, p1_2d, p2_2d, p3_2d)
    BasePoint4_2D[2] = 0
    ModPoint1_2D = DefMath.Transform_point_face2face(ModPoint1, p1_3d, p2_3d, p3_3d, p1_2d, p2_2d, p3_2d)
    ModPoint1_2D[2] = 0
    ModPoint2_2D = DefMath.Transform_point_face2face(ModPoint2, p1_3d, p2_3d, p3_3d, p1_2d, p2_2d, p3_2d)
    ModPoint2_2D[2] = 0
    ModPoint3_2D = DefMath.Transform_point_face2face(ModPoint3, p1_3d, p2_3d, p3_3d, p1_2d, p2_2d, p3_2d)
    ModPoint3_2D[2] = 0
    ModPoint4_2D = DefMath.Transform_point_face2face(ModPoint4, p1_3d, p2_3d, p3_3d, p1_2d, p2_2d, p3_2d)
    ModPoint4_2D[2] = 0
    CenPoint_2D = DefMath.Transform_point_face2face(CenPoint, p1_3d, p2_3d, p3_3d, p1_2d, p2_2d, p3_2d)
    CenPoint_2D[2] = 0

    # -------------------Vstiff（垂直補剛材）-------------------------------------------------------------------
    vstiff_left, vstiff_right = vstiff_taikeikou["L"], vstiff_taikeikou["R"]
    if pos == "L":
        thick_vstiff, mat_vstiff, width_vstiff = vstiff_left
        arCoord_Top_Stiff, arCoord_Bot_Stiff, arCoord_Left_Stiff, arCoord_Right_Stiff = (
            Calculate_Point_Vstiff_Taikeikou(width_vstiff, BasePoint1, BasePoint2, BasePoint3, BasePoint4, pos="L")
        )
    elif pos == "R":
        thick_vstiff, mat_vstiff, width_vstiff = vstiff_left
        arCoord_Top_Stiff, arCoord_Bot_Stiff, arCoord_Left_Stiff, arCoord_Right_Stiff = (
            Calculate_Point_Vstiff_Taikeikou(width_vstiff, BasePoint1, BasePoint2, BasePoint3, BasePoint4, pos="R")
        )

    p1_slot = None
    for i_2 in range(len(arCoord_Left_Stiff) - 1):
        p = DefMath.Intersection_line_plane(
            p1_guss, p2_guss, p3_guss, arCoord_Left_Stiff[i_2], arCoord_Left_Stiff[i_2 + 1]
        )
        if p[0] >= arCoord_Left_Stiff[i_2][0] and p[0] <= arCoord_Left_Stiff[i_2 + 1][0]:
            p1_slot = p
            break
    p2_slot = None
    for i_2 in range(len(arCoord_Right_Stiff) - 1):
        p = DefMath.Intersection_line_plane(
            p1_guss, p2_guss, p3_guss, arCoord_Right_Stiff[i_2], arCoord_Right_Stiff[i_2 + 1]
        )
        if p[0] >= arCoord_Right_Stiff[i_2][0] and p[0] <= arCoord_Right_Stiff[i_2 + 1][0]:
            p2_slot = p
            break

    if p1_slot is not None and p2_slot is not None:
        pal1_slot = p1_slot.copy()
        normal_p1p2p3 = DefMath.Normal_vector(p1_guss, p2_guss, p3_guss)

        if pos == "L":
            pal2_slot = p1_slot - 100 * normal_p1p2p3
        elif pos == "R":
            pal2_slot = p1_slot + 100 * normal_p1p2p3

        pal3_slot = DefMath.rotate_point_around_axis(p1_slot, pal2_slot, p2_slot, 90)
        # --------参照スロット----------------------------------------
        for slot in Member_data:
            if slot["Name"] == name_slot:
                infor_slot = slot["Infor"]
                wides_slot = slot["Wide"]
                radius_slot = slot["Radius"]
                break
        type_slot = infor_slot[0]
        wideL_slot = wides_slot[0]
        wideR_slot = wides_slot[1]
        r_slot = radius_slot[0]

        solid_slot = Draw_3Dsolid_Slot(
            ifc_file, p1_slot, p2_slot, wideL_slot, wideR_slot, r_slot, pal1_slot, pal2_slot, pal3_slot
        )

        if solid_slot_original is not None:
            if solid_slot is not None:
                solid_slot_original = ifc_file.createIfcBooleanResult("UNION", solid_slot_original, solid_slot)
        else:
            if solid_slot is not None:
                solid_slot_original = solid_slot

    return solid_slot_original


def Calculate_PointFLG_Subpanel_for_Guss_Yokokou(
    MainPanel_data,
    Senkei_data,
    Mem_Rib_data,
    arpoint_flg,
    ref_flg,
    pdir,
    arNamePoint,
    arCoordPoint,
    headname1_block_mainpanel,
    headname2_block_mainpanel,
    distKL1_face,
    distKL2_face,
):
    arCoord_flg = []
    for i in range(len(arpoint_flg)):
        index = arNamePoint.index(arpoint_flg[i])
        arCoord_flg.append(arCoordPoint[index])

    # --------参照リブ----------------------------------------
    for rib in Mem_Rib_data:
        if rib["Name"] == ref_flg:
            infor = rib["Infor"]
            ang = rib["Ang"]
            extend = rib["Extend"]
            corner = rib["Corner"]
            spl_s = rib["JointS"]
            spl_e = rib["JointE"]
            break
    thick1_rib, thick2_rib, mat_rib, height_rib = infor["Thick1"], infor["Thick2"], infor["Mat"], infor["Width"]
    angs_rib, ange_rib, anga_rib = ang
    extendT_rib, extendB_rib, extendL_rib, extendR_rib = extend
    corner1, corner2, corner3, corner4 = corner
    # -------------------------------------------------------------
    if distKL1_face != 0:
        distA = height_rib / 2 + distKL1_face
    else:
        distA = height_rib / 2
    if distKL2_face != 0:
        distF = height_rib / 2 + distKL2_face
    else:
        distF = height_rib / 2

    # TODO: Calculate_Coord_FLGとExtend_FLGはDefBridge.pyにまだあるため、インポートが必要
    from src.bridge_json_to_ifc.ifc_utils_new.core import DefBridge

    arCoorMod_A, arCoorMod_F = DefBridge.Calculate_Coord_FLG(
        arCoord_flg, pdir, distA, distF, anga_rib, 180 - anga_rib, angs_rib, ange_rib
    )
    arCoordFLG = [arCoorMod_F, arCoord_flg, arCoorMod_A]
    arCoordFLG_Out = arCoordFLG.copy()
    arCoordFLG_Out = DefBridge.Extend_FLG(
        MainPanel_data, Senkei_data, arCoordFLG_Out, extend, headname1_block_mainpanel, headname2_block_mainpanel
    )
    arCoordFLGT_Out = DefMath.Offset_Face(arCoordFLG_Out, thick1_rib)
    arCoordFLGB_Out = DefMath.Offset_Face(arCoordFLG_Out, -thick2_rib)
    arCoordFLGM_Out = DefMath.Calculate_Coord_Mid(arCoordFLGT_Out, arCoordFLGB_Out)

    return arCoordFLGT_Out, arCoordFLGB_Out


def Calculate_Face_Base_Guss_follow_SubPanel(
    Senkei_data,
    MainPanel_data,
    SubPanel_data,
    Mem_Rib_data,
    namepoint_guss,
    coordpoint_guss,
    typeTB_yokokou,
    girder_guss,
    distedge_face,
    distKL1_face,
    distKL2_face,
    Edge_guss_T,
    Edge_guss_S,
):
    for subpanel in SubPanel_data:
        # -----------------------Infor Panel------------------------------------------------------------
        name_subpanel = subpanel["Name"]
        girder_subpanel = subpanel["Girder"]
        sec_subpanel = subpanel["Sec"]
        point_subpanel = subpanel["Point"]
        part_subpanel = subpanel["Part"]

        argirder_subpanel = girder_subpanel.split("-")
        if len(argirder_subpanel) == 1:
            girder1_dia = argirder_subpanel[0]
            girder2_dia = argirder_subpanel[0]
        else:
            girder1_dia = argirder_subpanel[0]
            girder2_dia = argirder_subpanel[1]

        # TODO: Find_number_block_MainPanelとCalculate_points_Sub_PanelはDefBridge.pyにまだあるため、インポートが必要
        from src.bridge_json_to_ifc.ifc_utils_new.core import DefBridge

        number_block = DefBridge.Find_number_block_MainPanel(MainPanel_data, sec_subpanel)
        headname1_block_mainpanel = girder1_dia + "B" + number_block
        headname2_block_mainpanel = girder2_dia + "B" + number_block
        if sec_subpanel == namepoint_guss and argirder_subpanel == girder_guss:
            arNamePoint, arCoordPoint = DefBridge.Calculate_points_Sub_Panel(Senkei_data, point_subpanel, sec_subpanel)
            distmin = 100000
            for partsub in part_subpanel:
                name_part = partsub["Name"]
                material_part = partsub["Material"]
                out_part = partsub["Out"]
                extends_part = partsub["Extend"]
                corner_part = partsub["Corner"]
                slot_part = partsub["Slot"]
                joint_part = partsub["Joint"]
                cutout_part = partsub["Cutout"]
                stiff_part = partsub["Stiff"]
                flg_part = partsub["FLG"]

                thicka_part, thickf_part, mat_part = (
                    material_part["Thick1"],
                    material_part["Thick2"],
                    material_part["Mat"],
                )
                outL, outR, outT, outB = out_part["L"], out_part["R"], out_part["T"], out_part["B"]
                outR.reverse()
                outT.reverse()
                arCoord_Top = []
                arCoord_Bot = []
                arCoord_Left = []
                arCoord_Right = []
                for i in range(0, len(outT)):
                    index = arNamePoint.index(str(outT[i]))
                    arCoord_Top.append(arCoordPoint[index])
                for i in range(0, len(outB)):
                    index = arNamePoint.index(outB[i])
                    arCoord_Bot.append(arCoordPoint[index])
                for i in range(0, len(outL)):
                    index = arNamePoint.index(outL[i])
                    arCoord_Left.append(arCoordPoint[index])
                for i in range(0, len(outR)):
                    index = arNamePoint.index(outR[i])
                    arCoord_Right.append(arCoordPoint[index])

                if distedge_face.startswith("W"):
                    dimetion = distedge_face[1:].split("x")
                    dimetion_x = float(dimetion[0])
                    dimetion_y = float(dimetion[1])
                    p1mod = coordpoint_guss.copy()
                    p2mod = DefMath.Point_on_parallel_line(p1mod, arCoord_Bot[0], arCoord_Bot[1], dimetion_x)
                    if (arCoord_Bot[0][1] > arCoord_Bot[1][1] and p1mod[1] < p2mod[1]) or (
                        arCoord_Bot[0][1] < arCoord_Bot[1][1] and p1mod[1] > p2mod[1]
                    ):
                        p2mod = DefMath.Point_on_parallel_line(p1mod, arCoord_Bot[0], arCoord_Bot[1], -dimetion_x)
                    if arCoord_Bot[0][1] > arCoord_Bot[1][1]:
                        extend = ["Auto", 0, 0, 0]
                    else:
                        extend = [0, "Auto", 0, 0]

                    arCoord_flg = [p1mod, p2mod]
                    pdir = arCoord_Top[0]
                    arCoorMod_A, arCoorMod_F = DefBridge.Calculate_Coord_FLG(
                        arCoord_flg, pdir, dimetion_y / 2, dimetion_y / 2, 90, 90, 90, 90
                    )
                    arCoordFLG = [arCoorMod_F, arCoord_flg, arCoorMod_A]
                    arCoordFLG_Out = arCoordFLG.copy()

                    arCoordFLGT_Out = DefBridge.Extend_FLG(
                        MainPanel_data,
                        Senkei_data,
                        arCoordFLG_Out,
                        extend,
                        headname1_block_mainpanel,
                        headname2_block_mainpanel,
                    )
                    arCoordFLG = arCoordFLGT_Out
                else:
                    # -----------------flg（フランジ）----------------------------------
                    if flg_part:
                        uflg_part = flg_part["UFLG"]
                        lflg_part = flg_part["LFLG"]
                        if typeTB_yokokou == "T":
                            if uflg_part:
                                for i_2 in range(0, len(uflg_part), 2):
                                    namepoint_flg = uflg_part[i_2]
                                    ref_flg = uflg_part[i_2 + 1]
                                    if namepoint_flg == "Auto":
                                        arpoint_flg = outT.copy()
                                        arpoint_flg.reverse()
                                    else:
                                        arpoint_flg = namepoint_flg.split("-")

                                    pdir = arCoord_Bot[0]

                                    arCoordFLGT_Out, arCoordFLGB_Out = Calculate_PointFLG_Subpanel_for_Guss_Yokokou(
                                        MainPanel_data,
                                        Senkei_data,
                                        Mem_Rib_data,
                                        arpoint_flg,
                                        ref_flg,
                                        pdir,
                                        arNamePoint,
                                        arCoordPoint,
                                        headname1_block_mainpanel,
                                        headname2_block_mainpanel,
                                        distKL1_face,
                                        distKL2_face,
                                    )
                                    if distedge_face == "FT":
                                        arCoordFLG = arCoordFLGT_Out
                                    elif distedge_face == "FB":
                                        arCoordFLG = arCoordFLGB_Out
                        elif typeTB_yokokou == "B":
                            if lflg_part:
                                for i_2 in range(0, len(lflg_part), 2):
                                    namepoint_flg = lflg_part[i_2]
                                    ref_flg = lflg_part[i_2 + 1]
                                    if namepoint_flg == "Auto":
                                        arpoint_flg = outB
                                    else:
                                        arpoint_flg = namepoint_flg.split("-")

                                    pdir = arCoord_Top[-1]
                                    arCoordFLGT_Out, arCoordFLGB_Out = Calculate_PointFLG_Subpanel_for_Guss_Yokokou(
                                        MainPanel_data,
                                        Senkei_data,
                                        Mem_Rib_data,
                                        arpoint_flg,
                                        ref_flg,
                                        pdir,
                                        arNamePoint,
                                        arCoordPoint,
                                        headname1_block_mainpanel,
                                        headname2_block_mainpanel,
                                        distKL1_face,
                                        distKL2_face,
                                    )
                                    if distedge_face == "FT":
                                        arCoordFLG = arCoordFLGT_Out
                                    elif distedge_face == "FB":
                                        arCoordFLG = arCoordFLGB_Out
                        else:
                            print("Trường hợp này chưa phát triển !")

                if DefMath.Calculate_distance_p2p(coordpoint_guss, arCoordFLG[1][0]) < distmin:
                    p1T_guss = arCoordFLG[2][0]
                    p1S_guss = arCoordFLG[0][0]
                    p2T_guss = arCoordFLG[2][-1]
                    p2S_guss = arCoordFLG[0][-1]
                    distmin = DefMath.Calculate_distance_p2p(coordpoint_guss, arCoordFLG[1][0])

                    if DefMath.Calculate_distance_p2p(coordpoint_guss, p1T_guss) < DefMath.Calculate_distance_p2p(
                        coordpoint_guss, p2T_guss
                    ):
                        p1T_guss = arCoordFLG[2][-1]
                        p1S_guss = arCoordFLG[0][-1]
                        p2T_guss = arCoordFLG[2][0]
                        p2S_guss = arCoordFLG[0][0]

                if Edge_guss_T == "SPW":
                    normal = DefMath.Normal_vector(arCoord_Top[0], arCoord_Top[-1], arCoord_Bot[0])
                    p1plan = arCoord_Top[0] + thicka_part * normal
                    p2plan = arCoord_Top[-1] + thicka_part * normal
                    p3plan = arCoord_Bot[0] + thicka_part * normal
                    if p1plan[0] < arCoord_Top[0][0]:
                        p1plan = arCoord_Top[0] - thicka_part * normal
                        p2plan = arCoord_Top[-1] - thicka_part * normal
                        p3plan = arCoord_Bot[0] - thicka_part * normal
                    p1T_guss = DefMath.Intersection_line_plane(p1plan, p2plan, p3plan, p1T_guss, p1S_guss)
                    p2T_guss = DefMath.Intersection_line_plane(p1plan, p2plan, p3plan, p2T_guss, p2S_guss)
                elif Edge_guss_S == "SPW":
                    normal = DefMath.Normal_vector(arCoord_Top[0], arCoord_Top[-1], arCoord_Bot[0])
                    p1plan = arCoord_Top[0] + thickf_part * normal
                    p2plan = arCoord_Top[-1] + thickf_part * normal
                    p3plan = arCoord_Bot[0] + thickf_part * normal
                    if p1plan[0] > arCoord_Top[0][0]:
                        p1plan = arCoord_Top[0] - thickf_part * normal
                        p2plan = arCoord_Top[-1] - thickf_part * normal
                        p3plan = arCoord_Bot[0] - thickf_part * normal
                    p1S_guss = DefMath.Intersection_line_plane(p1plan, p2plan, p3plan, p1T_guss, p1S_guss)
                    p2S_guss = DefMath.Intersection_line_plane(p1plan, p2plan, p3plan, p2T_guss, p2S_guss)

            break

        if (
            distedge_face.startswith("O")
            or distedge_face.startswith("A")
            or distedge_face.startswith("F")
            or distedge_face.startswith("B")
            or distedge_face.startswith("C")
        ):
            numberoffset = float(distedge_face[1:])
            p1T_guss = DefMath.Point_on_parallel_line(p1T_guss, p1T_guss, p2T_guss, numberoffset)
            p1S_guss = DefMath.Point_on_parallel_line(p1S_guss, p1S_guss, p2S_guss, numberoffset)
            p2T_guss = DefMath.Point_on_parallel_line(p2T_guss, p2T_guss, p1T_guss, numberoffset)
            p2S_guss = DefMath.Point_on_parallel_line(p2S_guss, p2S_guss, p1S_guss, numberoffset)

    return p1T_guss, p1S_guss, p2T_guss, p2S_guss


# -----------------------------Yokokou_Structural（横構）------------------------------------------------------------
def Calculate_Yokokou_Structural(ifc_all, Senkei_data, MainPanel_data, infor_yokokou_structural):
    """
    横構（Yokokou_Structural / Lateral Bracing）の生成

    横構は、橋の主桁同士を水平方向につなぐトラス状の部材です。
    英語では Lateral Bracing と呼ばれ、横方向（ラテラル）の補強材として重要な役割を持ちます。

    トラス構造として、水平部材（弦材）と斜め部材（対角材）で構成されます。

    Args:
        ifc_all: (ifc_file, bridge_span, geom_context)
        Senkei_data: 線形データ
        MainPanel_data: メインパネルデータ
        infor_yokokou_structural: 横構情報のタプル
            (name, position_type, girder_list, section_name, z_offset, truss_info, hole_info, guss_list)
    """
    try:
        ifc_file, bridge_span, geom_context = ifc_all
        name_yokokou, position_type, girder_list, section_name, z_offset, truss_info, hole_info, guss_list = (
            infor_yokokou_structural
        )

        _log_print(f"    [Yokokou_Structural] 横構 '{name_yokokou}' の処理を開始")
        _log_print(f"    [Yokokou_Structural] 位置: {position_type}, 桁リスト: {girder_list}, 断面: {section_name}")

        # 座標点の計算
        _log_print("    [Yokokou_Structural] 座標点の計算を開始")
        arCoordPoint_Yokokou_Structural = Calculate_Point_Yokokou_Structural(
            Senkei_data, MainPanel_data, girder_list, position_type, section_name, z_offset
        )

        if len(arCoordPoint_Yokokou_Structural) == 0:
            _log_print("    [Yokokou_Structural] 警告: 座標点が0個です。形状の生成をスキップします。")
            return

        _log_print("    [Yokokou_Structural] トラス構造の生成を開始")
        Draw_Truss_Yokokou_Structural(ifc_all, arCoordPoint_Yokokou_Structural, truss_info, hole_info)

        # ガセットの生成（必要に応じて）
        if guss_list:
            _log_print("    [Yokokou_Structural] ガセットの生成を開始")
            # TODO: ガセット生成の実装
        else:
            _log_print("    [Yokokou_Structural] ガセットは定義されていません")

    except Exception as e:
        import traceback

        _log_print(f"    [Yokokou_Structural] エラーが発生しました: {e}")
        _log_print(f"    [Yokokou_Structural] トレースバック:\n{traceback.format_exc()}")
        raise


def Calculate_Point_Yokokou_Structural(Senkei_data, MainPanel_data, girder_list, position_type, section_name, z_offset):
    """
    横構の座標点を計算

    横構は主桁間を水平方向に繋ぐため、各桁の指定された位置（上フランジまたは下フランジ）から接続点を取得します。
    X型トラスを生成するため、各桁の両端（S1とE1）の点も取得します。

    Args:
        Senkei_data: 線形データ
        MainPanel_data: メインパネルデータ
        girder_list: 桁番号のリスト（例：["G1", "G2", "G3"]）
        position_type: 位置タイプ（"Top" または "Bottom"）
        section_name: 断面名（例："C1"）- 中央点として使用（オプション）
        z_offset: Z方向のオフセット

    Returns:
        arCoordPoint_Yokokou_Structural: 座標点のリスト（各桁について、S1, E1, および中央点（section_nameが指定されている場合）を含む）
    """
    arCoordPoint_Yokokou_Structural = []

    _log_print(
        f"    [Yokokou_Structural Point] 位置タイプ: {position_type}, 断面名: {section_name}, Zオフセット: {z_offset}"
    )

    # 各桁の接続点を計算（両端S1, E1、および中央点）
    for girder_name in girder_list:
        # 桁名からメインパネルを探す
        # まず、ブロック番号を取得
        number_block = None
        for panel in MainPanel_data:
            Type_panel = panel["Type"]
            if Type_panel["Girder"] == girder_name:
                number_block = Type_panel["Block"]
                break

        if number_block is None:
            _log_print(
                f"    [Yokokou_Structural Point] 警告: 桁 '{girder_name}' のブロック番号が見つかりません。デフォルト値 '1' を使用します。"
            )
            number_block = "1"

        # 位置タイプに応じてパネルを選択
        # number_blockは既に"B1"のような形式なので、"B"を追加しない
        if position_type == "Top":
            # 上横構：上フランジパネルを使用
            name_mainpanel = girder_name + number_block + "UF"
        elif position_type == "Bottom":
            # 下横構：下フランジパネルを使用
            name_mainpanel = girder_name + number_block + "LF"
        else:
            _log_print(
                f"    [Yokokou_Structural Point] 警告: 位置タイプ '{position_type}' が無効です。'Bottom' を使用します。"
            )
            name_mainpanel = girder_name + number_block + "LF"

        panel_found = False

        for panel in MainPanel_data:
            if panel["Name"] == name_mainpanel:
                panel_found = True
                Line_mainpanel = panel["Line"]
                Sec_mainpanel = panel["Sec"]
                _log_print(
                    f"    [Yokokou_Structural Point] パネル発見: {name_mainpanel}, Line={Line_mainpanel}, Sec={Sec_mainpanel}"
                )

                # 線形から座標を取得
                arCoordLines_Mod = Load_Coordinate_Panel(Senkei_data, Line_mainpanel, Sec_mainpanel)

                # 各桁の両端（S1, E1）の点を取得
                # S1（開始点）
                if "S1" in Sec_mainpanel:
                    idx_s1 = Sec_mainpanel.index("S1")
                    if position_type == "Top":
                        pt_s1 = arCoordLines_Mod[0][idx_s1]  # 上フランジの点
                    else:
                        pt_s1 = arCoordLines_Mod[-1][idx_s1]  # 下フランジの点
                    p_s1 = [pt_s1[0], pt_s1[1], pt_s1[2] + z_offset]
                    data_s1 = {
                        "Name": girder_name + "_S1",
                        "Girder": girder_name,
                        "Section": "S1",
                        "X": p_s1[0],
                        "Y": p_s1[1],
                        "Z": p_s1[2],
                    }
                    arCoordPoint_Yokokou_Structural.append(data_s1)
                    _log_print(
                        f"    [Yokokou_Structural Point] S1計算完了: {girder_name}_S1 = [{p_s1[0]:.2f}, {p_s1[1]:.2f}, {p_s1[2]:.2f}]"
                    )

                # E1（終了点）
                if "E1" in Sec_mainpanel:
                    idx_e1 = Sec_mainpanel.index("E1")
                    if position_type == "Top":
                        pt_e1 = arCoordLines_Mod[0][idx_e1]  # 上フランジの点
                    else:
                        pt_e1 = arCoordLines_Mod[-1][idx_e1]  # 下フランジの点
                    p_e1 = [pt_e1[0], pt_e1[1], pt_e1[2] + z_offset]
                    data_e1 = {
                        "Name": girder_name + "_E1",
                        "Girder": girder_name,
                        "Section": "E1",
                        "X": p_e1[0],
                        "Y": p_e1[1],
                        "Z": p_e1[2],
                    }
                    arCoordPoint_Yokokou_Structural.append(data_e1)
                    _log_print(
                        f"    [Yokokou_Structural Point] E1計算完了: {girder_name}_E1 = [{p_e1[0]:.2f}, {p_e1[1]:.2f}, {p_e1[2]:.2f}]"
                    )

                # 中央点（section_nameが指定されている場合、オプション）
                if section_name and section_name in Sec_mainpanel:
                    idx = Sec_mainpanel.index(section_name)
                    if position_type == "Top":
                        pt = arCoordLines_Mod[0][idx]  # 上フランジの点
                    else:
                        pt = arCoordLines_Mod[-1][idx]  # 下フランジの点
                    p = [pt[0], pt[1], pt[2] + z_offset]
                    data = {
                        "Name": girder_name + "_" + section_name,
                        "Girder": girder_name,
                        "Section": section_name,
                        "X": p[0],
                        "Y": p[1],
                        "Z": p[2],
                    }
                    arCoordPoint_Yokokou_Structural.append(data)
                    _log_print(
                        f"    [Yokokou_Structural Point] 中央点計算完了: {girder_name}_{section_name} = [{p[0]:.2f}, {p[1]:.2f}, {p[2]:.2f}]"
                    )

                break

        if not panel_found:
            _log_print(f"    [Yokokou_Structural Point] 警告: パネル '{name_mainpanel}' が見つかりません")

    _log_print(f"    [Yokokou_Structural Point] 計算完了: {len(arCoordPoint_Yokokou_Structural)}個の点を取得")
    return arCoordPoint_Yokokou_Structural


def Draw_Truss_Yokokou_Structural(ifc_all, arCoordPoint_Yokokou_Structural, truss_info, hole_info):
    """
    横構のトラス構造を生成

    横構はトラス構造として、水平部材（弦材）と斜め部材（対角材）で構成されます。

    Args:
        ifc_all: (ifc_file, bridge_span, geom_context)
        arCoordPoint_Yokokou_Structural: 座標点のリスト（各桁の接続点）
        truss_info: トラス情報 {"Horizontal": {...}, "Diagonal": {...}}
        hole_info: 穴情報
    """
    ifc_file, bridge_span, geom_context = ifc_all

    if len(arCoordPoint_Yokokou_Structural) < 2:
        _log_print(
            f"    [Yokokou_Structural Truss] エラー: 有効な点が2個未満です（{len(arCoordPoint_Yokokou_Structural)}個）"
        )
        return

    # 水平部材（弦材）の生成
    # 各桁のS1点とE1点を使用して水平部材を生成
    horizontal_info = truss_info.get("Horizontal", {})
    if horizontal_info:
        _log_print("    [Yokokou_Structural Truss] 水平部材の生成を開始")
        infor_horizontal = horizontal_info.get("Infor", [])
        pitch_horizontal = horizontal_info.get("Pitch", [0, "X", 0])

        if len(infor_horizontal) >= 3:
            type_shape = infor_horizontal[0]
            size_shape = infor_horizontal[1]
            mat_shape = infor_horizontal[2]

            # 各桁のS1点とE1点を取得
            girder_s1_points = []  # 各桁のS1点
            girder_e1_points = []  # 各桁のE1点
            girder_names = []

            for point in arCoordPoint_Yokokou_Structural:
                section = point.get("Section", "")
                girder_name = point.get("Girder", "")
                if section == "S1":
                    girder_s1_points.append([point["X"], point["Y"], point["Z"]])
                    if girder_name not in girder_names:
                        girder_names.append(girder_name)
                elif section == "E1":
                    girder_e1_points.append([point["X"], point["Y"], point["Z"]])

            _log_print(
                f"    [Yokokou_Structural Truss] S1点: {len(girder_s1_points)}個, E1点: {len(girder_e1_points)}個"
            )

            # 水平部材を生成する関数
            def create_horizontal_member(p1, p2, member_name):
                """水平部材を生成するヘルパー関数"""
                # ピッチ処理
                result_pitch_shape = "/".join(str(x) for x in pitch_horizontal)
                p1mod_shape, p2mod_shape = Calculate_Pse_Shape(result_pitch_shape, p1, p2)

                _log_print(
                    f"    [Yokokou_Structural Truss] 水平部材 {member_name}: p1mod={p1mod_shape}, p2mod={p2mod_shape}"
                )

                # プロファイル生成
                arCoor_profile = None
                if type_shape == "CT":
                    arCoor_profile = DefMath.profile2D_shapCT(size_shape, [0, 0])
                elif type_shape == "L":
                    arCoor_profile = DefMath.profile2D_shapL(size_shape, [0, 0])
                elif type_shape == "C":
                    arCoor_profile = DefMath.profile2D_shapC(size_shape, [0, 0])
                else:
                    _log_print(f"    [Yokokou_Structural Truss] エラー: 未対応の形状タイプ '{type_shape}'")
                    return False

                if arCoor_profile is None:
                    _log_print(
                        f"    [Yokokou_Structural Truss] エラー: 形状名 '{size_shape}' がprofile2D_shap{type_shape}のリストに存在しません。"
                    )
                    return False

                # 3D座標への変換
                p1_3d = p1mod_shape
                p2_3d = p2mod_shape
                p3_3d = [p1_3d[0], p1_3d[1], p1_3d[2] + 100]
                normal_shape = DefMath.Normal_vector(p1_3d, p2_3d, p3_3d)

                p1_2d = [0, 0, 0]
                p2_2d = [100, 0, 0]
                p3_2d = [0, 100, 0]

                p1mod_shape_3D_al = DefMath.Transform_point_face2face(
                    p1mod_shape, p1_2d, p2_2d, p3_2d, p1_3d, p2_3d, p3_3d
                )
                p2mod_shape_3D_al = DefMath.Transform_point_face2face(
                    p2mod_shape, p1_2d, p2_2d, p3_2d, p1_3d, p2_3d, p3_3d
                )
                p3mod_shape_3D_al = p1mod_shape_3D_al + 100 * normal_shape

                # ソリッド生成
                solid_shape = DefIFC.extrude_profile_and_align(
                    ifc_file,
                    arCoor_profile,
                    DefMath.Calculate_distance_p2p(p1mod_shape, p2mod_shape),
                    p1mod_shape_3D_al,
                    p2mod_shape_3D_al,
                    p3mod_shape_3D_al,
                )

                color_style = DefIFC.create_color(ifc_file, 92.0, 25.0, 25.0)
                styled_item = ifc_file.createIfcStyledItem(Item=solid_shape, Styles=[color_style])
                shape_representation = ifc_file.createIfcShapeRepresentation(
                    ContextOfItems=geom_context,
                    RepresentationIdentifier="Body",
                    RepresentationType="Brep",
                    Items=[solid_shape],
                )
                DefIFC.Add_shape_representation_in_Beam(ifc_file, bridge_span, shape_representation, member_name)

                return True

            # S1点同士を結ぶ水平部材
            for i in range(len(girder_s1_points) - 1):
                pbs_shape = girder_s1_points[i]
                pbe_shape = girder_s1_points[i + 1]
                create_horizontal_member(pbs_shape, pbe_shape, f"Yokokou_Structural-Horizontal-S1-{i + 1}")

            # E1点同士を結ぶ水平部材
            for i in range(len(girder_e1_points) - 1):
                pbs_shape = girder_e1_points[i]
                pbe_shape = girder_e1_points[i + 1]
                create_horizontal_member(pbs_shape, pbe_shape, f"Yokokou_Structural-Horizontal-E1-{i + 1}")

            _log_print("    [Yokokou_Structural Truss] 水平部材の生成完了")

    # 斜め部材（対角材）の生成
    diagonal_info = truss_info.get("Diagonal", {})
    if diagonal_info:
        _log_print("    [Yokokou_Structural Truss] 斜め部材の生成を開始")
        infor_diagonal = diagonal_info.get("Infor", [])
        pattern_diagonal = diagonal_info.get("Pattern", "X")  # "X" パターン（交差型）
        pitch_diagonal = diagonal_info.get("Pitch", [0, "X", 0])

        if len(infor_diagonal) >= 3:
            type_shape = infor_diagonal[0]
            size_shape = infor_diagonal[1]
            mat_shape = infor_diagonal[2]

            # Xパターンの場合、対角線を生成
            if pattern_diagonal == "X":
                # 各桁のS1とE1の点を取得
                girder_points = {}  # {girder_name: {"S1": [...], "E1": [...]}}
                for point in arCoordPoint_Yokokou_Structural:
                    girder_name = point.get("Girder", "")
                    section = point.get("Section", "")
                    if girder_name and section:
                        if girder_name not in girder_points:
                            girder_points[girder_name] = {}
                        girder_points[girder_name][section] = [point["X"], point["Y"], point["Z"]]

                _log_print(f"    [Yokokou_Structural Truss] 桁の点: {girder_points}")

                # 各セグメント（隣接する2桁間）でX型トラスを生成
                girder_names = list(girder_points.keys())
                for i in range(len(girder_names) - 1):
                    girder1 = girder_names[i]
                    girder2 = girder_names[i + 1]

                    # 各桁のS1とE1の点を取得
                    if (
                        "S1" in girder_points[girder1]
                        and "E1" in girder_points[girder1]
                        and "S1" in girder_points[girder2]
                        and "E1" in girder_points[girder2]
                    ):
                        # 対角線1: G1のS1 → G2のE1
                        p1_diag1 = girder_points[girder1]["S1"]
                        p2_diag1 = girder_points[girder2]["E1"]

                        # 対角線2: G1のE1 → G2のS1
                        p1_diag2 = girder_points[girder1]["E1"]
                        p2_diag2 = girder_points[girder2]["S1"]

                        # 対角線1を生成
                        result_pitch_shape = "/".join(str(x) for x in pitch_diagonal)
                        p1mod_shape, p2mod_shape = Calculate_Pse_Shape(result_pitch_shape, p1_diag1, p2_diag1)

                        _log_print(
                            f"    [Yokokou_Structural Truss] 斜め部材1 ({girder1}_S1→{girder2}_E1): p1mod={p1mod_shape}, p2mod={p2mod_shape}"
                        )

                        # プロファイル生成
                        arCoor_profile = None
                        if type_shape == "CT":
                            arCoor_profile = DefMath.profile2D_shapCT(size_shape, [0, 0])
                        elif type_shape == "L":
                            arCoor_profile = DefMath.profile2D_shapL(size_shape, [0, 0])
                        elif type_shape == "C":
                            arCoor_profile = DefMath.profile2D_shapC(size_shape, [0, 0])
                        else:
                            _log_print(f"    [Yokokou_Structural Truss] エラー: 未対応の形状タイプ '{type_shape}'")
                            continue

                        if arCoor_profile is None:
                            _log_print(
                                f"    [Yokokou_Structural Truss] エラー: 形状名 '{size_shape}' がprofile2D_shap{type_shape}のリストに存在しません。"
                            )
                            continue

                        # 3D座標への変換
                        p1_3d = p1mod_shape
                        p2_3d = p2mod_shape
                        p3_3d = [p1_3d[0], p1_3d[1], p1_3d[2] + 100]
                        normal_shape = DefMath.Normal_vector(p1_3d, p2_3d, p3_3d)

                        p1_2d = [0, 0, 0]
                        p2_2d = [100, 0, 0]
                        p3_2d = [0, 100, 0]

                        p1mod_shape_3D_al = DefMath.Transform_point_face2face(
                            p1mod_shape, p1_2d, p2_2d, p3_2d, p1_3d, p2_3d, p3_3d
                        )
                        p2mod_shape_3D_al = DefMath.Transform_point_face2face(
                            p2mod_shape, p1_2d, p2_2d, p3_2d, p1_3d, p2_3d, p3_3d
                        )
                        p3mod_shape_3D_al = p1mod_shape_3D_al + 100 * normal_shape

                        # ソリッド生成
                        solid_shape = DefIFC.extrude_profile_and_align(
                            ifc_file,
                            arCoor_profile,
                            DefMath.Calculate_distance_p2p(p1mod_shape, p2mod_shape),
                            p1mod_shape_3D_al,
                            p2mod_shape_3D_al,
                            p3mod_shape_3D_al,
                        )

                        color_style = DefIFC.create_color(ifc_file, 92.0, 25.0, 25.0)
                        styled_item = ifc_file.createIfcStyledItem(Item=solid_shape, Styles=[color_style])
                        shape_representation = ifc_file.createIfcShapeRepresentation(
                            ContextOfItems=geom_context,
                            RepresentationIdentifier="Body",
                            RepresentationType="Brep",
                            Items=[solid_shape],
                        )
                        DefIFC.Add_shape_representation_in_Beam(
                            ifc_file, bridge_span, shape_representation, f"Yokokou_Structural-Diagonal-{i + 1}-1"
                        )

                        # 対角線2を生成
                        p1mod_shape, p2mod_shape = Calculate_Pse_Shape(result_pitch_shape, p1_diag2, p2_diag2)

                        _log_print(
                            f"    [Yokokou_Structural Truss] 斜め部材2 ({girder1}_E1→{girder2}_S1): p1mod={p1mod_shape}, p2mod={p2mod_shape}"
                        )

                        p1_3d = p1mod_shape
                        p2_3d = p2mod_shape
                        p3_3d = [p1_3d[0], p1_3d[1], p1_3d[2] + 100]
                        normal_shape = DefMath.Normal_vector(p1_3d, p2_3d, p3_3d)

                        p1mod_shape_3D_al = DefMath.Transform_point_face2face(
                            p1mod_shape, p1_2d, p2_2d, p3_2d, p1_3d, p2_3d, p3_3d
                        )
                        p2mod_shape_3D_al = DefMath.Transform_point_face2face(
                            p2mod_shape, p1_2d, p2_2d, p3_2d, p1_3d, p2_3d, p3_3d
                        )
                        p3mod_shape_3D_al = p1mod_shape_3D_al + 100 * normal_shape

                        solid_shape = DefIFC.extrude_profile_and_align(
                            ifc_file,
                            arCoor_profile,
                            DefMath.Calculate_distance_p2p(p1mod_shape, p2mod_shape),
                            p1mod_shape_3D_al,
                            p2mod_shape_3D_al,
                            p3mod_shape_3D_al,
                        )

                        color_style = DefIFC.create_color(ifc_file, 92.0, 25.0, 25.0)
                        styled_item = ifc_file.createIfcStyledItem(Item=solid_shape, Styles=[color_style])
                        shape_representation = ifc_file.createIfcShapeRepresentation(
                            ContextOfItems=geom_context,
                            RepresentationIdentifier="Body",
                            RepresentationType="Brep",
                            Items=[solid_shape],
                        )
                        DefIFC.Add_shape_representation_in_Beam(
                            ifc_file, bridge_span, shape_representation, f"Yokokou_Structural-Diagonal-{i + 1}-2"
                        )

                        _log_print(f"    [Yokokou_Structural Truss] 斜め部材 セグメント {i + 1} (X型) の生成完了")
                    else:
                        _log_print(
                            f"    [Yokokou_Structural Truss] 警告: 桁 '{girder1}' または '{girder2}' のS1/E1点が見つかりません。"
                        )

            # より複雑なトラスパターン（例：K型、N型など）は将来の拡張として実装可能

    _log_print("    [Yokokou_Structural Truss] トラス構造の生成完了")


# -----------------------------Yokokou_LateralBracing（横構）--------------------------------------------
def Calculate_Yokokou_LateralBracing(ifc_all, Senkei_data, MainPanel_data, infor_lateral):
    """
    横構（Lateral Bracing）の生成
    単純に「開始点と終了点を結ぶ部材」を1本作成する。
    """
    try:
        ifc_file, bridge_span, geom_context = ifc_all
        (
            name_lb,
            level_lb,
            member_info,
            shape_info,
            pitch_info,
            z_offset,
            y_offset,
            hole_info,
            guss_list,
        ) = infor_lateral

        _log_print(f"    [Yokokou_LB] '{name_lb}' の処理を開始 (Level={level_lb})")

        # デバッグ: JSONから取得したmember_infoを確認
        _log_print(f"    [Yokokou_LB] member_info={member_info}")
        _log_print(f"    [Yokokou_LB] Start={member_info.get('Start', {})}, End={member_info.get('End', {})}")

        start_point = _get_lateral_brace_point(
            member_info.get("Start", {}),
            level_lb,
            Senkei_data,
            MainPanel_data,
            z_offset,
            y_offset,
            point_role="Start",
        )
        end_point = _get_lateral_brace_point(
            member_info.get("End", {}),
            level_lb,
            Senkei_data,
            MainPanel_data,
            z_offset,
            y_offset,
            point_role="End",
        )

        if start_point is None or end_point is None:
            _log_print("    [Yokokou_LB] エラー: Start/Endのいずれかの点が取得できなかったため処理を中断します。")
            return

        member_dict = {
            "Infor": shape_info,
            "Pitch": pitch_info,
        }

        distance = DefMath.Calculate_distance_p2p(start_point, end_point)
        _log_print(f"    [Yokokou_LB] Start={start_point}, End={end_point}, 長さ={distance:.2f}mm, Shape={shape_info}")

        # 位置情報を含む名前を生成: {Name}_G{Girder1}_{Section1}_G{Girder2}_{Section2}
        # 名前から既存の桁情報を削除して重複を避ける
        start_girder_raw = member_info.get("Start", {}).get("Girder", "")
        start_section_raw = member_info.get("Start", {}).get("Section", "")
        end_girder_raw = member_info.get("End", {}).get("Girder", "")
        end_section_raw = member_info.get("End", {}).get("Section", "")

        # G1 -> 1 のように数字部分だけを抽出（セクション名はそのまま使用）
        import re

        start_girder_num = re.sub(r"^G", "", start_girder_raw) if start_girder_raw.startswith("G") else start_girder_raw
        end_girder_num = re.sub(r"^G", "", end_girder_raw) if end_girder_raw.startswith("G") else end_girder_raw
        # セクション名はそのまま使用（S1, C1, D4など、元の形式を保持）
        start_section_name = start_section_raw
        end_section_name = end_section_raw

        # 名前から既存の桁情報パターンを削除
        base_name = name_lb
        # _G{桁名}のパターンを削除
        base_name = re.sub(r"_G\d+(_G\d+)?", "", base_name)
        # 末尾の_{セクション}も削除（既にある場合、Sで始まるものも含む）
        base_name = re.sub(r"_[SCE]\w+(_[SCE]\w+)?$", "", base_name)

        member_name = f"{base_name}_G{start_girder_num}_{start_section_name}_G{end_girder_num}_{end_section_name}"

        _create_bracing_member(ifc_all, member_dict, start_point, end_point, member_name, use_pitch_shape=False)

        if guss_list:
            _log_print("    [Yokokou_LB] ガセット定義が存在します（未実装）")
    except Exception as e:
        import traceback

        _log_print(f"    [Yokokou_LB] エラーが発生しました: {e}")
        _log_print(f"    [Yokokou_LB] トレースバック:\n{traceback.format_exc()}")
        raise


def _get_lateral_brace_point(point_info, level_lb, Senkei_data, MainPanel_data, z_offset, y_offset, point_role="Start"):
    """
    横構で指定されたStart/End点の座標を取得

    優先順位:
    1. Load_Coordinate_Point: SenkeiのPoint配列から直接取得（D4などの独自Section名に対応）
    2. Load_Coordinate_Panel + _pickup_point_from_line: パネルのSec配列に基づく取得（S1, C1, E1など）
    """
    if not point_info:
        _log_print(f"    [Yokokou_LB Point] 警告: {point_role}点の定義が存在しません。")
        return None

    girder_name = point_info.get("Girder")
    line_name = point_info.get("Line")
    section_name = point_info.get("Section")

    # デバッグ: JSONから取得した値を確認
    _log_print(f"    [Yokokou_LB Point] {point_role} JSON取得値: point_info={point_info}, section_name={section_name}")

    if not girder_name or not section_name:
        _log_print(
            f"    [Yokokou_LB Point] 警告: {point_role}点に必要な情報（Girder/Section）が不足しています: {point_info}"
        )
        return None

    # 方法1: Load_Coordinate_Pointを使用してSenkeiのPoint配列から直接取得を試みる
    # これにより、D4などの独自Section名がSenkeiに定義されていれば使用可能

    if line_name:
        p_direct = Load_Coordinate_Point(Senkei_data, line_name, section_name)
        if p_direct is not None:
            point_with_offset = [p_direct[0], p_direct[1] + y_offset, p_direct[2] + z_offset]
            _log_print(
                f"    [Yokokou_LB Point] {point_role}: 直接取得成功 - Girder={girder_name}, Line={line_name}, Section={section_name}, Point={point_with_offset}"
            )
            return point_with_offset
        else:
            _log_print(
                f"    [Yokokou_LB Point] {point_role}: 直接取得失敗（SenkeiのPoint配列に'{section_name}'が見つかりません）- パネルベースの取得にフォールバック"
            )

    # 方法2: パネルのSec配列に基づく取得（従来の方法）
    panel = _find_panel_for_level(girder_name, level_lb, MainPanel_data, preferred_line=line_name)
    if panel is None:
        _log_print(f"    [Yokokou_LB Point] 警告: 桁 '{girder_name}' の {level_lb} パネルが見つかりません。")
        return None

    arCoordLines = Load_Coordinate_Panel(Senkei_data, panel["Line"], panel["Sec"])
    if not arCoordLines:
        _log_print(f"    [Yokokou_LB Point] 警告: 桁 '{girder_name}' の座標取得に失敗しました。")
        return None

    line_idx = _find_line_index(panel["Line"], line_name)
    center_idx = min(max(len(arCoordLines) // 2, 0), len(arCoordLines) - 1)
    if line_idx is None:
        line_idx = center_idx
        fallback_name = panel["Line"][line_idx] if panel["Line"] else "Unknown"
        _log_print(
            f"    [Yokokou_LB Point] {girder_name}-{point_role}: 指定ライン '{line_name}' が見つからず、'{fallback_name}' を使用します。"
        )

    coord_line = arCoordLines[line_idx]
    idx_section = _find_section_index(panel["Sec"], section_name)
    p = _pickup_point_from_line(coord_line, idx_section, section_name, girder_name)

    if p is None:
        _log_print(f"    [Yokokou_LB Point] 警告: 桁 '{girder_name}' の断面 '{section_name}' の点が取得できません。")
        return None

    point_with_offset = [p[0], p[1] + y_offset, p[2] + z_offset]
    used_line_name = panel["Line"][line_idx] if panel["Line"] else "Unknown"
    _log_print(
        f"    [Yokokou_LB Point] {point_role}: パネルベース取得 - Girder={girder_name}, Line={used_line_name}, Section={section_name}, Point={point_with_offset}"
    )

    return point_with_offset


def Collect_Points_LateralBracing(
    Senkei_data,
    MainPanel_data,
    girder_pair,
    level_lb,
    range_lb,
    reference_line_info,
    z_offset,
    y_offset,
):
    """
    横構の座標点を取得
    """
    result = {}
    ordered_girders = []

    start_sec = range_lb.get("Start", "S1")
    end_sec = range_lb.get("End", "E1")

    if not girder_pair or len(girder_pair) < 2:
        _log_print(f"    [Yokokou_LB Point] 警告: GirderPairの定義が不十分です: {girder_pair}")
        return result, ordered_girders

    for idx_girder, girder_name in enumerate(girder_pair):
        panel = _find_panel_for_level(girder_name, level_lb, MainPanel_data)
        if panel is None:
            _log_print(f"    [Yokokou_LB Point] 警告: 桁 '{girder_name}' の{level_lb}パネルが見つかりません。")
            continue

        arCoordLines = Load_Coordinate_Panel(Senkei_data, panel["Line"], panel["Sec"])
        if not arCoordLines:
            _log_print(f"    [Yokokou_LB Point] 警告: 桁 '{girder_name}' の座標取得に失敗しました。")
            continue

        sec_list = panel["Sec"]
        target_line_name = _resolve_reference_line(reference_line_info, girder_name, idx_girder)
        line_idx = _find_line_index(panel["Line"], target_line_name)

        center_idx = min(max(len(arCoordLines) // 2, 0), len(arCoordLines) - 1)
        if line_idx is None:
            line_idx = center_idx
            fallback_name = panel["Line"][line_idx] if panel["Line"] else "Unknown"
            _log_print(
                f"    [Yokokou_LB Point] 桁 '{girder_name}' のReferenceLine '{target_line_name}' が見つからず、中央ライン '{fallback_name}' を使用します。"
            )
        used_line_name = panel["Line"][line_idx] if panel["Line"] else "Unknown"
        coord_line = arCoordLines[line_idx]

        idx_start = _find_section_index(sec_list, start_sec)
        idx_end = _find_section_index(sec_list, end_sec)

        p_start = _pickup_point_from_line(coord_line, idx_start, start_sec, girder_name)
        p_end = _pickup_point_from_line(coord_line, idx_end, end_sec, girder_name)

        if p_start is None or p_end is None:
            _log_print(f"    [Yokokou_LB Point] 警告: 桁 '{girder_name}' の範囲点が取得できません。")
            continue

        p_start = [p_start[0], p_start[1] + y_offset, p_start[2] + z_offset]
        p_end = [p_end[0], p_end[1] + y_offset, p_end[2] + z_offset]

        result[girder_name] = {"Start": p_start, "End": p_end}
        ordered_girders.append(girder_name)

        _log_print(
            f"    [Yokokou_LB Point] {girder_name}: Line={used_line_name}, Start={p_start}, End={p_end}, Yoffset={y_offset}"
        )

        if line_idx != center_idx and center_idx < len(arCoordLines):
            center_line = arCoordLines[center_idx]
            if idx_start is not None and idx_start < len(center_line):
                diff_start = np.array(coord_line[idx_start]) - np.array(center_line[idx_start])
                _log_print(
                    f"        [Yokokou_LB Point] Start偏差(参照線-中央) = [{diff_start[0]:.2f}, {diff_start[1]:.2f}, {diff_start[2]:.2f}]"
                )
            if idx_end is not None and idx_end < len(center_line):
                diff_end = np.array(coord_line[idx_end]) - np.array(center_line[idx_end])
                _log_print(
                    f"        [Yokokou_LB Point] End偏差(参照線-中央) = [{diff_end[0]:.2f}, {diff_end[1]:.2f}, {diff_end[2]:.2f}]"
                )

    return result, ordered_girders


def Draw_LateralBracing_Truss(ifc_all, name_lb, ordered_girders, girder_points, truss_info, hole_info):
    """
    横構の水平材・斜材を生成
    """
    if len(ordered_girders) < 2:
        return

    girder1, girder2 = ordered_girders[:2]
    points1 = girder_points[girder1]
    points2 = girder_points[girder2]

    chord_info = truss_info.get("Chord", {})
    diagonal_info = truss_info.get("Diagonal", {})

    _log_print(f"    [Yokokou_LB Draw] chord_info={chord_info}, diagonal_info={diagonal_info}")

    if chord_info.get("Infor"):
        _create_bracing_member(ifc_all, chord_info, points1["Start"], points2["Start"], f"{name_lb}-Chord-Start")
        _create_bracing_member(ifc_all, chord_info, points1["End"], points2["End"], f"{name_lb}-Chord-End")

    if diagonal_info.get("Infor"):
        pattern = diagonal_info.get("Pattern", "X")
        if pattern.upper() == "X":
            _create_bracing_member(ifc_all, diagonal_info, points1["Start"], points2["End"], f"{name_lb}-Diag-1")
            _create_bracing_member(ifc_all, diagonal_info, points1["End"], points2["Start"], f"{name_lb}-Diag-2")
        else:
            _create_bracing_member(ifc_all, diagonal_info, points1["Start"], points2["End"], f"{name_lb}-Diag")


def _create_bracing_member(ifc_all, member_info, p_start, p_end, member_name, use_pitch_shape=True):
    """
    プロファイルを用いて部材を生成
    """
    ifc_file, bridge_span, geom_context = ifc_all

    infor = member_info.get("Infor", [])
    if len(infor) < 3:
        _log_print(f"    [_create_bracing_member] 警告: Infor定義が不足しています: {member_info}")
        return

    type_shape, size_shape, mat_shape = infor[:3]
    pitch = member_info.get("Pitch", [0, "X", 0])

    if use_pitch_shape:
        result_pitch_shape = "/".join(str(x) for x in pitch)
        p1mod_shape, p2mod_shape = Calculate_Pse_Shape(result_pitch_shape, p_start, p_end)
    else:
        p1mod_shape, p2mod_shape = p_start, p_end

    if type_shape == "CT":
        arCoor_profile = DefMath.profile2D_shapCT(size_shape, [0, 0])
    elif type_shape == "L":
        arCoor_profile = DefMath.profile2D_shapL(size_shape, [0, 0])
    elif type_shape == "C":
        arCoor_profile = DefMath.profile2D_shapC(size_shape, [0, 0])
    else:
        _log_print(f"    [_create_bracing_member] 警告: 未対応の形状タイプ '{type_shape}'")
        return

    if arCoor_profile is None:
        _log_print(f"    [_create_bracing_member] 警告: 形状 '{size_shape}' が定義されていません。")
        return

    p1_3d = p1mod_shape
    p2_3d = p2mod_shape
    # 部材の向きを計算（p1からp2への方向ベクトル）
    dir_vec = [p2_3d[0] - p1_3d[0], p2_3d[1] - p1_3d[1], p2_3d[2] - p1_3d[2]]
    dir_len = (dir_vec[0] ** 2 + dir_vec[1] ** 2 + dir_vec[2] ** 2) ** 0.5
    if dir_len > 0:
        dir_vec = [dir_vec[0] / dir_len, dir_vec[1] / dir_len, dir_vec[2] / dir_len]

    # p3_3dは、p1_3dから部材の向きに垂直な方向に100オフセット
    # 横構（水平面内の部材）の場合は、常にZ方向にオフセット
    if abs(dir_vec[2]) < 0.1:  # Z成分がほぼ0（水平な部材 = 横構）
        p3_3d = [p1_3d[0], p1_3d[1], p1_3d[2] + 100]
    elif abs(dir_vec[1]) > 0.9:  # Y方向に主に伸びている
        p3_3d = [p1_3d[0] + 100, p1_3d[1], p1_3d[2]]
    elif abs(dir_vec[0]) > 0.9:  # X方向に主に伸びている
        p3_3d = [p1_3d[0], p1_3d[1] + 100, p1_3d[2]]
    else:  # その他の場合（斜めの部材など）
        p3_3d = [p1_3d[0], p1_3d[1], p1_3d[2] + 100]

    normal_shape = DefMath.Normal_vector(p1_3d, p2_3d, p3_3d)

    # p1mod_shape, p2mod_shapeは既に3D座標なので、変換不要
    p1mod_shape_3D_al = p1mod_shape
    p2mod_shape_3D_al = p2mod_shape
    p3mod_shape_3D_al = p1mod_shape_3D_al + 100 * normal_shape

    solid_shape = DefIFC.extrude_profile_and_align(
        ifc_file,
        arCoor_profile,
        DefMath.Calculate_distance_p2p(p1mod_shape, p2mod_shape),
        p1mod_shape_3D_al,
        p2mod_shape_3D_al,
        p3mod_shape_3D_al,
    )

    color_style = DefIFC.create_color(ifc_file, 92.0, 25.0, 25.0)
    if solid_shape:
        ifc_file.createIfcStyledItem(Item=solid_shape, Styles=[color_style])
        shape_representation = ifc_file.createIfcShapeRepresentation(
            ContextOfItems=geom_context, RepresentationIdentifier="Body", RepresentationType="Brep", Items=[solid_shape]
        )
        DefIFC.Add_shape_representation_in_Beam(ifc_file, bridge_span, shape_representation, member_name)
        _log_print(f"    [_create_bracing_member] {member_name} を生成しました。")


def _find_panel_for_level(girder_name, level_lb, MainPanel_data, preferred_line=None):
    target_type = "UF" if str(level_lb).lower() == "top" else "LF"
    fallback_panel = None
    for panel in MainPanel_data:
        Type_panel = panel.get("Type", {})
        if Type_panel.get("Girder") == girder_name and Type_panel.get("TypePanel") == target_type:
            if preferred_line is None or preferred_line in panel.get("Line", []):
                return panel
            if fallback_panel is None:
                fallback_panel = panel
    return fallback_panel


def _find_section_index(sec_list, target_sec):
    """
    セクションリストから対象セクションのインデックスを取得。
    C1が見つからない場合はNoneを返し、_pickup_point_from_lineで補間計算させる。
    """
    if target_sec in sec_list:
        return sec_list.index(target_sec)

    # 中間点が見つからない場合は補間計算させる
    interpolate_sections = {"S2", "C1", "E2"}
    if target_sec in interpolate_sections:
        _log_print(f"    [_find_section_index] {target_sec}がSecに存在しないため補間計算を実行: Sec={sec_list}")
        return None

    _log_print(f"    [_find_section_index] 警告: 断面 '{target_sec}' がSecに存在しません。Sec={sec_list}")
    if not sec_list:
        return None
    if target_sec < sec_list[0]:
        return 0
    return len(sec_list) - 1


def _pickup_point_from_line(coord_line, idx, section_name, girder_name):
    """
    座標線から指定インデックスの点を取得。
    インデックスが範囲外の場合、セクション名から補間計算。
    """
    if idx is None or (idx < 0 or idx >= len(coord_line)):
        # セクション名に基づいて補間計算
        if len(coord_line) >= 2:
            p_start = coord_line[0]
            p_end = coord_line[-1]

            # セクション名からX方向の比率を推定（30000mmスパンを想定）
            ratio = None
            if section_name == "S1":
                ratio = 0.0
            elif section_name == "S2":
                ratio = 4000.0 / 30000.0  # X=4000
            elif section_name == "C1":
                ratio = 0.5  # X=15000（中央）
            elif section_name == "E2":
                ratio = 26000.0 / 30000.0  # X=26000
            elif section_name == "E1":
                ratio = 1.0

            if ratio is not None:
                p_interp = [p_start[i] * (1 - ratio) + p_end[i] * ratio for i in range(3)]
                _log_print(
                    f"    [_pickup_point_from_line] {section_name}を補間計算: girder={girder_name}, ratio={ratio:.3f}, 点={[round(x, 2) for x in p_interp]}"
                )
                return p_interp

        _log_print(
            f"    [_pickup_point_from_line] 警告: 補間計算失敗 idx={idx}, girder={girder_name}, section={section_name}"
        )
        return None

    return coord_line[idx]


def _get_point_by_x_coordinate(Senkei_data, line_name, target_x):
    """
    指定された線形上の指定X座標に最も近い点を取得（線形補間も可能）

    Args:
        Senkei_data: 線形データ
        line_name: 線形名（例：TG1, TG2）
        target_x: 目標X座標（mm）

    Returns:
        座標点 [X, Y, Z]、見つからない場合はNone
    """

    coord_line = Load_Coordinate_PolLine(Senkei_data, line_name)
    if not coord_line or len(coord_line) == 0:
        _log_print(f"    [_get_point_by_x_coordinate] 警告: 線形 '{line_name}' が見つかりません")
        return None

    # X座標の範囲を確認
    x_coords = [pt[0] for pt in coord_line]
    min_x = min(x_coords)
    max_x = max(x_coords)

    # 目標X座標が範囲外の場合
    if target_x < min_x:
        _log_print(
            f"    [_get_point_by_x_coordinate] 警告: 目標X座標 {target_x}mm が線形 '{line_name}' の範囲外（最小: {min_x}mm）。最初の点を使用します。"
        )
        return coord_line[0]
    if target_x > max_x:
        _log_print(
            f"    [_get_point_by_x_coordinate] 警告: 目標X座標 {target_x}mm が線形 '{line_name}' の範囲外（最大: {max_x}mm）。最後の点を使用します。"
        )
        return coord_line[-1]

    # 目標X座標に最も近い点を見つける（線形補間）
    for i in range(len(coord_line) - 1):
        p1 = coord_line[i]
        p2 = coord_line[i + 1]
        x1, x2 = p1[0], p2[0]

        # このセグメント内に目標X座標があるか確認
        if (x1 <= target_x <= x2) or (x2 <= target_x <= x1):
            # 線形補間で点を計算
            if abs(x2 - x1) < 0.001:  # X座標がほぼ同じ場合
                return p1

            ratio = (target_x - x1) / (x2 - x1)
            y = p1[1] + (p2[1] - p1[1]) * ratio
            z = p1[2] + (p2[2] - p1[2]) * ratio
            result = [target_x, y, z]
            _log_print(f"    [_get_point_by_x_coordinate] 線形 '{line_name}' 上でX={target_x}mmの点を補間: {result}")
            return result

    # 見つからない場合（通常は発生しない）、最も近い点を返す
    closest_idx = 0
    min_dist = abs(coord_line[0][0] - target_x)
    for i, pt in enumerate(coord_line):
        dist = abs(pt[0] - target_x)
        if dist < min_dist:
            min_dist = dist
            closest_idx = i

    _log_print(
        f"    [_get_point_by_x_coordinate] 警告: 線形 '{line_name}' 上でX={target_x}mmの点が見つかりません。最も近い点を使用: {coord_line[closest_idx]}"
    )
    return coord_line[closest_idx]


def _resolve_reference_line(reference_line_info, girder_name, girder_index):
    if isinstance(reference_line_info, dict):
        return reference_line_info.get(girder_name)
    if isinstance(reference_line_info, list):
        if girder_index < len(reference_line_info):
            item = reference_line_info[girder_index]
            if isinstance(item, dict):
                if girder_name in item:
                    return item[girder_name]
                if len(item) == 1:
                    return next(iter(item.values()))
                return None
            return item
    if isinstance(reference_line_info, str):
        return reference_line_info
    return None


def _find_line_index(line_names, target_line_name):
    if not line_names:
        return None
    if target_line_name:
        for idx, name in enumerate(line_names):
            if name == target_line_name:
                return idx
    return None


# 注: Calculate_Yokogeta と関連関数は DefPanel.py に移動しました
# from src.bridge_json_to_ifc.ifc_utils_new.components.DefPanel import Calculate_Yokogeta
