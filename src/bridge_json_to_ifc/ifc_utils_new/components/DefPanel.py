"""
鋼橋IFCモデル生成 - パネル生成モジュール
メインパネルとサブパネルの生成、ブレーク処理、I形横桁生成など
"""

import copy
import math

import numpy as np

from src.bridge_json_to_ifc.ifc_utils_new.core import DefIFC, DefMath
from src.bridge_json_to_ifc.ifc_utils_new.io import DefStrings

# DefBridgeUtils.pyの関数をインポート
from src.bridge_json_to_ifc.ifc_utils_new.utils.DefBridgeUtils import Calculate_Extend_Coord, Load_Coordinate_Panel

# グローバル変数: ログファイル出力関数（DefBridge.pyから設定される）
log_print_func = None


def _log_print(*args, **kwargs):
    """ログファイル出力関数（DEBUG_MODE時のみ出力）"""
    if log_print_func:
        log_print_func(*args, **kwargs)


# ---------------パネルブレークケース------------------------------
def Check_break_mainpanle(MainPanel_data, name_panel, pos):
    """
    メインパネルのブレーク（分割）が必要かどうかをチェックする

    Args:
        MainPanel_data: メインパネルデータ
        name_panel: パネル名称
        pos: 位置（"T"=上、"B"=下）

    Returns:
        bool: ブレークが必要な場合True
    """
    for panel in MainPanel_data:
        if panel["Name"] == name_panel:
            Line_panel = panel["Line"]
            Sec_panel = panel["Sec"]
            Type_panel = panel["Type"]
            Mat_panel = panel["Material"]
            Expand_panel = panel["Expand"]
            break
    stt = False
    if pos == "T":
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
                if Break_panel_top:
                    arLength = Break_panel_top["Lenght"]
                    arExtend = Break_panel_top["Extend"]
                    arThick = Break_panel_top["Thick"]
                    cout_thick = 0
                    for thicks in arThick:
                        if f"{Mat_panel_top['Thick1']}/{Mat_panel_top['Thick2']}" == thicks:
                            cout_thick += 1
                    if cout_thick != len(arThick):
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
                    if Break_panel_top:
                        arLength = Break_panel_top["Lenght"]
                        arExtend = Break_panel_top["Extend"]
                        arThick = Break_panel_top["Thick"]
                        cout_thick = 0
                        for thicks in arThick:
                            if f"{Mat_panel_top['Thick1']}/{Mat_panel_top['Thick2']}" == thicks:
                                cout_thick += 1
                        if cout_thick != len(arThick):
                            stt = True
                    break

    if pos == "B":
        name_panel_bot = Type_panel["Girder"] + Type_panel["Block"] + "LF"
        for panel in MainPanel_data:
            if panel["Name"] == name_panel_bot:
                Line_panel_bot = panel["Line"]
                Sec_panel_bot = panel["Sec"]
                Type_panel_bot = panel["Type"]
                Mat_panel_bot = panel["Material"]
                Expand_panel_bot = panel["Expand"]
                Break_panel_bot = panel["Break"]
                if Break_panel_bot:
                    arLength = Break_panel_bot["Lenght"]
                    arExtend = Break_panel_bot["Extend"]
                    arThick = Break_panel_bot["Thick"]
                    cout_thick = 0
                    for thicks in arThick:
                        if f"{Mat_panel_bot['Thick1']}/{Mat_panel_bot['Thick2']}" == thicks:
                            cout_thick += 1

                    if cout_thick != len(arThick):
                        stt = True
                break
    return stt


