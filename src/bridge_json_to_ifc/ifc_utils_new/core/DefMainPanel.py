"""
鋼橋IFCモデル生成 - 主桁パネル描画モジュール
主桁パネル（Web/UF/LF）のブレーク処理と描画関数
"""

from src.bridge_json_to_ifc.ifc_utils_new.core import DefIFC, DefMath
from src.bridge_json_to_ifc.ifc_utils_new.io import DefStrings
from src.bridge_json_to_ifc.ifc_utils_new.utils import DefBridgeUtils
from src.bridge_json_to_ifc.ifc_utils_new.utils.DefBridgeUtils import (
    Load_Coordinate_Panel,
    Calculate_Extend,
    Calculate_Extend_Coord,
)
from src.bridge_json_to_ifc.ifc_utils_new.components.DefPanel import (
    Check_break_mainpanle,
    Devide_Coord_FLG_mainpanel_break,
)
from src.bridge_json_to_ifc.ifc_utils_new.components.DefComponent import Draw_Corner
import numpy as np
import copy

# グローバル変数: ログファイル出力関数
log_print_func = None


def _log_print(*args, **kwargs):
    """ログファイル出力関数（DEBUG_MODE時のみ出力）"""
    if log_print_func:
        log_print_func(*args, **kwargs)


def get_non_duplicate_indices(arCoordLines, tolerance=0.01):
    """
    座標線から連続する重複点でない点のインデックスを取得する

    最初の点と最後の点は常に保持し、中間の重複点を削除する。
    最後の点と重複している中間点は削除される。

    Args:
        arCoordLines: 座標線の配列（各線は点の配列）
        tolerance: 重複判定の許容誤差（mm）

    Returns:
        重複していない点のインデックスのリスト
    """
    if not arCoordLines or len(arCoordLines) == 0:
        return []

    # まず最初の線で重複点のインデックスを特定
    first_line = arCoordLines[0]
    if len(first_line) <= 2:
        return list(range(len(first_line)))  # 2点以下なら全て保持

    # 重複していない点のインデックスを収集（最後の点は別処理）
    keep_indices = [0]  # 最初の点は常に保持
    for i in range(1, len(first_line) - 1):  # 最後の点は別処理
        prev_point = first_line[keep_indices[-1]]
        curr_point = first_line[i]
        # 距離を計算
        dist = np.sqrt(sum((a - b) ** 2 for a, b in zip(prev_point, curr_point)))
        if dist > tolerance:
            keep_indices.append(i)

    # 最後の点は常に追加
    keep_indices.append(len(first_line) - 1)

    # 最後の2点が重複している場合、最後から2番目を削除
    # （最初の点と最後の点を優先して保持するため）
    if len(keep_indices) >= 2:
        last_point = first_line[keep_indices[-1]]
        second_last_point = first_line[keep_indices[-2]]
        dist = np.sqrt(sum((a - b) ** 2 for a, b in zip(last_point, second_last_point)))
        if dist <= tolerance and len(keep_indices) > 2:
            # 最後から2番目を削除（ただし、最低2点は保持）
            keep_indices.pop(-2)

    return keep_indices


def apply_indices_to_coord_lines(arCoordLines, keep_indices):
    """
    指定されたインデックスの点のみを抽出する

    Args:
        arCoordLines: 座標線の配列
        keep_indices: 保持する点のインデックスのリスト

    Returns:
        抽出後の座標線の配列
    """
    if not arCoordLines or len(keep_indices) < 2:
        return arCoordLines

    result = []
    for line in arCoordLines:
        new_line = [line[idx] for idx in keep_indices if idx < len(line)]
        result.append(new_line)

    return result


def remove_consecutive_duplicate_points(arCoordLines, tolerance=0.01):
    """
    座標線から連続する重複点を削除する

    Args:
        arCoordLines: 座標線の配列（各線は点の配列）
        tolerance: 重複判定の許容誤差（mm）

    Returns:
        重複点を削除した座標線の配列
    """
    keep_indices = get_non_duplicate_indices(arCoordLines, tolerance)
    if len(keep_indices) < 2:
        return arCoordLines
    return apply_indices_to_coord_lines(arCoordLines, keep_indices)