def Devide_Coord_FLG_mainpanel_break(arCoordLines_Mod, arLength_panel):
    """
    フランジパネルを長手方向に分割する

    Args:
        arCoordLines_Mod: 座標線の配列（各線は長手方向の点の配列）
        arLength_panel: 各区間の長さの配列（mm単位）

    Returns:
        tuple: (arCoordLines_Mod_new, ar_pos)
            - arCoordLines_Mod_new: 分割点が挿入された座標線の配列
            - ar_pos: 分割位置のインデックス配列
    """
    _log_print(f"    [BREAK DEBUG] Devide_Coord_FLG_mainpanel_break開始: arLength_panel={arLength_panel}")
    _log_print(
        f"    [BREAK DEBUG] 座標線の数={len(arCoordLines_Mod)}, 最初の線の点の数={len(arCoordLines_Mod[0]) if len(arCoordLines_Mod) > 0 else 0}"
    )
    if len(arCoordLines_Mod) > 0 and len(arCoordLines_Mod[0]) > 0:
        _log_print(f"    [BREAK DEBUG] 最初の点={arCoordLines_Mod[0][0]}, 最後の点={arCoordLines_Mod[0][-1]}")

    arCoordLines_Mod_new = copy.deepcopy(arCoordLines_Mod)
    pitch_length = ""
    for i in range(0, len(arLength_panel)):
        if pitch_length == "":
            pitch_length = arLength_panel[i]
        else:
            pitch_length = f"{pitch_length}/{arLength_panel[i]}"

    length_pitch = 0
    for i in range(0, len(arCoordLines_Mod_new[0]) - 1):
        # 座標がNoneでないことを確認
        if (
            arCoordLines_Mod_new[0][i] is None
            or arCoordLines_Mod_new[0][i + 1] is None
            or arCoordLines_Mod_new[-1][i] is None
            or arCoordLines_Mod_new[-1][i + 1] is None
        ):
            # Noneが見つかった場合、スキップして次の点に進む
            continue
        length_pitch += DefMath.Calculate_distance_p2p(
            (np.array(arCoordLines_Mod_new[0][i]) + np.array(arCoordLines_Mod_new[-1][i])) / 2,
            (np.array(arCoordLines_Mod_new[0][i + 1]) + np.array(arCoordLines_Mod_new[-1][i + 1])) / 2,
        )

    _log_print(f"    [BREAK DEBUG] 全体の長さ（分割前）: {length_pitch:.2f}mm")
    pitch_length = DefStrings.Xu_Ly_Pitch_va_Tim_X(pitch_length, length_pitch)
    _log_print(f"    [BREAK DEBUG] 調整後のpitch_length: {pitch_length}")

    ar_pitch_length = pitch_length.split("/")
    _log_print(f"    [BREAK DEBUG] ar_pitch_length: {ar_pitch_length}")
    length_pitch = 0
    ar_pos = []
    for i in range(0, len(ar_pitch_length) - 1):
        length_pitch += float(ar_pitch_length[i])
        _log_print(
            f"    [BREAK DEBUG] 分割[{i}]: 目標累積距離={length_pitch:.2f}mm (区間長={float(ar_pitch_length[i]):.2f}mm)"
        )
        len_pl = 0
        # 分割点を挿入した後、座標線が更新されるため、更新された座標線を使用する
        for i_1 in range(0, len(arCoordLines_Mod_new[0]) - 1):
            # 座標がNoneでないことを確認
            if (
                arCoordLines_Mod_new[0][i_1] is None
                or arCoordLines_Mod_new[0][i_1 + 1] is None
                or arCoordLines_Mod_new[-1][i_1] is None
                or arCoordLines_Mod_new[-1][i_1 + 1] is None
            ):
                # Noneが見つかった場合、スキップして次の点に進む
                continue
            segment_len = DefMath.Calculate_distance_p2p(
                (np.array(arCoordLines_Mod_new[0][i_1]) + np.array(arCoordLines_Mod_new[-1][i_1])) / 2,
                (np.array(arCoordLines_Mod_new[0][i_1 + 1]) + np.array(arCoordLines_Mod_new[-1][i_1 + 1])) / 2,
            )
            len_pl_before = len_pl
            len_pl += segment_len
            if len_pl > length_pitch:
                overshoot = len_pl - length_pitch
                distance_in_segment = segment_len - overshoot
                distance_from_current = length_pitch - len_pl_before
                _log_print(
                    f"    [BREAK DEBUG] 分割[{i}]: 位置{i_1 + 1}で分割点を挿入 "
                    f"(segment_len={segment_len:.2f}mm, len_pl_before={len_pl_before:.2f}mm, "
                    f"len_pl={len_pl:.2f}mm, 目標={length_pitch:.2f}mm, 差={overshoot:.2f}mm, "
                    f"segment内距離={distance_in_segment:.2f}mm, start基準距離={distance_from_current:.2f}mm)"
                )
                ar_pos.append(i_1 + 1)
                # 座標がNoneでないことを確認
                if (
                    arCoordLines_Mod_new[0][i_1] is None
                    or arCoordLines_Mod_new[0][i_1 + 1] is None
                    or arCoordLines_Mod_new[-1][i_1] is None
                    or arCoordLines_Mod_new[-1][i_1 + 1] is None
                ):
                    # Noneが見つかった場合、スキップして次の点に進む
                    continue

                mid_current = (np.array(arCoordLines_Mod_new[0][i_1]) + np.array(arCoordLines_Mod_new[-1][i_1])) / 2
                mid_next = (
                    np.array(arCoordLines_Mod_new[0][i_1 + 1]) + np.array(arCoordLines_Mod_new[-1][i_1 + 1])
                ) / 2
                ratio = 0.0
                if segment_len > 1e-8:
                    ratio = distance_from_current / segment_len
                p1 = DefMath.Point_on_line(mid_current, mid_next, distance_from_current)
                coord = []
                for i_2 in range(0, len(arCoordLines_Mod_new)):
                    # 座標がNoneでないことを確認
                    if arCoordLines_Mod_new[i_2][i_1] is None or arCoordLines_Mod_new[i_2][i_1 + 1] is None:
                        # Noneが見つかった場合、前後の有効な座標から中点を計算するか、デフォルト値を使用
                        # 有効な座標線（最初または最後）から座標を取得
                        if (
                            i_2 == 0
                            and arCoordLines_Mod_new[-1][i_1] is not None
                            and arCoordLines_Mod_new[-1][i_1 + 1] is not None
                        ):
                            # 最初の線がNoneの場合、最後の線の中点を使用
                            coord.append(
                                (np.array(arCoordLines_Mod_new[-1][i_1]) + np.array(arCoordLines_Mod_new[-1][i_1 + 1]))
                                / 2
                            )
                        elif (
                            i_2 == len(arCoordLines_Mod_new) - 1
                            and arCoordLines_Mod_new[0][i_1] is not None
                            and arCoordLines_Mod_new[0][i_1 + 1] is not None
                        ):
                            # 最後の線がNoneの場合、最初の線の中点を使用
                            coord.append(
                                (np.array(arCoordLines_Mod_new[0][i_1]) + np.array(arCoordLines_Mod_new[0][i_1 + 1]))
                                / 2
                            )
                        else:
                            # 中間の線がNoneの場合、midラインの点を使用
                            coord.append(np.array(p1))
                    else:
                        start_pt = np.array(arCoordLines_Mod_new[i_2][i_1], dtype=float)
                        end_pt = np.array(arCoordLines_Mod_new[i_2][i_1 + 1], dtype=float)
                        coord.append(start_pt + ratio * (end_pt - start_pt))

                for i_2 in range(0, len(arCoordLines_Mod_new)):
                    arCoordLines_Mod_new[i_2].insert(i_1 + 1, coord[i_2])

                inserted_mid = (np.array(coord[0]) + np.array(coord[-1])) / 2
                _log_print(
                    f"    [BREAK DEBUG] 分割[{i}]: 挿入点情報 -> "
                    f"top={np.round(coord[0], 3).tolist()}, bottom={np.round(coord[-1], 3).tolist()}, "
                    f"mid={np.round(inserted_mid, 3).tolist()}"
                )

                break
    ar_pos.append(len(arCoordLines_Mod_new[0]) - 1)

    if len(arCoordLines_Mod_new) > 0:
        top_line = arCoordLines_Mod_new[0]
        bottom_line = arCoordLines_Mod_new[-1]
        x_coords = []
        for pt in top_line:
            if pt is None:
                x_coords.append(None)
            else:
                try:
                    x_coords.append(round(float(pt[0]), 3))
                except (TypeError, ValueError):
                    x_coords.append(None)
        _log_print(f"    [BREAK DEBUG] 分割後上側ラインX座標={x_coords}")

        segment_lengths = []
        for idx in range(0, len(top_line) - 1):
            if (
                top_line[idx] is None
                or top_line[idx + 1] is None
                or bottom_line[idx] is None
                or bottom_line[idx + 1] is None
            ):
                segment_lengths.append(None)
                continue
            mid1 = (np.array(top_line[idx]) + np.array(bottom_line[idx])) / 2
            mid2 = (np.array(top_line[idx + 1]) + np.array(bottom_line[idx + 1])) / 2
            seg_len = DefMath.Calculate_distance_p2p(mid1, mid2)
            segment_lengths.append(round(seg_len, 3))
        _log_print(f"    [BREAK DEBUG] 分割後セグメント長={segment_lengths}")

    _log_print(f"    [BREAK DEBUG] 分割位置 ar_pos={ar_pos}")
    _log_print(
        f"    [BREAK DEBUG] 分割後の点の数={len(arCoordLines_Mod_new[0]) if len(arCoordLines_Mod_new) > 0 else 0}"
    )

    return arCoordLines_Mod_new, ar_pos


# Draw_solid_Web_mainpanel_break_FLGとDraw_solid_FLG_mainpanel_breakは非常に長い関数なので、
# ここではコメントのみを残し、実際の実装はDefBridge.pyに残します
# TODO: これらの関数をDefPanel.pyに移動する（ファイルサイズが大きいため、後で対応）

# ===============================================================================
# I形横桁（Yokogeta）関連関数
# 横桁はI型断面のパネル系部材として、DefPanel.pyで管理する
# ===============================================================================


def Extend_Yokoketa_Face(
    MainPanel_data,
    Senkei_data,
    headname1_block_mainpanel,
    headname2_block_mainpanel,
    arCoord_Top,
    arCoord_Bot,
    arCoord_Left,
    arCoord_Right,
    extends,
):
    arCoord_Top_New = arCoord_Top.copy()
    arCoord_Bot_New = arCoord_Bot.copy()
    arCoord_Left_New = arCoord_Left.copy()
    arCoord_Right_New = arCoord_Right.copy()
    (
        extendL,
        extendR,
        extendT,
        extendB,
    ) = extends
    p1_dia = arCoord_Bot[0]
    p2_dia = arCoord_Bot[-1]
    p3_dia = arCoord_Top[-1]
    normal_dia = DefMath.Normal_vector(p1_dia, p2_dia, p3_dia)
    # Top
    if DefMath.is_number(extendT) == False:
        # face 1
        name_mainpanel = headname1_block_mainpanel + "UF"
        dem = 0
        for panel in MainPanel_data:
            if panel["Name"] == name_mainpanel:
                Line_mainpanel = panel["Line"]
                Sec_mainpanel = panel["Sec"]
                Type_mainpanel = panel["Type"]
                Mat_mainpanel = panel["Material"]
                Expand_mainpanel = panel["Expand"]
                dem += 1
                break
        if dem == 0:
            name_mainpanel = headname1_block_mainpanel + "DK"
            for panel in MainPanel_data:
                if panel["Name"] == name_mainpanel:
                    Line_mainpanel = panel["Line"]
                    Sec_mainpanel = panel["Sec"]
                    Type_mainpanel = panel["Type"]
                    Mat_mainpanel = panel["Material"]
                    Expand_mainpanel = panel["Expand"]
                    dem += 1
                    break
        if dem != 0:
            thick1_panel, thick2_panel, mat_panel = (
                Mat_mainpanel["Thick1"],
                Mat_mainpanel["Thick2"],
                Mat_mainpanel["Mat"],
            )
            arCoordLines_Out = Load_Coordinate_Panel(Senkei_data, Line_mainpanel, Sec_mainpanel)
            arCoordLines_Out = DefMath.Offset_Face(arCoordLines_Out, -thick2_panel)
            arCoordLines_Out = Calculate_Extend_Coord(arCoordLines_Out, 5, "L")
            arCoordLines_Out = Calculate_Extend_Coord(arCoordLines_Out, 5, "R")
            for i in range(len(arCoord_Top_New)):
                if i == 0 or i == len(arCoord_Top_New) - 1:
                    p1_line = arCoord_Top_New[i]
                    p2_line = arCoord_Bot_New[len(arCoord_Bot_New) - 1 - i]
                else:
                    p1_line = arCoord_Top_New[i]
                    p2_line = DefMath.Point_on_parallel_line(
                        arCoord_Top_New[i], arCoord_Top_New[0], arCoord_Bot_New[-1], 100
                    )

                for i_1 in range(len(arCoordLines_Out) - 1):
                    status_exit = False
                    arCoordLines_Out_1 = arCoordLines_Out[i_1]
                    arCoordLines_Out_2 = arCoordLines_Out[i_1 + 1]
                    for i_2 in range(len(arCoordLines_Out_1) - 1):
                        p1_plan = arCoordLines_Out_1[i_2]
                        p2_plan = arCoordLines_Out_1[i_2 + 1]
                        p3_plan = arCoordLines_Out_2[i_2]
                        p4_plan = arCoordLines_Out_2[i_2 + 1]

                        if i != 0 and i != len(arCoord_Top_New) - 1:
                            p2_line = p1_line - 100 * DefMath.Normal_vector(p3_plan, p4_plan, p2_plan)
                            if p2_line[2] > p1_line[2]:
                                p2_line = p1_line + 100 * DefMath.Normal_vector(p3_plan, p4_plan, p2_plan)
                            p2_line = DefMath.point_per_plan(p2_line, p1_dia, p2_dia, p3_dia)

                        p = DefMath.Intersection_line_plane(p1_plan, p2_plan, p3_plan, p1_line, p2_line)

                        if p is not None:
                            polygon3d = [p1_plan, p2_plan, p3_plan, p4_plan]
                            polygon3d = DefMath.sort_points_clockwise(polygon3d)
                            if DefMath.is_point_in_polygon_3d(p, polygon3d, p1_plan, p2_plan, p3_plan) == True:
                                arCoord_Top_New[i] = p
                                status_exit = True
                                break
                    if status_exit == True:
                        break

            arCoord_Left_New[0] = arCoord_Top_New[-1]
            arCoord_Right_New[-1] = arCoord_Top_New[0]

        # face 2
        name_mainpanel = headname2_block_mainpanel + "UF"
        dem = 0
        for panel in MainPanel_data:
            if panel["Name"] == name_mainpanel:
                Line_mainpanel = panel["Line"]
                Sec_mainpanel = panel["Sec"]
                Type_mainpanel = panel["Type"]
                Mat_mainpanel = panel["Material"]
                Expand_mainpanel = panel["Expand"]
                dem += 1
                break
        if dem == 0:
            name_mainpanel = headname2_block_mainpanel + "DK"
            for panel in MainPanel_data:
                if panel["Name"] == name_mainpanel:
                    Line_mainpanel = panel["Line"]
                    Sec_mainpanel = panel["Sec"]
                    Type_mainpanel = panel["Type"]
                    Mat_mainpanel = panel["Material"]
                    Expand_mainpanel = panel["Expand"]
                    dem += 1
                    break
        if dem != 0:
            thick1_panel, thick2_panel, mat_panel = (
                Mat_mainpanel["Thick1"],
                Mat_mainpanel["Thick2"],
                Mat_mainpanel["Mat"],
            )
            arCoordLines_Out = Load_Coordinate_Panel(Senkei_data, Line_mainpanel, Sec_mainpanel)
            arCoordLines_Out = DefMath.Offset_Face(arCoordLines_Out, -thick2_panel)
            arCoordLines_Out = Calculate_Extend_Coord(arCoordLines_Out, 5, "L")
            arCoordLines_Out = Calculate_Extend_Coord(arCoordLines_Out, 5, "R")

            for i in range(len(arCoord_Top_New)):
                if i == 0 or i == len(arCoord_Top_New) - 1:
                    p1_line = arCoord_Top_New[i]
                    p2_line = arCoord_Bot_New[len(arCoord_Bot_New) - 1 - i]
                else:
                    p1_line = arCoord_Top_New[i]
                    p2_line = DefMath.Point_on_parallel_line(
                        arCoord_Top_New[i], arCoord_Top_New[0], arCoord_Bot_New[-1], 100
                    )

                for i_1 in range(len(arCoordLines_Out) - 1):
                    status_exit = False
                    arCoordLines_Out_1 = arCoordLines_Out[i_1]
                    arCoordLines_Out_2 = arCoordLines_Out[i_1 + 1]
                    for i_2 in range(len(arCoordLines_Out_1) - 1):
                        p1_plan = arCoordLines_Out_1[i_2]
                        p2_plan = arCoordLines_Out_1[i_2 + 1]
                        p3_plan = arCoordLines_Out_2[i_2]
                        p4_plan = arCoordLines_Out_2[i_2 + 1]

                        if i != 0 and i != len(arCoord_Top_New) - 1:
                            p2_line = p1_line - 100 * DefMath.Normal_vector(p3_plan, p4_plan, p2_plan)
                            if p2_line[2] > p1_line[2]:
                                p2_line = p1_line + 100 * DefMath.Normal_vector(p3_plan, p4_plan, p2_plan)
                            p2_line = DefMath.point_per_plan(p2_line, p1_dia, p2_dia, p3_dia)

                        p = DefMath.Intersection_line_plane(p1_plan, p2_plan, p3_plan, p1_line, p2_line)
                        if p is not None:
                            polygon3d = [p1_plan, p2_plan, p3_plan, p4_plan]
                            polygon3d = DefMath.sort_points_clockwise(polygon3d)
                            if DefMath.is_point_in_polygon_3d(p, polygon3d, p1_plan, p2_plan, p3_plan) == True:
                                arCoord_Top_New[i] = p
                                status_exit = True
                                break
                    if status_exit == True:
                        break

            arCoord_Left_New[0] = arCoord_Top_New[-1]
            arCoord_Right_New[-1] = arCoord_Top_New[0]

    # Bot
    if DefMath.is_number(extendB) == False:
        # face1
        name_mainpanel = headname1_block_mainpanel + "LF"
        dem = 0
        for panel in MainPanel_data:
            if panel["Name"] == name_mainpanel:
                Line_mainpanel = panel["Line"]
                Sec_mainpanel = panel["Sec"]
                Type_mainpanel = panel["Type"]
                Mat_mainpanel = panel["Material"]
                Expand_mainpanel = panel["Expand"]
                dem += 1
                break
        if dem != 0:
            thick1_panel, thick2_panel, mat_panel = (
                Mat_mainpanel["Thick1"],
                Mat_mainpanel["Thick2"],
                Mat_mainpanel["Mat"],
            )
            arCoordLines_Out = Load_Coordinate_Panel(Senkei_data, Line_mainpanel, Sec_mainpanel)
            arCoordLines_Out = DefMath.Offset_Face(arCoordLines_Out, thick1_panel)
            arCoordLines_Out = Calculate_Extend_Coord(arCoordLines_Out, 5, "L")
            arCoordLines_Out = Calculate_Extend_Coord(arCoordLines_Out, 5, "R")

            for i in range(len(arCoord_Bot_New)):
                if i == 0 or i == len(arCoord_Bot_New) - 1:
                    p1_line = arCoord_Bot_New[i]
                    p2_line = arCoord_Top_New[len(arCoord_Top_New) - 1 - i]
                else:
                    p1_line = arCoord_Bot_New[i]
                    p2_line = DefMath.Point_on_parallel_line(
                        arCoord_Bot_New[i], arCoord_Bot_New[0], arCoord_Top_New[-1], 100
                    )

                for i_1 in range(len(arCoordLines_Out) - 1):
                    status_exit = False
                    arCoordLines_Out_1 = arCoordLines_Out[i_1]
                    arCoordLines_Out_2 = arCoordLines_Out[i_1 + 1]
                    for i_2 in range(len(arCoordLines_Out_1) - 1):
                        p1_plan = arCoordLines_Out_1[i_2]
                        p2_plan = arCoordLines_Out_1[i_2 + 1]
                        p3_plan = arCoordLines_Out_2[i_2]
                        p4_plan = arCoordLines_Out_2[i_2 + 1]

                        if i != 0 and i != len(arCoord_Top_New) - 1:
                            p2_line = p1_line - 100 * DefMath.Normal_vector(p3_plan, p4_plan, p2_plan)
                            if p2_line[2] < p1_line[2]:
                                p2_line = p1_line + 100 * DefMath.Normal_vector(p3_plan, p4_plan, p2_plan)
                            p2_line = DefMath.point_per_plan(p2_line, p1_dia, p2_dia, p3_dia)

                        p = DefMath.Intersection_line_plane(p1_plan, p2_plan, p3_plan, p1_line, p2_line)
                        if p is not None:
                            polygon3d = [p1_plan, p2_plan, p3_plan, p4_plan]
                            polygon3d = DefMath.sort_points_clockwise(polygon3d)
                            if DefMath.is_point_in_polygon_3d(p, polygon3d, p1_plan, p2_plan, p3_plan) == True:
                                arCoord_Bot_New[i] = p
                                status_exit = True
                                break
                    if status_exit == True:
                        break

            arCoord_Left_New[-1] = arCoord_Bot_New[0]
            arCoord_Right_New[0] = arCoord_Bot_New[-1]

        # face2
        name_mainpanel = headname2_block_mainpanel + "LF"
        dem = 0
        for panel in MainPanel_data:
            if panel["Name"] == name_mainpanel:
                Line_mainpanel = panel["Line"]
                Sec_mainpanel = panel["Sec"]
                Type_mainpanel = panel["Type"]
                Mat_mainpanel = panel["Material"]
                Expand_mainpanel = panel["Expand"]
                dem += 1
                break
        if dem != 0:
            thick1_panel, thick2_panel, mat_panel = (
                Mat_mainpanel["Thick1"],
                Mat_mainpanel["Thick2"],
                Mat_mainpanel["Mat"],
            )
            arCoordLines_Out = Load_Coordinate_Panel(Senkei_data, Line_mainpanel, Sec_mainpanel)
            arCoordLines_Out = DefMath.Offset_Face(arCoordLines_Out, thick1_panel)
            arCoordLines_Out = Calculate_Extend_Coord(arCoordLines_Out, 5, "L")
            arCoordLines_Out = Calculate_Extend_Coord(arCoordLines_Out, 5, "R")

            for i in range(len(arCoord_Bot_New)):
                if i == 0 or i == len(arCoord_Bot_New) - 1:
                    p1_line = arCoord_Bot_New[i]
                    p2_line = arCoord_Top_New[len(arCoord_Top_New) - 1 - i]
                else:
                    p1_line = arCoord_Bot_New[i]
                    p2_line = DefMath.Point_on_parallel_line(
                        arCoord_Bot_New[i], arCoord_Bot_New[0], arCoord_Top_New[-1], 100
                    )

                for i_1 in range(len(arCoordLines_Out) - 1):
                    status_exit = False
                    arCoordLines_Out_1 = arCoordLines_Out[i_1]
                    arCoordLines_Out_2 = arCoordLines_Out[i_1 + 1]
                    for i_2 in range(len(arCoordLines_Out_1) - 1):
                        p1_plan = arCoordLines_Out_1[i_2]
                        p2_plan = arCoordLines_Out_1[i_2 + 1]
                        p3_plan = arCoordLines_Out_2[i_2]
                        p4_plan = arCoordLines_Out_2[i_2 + 1]

                        if i != 0 and i != len(arCoord_Top_New) - 1:
                            p2_line = p1_line - 100 * DefMath.Normal_vector(p3_plan, p4_plan, p2_plan)
                            if p2_line[2] < p1_line[2]:
                                p2_line = p1_line + 100 * DefMath.Normal_vector(p3_plan, p4_plan, p2_plan)
                            p2_line = DefMath.point_per_plan(p2_line, p1_dia, p2_dia, p3_dia)

                        p = DefMath.Intersection_line_plane(p1_plan, p2_plan, p3_plan, p1_line, p2_line)
                        if p is not None:
                            polygon3d = [p1_plan, p2_plan, p3_plan, p4_plan]
                            polygon3d = DefMath.sort_points_clockwise(polygon3d)
                            if DefMath.is_point_in_polygon_3d(p, polygon3d, p1_plan, p2_plan, p3_plan) == True:
                                arCoord_Bot_New[i] = p
                                status_exit = True
                                break
                    if status_exit == True:
                        break

            arCoord_Left_New[-1] = arCoord_Bot_New[0]
            arCoord_Right_New[0] = arCoord_Bot_New[-1]

    # Left
    if DefMath.is_number(extendL) == False:
        name_mainpanel = headname1_block_mainpanel + "WR"
        dem = 0
        for panel in MainPanel_data:
            if panel["Name"] == name_mainpanel:
                Line_mainpanel = panel["Line"]
                Sec_mainpanel = panel["Sec"]
                Type_mainpanel = panel["Type"]
                Mat_mainpanel = panel["Material"]
                Expand_mainpanel = panel["Expand"]
                dem += 1
                break
        if dem == 0:
            name_mainpanel = headname1_block_mainpanel + "W"
            for panel in MainPanel_data:
                if panel["Name"] == name_mainpanel:
                    Line_mainpanel = panel["Line"]
                    Sec_mainpanel = panel["Sec"]
                    Type_mainpanel = panel["Type"]
                    Mat_mainpanel = panel["Material"]
                    Expand_mainpanel = panel["Expand"]
                    dem += 1
                    break
        if dem != 0:
            thick1_panel, thick2_panel, mat_panel = (
                Mat_mainpanel["Thick1"],
                Mat_mainpanel["Thick2"],
                Mat_mainpanel["Mat"],
            )
            arCoordLines_Out = Load_Coordinate_Panel(Senkei_data, Line_mainpanel, Sec_mainpanel)
            arCoordLines_Out = DefMath.Offset_Face(arCoordLines_Out, thick2_panel)

            for i in range(len(arCoord_Left_New)):
                if i == 0 or i == len(arCoord_Left_New) - 1:
                    p1_line = arCoord_Left_New[i]
                    p2_line = arCoord_Right_New[len(arCoord_Right_New) - 1 - i]
                else:
                    p1_line = arCoord_Left_New[i]
                    p2_line = DefMath.Point_on_parallel_line(
                        arCoord_Left_New[i], arCoord_Left_New[0], arCoord_Right_New[-1], 100
                    )

                for i_1 in range(len(arCoordLines_Out) - 1):
                    status_exit = False
                    arCoordLines_Out_1 = arCoordLines_Out[i_1]
                    arCoordLines_Out_2 = arCoordLines_Out[i_1 + 1]
                    for i_2 in range(len(arCoordLines_Out_1) - 1):
                        p1_plan = arCoordLines_Out_1[i_2]
                        p2_plan = arCoordLines_Out_1[i_2 + 1]
                        p3_plan = arCoordLines_Out_2[i_2]
                        p4_plan = arCoordLines_Out_2[i_2 + 1]
                        p = DefMath.Intersection_line_plane(p1_plan, p2_plan, p3_plan, p1_line, p2_line)
                        polygon3d = [p1_plan, p2_plan, p3_plan, p4_plan]
                        polygon3d = DefMath.sort_points_clockwise(polygon3d)
                        if DefMath.is_point_in_polygon_3d(p, polygon3d, p1_plan, p2_plan, p3_plan) == True:
                            arCoord_Left_New[i] = p
                            status_exit = True
                            break
                    if status_exit == True:
                        break

            arCoord_Top_New[-1] = arCoord_Left_New[0]
            arCoord_Bot_New[0] = arCoord_Left_New[-1]

    # Right
    if DefMath.is_number(extendR) == False:
        name_mainpanel = headname2_block_mainpanel + "WL"
        dem = 0
        for panel in MainPanel_data:
            if panel["Name"] == name_mainpanel:
                Line_mainpanel = panel["Line"]
                Sec_mainpanel = panel["Sec"]
                Type_mainpanel = panel["Type"]
                Mat_mainpanel = panel["Material"]
                Expand_mainpanel = panel["Expand"]
                dem += 1
                break
        if dem == 0:
            name_mainpanel = headname2_block_mainpanel + "W"
            for panel in MainPanel_data:
                if panel["Name"] == name_mainpanel:
                    Line_mainpanel = panel["Line"]
                    Sec_mainpanel = panel["Sec"]
                    Type_mainpanel = panel["Type"]
                    Mat_mainpanel = panel["Material"]
                    Expand_mainpanel = panel["Expand"]
                    dem += 1
                    break
        if dem != 0:
            thick1_panel, thick2_panel, mat_panel = (
                Mat_mainpanel["Thick1"],
                Mat_mainpanel["Thick2"],
                Mat_mainpanel["Mat"],
            )
            arCoordLines_Out = Load_Coordinate_Panel(Senkei_data, Line_mainpanel, Sec_mainpanel)
            arCoordLines_Out = DefMath.Offset_Face(arCoordLines_Out, -thick1_panel)

            for i in range(len(arCoord_Right_New)):
                if i == 0 or i == len(arCoord_Right_New) - 1:
                    p1_line = arCoord_Right_New[i]
                    p2_line = arCoord_Left_New[len(arCoord_Left_New) - 1 - i]
                else:
                    p1_line = arCoord_Right_New[i]
                    p2_line = DefMath.Point_on_parallel_line(
                        arCoord_Right_New[i], arCoord_Right_New[0], arCoord_Left_New[-1], 100
                    )

                for i_1 in range(len(arCoordLines_Out) - 1):
                    status_exit = False
                    arCoordLines_Out_1 = arCoordLines_Out[i_1]
                    arCoordLines_Out_2 = arCoordLines_Out[i_1 + 1]
                    for i_2 in range(len(arCoordLines_Out_1) - 1):
                        p1_plan = arCoordLines_Out_1[i_2]
                        p2_plan = arCoordLines_Out_1[i_2 + 1]
                        p3_plan = arCoordLines_Out_2[i_2]
                        p4_plan = arCoordLines_Out_2[i_2 + 1]
                        p = DefMath.Intersection_line_plane(p1_plan, p2_plan, p3_plan, p1_line, p2_line)
                        polygon3d = [p1_plan, p2_plan, p3_plan, p4_plan]
                        polygon3d = DefMath.sort_points_clockwise(polygon3d)
                        if DefMath.is_point_in_polygon_3d(p, polygon3d, p1_plan, p2_plan, p3_plan) == True:
                            arCoord_Right_New[i] = p
                            status_exit = True
                            break
                    if status_exit == True:
                        break

            arCoord_Top_New[0] = arCoord_Right_New[-1]
            arCoord_Bot_New[-1] = arCoord_Right_New[0]

    return arCoord_Top_New, arCoord_Bot_New, arCoord_Left_New, arCoord_Right_New