def Draw_solid_Web_mainpanel_break_FLG(ifc_all, MainPanel_data, Senkei_data, name_panel, arCoordLines_Mod, side_export):
    """
    Webパネルのブレーク処理付き描画

    フランジパネル（UF/LF）のBreak情報に基づいて、Webパネルを複数のソリッドに分割して生成する。
    各分割区間でフランジとの接続面を計算し、板厚の変化に対応する。

    Args:
        ifc_all: (ifc_file, bridge_span, geom_context)のタプル
        MainPanel_data: メインパネルデータの配列
        Senkei_data: 線形データ
        name_panel: パネル名称（例: "G1B1W"）
        arCoordLines_Mod: パネルの座標線配列
        side_export: 出力側面指定（2:両面, 1:表面のみ, -1:裏面のみ）

    Returns:
        tuple: (arSolid_Panel1, arSolid_Panel2) 分割されたソリッドの配列
    """
    ifc_file, bridge_span, geom_context = ifc_all
    arSolid_Panel1 = []
    arSolid_Panel2 = []

    for panel in MainPanel_data:
        if panel["Name"] == name_panel:
            Line_panel = panel["Line"]
            Sec_panel = panel["Sec"]
            Type_panel = panel["Type"]
            Mat_panel = panel["Material"]
            Expand_panel = panel["Expand"]
            break
    ExtendL, ExtendR, ExtendT, ExtendB = Expand_panel["E1"], Expand_panel["E2"], Expand_panel["E3"], Expand_panel["E4"]
    arCoordLines_Out = Calculate_Extend(
        MainPanel_data, Senkei_data, name_panel, arCoordLines_Mod, ExtendL, ExtendR, ExtendT, ExtendB
    )
    Thick1, Thick2, Mat = Mat_panel["Thick1"], Mat_panel["Thick2"], Mat_panel["Mat"]
    arCoordLines_Out_off1 = DefMath.Offset_Face(arCoordLines_Out, -Thick1)
    arCoordLines_Out_off2 = DefMath.Offset_Face(arCoordLines_Out, Thick2)
    arCoordLines_mid = DefMath.Calculate_Coord_Mid(arCoordLines_Out_off1, arCoordLines_Out_off2)

    if Check_break_mainpanle(MainPanel_data, name_panel, "T") == True and DefMath.is_number(ExtendT) == False:
        name_panel_top = Type_panel["Girder"] + Type_panel["Block"] + "UF"
        dem = 0
        for panel in MainPanel_data:
            if panel["Name"] == name_panel_top:
                Line_panel_top = panel["Line"]
                Sec_panel_top = panel["Sec"]
                Type_panel_top = panel["Type"]
                Mat_panel_top = panel["Material"]
                Expand_panel_top = panel["Expand"]
                Break_panel_top = panel["Break"]
                stt = True
                dem += 1
                break
        if dem == 0:
            name_panel_top = Type_panel["Girder"] + Type_panel["Block"] + "DK"
            for panel in MainPanel_data:
                if panel["Name"] == name_panel_top:
                    Line_panel_top = panel["Line"]
                    Sec_panel_top = panel["Sec"]
                    Type_panel_top = panel["Type"]
                    Mat_panel_top = panel["Material"]
                    Expand_panel_top = panel["Expand"]
                    Break_panel_top = panel["Break"]
                    stt = True
                    break
        arCoordLines_mod_top = Load_Coordinate_Panel(Senkei_data, Line_panel_top, Sec_panel_top)
        arLength = Break_panel_top["Lenght"]
        arExtend = Break_panel_top["Extend"]
        arThick = Break_panel_top["Thick"]
        _log_print(f"  [WEB BREAK DEBUG] Webパネル {name_panel}: 上フランジ {name_panel_top} のBreak情報を参照")
        _log_print(f"  [WEB BREAK DEBUG] arLength={arLength}, arExtend={arExtend}, arThick={arThick}")

        # Webパネルの座標を使って分割位置を計算
        arCoordLines_Mod_for_break = Load_Coordinate_Panel(Senkei_data, Line_panel, Sec_panel)
        arCoordLines_Mod_for_break, ar_pos = Devide_Coord_FLG_mainpanel_break(arCoordLines_Mod_for_break, arLength)
        _log_print(
            f"  [WEB BREAK DEBUG] Webパネル {name_panel}: Webパネル自身の座標から計算した分割位置 ar_pos={ar_pos}"
        )

        # フランジの座標も分割
        arCoordLines_mod_top, ar_pos_flange = Devide_Coord_FLG_mainpanel_break(arCoordLines_mod_top, arLength)
        _log_print(
            f"  [WEB BREAK DEBUG] Webパネル {name_panel}: フランジの座標から計算した分割位置 ar_pos_flange={ar_pos_flange}"
        )

        if ar_pos != ar_pos_flange:
            _log_print(f"  [WEB BREAK DEBUG] 警告: Webパネルとフランジで分割位置が異なります")

        # 各分割位置での交点を計算
        for i in range(0, len(ar_pos) - 1):
            if ar_pos[i] < len(arCoordLines_Mod_for_break[0]):
                pp1 = arCoordLines_Mod_for_break[0][ar_pos[i]]
                pp2 = arCoordLines_Mod_for_break[-1][ar_pos[i]]
            else:
                if ar_pos_flange[i] < len(arCoordLines_mod_top[0]):
                    pp1 = arCoordLines_mod_top[0][ar_pos_flange[i]]
                    pp2 = arCoordLines_mod_top[-1][ar_pos_flange[i]]
                else:
                    continue
            stt = False
            for i_1 in range(0, len(arCoordLines_mid[0]) - 1):
                coord_mid = []
                coord_off1 = []
                coord_off2 = []
                pp3 = DefMath.Point_on_parallel_line(pp1, arCoordLines_mid[0][i_1], arCoordLines_mid[-1][i_1], 1000)
                for i_2 in range(0, len(arCoordLines_mid)):
                    p_mid = DefMath.Intersection_plane_segment(
                        pp1, pp2, pp3, arCoordLines_mid[i_2][i_1], arCoordLines_mid[i_2][i_1 + 1]
                    )
                    p_off1 = DefMath.Intersection_plane_segment(
                        pp1, pp2, pp3, arCoordLines_Out_off1[i_2][i_1], arCoordLines_Out_off1[i_2][i_1 + 1]
                    )
                    p_off2 = DefMath.Intersection_plane_segment(
                        pp1, pp2, pp3, arCoordLines_Out_off2[i_2][i_1], arCoordLines_Out_off2[i_2][i_1 + 1]
                    )
                    if p_mid is not None:
                        coord_mid.append(p_mid)
                        coord_off1.append(p_off1)
                        coord_off2.append(p_off2)

                if coord_mid:
                    for i_2 in range(0, len(arCoordLines_mid)):
                        arCoordLines_mid[i_2].insert(i_1 + 1, coord_mid[i_2])
                        arCoordLines_Out_off1[i_2].insert(i_1 + 1, coord_off1[i_2])
                        arCoordLines_Out_off2[i_2].insert(i_1 + 1, coord_off2[i_2])
                        stt = True

                if stt == True:
                    break

        n = 0
        n_flange = 0
        for i in range(0, len(ar_pos)):
            _log_print(f"  [WEB BREAK DEBUG] Webパネル {name_panel}: 区間[{i}]: n={n}, n_flange={n_flange}")

            arCoordLines_Mod_part = []
            for i_1 in range(0, len(arCoordLines_mod_top)):
                coord = []
                if i < len(ar_pos_flange):
                    for i_2 in range(n_flange, ar_pos_flange[i] + 1):
                        coord.append(arCoordLines_mod_top[i_1][i_2])
                arCoordLines_Mod_part.append(coord)

            arCoordLines_mid_part = []
            arCoordLines_Out_off1_part = []
            arCoordLines_Out_off2_part = []
            for i_1 in range(0, len(arCoordLines_mid)):
                coord_mid = []
                coord_off1 = []
                coord_off2 = []
                for i_2 in range(n, ar_pos[i] + 1):
                    if i_2 < len(arCoordLines_mid[i_1]):
                        coord_mid.append(arCoordLines_mid[i_1][i_2])
                    if i_2 < len(arCoordLines_Out_off1[i_1]):
                        coord_off1.append(arCoordLines_Out_off1[i_1][i_2])
                    if i_2 < len(arCoordLines_Out_off2[i_1]):
                        coord_off2.append(arCoordLines_Out_off2[i_1][i_2])
                arCoordLines_mid_part.append(coord_mid)
                arCoordLines_Out_off1_part.append(coord_off1)
                arCoordLines_Out_off2_part.append(coord_off2)

            Thick1, Thick2 = arThick[i].split("/")
            thick1_top = float(Thick1)
            thick2_top = float(Thick2)

            arCoordLines_Mod_part = Calculate_Extend(
                MainPanel_data, Senkei_data, name_panel_top, arCoordLines_Mod_part, 10, 10, 0, 0
            )
            arCoordLines_Mod_part = DefMath.Offset_Face(arCoordLines_Mod_part, -thick2_top)

            arCoordLines_mid_part = DefMath.intersec_face_with_face(arCoordLines_mid_part, arCoordLines_Mod_part, "S")
            arCoordLines_Out_off1_part = DefMath.intersec_face_with_face(
                arCoordLines_Out_off1_part, arCoordLines_Mod_part, "S"
            )
            arCoordLines_Out_off2_part = DefMath.intersec_face_with_face(
                arCoordLines_Out_off2_part, arCoordLines_Mod_part, "S"
            )

            if side_export == 2:
                Solid_Panel1 = DefIFC.Create_brep_from_box_points(
                    ifc_file, arCoordLines_Out_off1_part, arCoordLines_mid_part
                )
                arSolid_Panel1.append(Solid_Panel1)
                Solid_Panel2 = DefIFC.Create_brep_from_box_points(
                    ifc_file, arCoordLines_mid_part, arCoordLines_Out_off2_part
                )
                arSolid_Panel2.append(Solid_Panel2)
            elif side_export == 1:
                Solid_Panel1 = DefIFC.Create_brep_from_box_points(
                    ifc_file, arCoordLines_Out_off1_part, arCoordLines_mid_part
                )
                arSolid_Panel1.append(Solid_Panel1)
                arSolid_Panel2.append(None)
            elif side_export == -1:
                arSolid_Panel1.append(None)
                Solid_Panel2 = DefIFC.Create_brep_from_box_points(
                    ifc_file, arCoordLines_mid_part, arCoordLines_Out_off2_part
                )
                arSolid_Panel2.append(Solid_Panel2)

            n = ar_pos[i]
            if i < len(ar_pos_flange):
                n_flange = ar_pos_flange[i]

    elif Check_break_mainpanle(MainPanel_data, name_panel, "B") == True and DefMath.is_number(ExtendB) == False:
        # 下フランジのBreak処理（上フランジと同様のロジック）
        name_panel_bot = Type_panel["Girder"] + Type_panel["Block"] + "LF"
        for panel in MainPanel_data:
            if panel["Name"] == name_panel_bot:
                Line_panel_bot = panel["Line"]
                Sec_panel_bot = panel["Sec"]
                Type_panel_bot = panel["Type"]
                Mat_panel_bot = panel["Material"]
                Expand_panel_bot = panel["Expand"]
                Break_panel_bot = panel["Break"]
                break

        arCoordLines_mod_bot = Load_Coordinate_Panel(Senkei_data, Line_panel_bot, Sec_panel_bot)
        arLength = Break_panel_bot["Lenght"]
        arExtend = Break_panel_bot["Extend"]
        arThick = Break_panel_bot["Thick"]

        arCoordLines_Mod_for_break = Load_Coordinate_Panel(Senkei_data, Line_panel, Sec_panel)
        arCoordLines_Mod_for_break, ar_pos = Devide_Coord_FLG_mainpanel_break(arCoordLines_Mod_for_break, arLength)
        arCoordLines_mod_bot, ar_pos_flange_bot = Devide_Coord_FLG_mainpanel_break(arCoordLines_mod_bot, arLength)

        for i in range(0, len(ar_pos) - 1):
            if ar_pos[i] < len(arCoordLines_Mod_for_break[0]):
                pp1 = arCoordLines_Mod_for_break[0][ar_pos[i]]
                pp2 = arCoordLines_Mod_for_break[-1][ar_pos[i]]
            else:
                if ar_pos_flange_bot[i] < len(arCoordLines_mod_bot[0]):
                    pp1 = arCoordLines_mod_bot[0][ar_pos_flange_bot[i]]
                    pp2 = arCoordLines_mod_bot[-1][ar_pos_flange_bot[i]]
                else:
                    continue
            stt = False
            for i_1 in range(0, len(arCoordLines_mid[0]) - 1):
                coord_mid = []
                coord_off1 = []
                coord_off2 = []
                pp3 = DefMath.Point_on_parallel_line(pp1, arCoordLines_mid[0][i_1], arCoordLines_mid[-1][i_1], 1000)
                for i_2 in range(0, len(arCoordLines_mid)):
                    p_mid = DefMath.Intersection_plane_segment(
                        pp1, pp2, pp3, arCoordLines_mid[i_2][i_1], arCoordLines_mid[i_2][i_1 + 1]
                    )
                    p_off1 = DefMath.Intersection_plane_segment(
                        pp1, pp2, pp3, arCoordLines_Out_off1[i_2][i_1], arCoordLines_Out_off1[i_2][i_1 + 1]
                    )
                    p_off2 = DefMath.Intersection_plane_segment(
                        pp1, pp2, pp3, arCoordLines_Out_off2[i_2][i_1], arCoordLines_Out_off2[i_2][i_1 + 1]
                    )
                    if p_mid is not None:
                        coord_mid.append(p_mid)
                        coord_off1.append(p_off1)
                        coord_off2.append(p_off2)

                if coord_mid:
                    for i_2 in range(0, len(arCoordLines_mid)):
                        arCoordLines_mid[i_2].insert(i_1 + 1, coord_mid[i_2])
                        arCoordLines_Out_off1[i_2].insert(i_1 + 1, coord_off1[i_2])
                        arCoordLines_Out_off2[i_2].insert(i_1 + 1, coord_off2[i_2])
                        stt = True

                if stt == True:
                    break

        n = 0
        n_flange = 0
        for i in range(0, len(ar_pos)):
            arCoordLines_Mod_part = []
            for i_1 in range(0, len(arCoordLines_mod_bot)):
                coord = []
                if i < len(ar_pos_flange_bot):
                    for i_2 in range(n_flange, ar_pos_flange_bot[i] + 1):
                        coord.append(arCoordLines_mod_bot[i_1][i_2])
                arCoordLines_Mod_part.append(coord)

            arCoordLines_mid_part = []
            arCoordLines_Out_off1_part = []
            arCoordLines_Out_off2_part = []
            for i_1 in range(0, len(arCoordLines_mid)):
                coord_mid = []
                coord_off1 = []
                coord_off2 = []
                for i_2 in range(n, ar_pos[i] + 1):
                    if i_2 < len(arCoordLines_mid[i_1]):
                        coord_mid.append(arCoordLines_mid[i_1][i_2])
                    if i_2 < len(arCoordLines_Out_off1[i_1]):
                        coord_off1.append(arCoordLines_Out_off1[i_1][i_2])
                    if i_2 < len(arCoordLines_Out_off2[i_1]):
                        coord_off2.append(arCoordLines_Out_off2[i_1][i_2])
                arCoordLines_mid_part.append(coord_mid)
                arCoordLines_Out_off1_part.append(coord_off1)
                arCoordLines_Out_off2_part.append(coord_off2)

            Thick1, Thick2 = arThick[i].split("/")
            thick1_bot = float(Thick1)
            thick2_bot = float(Thick2)

            arCoordLines_Mod_part = Calculate_Extend(
                MainPanel_data, Senkei_data, name_panel_bot, arCoordLines_Mod_part, 10, 10, 0, 0
            )
            arCoordLines_Mod_part = DefMath.Offset_Face(arCoordLines_Mod_part, thick1_bot)

            arCoordLines_mid_part = DefMath.intersec_face_with_face(arCoordLines_mid_part, arCoordLines_Mod_part, "E")
            arCoordLines_Out_off1_part = DefMath.intersec_face_with_face(
                arCoordLines_Out_off1_part, arCoordLines_Mod_part, "E"
            )
            arCoordLines_Out_off2_part = DefMath.intersec_face_with_face(
                arCoordLines_Out_off2_part, arCoordLines_Mod_part, "E"
            )

            if side_export == 2:
                Solid_Panel1 = DefIFC.Create_brep_from_box_points(
                    ifc_file, arCoordLines_Out_off1_part, arCoordLines_mid_part
                )
                arSolid_Panel1.append(Solid_Panel1)
                Solid_Panel2 = DefIFC.Create_brep_from_box_points(
                    ifc_file, arCoordLines_mid_part, arCoordLines_Out_off2_part
                )
                arSolid_Panel2.append(Solid_Panel2)
            elif side_export == 1:
                Solid_Panel1 = DefIFC.Create_brep_from_box_points(
                    ifc_file, arCoordLines_Out_off1_part, arCoordLines_mid_part
                )
                arSolid_Panel1.append(Solid_Panel1)
                arSolid_Panel2.append(None)
            elif side_export == -1:
                arSolid_Panel1.append(None)
                Solid_Panel2 = DefIFC.Create_brep_from_box_points(
                    ifc_file, arCoordLines_mid_part, arCoordLines_Out_off2_part
                )
                arSolid_Panel2.append(Solid_Panel2)

            n = ar_pos[i]
            if i < len(ar_pos_flange_bot):
                n_flange = ar_pos_flange_bot[i]

    # Webパネル自身のBreak情報を使った処理
    if len(arSolid_Panel1) == 0 and len(arSolid_Panel2) == 0:
        Break_panel = None
        for panel in MainPanel_data:
            if panel["Name"] == name_panel:
                Break_panel = panel.get("Break")
                break

        if Break_panel:
            _log_print(f"  [WEB BREAK DEBUG] Webパネル {name_panel}: 自身のBreak情報を使用")
            arLength = Break_panel["Lenght"]
            arExtend = Break_panel["Extend"]
            arThick = Break_panel["Thick"]

            arCoordLines_Mod_new, ar_pos = Devide_Coord_FLG_mainpanel_break(arCoordLines_Mod, arLength)

            n = 0
            for i in range(0, len(ar_pos)):
                arCoordLines_Mod_part = []
                for i_1 in range(0, len(arCoordLines_Mod_new)):
                    coord = []
                    for i_2 in range(n, ar_pos[i] + 1):
                        coord.append(arCoordLines_Mod_new[i_1][i_2])
                    arCoordLines_Mod_part.append(coord)

                arCoordLines_Mod_part = remove_consecutive_duplicate_points(arCoordLines_Mod_part)

                arCoordLines_Out_part = Calculate_Extend_Coord(arCoordLines_Mod_part, arExtend[i], "T")
                arCoordLines_Out_part = Calculate_Extend_Coord(arCoordLines_Out_part, arExtend[i], "B")

                Thick1, Thick2 = arThick[i].split("/")
                thick1 = float(Thick1)
                thick2 = float(Thick2)

                arCoordLines_Out_off1_part = DefMath.Offset_Face(arCoordLines_Out_part, -thick1)
                arCoordLines_Out_off2_part = DefMath.Offset_Face(arCoordLines_Out_part, thick2)
                arCoordLines_mid_part = DefMath.Calculate_Coord_Mid(
                    arCoordLines_Out_off1_part, arCoordLines_Out_off2_part
                )

                if side_export == 2:
                    Solid_Panel1 = DefIFC.Create_brep_from_box_points(
                        ifc_file, arCoordLines_Out_off1_part, arCoordLines_mid_part
                    )
                    arSolid_Panel1.append(Solid_Panel1)
                    Solid_Panel2 = DefIFC.Create_brep_from_box_points(
                        ifc_file, arCoordLines_mid_part, arCoordLines_Out_off2_part
                    )
                    arSolid_Panel2.append(Solid_Panel2)
                elif side_export == 1:
                    Solid_Panel1 = DefIFC.Create_brep_from_box_points(
                        ifc_file, arCoordLines_Out_off1_part, arCoordLines_mid_part
                    )
                    arSolid_Panel1.append(Solid_Panel1)
                    arSolid_Panel2.append(None)
                elif side_export == -1:
                    arSolid_Panel1.append(None)
                    Solid_Panel2 = DefIFC.Create_brep_from_box_points(
                        ifc_file, arCoordLines_mid_part, arCoordLines_Out_off2_part
                    )
                    arSolid_Panel2.append(Solid_Panel2)

                n = ar_pos[i]

    _log_print(
        f"  [WEB BREAK DEBUG] Webパネル {name_panel}: 完了 - arSolid_Panel1={len(arSolid_Panel1)}, arSolid_Panel2={len(arSolid_Panel2)}"
    )

    return arSolid_Panel1, arSolid_Panel2