def Extend_Yokoketa_Face_FLG(
    Mem_Rib_data,
    flg_part,
    namepart,
    arCoord_Top,
    arCoord_Bot,
    arCoord_Left,
    arCoord_Right,
    namepoint_Top,
    namepoint_Bot,
    arNamePoint,
    arCoordPoint,
):
    # 循環依存を避けるため、関数内で遅延インポート
    from src.bridge_json_to_ifc.ifc_utils_new.utils.DefBridgeUtils import Calculate_Coord_FLG

    arCoord_Top_New = arCoord_Top.copy()
    arCoord_Bot_New = arCoord_Bot.copy()
    arCoord_Left_New = arCoord_Left.copy()
    arCoord_Right_New = arCoord_Right.copy()
    p1_dia = arCoord_Bot[0]
    p2_dia = arCoord_Bot[-1]
    p3_dia = arCoord_Top[-1]

    if flg_part:
        uflg_part = flg_part["UFLG"]
        lflg_part = flg_part["LFLG"]
        if uflg_part:
            for i_1 in range(0, len(uflg_part), 2):
                namepoint_flg = uflg_part[i_1]
                ref_flg = uflg_part[i_1 + 1]
                arCoord_flg = []
                if namepoint_flg == "Auto":
                    arpoint_flg = namepoint_Top.copy()
                    arpoint_flg.reverse()
                else:
                    arpoint_flg = namepoint_flg.split("-")

                for i_2 in range(len(arpoint_flg)):
                    index = arNamePoint.index(arpoint_flg[i_2])
                    arCoord_flg.append(arCoordPoint[index])
                pdir = arCoord_Bot[0]
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
                thick1_rib, thick2_rib, mat_rib, height_rib = (
                    infor["Thick1"],
                    infor["Thick2"],
                    infor["Mat"],
                    infor["Width"],
                )
                angs_rib, ange_rib, anga_rib = ang
                # -------------------------------------------------------------
                arCoorMod_A, arCoorMod_F = Calculate_Coord_FLG(
                    arCoord_flg, pdir, height_rib / 2, height_rib / 2, anga_rib, 180 - anga_rib, angs_rib, ange_rib
                )
                arCoordFLG = [arCoorMod_F, arCoord_flg, arCoorMod_A]
                arCoordFLG = Calculate_Extend_Coord(arCoordFLG, 10, "A")
                arCoordFLG = Calculate_Extend_Coord(arCoordFLG, 10, "F")
                arCoordFLGT_Out = DefMath.Offset_Face(arCoordFLG, thick1_rib)
                arCoordFLGB_Out = DefMath.Offset_Face(arCoordFLG, -thick2_rib)
                # --------------------------------------------------------------
                for i_2 in range(len(arCoord_Top_New)):
                    if i_2 == 0 or i_2 == len(arCoord_Top_New) - 1:
                        p1_line = arCoord_Top_New[i_2]
                        p2_line = arCoord_Bot_New[len(arCoord_Bot_New) - 1 - i_2]
                    else:
                        p1_line = arCoord_Top_New[i_2]
                        p2_line = DefMath.Point_on_parallel_line(
                            arCoord_Top_New[i_2], arCoord_Top_New[0], arCoord_Bot_New[-1], 100
                        )

                    for i_3 in range(len(arCoordFLGB_Out) - 1):
                        status_exit = False
                        arCoordLines_Out_1 = arCoordFLGB_Out[i_3]
                        arCoordLines_Out_2 = arCoordFLGB_Out[i_3 + 1]
                        for i_4 in range(len(arCoordLines_Out_1) - 1):
                            p1_plan = arCoordLines_Out_1[i_4]
                            p2_plan = arCoordLines_Out_1[i_4 + 1]
                            p3_plan = arCoordLines_Out_2[i_4]
                            p4_plan = arCoordLines_Out_2[i_4 + 1]

                            if i_2 != 0 and i_2 != len(arCoord_Top_New) - 1:
                                p2_line = p1_line - 100 * DefMath.Normal_vector(p3_plan, p4_plan, p2_plan)
                                if p2_line[2] > p1_line[2]:
                                    p2_line = p1_line + 100 * DefMath.Normal_vector(p3_plan, p4_plan, p2_plan)
                                p2_line = DefMath.point_per_plan(p2_line, p1_dia, p2_dia, p3_dia)

                            p = DefMath.Intersection_plane_segment(p1_plan, p2_plan, p3_plan, p1_line, p2_line)

                            if p is not None:
                                polygon3d = [p1_plan, p2_plan, p3_plan, p4_plan]
                                polygon3d = DefMath.sort_points_clockwise(polygon3d)
                                if DefMath.is_point_in_polygon_3d(p, polygon3d, p1_plan, p2_plan, p3_plan) == True:
                                    arCoord_Top_New[i_2] = p
                                    status_exit = True
                                    break
                        if status_exit == True:
                            break

                arCoord_Left_New[0] = arCoord_Top_New[-1]
                arCoord_Right_New[-1] = arCoord_Top_New[0]

        if lflg_part:
            for i_1 in range(0, len(lflg_part), 2):
                namepoint_flg = lflg_part[i_1]
                ref_flg = lflg_part[i_1 + 1]
                arCoord_flg = []
                if namepoint_flg == "Auto":
                    arpoint_flg = namepoint_Bot
                else:
                    arpoint_flg = namepoint_flg.split("-")

                for i_2 in range(len(arpoint_flg)):
                    index = arNamePoint.index(arpoint_flg[i_2])
                    arCoord_flg.append(arCoordPoint[index])
                pdir = arCoord_Top[-1]

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
                thick1_rib, thick2_rib, mat_rib, height_rib = (
                    infor["Thick1"],
                    infor["Thick2"],
                    infor["Mat"],
                    infor["Width"],
                )
                angs_rib, ange_rib, anga_rib = ang
                # -------------------------------------------------------------
                arCoorMod_A, arCoorMod_F = Calculate_Coord_FLG(
                    arCoord_flg, pdir, height_rib / 2, height_rib / 2, anga_rib, 180 - anga_rib, angs_rib, ange_rib
                )
                arCoordFLG = [arCoorMod_F, arCoord_flg, arCoorMod_A]
                arCoordFLG = Calculate_Extend_Coord(arCoordFLG, 10, "A")
                arCoordFLG = Calculate_Extend_Coord(arCoordFLG, 10, "F")
                arCoordFLGT_Out = DefMath.Offset_Face(arCoordFLG, thick1_rib)
                arCoordFLGB_Out = DefMath.Offset_Face(arCoordFLG, -thick2_rib)
                # --------------------------------------------------------------

                for i_2 in range(len(arCoord_Bot_New)):
                    if i_2 == 0 or i_2 == len(arCoord_Bot_New) - 1:
                        p1_line = arCoord_Bot_New[i_2]
                        p2_line = arCoord_Top_New[len(arCoord_Top_New) - 1 - i_2]
                    else:
                        p1_line = arCoord_Bot_New[i_2]
                        p2_line = DefMath.Point_on_parallel_line(
                            arCoord_Bot_New[i_2], arCoord_Bot_New[0], arCoord_Top_New[-1], 100
                        )

                    for i_3 in range(len(arCoordFLGT_Out) - 1):
                        status_exit = False
                        arCoordLines_Out_1 = arCoordFLGT_Out[i_3]
                        arCoordLines_Out_2 = arCoordFLGT_Out[i_3 + 1]
                        for i_4 in range(len(arCoordLines_Out_1) - 1):
                            p1_plan = arCoordLines_Out_1[i_4]
                            p2_plan = arCoordLines_Out_1[i_4 + 1]
                            p3_plan = arCoordLines_Out_2[i_4]
                            p4_plan = arCoordLines_Out_2[i_4 + 1]

                            if i_2 != 0 and i_2 != len(arCoord_Bot_New) - 1:
                                p2_line = p1_line - 100 * DefMath.Normal_vector(p3_plan, p4_plan, p2_plan)
                                if p2_line[2] < p1_line[2]:
                                    p2_line = p1_line + 100 * DefMath.Normal_vector(p3_plan, p4_plan, p2_plan)
                                p2_line = DefMath.point_per_plan(p2_line, p1_dia, p2_dia, p3_dia)

                            p = DefMath.Intersection_plane_segment(p1_plan, p2_plan, p3_plan, p1_line, p2_line)

                            if p is not None:
                                polygon3d = [p1_plan, p2_plan, p3_plan, p4_plan]
                                polygon3d = DefMath.sort_points_clockwise(polygon3d)
                                if DefMath.is_point_in_polygon_3d(p, polygon3d, p1_plan, p2_plan, p3_plan) == True:
                                    arCoord_Bot_New[i_2] = p
                                    status_exit = True
                                    break
                        if status_exit == True:
                            break

                arCoord_Left_New[-1] = arCoord_Bot_New[0]
                arCoord_Right_New[0] = arCoord_Bot_New[-1]

    return arCoord_Top_New, arCoord_Bot_New, arCoord_Left_New, arCoord_Right_New


# ===============================================================================
# I形横桁（Yokogeta）生成関数 - DefBracing.pyから移動
# ===============================================================================


def Calculate_Yokogeta(ifc_all, Senkei_data, MainPanel_data, infor_yokogeta):
    """
    I形横桁（Yokogeta / Cross Beam）の生成

    横桁は主桁間を繋ぐI形断面の部材です。
    ウェブ+上フランジ+下フランジの3枚のプレートで構成されます。
    Break情報に基づいて分割して生成することも可能です。

    Args:
        ifc_all: (ifc_file, bridge_span, geom_context)
        Senkei_data: 線形データ
        MainPanel_data: メインパネルデータ
        infor_yokogeta: 横桁情報のタプル
            (name, girder_list, section, reference, height, z_offset, web_info, uflange_info, lflange_info, break_info)
    """
    try:
        ifc_file, bridge_span, geom_context = ifc_all
        (
            name_yokogeta,
            girder_list,
            section,
            reference,
            height,
            z_offset,
            web_info,
            uflange_info,
            lflange_info,
            break_info,
        ) = infor_yokogeta

        _log_print(f"    [Yokogeta] I形横桁 '{name_yokogeta}' の処理を開始")
        _log_print(f"    [Yokogeta] 桁: {girder_list}, 断面: {section}, 基準: {reference}, 高さ: {height}")

        if len(girder_list) != 2:
            _log_print("    [Yokogeta] エラー: 桁リストは2つの桁を指定してください")
            return

        girder1, girder2 = girder_list

        # 各主桁のウェブ位置を取得
        p1_top, p1_bottom = _get_girder_web_position(Senkei_data, MainPanel_data, girder1, section)
        p2_top, p2_bottom = _get_girder_web_position(Senkei_data, MainPanel_data, girder2, section)

        if p1_top is None or p2_top is None:
            _log_print("    [Yokogeta] エラー: 主桁の座標が取得できません")
            return

        _log_print(f"    [Yokogeta] G1上: {p1_top}, G1下: {p1_bottom}")
        _log_print(f"    [Yokogeta] G2上: {p2_top}, G2下: {p2_bottom}")

        # 主桁上フランジの厚さを取得（Break.Thickから実際の厚さを取得）
        uf_thick1 = 0  # 上半分の厚さ
        uf_thick2 = 0  # 下半分の厚さ
        for panel in MainPanel_data:
            if panel.get("Type", {}).get("TypePanel") == "UF":
                break_data = panel.get("Break", {})
                break_thick_list = break_data.get("Thick", [])
                if break_thick_list and len(break_thick_list) > 0:
                    thick_str = break_thick_list[0]  # 例: "20.0/20.0"
                    if "/" in str(thick_str):
                        parts = str(thick_str).split("/")
                        uf_thick1 = float(parts[0])  # 上半分
                        uf_thick2 = float(parts[1]) if len(parts) > 1 else uf_thick1  # 下半分
                    else:
                        uf_thick1 = float(thick_str)
                        uf_thick2 = uf_thick1
                else:
                    mat_panel = panel.get("Material", {})
                    uf_thick1 = mat_panel.get("Thick1", 0)
                    uf_thick2 = mat_panel.get("Thick2", uf_thick1)
                break

        _log_print(f"    [Yokogeta] 主桁上フランジ厚さ: 上半分={uf_thick1}mm, 下半分={uf_thick2}mm")

        # 横桁の配置位置を計算
        # Reference: "Top" = 横桁上フランジ上面が主桁上フランジ下面に合う
        # Reference: "Bottom" = 横桁下フランジが主桁下フランジ上面に合う
        if reference == "Top":
            # 横桁上面 = 主桁上フランジ下面（中心線 - 下半分厚さ）
            z_base = min(p1_top[2], p2_top[2]) - uf_thick2 + z_offset
            z_top = z_base
            z_bottom = z_base - height
        else:  # Bottom
            # 横桁下面 = 主桁下フランジ上面（p_bottomのZ座標）
            z_base = max(p1_bottom[2], p2_bottom[2]) + z_offset
            z_bottom = z_base
            z_top = z_base + height

        _log_print(f"    [Yokogeta] Z座標: 上={z_top}, 下={z_bottom}")

        # 横桁の両端座標（主桁ウェブ位置のXY座標を使用）
        # 中央のZ座標を使用
        z_center = (z_top + z_bottom) / 2
        pt1 = [p1_top[0], p1_top[1], z_center]
        pt2 = [p2_top[0], p2_top[1], z_center]

        # 横桁の長さと方向ベクトル
        dx = pt2[0] - pt1[0]
        dy = pt2[1] - pt1[1]
        length = math.sqrt(dx**2 + dy**2)

        if length < 1:
            _log_print(f"    [Yokogeta] エラー: 横桁の長さが短すぎます: {length}")
            return

        # 方向ベクトル（横桁の長さ方向）
        dir_length = [dx / length, dy / length, 0]
        # 垂直方向（Z方向）
        dir_z = [0, 0, 1]
        # 幅方向（横桁の幅方向）
        dir_width = [dir_length[1], -dir_length[0], 0]

        _log_print(f"    [Yokogeta] 長さ: {length:.2f}, 方向: {dir_length}")

        # 分割情報の取得（厚さ方向の分割）
        break_count = break_info.get("Count", 1) if break_info else 1
        if break_count < 1:
            break_count = 1
        _log_print(f"    [Yokogeta] 厚さ方向分割数: {break_count}")

        # ウェブ情報
        web_thick = web_info.get("Thick", 12)
        web_mat = web_info.get("Mat", "SM490A")

        # 上フランジ情報
        uf_thick = uflange_info.get("Thick", 16)
        uf_width = uflange_info.get("Width", 200)
        uf_mat = uflange_info.get("Mat", "SM490A")

        # 下フランジ情報
        lf_thick = lflange_info.get("Thick", 16)
        lf_width = lflange_info.get("Width", 200)
        lf_mat = lflange_info.get("Mat", "SM490A")

        # ウェブの生成（厚さ方向に分割）
        web_split_thick = web_thick / break_count
        for i in range(break_count):
            suffix = f"_{i + 1}" if break_count > 1 else ""
            # 各分割の厚さ方向オフセット
            offset_ratio = (i - (break_count - 1) / 2) / break_count  # 中心からのオフセット比率
            _draw_yokogeta_web_split(
                ifc_all,
                name_yokogeta + "_Web" + suffix,
                pt1,
                pt2,
                z_top,
                z_bottom,
                web_split_thick,
                web_thick,
                i,
                break_count,
                web_mat,
                dir_length,
                dir_width,
            )

        # 上フランジの生成（厚さ方向に分割）
        uf_split_thick = uf_thick / break_count
        for i in range(break_count):
            suffix = f"_{i + 1}" if break_count > 1 else ""
            _draw_yokogeta_flange_split(
                ifc_all,
                name_yokogeta + "_UF" + suffix,
                pt1,
                pt2,
                z_top,
                uf_split_thick,
                uf_thick,
                i,
                break_count,
                uf_width,
                uf_mat,
                dir_length,
                dir_width,
                "Top",
            )

        # 下フランジの生成（厚さ方向に分割）
        lf_split_thick = lf_thick / break_count
        for i in range(break_count):
            suffix = f"_{i + 1}" if break_count > 1 else ""
            _draw_yokogeta_flange_split(
                ifc_all,
                name_yokogeta + "_LF" + suffix,
                pt1,
                pt2,
                z_bottom,
                lf_split_thick,
                lf_thick,
                i,
                break_count,
                lf_width,
                lf_mat,
                dir_length,
                dir_width,
                "Bottom",
            )

        _log_print(f"    [Yokogeta] I形横桁 '{name_yokogeta}' の生成完了（厚さ方向{break_count}分割）")

    except Exception as e:
        import traceback

        _log_print(f"    [Yokogeta] エラーが発生しました: {e}")
        _log_print(f"    [Yokogeta] トレースバック:\n{traceback.format_exc()}")
        raise