def Draw_solid_FLG_mainpanel_break(
    ifc_all, arCoordLines_Mod, arLength_panel, arExtend, arThick, Type_panel, side_export, SplitThickness=False
):
    """
    フランジパネルのブレーク処理付き描画

    フランジパネル（UF/LF）をBreak情報に基づいて複数のソリッドに分割して生成する。
    各分割区間で異なる板厚と延長量を適用し、コーナーカットも処理する。

    Args:
        ifc_all: (ifc_file, bridge_span, geom_context)のタプル
        arCoordLines_Mod: パネルの座標線配列
        arLength_panel: 各区間の長さ配列（mm）
        arExtend: 各区間の延長量配列
        arThick: 各区間の板厚配列（"Thick1/Thick2"形式）
        Type_panel: パネルタイプ情報（"TypePanel"キーを含む辞書）
        side_export: 出力側面指定（2:両面, 1:表面のみ, -1:裏面のみ）
        SplitThickness: 板厚分割モード（True:両方向に分割）

    Returns:
        tuple: (arSolid_Panel1, arSolid_Panel2) 分割されたソリッドの配列
    """
    ifc_file, bridge_span, geom_context = ifc_all
    arSolid_Panel1 = []
    arSolid_Panel2 = []
    arCoordLines_Mod_new, ar_pos = Devide_Coord_FLG_mainpanel_break(arCoordLines_Mod, arLength_panel)
    _log_print(
        f"  [THICK DEBUG] Draw_solid_FLG_mainpanel_break開始: arLength={len(arLength_panel)}, arThick={len(arThick)}"
    )

    # 全体座標に対してOffset_Faceを計算
    arCoordLines_Out_full = Calculate_Extend_Coord(arCoordLines_Mod_new, arExtend[0], "T")
    arCoordLines_Out_full = Calculate_Extend_Coord(arCoordLines_Out_full, arExtend[0], "B")

    max_thick1 = max(float(thick.split("/")[0]) for thick in arThick)
    max_thick2 = max(float(thick.split("/")[1]) for thick in arThick)

    arCoordLines_Out_off1_full = DefMath.Offset_Face(arCoordLines_Out_full, -max_thick2)
    arCoordLines_Out_off2_full = DefMath.Offset_Face(arCoordLines_Out_full, max_thick1)
    arCoordLines_mid_full = DefMath.Calculate_Coord_Mid(arCoordLines_Out_off1_full, arCoordLines_Out_off2_full)

    n = 0
    for i in range(0, len(ar_pos)):
        if i < len(arLength_panel) and float(arLength_panel[i]) == 0.0:
            n = ar_pos[i]
            continue

        current_start = n
        current_end = ar_pos[i] + 1

        arCoordLines_Out_part = []
        arCoordLines_Out_off1 = []
        arCoordLines_Out_off2 = []
        arCoordLines_mid = []

        for line_idx in range(len(arCoordLines_Out_full)):
            arCoordLines_Out_part.append(arCoordLines_Out_full[line_idx][current_start:current_end])
            arCoordLines_Out_off1.append(arCoordLines_Out_off1_full[line_idx][current_start:current_end])
            arCoordLines_Out_off2.append(arCoordLines_Out_off2_full[line_idx][current_start:current_end])
            arCoordLines_mid.append(arCoordLines_mid_full[line_idx][current_start:current_end])

        # 重複点を削除
        keep_indices = get_non_duplicate_indices(arCoordLines_Out_part)
        if len(keep_indices) >= 2:
            arCoordLines_Out_part = apply_indices_to_coord_lines(arCoordLines_Out_part, keep_indices)
            arCoordLines_Out_off1 = apply_indices_to_coord_lines(arCoordLines_Out_off1, keep_indices)
            arCoordLines_Out_off2 = apply_indices_to_coord_lines(arCoordLines_Out_off2, keep_indices)
            arCoordLines_mid = apply_indices_to_coord_lines(arCoordLines_mid, keep_indices)

        n = ar_pos[i]

        if i >= len(arThick):
            Thick1, Thick2 = arThick[-1].split("/")
        else:
            Thick1, Thick2 = arThick[i].split("/")
        Thick1 = float(Thick1)
        Thick2 = float(Thick2)

        if Type_panel["TypePanel"] == "W" or Type_panel["TypePanel"] == "WL" or Type_panel["TypePanel"] == "WR":
            if side_export == 2:
                Solid_Panel1 = DefIFC.Create_brep_from_box_points(ifc_file, arCoordLines_Out_off1, arCoordLines_mid)
                arSolid_Panel1.append(Solid_Panel1)
                Solid_Panel2 = DefIFC.Create_brep_from_box_points(ifc_file, arCoordLines_mid, arCoordLines_Out_off2)
                arSolid_Panel2.append(Solid_Panel2)
            elif side_export == 1:
                Solid_Panel1 = DefIFC.Create_brep_from_box_points(ifc_file, arCoordLines_Out_off1, arCoordLines_mid)
                arSolid_Panel1.append(Solid_Panel1)
                arSolid_Panel2.append(None)
            elif side_export == -1:
                arSolid_Panel1.append(None)
                Solid_Panel2 = DefIFC.Create_brep_from_box_points(ifc_file, arCoordLines_mid, arCoordLines_Out_off2)
                arSolid_Panel2.append(Solid_Panel2)
        else:
            # フランジ（UF/LF）の場合
            effective_Thick1 = Thick1
            effective_Thick2 = Thick2

            if not SplitThickness:
                if Type_panel["TypePanel"] == "UF":
                    effective_Thick2 = 0
                elif Type_panel["TypePanel"] == "LF":
                    effective_Thick1 = 0

            if side_export == 2:
                if effective_Thick1 > 0 and effective_Thick2 > 0:
                    Solid_Panel1 = DefIFC.Create_brep_from_box_points(ifc_file, arCoordLines_Out_off1, arCoordLines_mid)
                    Solid_Panel2 = DefIFC.Create_brep_from_box_points(ifc_file, arCoordLines_mid, arCoordLines_Out_off2)
                elif effective_Thick1 > 0:
                    Solid_Panel1 = None
                    Solid_Panel2 = DefIFC.Create_brep_from_box_points(
                        ifc_file, arCoordLines_Out_part, arCoordLines_Out_off2
                    )
                elif effective_Thick2 > 0:
                    Solid_Panel1 = DefIFC.Create_brep_from_box_points(
                        ifc_file, arCoordLines_Out_off1, arCoordLines_Out_part
                    )
                    Solid_Panel2 = None
                else:
                    Solid_Panel1 = None
                    Solid_Panel2 = None
            elif side_export == 1:
                if effective_Thick1 > 0:
                    Solid_Panel1 = DefIFC.Create_brep_from_box_points(
                        ifc_file, arCoordLines_Out_part, arCoordLines_Out_off2
                    )
                else:
                    Solid_Panel1 = None
                Solid_Panel2 = None
            elif side_export == -1:
                Solid_Panel1 = None
                if effective_Thick2 > 0:
                    Solid_Panel2 = DefIFC.Create_brep_from_box_points(
                        ifc_file, arCoordLines_Out_off1, arCoordLines_Out_part
                    )
                else:
                    Solid_Panel2 = None

            # コーナーカット処理
            if i == 0 and i + 1 < len(arExtend):
                if float(arExtend[i]) > float(arExtend[i + 1]):
                    pcorner = arCoordLines_Out_part[0][-1]
                    pdirX = arCoordLines_Out_part[0][-2]
                    pdirY = arCoordLines_Out_part[1][-1]
                    corner = f"C{(float(arExtend[i]) - float(arExtend[i + 1])) * 10}x{(float(arExtend[i]) - float(arExtend[i + 1]))}"
                    if Solid_Panel1 is not None:
                        solid_corner = Draw_Corner(ifc_file, corner, pcorner, pdirX, pdirY)
                        Solid_Panel1 = ifc_file.createIfcBooleanResult("DIFFERENCE", Solid_Panel1, solid_corner)
                    if Solid_Panel2 is not None:
                        solid_corner = Draw_Corner(ifc_file, corner, pcorner, pdirX, pdirY)
                        Solid_Panel2 = ifc_file.createIfcBooleanResult("DIFFERENCE", Solid_Panel2, solid_corner)

                    pcorner = arCoordLines_Out_part[-1][-1]
                    pdirX = arCoordLines_Out_part[-1][-2]
                    pdirY = arCoordLines_Out_part[-2][-1]
                    if Solid_Panel1 is not None:
                        solid_corner = Draw_Corner(ifc_file, corner, pcorner, pdirX, pdirY)
                        Solid_Panel1 = ifc_file.createIfcBooleanResult("DIFFERENCE", Solid_Panel1, solid_corner)
                    if Solid_Panel2 is not None:
                        solid_corner = Draw_Corner(ifc_file, corner, pcorner, pdirX, pdirY)
                        Solid_Panel2 = ifc_file.createIfcBooleanResult("DIFFERENCE", Solid_Panel2, solid_corner)

            arSolid_Panel1.append(Solid_Panel1)
            arSolid_Panel2.append(Solid_Panel2)

    return arSolid_Panel1, arSolid_Panel2