def _get_girder_web_position(Senkei_data, MainPanel_data, girder_name, section):
    """
    主桁のウェブ位置（上端・下端）を取得

    Args:
        Senkei_data: 線形データ
        MainPanel_data: メインパネルデータ
        girder_name: 桁名（例: "G1"）
        section: 断面名（例: "C1"）

    Returns:
        (p_top, p_bottom): 上端座標と下端座標のタプル
    """
    # 桁名からウェブパネルを探す
    number_block = None
    for panel in MainPanel_data:
        Type_panel = panel["Type"]
        if Type_panel["Girder"] == girder_name and Type_panel["TypePanel"] == "W":
            number_block = Type_panel["Block"]
            break

    if number_block is None:
        _log_print(f"    [Yokogeta] 警告: 桁 '{girder_name}' のウェブパネルが見つかりません")
        return None, None

    # ウェブパネルを取得
    name_webpanel = girder_name + number_block + "W"

    for panel in MainPanel_data:
        if panel["Name"] == name_webpanel:
            Line_panel = panel["Line"]
            Sec_panel = panel["Sec"]

            # 線形から座標を取得
            arCoordLines = Load_Coordinate_Panel(Senkei_data, Line_panel, Sec_panel)

            if section in Sec_panel:
                idx = Sec_panel.index(section)
                # 上端（最初の線形）と下端（最後の線形）の座標
                p_top = list(arCoordLines[0][idx])
                p_bottom = list(arCoordLines[-1][idx])
                return p_top, p_bottom
            else:
                _log_print(f"    [Yokogeta] 警告: 断面 '{section}' がパネル '{name_webpanel}' に見つかりません")
                _log_print(f"    [Yokogeta] 利用可能な断面: {Sec_panel}")
                return None, None

    _log_print(f"    [Yokogeta] 警告: パネル '{name_webpanel}' が見つかりません")
    return None, None


def _draw_yokogeta_web(ifc_all, name, pt1, pt2, z_top, z_bottom, thick, mat, dir_length, dir_width):
    """
    横桁のウェブを生成
    """
    ifc_file, bridge_span, geom_context = ifc_all

    height = z_top - z_bottom
    dx = pt2[0] - pt1[0]
    dy = pt2[1] - pt1[1]
    length = math.sqrt(dx**2 + dy**2)

    # ウェブの4点（厚さ方向の中心）
    half_thick = thick / 2

    # 断面プロファイル（長さ×高さの矩形）
    p1 = [0, 0]
    p2 = [length, 0]
    p3 = [length, height]
    p4 = [0, height]

    profile_points = [p1, p2, p3, p4]

    # 押し出し方向（厚さ方向 = dir_width）
    # 配置位置（pt1からZ_bottomの位置、厚さの半分だけオフセット）
    origin = [pt1[0] - dir_width[0] * half_thick, pt1[1] - dir_width[1] * half_thick, z_bottom]

    # IFCでソリッドを生成
    solid = _create_extruded_solid(ifc_file, profile_points, origin, dir_length, dir_width, [0, 0, 1], thick)

    if solid:
        shape_representation = ifc_file.createIfcShapeRepresentation(
            ContextOfItems=geom_context, RepresentationIdentifier="Body", RepresentationType="Brep", Items=[solid]
        )

        DefIFC.Add_shape_representation_in_Beam(ifc_file, bridge_span, shape_representation, name + "_Web")
        _log_print(f"    [Yokogeta] ウェブ生成完了: {name}_Web")


def _draw_yokogeta_flange(ifc_all, name, pt1, pt2, z_level, thick, width, mat, dir_length, dir_width, position):
    """
    横桁のフランジを生成

    Args:
        position: "Top" または "Bottom"
    """
    ifc_file, bridge_span, geom_context = ifc_all

    dx = pt2[0] - pt1[0]
    dy = pt2[1] - pt1[1]
    length = math.sqrt(dx**2 + dy**2)

    half_width = width / 2

    # フランジの断面プロファイル（長さ×幅の矩形）
    p1 = [0, -half_width]
    p2 = [length, -half_width]
    p3 = [length, half_width]
    p4 = [0, half_width]

    profile_points = [p1, p2, p3, p4]

    # 配置位置
    if position == "Top":
        # 上フランジ: z_levelから下に向かって厚さ分
        origin = [pt1[0], pt1[1], z_level]
        extrude_dir = [0, 0, -1]  # 下向きに押し出し
    else:
        # 下フランジ: z_levelから上に向かって厚さ分
        origin = [pt1[0], pt1[1], z_level]
        extrude_dir = [0, 0, 1]  # 上向きに押し出し

    # IFCでソリッドを生成
    solid = _create_extruded_solid_flange(ifc_file, profile_points, origin, dir_length, dir_width, extrude_dir, thick)

    if solid:
        shape_representation = ifc_file.createIfcShapeRepresentation(
            ContextOfItems=geom_context, RepresentationIdentifier="Body", RepresentationType="Brep", Items=[solid]
        )

        DefIFC.Add_shape_representation_in_Beam(ifc_file, bridge_span, shape_representation, name)
        _log_print(f"    [Yokogeta] フランジ生成完了: {name}")


def _draw_yokogeta_web_split(
    ifc_all,
    name,
    pt1,
    pt2,
    z_top,
    z_bottom,
    split_thick,
    total_thick,
    split_idx,
    split_count,
    mat,
    dir_length,
    dir_width,
):
    """
    横桁のウェブを厚さ方向に分割して生成

    Args:
        split_thick: 分割後の1枚あたりの厚さ
        total_thick: 分割前の全体厚さ
        split_idx: 分割インデックス（0から）
        split_count: 分割数
    """
    ifc_file, bridge_span, geom_context = ifc_all

    height = z_top - z_bottom
    dx = pt2[0] - pt1[0]
    dy = pt2[1] - pt1[1]
    length = math.sqrt(dx**2 + dy**2)

    # 断面プロファイル（長さ×高さの矩形）
    p1 = [0, 0]
    p2 = [length, 0]
    p3 = [length, height]
    p4 = [0, height]
    profile_points = [p1, p2, p3, p4]

    # 厚さ方向のオフセット計算
    # 全体の厚さの中心を基準に、各分割をオフセット
    # split_idx=0 が一番外側（-方向）、split_idx=split_count-1 が内側（+方向）
    half_total = total_thick / 2
    offset_start = -half_total + split_idx * split_thick

    origin = [pt1[0] + dir_width[0] * offset_start, pt1[1] + dir_width[1] * offset_start, z_bottom]

    # IFCでソリッドを生成
    solid = _create_extruded_solid(ifc_file, profile_points, origin, dir_length, dir_width, [0, 0, 1], split_thick)

    if solid:
        shape_representation = ifc_file.createIfcShapeRepresentation(
            ContextOfItems=geom_context, RepresentationIdentifier="Body", RepresentationType="Brep", Items=[solid]
        )

        DefIFC.Add_shape_representation_in_Beam(ifc_file, bridge_span, shape_representation, name)
        _log_print(f"    [Yokogeta] ウェブ生成完了: {name}")


def _draw_yokogeta_flange_split(
    ifc_all,
    name,
    pt1,
    pt2,
    z_level,
    split_thick,
    total_thick,
    split_idx,
    split_count,
    width,
    mat,
    dir_length,
    dir_width,
    position,
):
    """
    横桁のフランジを厚さ方向に分割して生成

    Args:
        split_thick: 分割後の1枚あたりの厚さ
        total_thick: 分割前の全体厚さ
        split_idx: 分割インデックス（0から）
        split_count: 分割数
        position: "Top" または "Bottom"
    """
    ifc_file, bridge_span, geom_context = ifc_all

    dx = pt2[0] - pt1[0]
    dy = pt2[1] - pt1[1]
    length = math.sqrt(dx**2 + dy**2)

    half_width = width / 2

    # フランジの断面プロファイル（長さ×幅の矩形）
    p1 = [0, -half_width]
    p2 = [length, -half_width]
    p3 = [length, half_width]
    p4 = [0, half_width]
    profile_points = [p1, p2, p3, p4]

    # 厚さ方向のオフセット計算
    # 上フランジ: split_idx=0 が上面（外側）、split_idx=split_count-1 が下面（内側）
    # 下フランジ: split_idx=0 が下面（外側）、split_idx=split_count-1 が上面（内側）
    if position == "Top":
        # 上フランジ: z_levelから下に向かって押し出し
        # split_idx=0 → z_level から split_thick 分下へ（上面側）
        # split_idx=1 → z_level - split_thick から split_thick 分下へ（下面側）
        z_start = z_level - split_idx * split_thick
        origin = [pt1[0], pt1[1], z_start]
        extrude_dir = [0, 0, -1]
    else:
        # 下フランジ: z_levelから上に向かって押し出し
        # split_idx=0 → z_level から split_thick 分上へ（下面側）
        # split_idx=1 → z_level + split_thick から split_thick 分上へ（上面側）
        z_start = z_level + split_idx * split_thick
        origin = [pt1[0], pt1[1], z_start]
        extrude_dir = [0, 0, 1]

    # IFCでソリッドを生成
    solid = _create_extruded_solid_flange(
        ifc_file, profile_points, origin, dir_length, dir_width, extrude_dir, split_thick
    )

    if solid:
        shape_representation = ifc_file.createIfcShapeRepresentation(
            ContextOfItems=geom_context, RepresentationIdentifier="Body", RepresentationType="Brep", Items=[solid]
        )

        DefIFC.Add_shape_representation_in_Beam(ifc_file, bridge_span, shape_representation, name)
        _log_print(f"    [Yokogeta] フランジ生成完了: {name}")


def _create_extruded_solid(ifc_file, profile_points, origin, dir_x, dir_y, dir_z, extrude_length):
    """
    押し出しソリッドを生成（ウェブ用）
    """
    try:
        # プロファイルをワールド座標に変換（下面）
        bottom_points = []
        for p in profile_points:
            wx = origin[0] + p[0] * dir_x[0] + p[1] * dir_z[0]
            wy = origin[1] + p[0] * dir_x[1] + p[1] * dir_z[1]
            wz = origin[2] + p[0] * dir_x[2] + p[1] * dir_z[2]
            bottom_points.append([wx, wy, wz])

        # 上面（押し出し方向にオフセット）
        top_points = []
        for p in bottom_points:
            wx = p[0] + dir_y[0] * extrude_length
            wy = p[1] + dir_y[1] * extrude_length
            wz = p[2] + dir_y[2] * extrude_length
            top_points.append([wx, wy, wz])

        # Brepとしてソリッドを生成
        solid = DefIFC.Create_brep_from_prism(ifc_file, top_points, bottom_points)
        return solid
    except Exception as e:
        _log_print(f"    [Yokogeta] ソリッド生成エラー: {e}")
        import traceback

        _log_print(f"    [Yokogeta] トレースバック:\n{traceback.format_exc()}")
        return None


def _create_extruded_solid_flange(ifc_file, profile_points, origin, dir_x, dir_y, dir_z, extrude_length):
    """
    押し出しソリッドを生成（フランジ用）
    """
    try:
        # プロファイルをワールド座標に変換（下面）
        bottom_points = []
        for p in profile_points:
            wx = origin[0] + p[0] * dir_x[0] + p[1] * dir_y[0]
            wy = origin[1] + p[0] * dir_x[1] + p[1] * dir_y[1]
            wz = origin[2] + p[0] * dir_x[2] + p[1] * dir_y[2]
            bottom_points.append([wx, wy, wz])

        # 上面（押し出し方向にオフセット）
        top_points = []
        for p in bottom_points:
            wx = p[0] + dir_z[0] * extrude_length
            wy = p[1] + dir_z[1] * extrude_length
            wz = p[2] + dir_z[2] * extrude_length
            top_points.append([wx, wy, wz])

        # Brepとしてソリッドを生成
        solid = DefIFC.Create_brep_from_prism(ifc_file, top_points, bottom_points)
        return solid
    except Exception as e:
        _log_print(f"    [Yokogeta] フランジソリッド生成エラー: {e}")
        import traceback

        _log_print(f"    [Yokogeta] トレースバック:\n{traceback.format_exc()}")
        return None
