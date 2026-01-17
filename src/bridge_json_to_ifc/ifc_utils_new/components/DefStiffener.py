"""
鋼橋IFCモデル生成 - 補強材生成モジュール
SPL（ジョイントプレート）、Vstiff（垂直補剛材）、Hstiff（水平補剛材）、LRib（縦リブ）などの補強材生成
"""

import math
from math import cos, pi

import numpy as np
import pandas as pd

from src.bridge_json_to_ifc.ifc_utils_new.core import DefIFC, DefMath
from src.bridge_json_to_ifc.ifc_utils_new.io import DefStrings
from src.bridge_json_to_ifc.ifc_utils_new.utils import DefBridgeUtils

# グローバル変数: ログファイル出力関数（DefBridge.pyから設定される）
log_print_func = None


def _log_print(*args, **kwargs):
    """ログファイル出力関数（DEBUG_MODE時のみ出力）"""
    if log_print_func:
        log_print_func(*args, **kwargs)


# ---------------------------Vstiff（垂直補剛材）---------------------------------------------------------------------------------------------
def Draw_3DSolid_Vstiff(ifc_file, Len, Width, ThickA, ThickF, SideStiff, pal1, pal2, pal3):
    """
    3Dソリッドの垂直補剛材（Vstiff）を描画する

    Args:
        ifc_file: IFCファイルオブジェクト
        Len: 補剛材の長さ
        Width: 補剛材の幅
        ThickA: A側の厚さ
        ThickF: F側の厚さ
        SideStiff: 補剛材の側面位置（"L", "R", "A", "F", "T", "B"）
        pal1, pal2, pal3: 座標系を定義する3点

    Returns:
        IfcBooleanResultエンティティ（UNION演算後のソリッド）
    """
    pal1 = np.array(pal1, dtype=float)
    pal2 = np.array(pal2, dtype=float)
    pal3 = np.array(pal3, dtype=float)
    # pal1を基準としてpal2_listとpal3_listのベクトルを計算
    pal2_vector = pal2 - pal1
    pal3_vector = pal3 - pal1

    profile_points = [(0, 0), (Width, 0), (Width, Len), (0, Len), (0, 0)]
    polyline = ifc_file.createIfcPolyline([DefIFC.create_cartesian_point(ifc_file, point) for point in profile_points])
    profile = ifc_file.createIfcArbitraryClosedProfileDef("AREA", None, polyline)
    # NumPy配列をリストに変換

    pal1_list = pal1.tolist()
    pal2_list = pal2_vector.tolist()
    pal3_list = pal3_vector.tolist()
    axis2placement = ifc_file.createIfcAxis2Placement3D(
        DefIFC.create_cartesian_point(ifc_file, pal1_list),
        ifc_file.createIfcDirection(pal2_list),
        ifc_file.createIfcDirection(pal3_list),
    )
    if SideStiff == "L" or SideStiff == "A" or SideStiff == "T":
        solidA = ifc_file.createIfcExtrudedAreaSolid(
            profile, axis2placement, ifc_file.createIfcDirection([0.0, 0.0, 1.0]), -ThickA
        )
        solidF = ifc_file.createIfcExtrudedAreaSolid(
            profile, axis2placement, ifc_file.createIfcDirection([0.0, 0.0, 1.0]), ThickF
        )
    elif SideStiff == "R" or SideStiff == "F" or SideStiff == "B":
        solidA = ifc_file.createIfcExtrudedAreaSolid(
            profile, axis2placement, ifc_file.createIfcDirection([0.0, 0.0, 1.0]), ThickA
        )
        solidF = ifc_file.createIfcExtrudedAreaSolid(
            profile, axis2placement, ifc_file.createIfcDirection([0.0, 0.0, 1.0]), -ThickF
        )

    main_solid = ifc_file.createIfcBooleanResult("UNION", solidA, solidF)

    return main_solid


def Devide_Pitch_Vstiff(arCoordLines, infor_devide_stiff):
    """
    垂直補剛材のピッチに従って座標を分割する

    Args:
        arCoordLines: 座標線の配列
        infor_devide_stiff: 分割情報（タイプ、ピッチ上、ピッチ下、点名称）

    Returns:
        tuple: (arCoordLines_Vstif, PosVstiff)
            - arCoordLines_Vstif: 分割された座標線の配列
            - PosVstiff: 分割位置のインデックス配列
    """
    type_devide, pitch_top, pitch_bot, namepoint = infor_devide_stiff
    namepoint = DefStrings.Chuyen_Name_LRib_thanh_Array(namepoint)

    arCoordLines_New = []
    PosVstiff = []
    arCoordLineT = arCoordLines[0]
    arCoordLineB = arCoordLines[len(arCoordLines) - 1]
    if type_devide == "XY":
        sum2DT = 0
        sum2DB = 0
        sum3DT = 0
        sum3DB = 0
        for i in range(0, len(arCoordLineT) - 1):
            sum2DT += DefMath.Calculate_distance_p2p(
                [arCoordLineT[i][0], arCoordLineT[i][1], 0], [arCoordLineT[i + 1][0], arCoordLineT[i + 1][1], 0]
            )
            sum2DB += DefMath.Calculate_distance_p2p(
                [arCoordLineB[i][0], arCoordLineB[i][1], 0], [arCoordLineB[i + 1][0], arCoordLineB[i + 1][1], 0]
            )
            sum3DT += DefMath.Calculate_distance_p2p(arCoordLineT[i], arCoordLineT[i + 1])
            sum3DB += DefMath.Calculate_distance_p2p(arCoordLineB[i], arCoordLineB[i + 1])

        PitchT_New = DefStrings.Xu_Ly_Pitch_va_Tim_X(pitch_top, sum2DT)
        PitchB_New = DefStrings.Xu_Ly_Pitch_va_Tim_X(pitch_bot, sum2DB)

        PitchT_New = DefStrings.Xu_Ly_Pitch_va_Tim_X(PitchT_New, sum3DT)
        PitchB_New = DefStrings.Xu_Ly_Pitch_va_Tim_X(PitchB_New, sum3DB)

        arPitchT = PitchT_New.split("/")
        arPitchB = PitchB_New.split("/")
        sumpitchT = 0
        sumpitchB = 0
        for i in range(0, len(arPitchT) - 1):
            sumpitchT += float(arPitchT[i])
            sumpitchB += float(arPitchB[i])
            sumT = 0
            sumB = 0
            for i_1 in range(0, len(arCoordLineT) - 1):
                sumT += DefMath.Calculate_distance_p2p(arCoordLineT[i_1], arCoordLineT[i_1 + 1])
                sumB += DefMath.Calculate_distance_p2p(arCoordLineB[i_1], arCoordLineB[i_1 + 1])
                if sumT > sumpitchT:
                    pt = DefMath.Point_on_line(arCoordLineT[i_1 + 1], arCoordLineT[i_1], sumT - sumpitchT)
                    pb = DefMath.Point_on_line(arCoordLineB[i_1 + 1], arCoordLineB[i_1], sumB - sumpitchB)
                    pos = i_1
                    break

            ptt = pt.copy()
            ptt[1] += 100
            arCoordLine = []
            for i_1 in range(0, len(arCoordLines)):
                arCoordLinebase = arCoordLines[i_1]
                p = DefMath.Intersection_line_plane(pt, pb, ptt, arCoordLinebase[pos], arCoordLinebase[pos + 1])
                arCoordLine.append(p)

            arCoordLines_New.append(arCoordLine)
            PosVstiff.append(pos)
        ################################################################
        arCoordLines_Vstif = arCoordLines_New.copy()
        arCoordLines_Vstif = np.transpose(arCoordLines_Vstif, (1, 0, 2))

        return arCoordLines_Vstif, PosVstiff


def Extend_Vstiff_Auto_Face_FLG(MainPanel_data, Senkei_data, name_panel, P1Mod_Vstiff, P2Mod_Vstiff, Pos):
    """
    垂直補剛材をフランジ面で自動的に延長する

    Args:
        MainPanel_data: メインパネルデータ
        Senkei_data: 線形データ
        name_panel: パネル名称
        P1Mod_Vstiff, P2Mod_Vstiff: 補剛材の2点
        Pos: 位置（"T"=上、"B"=下）

    Returns:
        tuple: (P1Mod_Vstiff, P2Mod_Vstiff) - 延長後の2点
    """
    for panel in MainPanel_data:
        if panel["Name"] == name_panel:
            Line_panel = panel["Line"]
            Sec_panel = panel["Sec"]
            Type_panel = panel["Type"]
            Mat_panel = panel["Material"]
            Expand_panel = panel["Expand"]
            break
    # ---------------------Cut top--------------------------------------------
    if Pos == "T":
        name_panel_top = Type_panel["Girder"] + Type_panel["Block"] + "UF"
        dem = 0
        for panel in MainPanel_data:
            if panel["Name"] == name_panel_top:
                Line_panel_top = panel["Line"]
                Sec_panel_top = panel["Sec"]
                Type_panel_top = panel["Type"]
                Mat_panel_top = panel["Material"]
                Expand_panel_top = panel["Expand"]
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
                    break

        thick1_top, thick2_top, mat_top = Mat_panel_top["Thick1"], Mat_panel_top["Thick2"], Mat_panel_top["Mat"]
        arCoordLines_Out_top = DefBridgeUtils.Load_Coordinate_Panel(Senkei_data, Line_panel_top, Sec_panel_top)
        arCoordLines_Out_top = DefBridgeUtils.Calculate_Extend(
            MainPanel_data, Senkei_data, name_panel_top, arCoordLines_Out_top, 100, 100, 0, 0
        )
        arCoordLines_Out_top = DefMath.Offset_Face(arCoordLines_Out_top, -thick2_top)

        for i_1 in range(len(arCoordLines_Out_top) - 1):
            status_exit = False
            arCoordLines_Out_top_1 = arCoordLines_Out_top[i_1]
            arCoordLines_Out_top_2 = arCoordLines_Out_top[i_1 + 1]
            for i_2 in range(len(arCoordLines_Out_top_1) - 1):
                p1_plan = arCoordLines_Out_top_1[i_2]
                p2_plan = arCoordLines_Out_top_1[i_2 + 1]
                p3_plan = arCoordLines_Out_top_2[i_2]
                p4_plan = arCoordLines_Out_top_2[i_2 + 1]
                p = DefMath.Intersection_line_plane(p1_plan, p2_plan, p3_plan, P1Mod_Vstiff, P2Mod_Vstiff)
                polygon3d = [p1_plan, p2_plan, p3_plan, p4_plan]
                polygon3d = DefMath.sort_points_clockwise(polygon3d)
                if DefMath.is_point_in_polygon_3d(p, polygon3d, p1_plan, p2_plan, p3_plan) == True:
                    P1Mod_Vstiff = p
                    status_exit = True
                    break
            if status_exit == True:
                break

    # ---------------------Cut Bot--------------------------------------------
    if Pos == "B":
        name_panel_bot = Type_panel["Girder"] + Type_panel["Block"] + "LF"
        for panel in MainPanel_data:
            if panel["Name"] == name_panel_bot:
                Line_panel_bot = panel["Line"]
                Sec_panel_bot = panel["Sec"]
                Type_panel_bot = panel["Type"]
                Mat_panel_bot = panel["Material"]
                Expand_panel_bot = panel["Expand"]

        thick1_bot, thick2_bot, mat_bot = Mat_panel_bot["Thick1"], Mat_panel_bot["Thick2"], Mat_panel_bot["Mat"]
        arCoordLines_Out_bot = DefBridgeUtils.Load_Coordinate_Panel(Senkei_data, Line_panel_bot, Sec_panel_bot)
        arCoordLines_Out_bot = DefBridgeUtils.Calculate_Extend(
            MainPanel_data, Senkei_data, name_panel_bot, arCoordLines_Out_bot, 100, 100, 0, 0
        )
        arCoordLines_Out_bot = DefMath.Offset_Face(arCoordLines_Out_bot, thick1_bot)

        for i_1 in range(len(arCoordLines_Out_bot) - 1):
            status_exit = False
            arCoordLines_Out_bot_1 = arCoordLines_Out_bot[i_1]
            arCoordLines_Out_bot_2 = arCoordLines_Out_bot[i_1 + 1]
            for i_2 in range(len(arCoordLines_Out_bot_1) - 1):
                p1_plan = arCoordLines_Out_bot_1[i_2]
                p2_plan = arCoordLines_Out_bot_1[i_2 + 1]
                p3_plan = arCoordLines_Out_bot_2[i_2]
                p4_plan = arCoordLines_Out_bot_2[i_2 + 1]
                p = DefMath.Intersection_line_plane(p1_plan, p2_plan, p3_plan, P1Mod_Vstiff, P2Mod_Vstiff)
                polygon3d = [p1_plan, p2_plan, p3_plan, p4_plan]
                polygon3d = DefMath.sort_points_clockwise(polygon3d)
                if DefMath.is_point_in_polygon_3d(p, polygon3d, p1_plan, p2_plan, p3_plan) == True:
                    P2Mod_Vstiff = p
                    status_exit = True
                    break
            if status_exit == True:
                break

    return P1Mod_Vstiff, P2Mod_Vstiff


def Devide_Coord_LRib(arCoordLines, Pitch):
    """
    Long Rib（縦リブ）のピッチに従って座標を分割する

    Args:
        arCoordLines: 座標線の配列 [arCoordLine1, arCoordLine2]
        Pitch: ピッチ文字列（"/"で区切られた値、Xを含むことも可）

    Returns:
        分割された座標線の配列（元の2線を含む）
    """
    arCoordLine1 = arCoordLines[0]
    arCoordLine2 = arCoordLines[1]
    arCoordLines_New = []

    for i in range(0, len(arCoordLine1)):
        DistanceP2P = DefMath.Calculate_distance_p2p(arCoordLine1[i], arCoordLine2[i])
        Pitch_New = DefStrings.Xu_Ly_Pitch_va_Tim_X(Pitch, DistanceP2P)
        arPitch = Pitch_New.split("/")
        sumpitch = 0
        arCoordLine = []
        for i_1 in range(0, len(arPitch) - 1):
            sumpitch += float(arPitch[i_1])
            p = DefMath.Point_on_line(arCoordLine1[i], arCoordLine2[i], sumpitch)
            arCoordLine.append(p)
        arCoordLines_New.append(arCoordLine)

    arCoordLines_New = np.transpose(arCoordLines_New, (1, 0, 2))
    arCoordLines_New = np.insert(arCoordLines_New, 0, arCoordLine1, axis=0)
    arCoordLines_New = np.append(arCoordLines_New, [arCoordLine2], axis=0)

    return arCoordLines_New


def Calculate_X_SPL_Pitch(SPL_Pitch, length, Member_SPL_data, scale):
    """
    SPLピッチ文字列のXを計算して置き換える

    Args:
        SPL_Pitch: ピッチ文字列（"/"で区切られた値、Xを含むことも可）
        length: 全長
        Member_SPL_data: メンバーSPLデータ
        scale: スケール係数

    Returns:
        Xが計算されたピッチ文字列
    """
    arSPL_Pitch = SPL_Pitch.split("/")
    count_x = 0
    total_sum = 0

    for i in range(len(arSPL_Pitch)):
        pitch = arSPL_Pitch[i]
        if pitch != "X":
            try:
                value = float(pitch)
                total_sum += value * scale
            except ValueError:
                for spl in Member_SPL_data:
                    if spl["Name"] == pitch:
                        infor = spl["Infor"]
                        pitchj = spl["PJ"]
                        pitchl = spl["PL"]
                        pitchr = spl["PR"]
                        out = spl["Out"]
                        dhole = spl["Dhole"]
                        solid = spl["Solid"]
                        result = infor, pitchj, pitchl, pitchr, out, dhole, solid
                        Thick, Mat, Side, Angle, Gline = (
                            infor["Thick"],
                            infor["Mat"],
                            infor["Side"],
                            infor["Ang"],
                            infor["GLine"],
                        )
                        break
                Angle = Angle.split("/")

                scale_gline = 1
                if Gline == "O":
                    scale_gline = abs(1 / cos(float(Angle[0]) * pi / 180 - pi / 2))

                if len(pitchj) == 1 and pitchj[0] == 0:
                    total_sum = total_sum
                    count_x = count_x
                else:
                    for i_1 in range(len(pitchj)):
                        cell_value = pitchj[i_1]
                        if isinstance(cell_value, str) and "@" in cell_value:
                            atc1 = cell_value.split("@")
                            for _ in range(int(atc1[0])):
                                if atc1[1] != "X":
                                    total_sum += float(atc1[1]) * scale_gline * scale
                                else:
                                    count_x += 1
                        elif isinstance(cell_value, str) and ":" in cell_value:
                            atc1 = cell_value.split(":")
                            for _ in range(int(atc1[1])):
                                total_sum += (float(atc1[0]) / float(atc1[1])) * scale_gline * scale
                        else:
                            if cell_value != "X":
                                try:
                                    total_sum += float(cell_value) * scale_gline * scale
                                except ValueError:
                                    pass
                            else:
                                count_x += 1
        else:
            count_x += 1

    if count_x > 0:
        x_value = (length - total_sum) / count_x
        arSPL_Pitch = [str(x_value) if p == "X" else p for p in arSPL_Pitch]

    return "/".join(arSPL_Pitch)


# DefPanelからExtend_Yokoketa_Faceをインポート（DefBracing.pyからDefPanel.pyに移動済み）
# DefComponentからDraw_Cornerをインポート
from src.bridge_json_to_ifc.ifc_utils_new.components.DefComponent import Draw_Corner
from src.bridge_json_to_ifc.ifc_utils_new.components.DefPanel import Extend_Yokoketa_Face

# DefBridgeUtilsからCalculate_Extend_Coordをインポート
from src.bridge_json_to_ifc.ifc_utils_new.utils.DefBridgeUtils import Calculate_Extend_Coord

# 以下の関数はDefBridge.pyから移動しました
# - Calculate_Vstiff
# - Calculate_Hstiff
# - Calculate_LRib
# - Calculate_SPL
# - Calculate_SPL_Rib
# - Calculate_Vstiff_Subpanel
# - Calculate_SPL_SubPanel
# - Draw_3DSolid_SPL
# - Draw_Solid_Hole_SPL
# - Draw_Solid_Bolt_SPL
# - Draw_3DSolid_Vstiff_Taikeikou


# ---------------------------Draw_3DSolid_Vstiff_Taikeikou（横構用垂直補剛材）---------------------------------------------------------------------------------------------
def Draw_3DSolid_Vstiff_Taikeikou(
    ifc_all,
    MainPanel_data,
    Senkei_data,
    headname_block_mainpanel,
    thick_vstiff,
    width_vstiff,
    pb1_tai,
    pb2_tai,
    pb3_tai,
    pb4_tai,
    pos="R",
):
    ifc_file, bridge_span, geom_context = ifc_all

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

        arCoord_Top_Out, arCoord_Bot_Out, arCoord_Left_Out, arCoord_Right_Out = Extend_Yokoketa_Face(
            MainPanel_data,
            Senkei_data,
            headname_block_mainpanel,
            headname_block_mainpanel,
            arCoord_Top,
            arCoord_Bot,
            arCoord_Left,
            arCoord_Right,
            ["Auto", 0, "Auto", "Auto"],
        )

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

        arCoord_Top_Out, arCoord_Bot_Out, arCoord_Left_Out, arCoord_Right_Out = Extend_Yokoketa_Face(
            MainPanel_data,
            Senkei_data,
            headname_block_mainpanel,
            headname_block_mainpanel,
            arCoord_Top,
            arCoord_Bot,
            arCoord_Left,
            arCoord_Right,
            [0, "Auto", "Auto", "Auto"],
        )

    # -------------------------------------Align 2D-----------------------------------------------------
    p1_3d = arCoord_Bot[0]
    p2_3d = arCoord_Bot[-1]
    p3_3d = arCoord_Top[-1]
    p1_2d = [0, 0, 0]
    p2_2d = [100, 0, 0]
    p3_2d = [0, 100, 0]

    for i in range(0, len(arCoord_Top_Out)):
        arCoord_Top_Out[i] = DefMath.Transform_point_face2face(
            arCoord_Top_Out[i], p1_3d, p2_3d, p3_3d, p1_2d, p2_2d, p3_2d
        )
        arCoord_Top_Out[i][2] = 0
    for i in range(0, len(arCoord_Bot_Out)):
        arCoord_Bot_Out[i] = DefMath.Transform_point_face2face(
            arCoord_Bot_Out[i], p1_3d, p2_3d, p3_3d, p1_2d, p2_2d, p3_2d
        )
        arCoord_Bot_Out[i][2] = 0
    for i in range(0, len(arCoord_Left_Out)):
        arCoord_Left_Out[i] = DefMath.Transform_point_face2face(
            arCoord_Left_Out[i], p1_3d, p2_3d, p3_3d, p1_2d, p2_2d, p3_2d
        )
        arCoord_Left_Out[i][2] = 0
    for i in range(0, len(arCoord_Right_Out)):
        arCoord_Right_Out[i] = DefMath.Transform_point_face2face(
            arCoord_Right_Out[i], p1_3d, p2_3d, p3_3d, p1_2d, p2_2d, p3_2d
        )
        arCoord_Right_Out[i][2] = 0

    pal1 = p1_3d
    pal2 = DefMath.Offset_point(p1_3d, p2_3d, p3_3d, 100)
    pal3 = p2_3d

    arPoint = []
    for i in range(0, len(arCoord_Left_Out)):
        arPoint.append(arCoord_Left_Out[i])
    for i in range(0, len(arCoord_Bot_Out)):
        arPoint.append(arCoord_Bot_Out[i])
    for i in range(0, len(arCoord_Right_Out)):
        arPoint.append(arCoord_Right_Out[i])
    for i in range(0, len(arCoord_Top_Out)):
        arPoint.append(arCoord_Top_Out[i])

    Solid_vstiff_A = DefIFC.extrude_profile_and_align(ifc_file, arPoint, thick_vstiff / 2, pal1, pal2, pal3)
    Solid_vstiff_F = DefIFC.extrude_profile_and_align(ifc_file, arPoint, -thick_vstiff / 2, pal1, pal2, pal3)
    Solid_vstiff = ifc_file.createIfcBooleanResult("UNION", Solid_vstiff_A, Solid_vstiff_F)

    return Solid_vstiff


# ---------------------------Calculate_Vstiff_Subpanel（サブパネル用垂直補剛材計算）---------------------------------------------------------------------------------------------
def Calculate_Vstiff_Subpanel(
    ifc_all,
    Mem_Rib_data,
    p1_stiff,
    p2_stiff,
    name_stiff,
    ref_stiff,
    face_stiff,
    ThickA_PA,
    ThickF_PA,
    p1_3d,
    p2_3d,
    p3_3d,
):
    ifc_file, bridge_span, geom_context = ifc_all
    normal_p1p2p3 = DefMath.Normal_vector(p1_3d, p2_3d, p3_3d)
    # --------参照リブ----------------------------------------
    for rib in Mem_Rib_data:
        if rib["Name"] == ref_stiff:
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

    arface_stiff = []
    if face_stiff == "ALL":
        arface_vstiff = ["A", "F"]
    else:
        arface_vstiff = [face_stiff]

    for side in arface_vstiff:
        if side == "A" or side == "R":
            P1Mod = p1_stiff + ThickA_PA * normal_p1p2p3
            P2Mod = p2_stiff + ThickA_PA * normal_p1p2p3
        elif side == "F" or side == "L":
            P1Mod = p1_stiff - ThickF_PA * normal_p1p2p3
            P2Mod = p2_stiff - ThickF_PA * normal_p1p2p3

        if DefMath.is_number(extendT_rib) == True:
            p = DefMath.Point_on_line(P1Mod, P2Mod, -extendT_rib)
            P1Mod = p

        if DefMath.is_number(extendB_rib) == True:
            p = DefMath.Point_on_line(P2Mod, P1Mod, -extendB_rib)
            P2Mod = p

        p1al = P2Mod.copy()
        if side == "A" or side == "R":
            p3al = p1al + 100 * normal_p1p2p3
            p2al = DefMath.Offset_point(P2Mod, P1Mod, p3al, -100)
            P3Mod = P1Mod + height_rib * normal_p1p2p3
            P4Mod = P2Mod + height_rib * normal_p1p2p3
        elif side == "F" or side == "L":
            p3al = p1al - 100 * normal_p1p2p3
            p2al = DefMath.Offset_point(P2Mod, P1Mod, p3al, -100)
            P3Mod = P1Mod - height_rib * normal_p1p2p3
            P4Mod = P2Mod - height_rib * normal_p1p2p3

        Solid_Vstiff = Draw_3DSolid_Vstiff(
            ifc_file,
            DefMath.Calculate_distance_p2p(P1Mod, P2Mod),
            height_rib,
            thick1_rib,
            thick2_rib,
            side,
            p1al,
            p2al,
            p3al,
        )

        # ------------Corner cut-------------------------------
        if not pd.isnull(corner1) and corner1 != "N":
            pcorner = P1Mod
            pdirX = P3Mod
            pdirY = P2Mod
            solid_corner = Draw_Corner(ifc_file, corner1, pcorner, pdirX, pdirY)

            Solid_Vstiff = ifc_file.createIfcBooleanResult("DIFFERENCE", Solid_Vstiff, solid_corner)

        if not pd.isnull(corner2) and corner2 != "N":
            pcorner = P2Mod
            pdirX = P4Mod
            pdirY = P1Mod
            solid_corner = Draw_Corner(ifc_file, corner2, pcorner, pdirX, pdirY)

            Solid_Vstiff = ifc_file.createIfcBooleanResult("DIFFERENCE", Solid_Vstiff, solid_corner)

        if not pd.isnull(corner3) and corner3 != "N":
            pcorner = P3Mod
            pdirX = P1Mod
            pdirY = P4Mod
            solid_corner = Draw_Corner(ifc_file, corner3, pcorner, pdirX, pdirY)

            Solid_Vstiff = ifc_file.createIfcBooleanResult("DIFFERENCE", Solid_Vstiff, solid_corner)

        if not pd.isnull(corner4) and corner4 != "N":
            pcorner = P4Mod
            pdirX = P2Mod
            pdirY = P3Mod
            solid_corner = Draw_Corner(ifc_file, corner4, pcorner, pdirX, pdirY)

            Solid_Vstiff = ifc_file.createIfcBooleanResult("DIFFERENCE", Solid_Vstiff, solid_corner)

        color_style = DefIFC.create_color(ifc_file, 164.0, 206.0, 218.0)
        styled_item = ifc_file.createIfcStyledItem(Item=Solid_Vstiff, Styles=[color_style])
        shape_representation = ifc_file.createIfcShapeRepresentation(
            ContextOfItems=geom_context,
            RepresentationIdentifier="Body",
            RepresentationType="Brep",
            Items=[Solid_Vstiff],
        )
        DefIFC.Add_shape_representation_in_Beam(ifc_file, bridge_span, shape_representation, name_stiff)


# ---------------------------Calculate_SPL_SubPanel（サブパネル用SPL計算）---------------------------------------------------------------------------------------------
def Calculate_SPL_SubPanel(
    ifc_all,
    Member_SPL_data,
    arCoord_Top,
    arNamePoint,
    arCoordPoint,
    SPL_point,
    SPL_pitch,
    posJoint,
    mats_part,
    Solid_part,
):
    ifc_file, bridge_span, geom_context = ifc_all
    thicka_part, thickf_part, mat_part = mats_part

    SPL_point = SPL_point.split("-")
    index1 = arNamePoint.index(str(SPL_point[0]))
    index2 = arNamePoint.index(str(SPL_point[1]))
    pj1 = arCoordPoint[index1]
    pj2 = arCoordPoint[index2]

    pj1_2d = [0, 0]
    pj2_2d = [0, 0]
    pj1_2d[0] = 0
    pj1_2d[1] = 0
    pj2_2d[0] = 0
    pj2_2d[1] = -DefMath.Calculate_distance_p2p(pj1, pj2)

    SPL_Pitch_New = Calculate_X_SPL_Pitch(SPL_pitch, DefMath.Calculate_distance_p2p(pj1, pj2), Member_SPL_data, 1)
    arSPL_Pitch = SPL_pitch.split("/")
    arSPL_Pitch_New = SPL_Pitch_New.split("/")

    Pbase_SPL = [0, 0]
    Pbase_SPL[0] = pj1_2d[0]
    Pbase_SPL[1] = pj1_2d[1]
    for i in range(0, len(arSPL_Pitch)):
        if arSPL_Pitch[i] != "X" and DefMath.is_number(arSPL_Pitch[i]) == False:
            NameSPL = arSPL_Pitch[i]
            for spl in Member_SPL_data:
                if spl["Name"] == NameSPL:
                    infor = spl["Infor"]
                    pitchj = spl["PJ"]
                    pitchl = spl["PL"]
                    pitchr = spl["PR"]
                    out = spl["Out"]
                    dhole = spl["Dhole"]
                    solid = spl["Solid"]
                    result = infor, pitchj, pitchl, pitchr, out, dhole, solid
                    Thick, Mat, Side, Angle, Gline = (
                        infor["Thick"],
                        infor["Mat"],
                        infor["Side"],
                        infor["Ang"],
                        infor["GLine"],
                    )
                    break
            result = infor, pitchj, pitchl, pitchr, out, dhole, solid
            if solid:
                if (solid[0] == "A" or solid[0] == "L") and posJoint == "E":
                    if Side == "A":
                        pj1_3D = DefMath.Offset_point(pj1, pj2, arCoord_Top[-1], -thicka_part)
                        pj2_3D = DefMath.Offset_point(pj2, pj1, arCoord_Top[-1], thicka_part)
                        pj3_3D = DefMath.Offset_point(arCoord_Top[-1], pj1, pj2, -thicka_part)
                    elif Side == "F":
                        pj1_3D = DefMath.Offset_point(pj1, pj2, arCoord_Top[-1], thickf_part)
                        pj2_3D = DefMath.Offset_point(pj2, pj1, arCoord_Top[-1], -thickf_part)
                        pj3_3D = DefMath.Offset_point(arCoord_Top[-1], pj1, pj2, thickf_part)
                    pal1 = [0, 0, 0]
                    pal1[0] = pj1_3D[0]
                    pal1[1] = pj1_3D[1]
                    pal1[2] = pj1_3D[2]
                    pal2 = DefMath.Offset_point(pj1_3D, pj2_3D, pj3_3D, -100)
                    pal3 = DefMath.Offset_point(pj1_3D, pj2_3D, pal2, -100)

                    solidspl = Draw_3DSolid_SPL(ifc_all, Pbase_SPL, result, arSPL_Pitch_New[i], pal1, pal2, pal3)

                    if solid[1] == "HY":
                        Solid_Hole_SPL = Draw_Solid_Hole_SPL(
                            ifc_file, Pbase_SPL, result, arSPL_Pitch_New[i], pal1, pal2, pal3
                        )
                        if Solid_Hole_SPL:
                            for Solid_Hole in Solid_Hole_SPL:
                                solidspl = ifc_file.createIfcBooleanResult("DIFFERENCE", solidspl, Solid_Hole)

                    color_style = DefIFC.create_color(ifc_file, 206.0, 220.0, 163.0)
                    styled_item = ifc_file.createIfcStyledItem(Item=solidspl, Styles=[color_style])
                    shape_representation = ifc_file.createIfcShapeRepresentation(
                        ContextOfItems=geom_context,
                        RepresentationIdentifier="Body",
                        RepresentationType="Brep",
                        Items=[solidspl],
                    )
                    DefIFC.Add_shape_representation_in_Beam(ifc_file, bridge_span, shape_representation, NameSPL)

                elif (solid[0] == "F" or solid[0] == "R") and posJoint == "S":
                    if Side == "A":
                        pj1_3D = DefMath.Offset_point(pj1, pj2, arCoord_Top[0], thicka_part)
                        pj2_3D = DefMath.Offset_point(pj2, pj1, arCoord_Top[0], -thicka_part)
                        pj3_3D = DefMath.Offset_point(arCoord_Top[0], pj1, pj2, thicka_part)
                    elif Side == "F":
                        pj1_3D = DefMath.Offset_point(pj1, pj2, arCoord_Top[0], -thickf_part)
                        pj2_3D = DefMath.Offset_point(pj2, pj1, arCoord_Top[0], thickf_part)
                        pj3_3D = DefMath.Offset_point(arCoord_Top[0], pj1, pj2, -thickf_part)

                    pal1 = [0, 0, 0]
                    pal1[0] = pj1_3D[0]
                    pal1[1] = pj1_3D[1]
                    pal1[2] = pj1_3D[2]
                    pal2 = DefMath.Offset_point(pj1_3D, pj2_3D, pj3_3D, 100)
                    pal3 = DefMath.Offset_point(pj1_3D, pj2_3D, pal2, -100)

                    solidspl = Draw_3DSolid_SPL(ifc_all, Pbase_SPL, result, arSPL_Pitch_New[i], pal1, pal2, pal3)
                    if solid[1] == "HY":
                        Solid_Hole_SPL = Draw_Solid_Hole_SPL(
                            ifc_file, Pbase_SPL, result, arSPL_Pitch_New[i], pal1, pal2, pal3
                        )
                        if Solid_Hole_SPL:
                            for Solid_Hole in Solid_Hole_SPL:
                                solidspl = ifc_file.createIfcBooleanResult("DIFFERENCE", solidspl, Solid_Hole)

                    color_style = DefIFC.create_color(ifc_file, 206.0, 220.0, 163.0)
                    styled_item = ifc_file.createIfcStyledItem(Item=solidspl, Styles=[color_style])
                    shape_representation = ifc_file.createIfcShapeRepresentation(
                        ContextOfItems=geom_context,
                        RepresentationIdentifier="Body",
                        RepresentationType="Brep",
                        Items=[solidspl],
                    )
                    DefIFC.Add_shape_representation_in_Beam(ifc_file, bridge_span, shape_representation, NameSPL)

                if solid[1] == "HY":
                    if posJoint == "S":
                        pal1 = [0, 0, 0]
                        pal1[0] = pj1[0]
                        pal1[1] = pj1[1]
                        pal1[2] = pj1[2]
                        pal2 = DefMath.Offset_point(pj1, pj2, arCoord_Top[0], 100)
                        pal3 = DefMath.Offset_point(pj1, pj2, pal2, -100)
                        Solid_Hole_SPL = Draw_Solid_Hole_SPL(
                            ifc_file, Pbase_SPL, result, arSPL_Pitch_New[i], pal1, pal2, pal3, "S"
                        )
                        if Solid_Hole_SPL:
                            for Solid_Hole in Solid_Hole_SPL:
                                Solid_part = ifc_file.createIfcBooleanResult("DIFFERENCE", Solid_part, Solid_Hole)

                    elif posJoint == "E":
                        pal1 = [0, 0, 0]
                        pal1[0] = pj1[0]
                        pal1[1] = pj1[1]
                        pal1[2] = pj1[2]
                        pal2 = DefMath.Offset_point(pj1, pj2, arCoord_Top[-1], -100)
                        pal3 = DefMath.Offset_point(pj1, pj2, pal2, -100)
                        Solid_Hole_SPL = Draw_Solid_Hole_SPL(
                            ifc_file, Pbase_SPL, result, arSPL_Pitch_New[i], pal1, pal2, pal3, "E"
                        )
                        if Solid_Hole_SPL:
                            for Solid_Hole in Solid_Hole_SPL:
                                Solid_part = ifc_file.createIfcBooleanResult("DIFFERENCE", Solid_part, Solid_Hole)

                elif solid[1] == "BY":
                    gap_cen_to_head = thicka_part + Thick
                    gap_cen_to_nut = thickf_part + Thick

                    if posJoint == "S":
                        pal1 = [0, 0, 0]
                        pal1[0] = pj1[0]
                        pal1[1] = pj1[1]
                        pal1[2] = pj1[2]
                        pal2 = DefMath.Offset_point(pj1, pj2, arCoord_Top[0], 100)
                        pal3 = DefMath.Offset_point(pj1, pj2, pal2, -100)

                        Solid_Hole_SPL = Draw_Solid_Bolt_SPL(
                            ifc_all,
                            Pbase_SPL,
                            result,
                            arSPL_Pitch_New[i],
                            gap_cen_to_head,
                            gap_cen_to_nut,
                            pal1,
                            pal2,
                            pal3,
                            "S",
                        )
                        if Solid_Hole_SPL:
                            for Solid_Hole in Solid_Hole_SPL:
                                shape_representation = ifc_file.createIfcShapeRepresentation(
                                    ContextOfItems=geom_context,
                                    RepresentationIdentifier="Body",
                                    RepresentationType="Brep",
                                    Items=[Solid_Hole],
                                )
                                DefIFC.Add_shape_representation_in_Beam(
                                    ifc_file, bridge_span, shape_representation, "Bolt"
                                )

                    elif posJoint == "E":
                        pal1 = [0, 0, 0]
                        pal1[0] = pj1[0]
                        pal1[1] = pj1[1]
                        pal1[2] = pj1[2]
                        pal2 = DefMath.Offset_point(pj1, pj2, arCoord_Top[-1], -100)
                        pal3 = DefMath.Offset_point(pj1, pj2, pal2, -100)
                        Solid_Hole_SPL = Draw_Solid_Bolt_SPL(
                            ifc_all,
                            Pbase_SPL,
                            result,
                            arSPL_Pitch_New[i],
                            gap_cen_to_head,
                            gap_cen_to_nut,
                            pal1,
                            pal2,
                            pal3,
                            "E",
                        )
                        if Solid_Hole_SPL:
                            for Solid_Hole in Solid_Hole_SPL:
                                shape_representation = ifc_file.createIfcShapeRepresentation(
                                    ContextOfItems=geom_context,
                                    RepresentationIdentifier="Body",
                                    RepresentationType="Brep",
                                    Items=[Solid_Hole],
                                )
                                DefIFC.Add_shape_representation_in_Beam(
                                    ifc_file, bridge_span, shape_representation, "Bolt"
                                )

            # -----------------------------------------------------------------
            pbase = [0, 0, 0]
            pbase[0] = Pbase_SPL[0]
            pbase[1] = Pbase_SPL[1]
            pbase[2] = 0
            p1 = [0, 0, 0]
            p1[0] = pj1_2d[0]
            p1[1] = pj1_2d[1]
            p1[2] = 0
            p2 = [0, 0, 0]
            p2[0] = pj2_2d[0]
            p2[1] = pj2_2d[1]
            p2[2] = 0
            Angle = Angle.split("/")
            if Gline == "O":
                p = DefMath.Point_on_line(pbase, p2, float(arSPL_Pitch_New[i]) / abs(cos(Angle[0] * pi / 180 - pi / 2)))
            else:
                p = DefMath.Point_on_line(pbase, p2, float(arSPL_Pitch_New[i]))

            Pbase_SPL[0] = p[0]
            Pbase_SPL[1] = p[1]
        else:
            pbase = [0, 0, 0]
            pbase[0] = Pbase_SPL[0]
            pbase[1] = Pbase_SPL[1]
            pbase[2] = 0
            p1 = [0, 0, 0]
            p1[0] = pj1_2d[0]
            p1[1] = pj1_2d[1]
            p1[2] = 0
            p2 = [0, 0, 0]
            p2[0] = pj2_2d[0]
            p2[1] = pj2_2d[1]
            p2[2] = 0
            p = DefMath.Point_on_line(pbase, p2, float(arSPL_Pitch_New[i]))
            Pbase_SPL[0] = p[0]
            Pbase_SPL[1] = p[1]

    return Solid_part


# ---------------------------Draw_3DSolid_SPL（SPL 3Dソリッド生成）---------------------------------------------------------------------------------------------
def Draw_3DSolid_SPL(ifc_all, Pbase, result_load_infor_spl, Lenpj, pal1, pal2, pal3):
    ifc_file, bridge_span, geom_context = ifc_all
    Lenpj = float(Lenpj)
    infor, pitchj, pitchl, pitchr, out, dhole, solid = result_load_infor_spl
    Thick, Mat, Side, Angle, Gline = infor["Thick"], infor["Mat"], infor["Side"], infor["Ang"], infor["GLine"]
    Angle = Angle.split("/")
    outT, outB, outL, outR = out
    dholeA, dholeF = dhole
    pitchl = DefStrings.process_array(pitchl)
    pitchr = DefStrings.process_array(pitchl)
    pitchj_str = "/".join(map(str, pitchj))
    pitchj_str = DefStrings.Xu_Ly_Pitch_va_Tim_X(pitchj_str, Lenpj)
    pitchj_new = pitchj_str.split("/")

    if len(pitchj_new) == 1 and pitchj_new[0] == str(0):
        pj1 = [0, 0]
        pj1[0] = Pbase[0]
        pj1[1] = Pbase[1]
        pj2 = [0, 0]
        pj2[0] = Pbase[0]
        pj2[1] = Pbase[1] - 100
    else:
        pj1 = [0, 0]
        pj1[0] = Pbase[0]
        pj1[1] = Pbase[1]
        pj2 = [0, 0]
        pj2[0] = Pbase[0]
        pj2[1] = Pbase[1] - Lenpj

    LineLeft_B, LineLeft_T = DefMath.Offset_Line(pj2, pj1, (np.sum(pitchl) + float(outL)))
    LineRight_B, LineRight_T = DefMath.Offset_Line(pj2, pj1, -(np.sum(pitchr) + float(outR)))

    LineTop_L = [0, 0]
    LineTop_R = [0, 0]
    LineTop_R[0] = pj1[0] + 100
    LineTop_R[1] = pj1[1] + 100 * math.tan(math.radians(float(Angle[0]) - 90))
    LineTop_L[0] = pj1[0] - 100
    LineTop_L[1] = pj1[1] - 100 * math.tan(math.radians(float(Angle[0]) - 90))
    LineTop_L, LineTop_R = DefMath.Offset_Line(LineTop_L, LineTop_R, float(outT))

    if len(pitchj_new) == 1 and pitchj_new[0] == str(0):
        pj2 = [0, 0]
        pj2[0] = Pbase[0]
        pj2[1] = Pbase[1] - Lenpj
    LineBot_L = [0, 0]
    LineBot_R = [0, 0]
    if Gline == "P" or Gline == "O":
        LineBot_R[0] = pj2[0] + 100
        LineBot_R[1] = pj2[1] - 100 * math.tan(math.radians(180 - float(Angle[0]) - 90))
        LineBot_L[0] = pj2[0] - 100
        LineBot_L[1] = pj2[1] + 100 * math.tan(math.radians(180 - float(Angle[0]) - 90))
        LineBot_L, LineBot_R = DefMath.Offset_Line(LineBot_L, LineBot_R, -float(outB))
    else:  # "T" or "F"
        LineBot_R[0] = pj2[0] + 100
        LineBot_R[1] = pj2[1] - 100 * math.tan(math.radians(float(Angle[1]) - 90))
        LineBot_L[0] = pj2[0] - 100
        LineBot_L[1] = pj2[1] + 100 * math.tan(math.radians(float(Angle[1]) - 90))
        LineBot_L, LineBot_R = DefMath.Offset_Line(LineBot_L, LineBot_R, -float(outB))

    p1 = DefMath.Intersec_line_line(LineLeft_B, LineLeft_T, LineBot_L, LineBot_R)
    p2 = DefMath.Intersec_line_line(LineLeft_B, LineLeft_T, LineTop_L, LineTop_R)
    p3 = DefMath.Intersec_line_line(LineRight_B, LineRight_T, LineTop_L, LineTop_R)
    p4 = DefMath.Intersec_line_line(LineRight_B, LineRight_T, LineBot_L, LineBot_R)

    profile_points = [p1, p2, p3, p4, p1]

    if Side == "T":
        SolidSPL = DefIFC.extrude_profile_and_align(ifc_file, profile_points, Thick, pal1, pal2, pal3)
    elif Side == "B":
        SolidSPL = DefIFC.extrude_profile_and_align(ifc_file, profile_points, -Thick, pal1, pal2, pal3)
    elif Side == "L":
        SolidSPL = DefIFC.extrude_profile_and_align(ifc_file, profile_points, -Thick, pal1, pal2, pal3)
    elif Side == "R":
        SolidSPL = DefIFC.extrude_profile_and_align(ifc_file, profile_points, Thick, pal1, pal2, pal3)
    if Side == "A":
        SolidSPL = DefIFC.extrude_profile_and_align(ifc_file, profile_points, Thick, pal1, pal2, pal3)
    if Side == "F":
        SolidSPL = DefIFC.extrude_profile_and_align(ifc_file, profile_points, -Thick, pal1, pal2, pal3)

    return SolidSPL


# ---------------------------Draw_Solid_Hole_SPL（SPL穴生成）---------------------------------------------------------------------------------------------
def Draw_Solid_Hole_SPL(ifc_all, Pbase, result_load_infor_spl, Lenpj, pal1, pal2, pal3, posjoint="all"):
    ifc_file, bridge_span, geom_context = ifc_all
    Solid_HoleL_SPL = []
    Solid_HoleR_SPL = []
    Lenpj = float(Lenpj)
    infor, pitchj, pitchl, pitchr, out, dhole, solid = result_load_infor_spl
    Thick, Mat, Side, Angle, Gline = infor["Thick"], infor["Mat"], infor["Side"], infor["Ang"], infor["GLine"]
    Angle = Angle.split("/")
    outT, outB, outL, outR = out
    dholeA, dholeF = dhole
    pitchl = DefStrings.process_array(pitchl)
    pitchr = DefStrings.process_array(pitchl)

    pitchj_str = "/".join(map(str, pitchj))
    pitchj_str = DefStrings.Xu_Ly_Pitch_va_Tim_X(pitchj_str, Lenpj)
    pitchj_new = pitchj_str.split("/")

    if len(pitchj_new) == 1 and pitchj_new[0] == str(0):
        pj1 = [0, 0]
        pj1[0] = Pbase[0]
        pj1[1] = Pbase[1]
        pj2 = [0, 0]
        pj2[0] = Pbase[0]
        pj2[1] = Pbase[1] - 100
    else:
        pj1 = [0, 0]
        pj1[0] = Pbase[0]
        pj1[1] = Pbase[1]
        pj2 = [0, 0]
        pj2[0] = Pbase[0]
        pj2[1] = Pbase[1] - Lenpj

    SumTran = 0
    for i in range(0, len(pitchl)):
        SumTran += float(pitchl[i])
        p1_tran, p2_tran = DefMath.Offset_Line(pj1, pj2, -SumTran)
        if Gline == "P":
            LineTop_L = [0, 0]
            LineTop_R = [0, 0]
            LineTop_R[0] = pj1[0] + 100
            LineTop_R[1] = pj1[1] + 100 * math.tan(math.radians(float(Angle[0]) - 90))
            LineTop_L[0] = pj1[0] - 100
            LineTop_L[1] = pj1[1] - 100 * math.tan(math.radians(float(Angle[0]) - 90))

            p1_long = LineTop_L.copy()
            p2_long = LineTop_R.copy()
            p = DefMath.Intersec_line_line(p1_long, p2_long, p1_tran, p2_tran)
            solid_hole = DefIFC.Draw_Solid_Circle(ifc_file, p, dholeA, pal1, pal2, pal3)
            Solid_HoleL_SPL.append(solid_hole)
            SumLong = 0
            for i_1 in range(0, len(pitchj_new)):
                SumLong += float(pitchj_new[i_1])
                p1_long = LineTop_L.copy()
                p1_long[1] = LineTop_L[1] - SumLong
                p2_long = LineTop_R.copy()
                p2_long[1] = LineTop_R[1] - SumLong
                p = DefMath.Intersec_line_line(p1_long, p2_long, p1_tran, p2_tran)
                solid_hole = DefIFC.Draw_Solid_Circle(ifc_file, p, dholeA, pal1, pal2, pal3)
                Solid_HoleL_SPL.append(solid_hole)

        elif Gline == "T":
            LineTop_L = [0, 0]
            LineTop_R = [0, 0]
            LineTop_R[0] = pj1[0] + 100
            LineTop_R[1] = pj1[1] + 100 * math.tan(math.radians(float(Angle[0]) - 90))
            LineTop_L[0] = pj1[0] - 100
            LineTop_L[1] = pj1[1] - 100 * math.tan(math.radians(float(Angle[0]) - 90))

            p1_long = LineTop_L.copy()
            p2_long = LineTop_R.copy()
            p = DefMath.Intersec_line_line(p1_long, p2_long, p1_tran, p2_tran)

            solid_hole = DefIFC.Draw_Solid_Circle(ifc_file, p, dholeA, pal1, pal2, pal3)

            Solid_HoleL_SPL.append(solid_hole)
            SumLong = 0

            for i_1 in range(0, len(pitchj_new) - 1):
                SumLong += float(pitchj_new[i_1])
                p1_long = pj1.copy()
                p1_long[0] = pj1[0] - 100
                p1_long[1] = pj1[1] - SumLong
                p2_long = pj1.copy()
                p2_long[0] = pj1[0] + 100
                p2_long[1] = pj1[1] - SumLong
                p = DefMath.Intersec_line_line(p1_long, p2_long, p1_tran, p2_tran)
                solid_hole = DefIFC.Draw_Solid_Circle(ifc_file, p, dholeA, pal1, pal2, pal3)
                Solid_HoleL_SPL.append(solid_hole)

            if len(pitchj_new) == 1 and pitchj_new[0] == str(0):
                LineBot_L = [0, 0]
                LineBot_R = [0, 0]
                LineBot_R[0] = pj1[0] + 100
                LineBot_R[1] = pj1[1] - 100 * math.tan(math.radians(float(Angle[1]) - 90))
                LineBot_L[0] = pj1[0] - 100
                LineBot_L[1] = pj1[1] + 100 * math.tan(math.radians(float(Angle[1]) - 90))
            else:
                LineBot_L = [0, 0]
                LineBot_R = [0, 0]
                LineBot_R[0] = pj2[0] + 100
                LineBot_R[1] = pj2[1] - 100 * math.tan(math.radians(float(Angle[1]) - 90))
                LineBot_L[0] = pj2[0] - 100
                LineBot_L[1] = pj2[1] + 100 * math.tan(math.radians(float(Angle[1]) - 90))

            p = DefMath.Intersec_line_line(LineBot_R, LineBot_L, p1_tran, p2_tran)
            solid_hole = DefIFC.Draw_Solid_Circle(ifc_file, p, dholeA, pal1, pal2, pal3)
            Solid_HoleL_SPL.append(solid_hole)

    SumTran = 0
    for i in range(0, len(pitchr)):
        SumTran += float(pitchr[i])
        p1_tran, p2_tran = DefMath.Offset_Line(pj1, pj2, SumTran)
        if Gline == "P":
            LineTop_L = [0, 0]
            LineTop_R = [0, 0]
            LineTop_R[0] = pj1[0] + 100
            LineTop_R[1] = pj1[1] + 100 * math.tan(math.radians(float(Angle[0]) - 90))
            LineTop_L[0] = pj1[0] - 100
            LineTop_L[1] = pj1[1] - 100 * math.tan(math.radians(float(Angle[0]) - 90))

            p1_long = LineTop_L.copy()
            p2_long = LineTop_R.copy()
            p = DefMath.Intersec_line_line(p1_long, p2_long, p1_tran, p2_tran)
            solid_hole = DefIFC.Draw_Solid_Circle(ifc_file, p, dholeA, pal1, pal2, pal3)
            Solid_HoleR_SPL.append(solid_hole)
            SumLong = 0
            for i_1 in range(0, len(pitchj_new)):
                SumLong += float(pitchj_new[i_1])
                p1_long = LineTop_L.copy()
                p1_long[1] = LineTop_L[1] - SumLong
                p2_long = LineTop_R.copy()
                p2_long[1] = LineTop_R[1] - SumLong
                p = DefMath.Intersec_line_line(p1_long, p2_long, p1_tran, p2_tran)
                solid_hole = DefIFC.Draw_Solid_Circle(ifc_file, p, dholeA, pal1, pal2, pal3)
                Solid_HoleR_SPL.append(solid_hole)

        elif Gline == "T":
            LineTop_L = [0, 0]
            LineTop_R = [0, 0]
            LineTop_R[0] = pj1[0] + 100
            LineTop_R[1] = pj1[1] + 100 * math.tan(math.radians(float(Angle[0]) - 90))
            LineTop_L[0] = pj1[0] - 100
            LineTop_L[1] = pj1[1] - 100 * math.tan(math.radians(float(Angle[0]) - 90))

            p1_long = LineTop_L.copy()
            p2_long = LineTop_R.copy()
            p = DefMath.Intersec_line_line(p1_long, p2_long, p1_tran, p2_tran)

            solid_hole = DefIFC.Draw_Solid_Circle(ifc_file, p, dholeA, pal1, pal2, pal3)

            Solid_HoleR_SPL.append(solid_hole)
            SumLong = 0

            for i_1 in range(0, len(pitchj_new) - 1):
                SumLong += float(pitchj_new[i_1])
                p1_long = pj1.copy()
                p1_long[0] = pj1[0] - 100
                p1_long[1] = pj1[1] - SumLong
                p2_long = pj1.copy()
                p2_long[0] = pj1[0] + 100
                p2_long[1] = pj1[1] - SumLong
                p = DefMath.Intersec_line_line(p1_long, p2_long, p1_tran, p2_tran)
                solid_hole = DefIFC.Draw_Solid_Circle(ifc_file, p, dholeA, pal1, pal2, pal3)
                Solid_HoleR_SPL.append(solid_hole)

            if len(pitchj_new) == 1 and pitchj_new[0] == str(0):
                LineBot_L = [0, 0]
                LineBot_R = [0, 0]
                LineBot_R[0] = pj1[0] + 100
                LineBot_R[1] = pj1[1] - 100 * math.tan(math.radians(float(Angle[1]) - 90))
                LineBot_L[0] = pj1[0] - 100
                LineBot_L[1] = pj1[1] + 100 * math.tan(math.radians(float(Angle[1]) - 90))
            else:
                LineBot_L = [0, 0]
                LineBot_R = [0, 0]
                LineBot_R[0] = pj2[0] + 100
                LineBot_R[1] = pj2[1] - 100 * math.tan(math.radians(float(Angle[1]) - 90))
                LineBot_L[0] = pj2[0] - 100
                LineBot_L[1] = pj2[1] + 100 * math.tan(math.radians(float(Angle[1]) - 90))

            p = DefMath.Intersec_line_line(LineBot_R, LineBot_L, p1_tran, p2_tran)
            solid_hole = DefIFC.Draw_Solid_Circle(ifc_file, p, dholeA, pal1, pal2, pal3)
            Solid_HoleR_SPL.append(solid_hole)

    if posjoint == "all":
        return Solid_HoleL_SPL + Solid_HoleR_SPL
    elif posjoint == "S":
        return Solid_HoleR_SPL
    elif posjoint == "E":
        return Solid_HoleL_SPL
    else:
        return []


# ---------------------------Draw_Solid_Bolt_SPL（SPLボルト生成）---------------------------------------------------------------------------------------------
def Draw_Solid_Bolt_SPL(
    ifc_all, Pbase, result_load_infor_spl, Lenpj, gap_cen_to_head, gap_cen_to_nut, pal1, pal2, pal3, posjoint="all"
):
    ifc_file, bridge_span, geom_context = ifc_all
    Solid_HoleL_SPL = []
    Solid_HoleR_SPL = []
    Lenpj = float(Lenpj)
    infor, pitchj, pitchl, pitchr, out, dhole, solid = result_load_infor_spl
    Thick, Mat, Side, Angle, Gline = infor["Thick"], infor["Mat"], infor["Side"], infor["Ang"], infor["GLine"]
    Angle = Angle.split("/")
    outT, outB, outL, outR = out
    dholeA, dholeF = dhole
    pitchl = DefStrings.process_array(pitchl)
    pitchr = DefStrings.process_array(pitchl)

    pitchj_str = "/".join(map(str, pitchj))
    pitchj_str = DefStrings.Xu_Ly_Pitch_va_Tim_X(pitchj_str, Lenpj)
    pitchj_new = pitchj_str.split("/")

    if len(pitchj_new) == 1 and pitchj_new[0] == str(0):
        pj1 = [0, 0]
        pj1[0] = Pbase[0]
        pj1[1] = Pbase[1]
        pj2 = [0, 0]
        pj2[0] = Pbase[0]
        pj2[1] = Pbase[1] - 100
    else:
        pj1 = [0, 0]
        pj1[0] = Pbase[0]
        pj1[1] = Pbase[1]
        pj2 = [0, 0]
        pj2[0] = Pbase[0]
        pj2[1] = Pbase[1] - Lenpj

    SumTran = 0
    for i in range(0, len(pitchl)):
        SumTran += float(pitchl[i])
        p1_tran, p2_tran = DefMath.Offset_Line(pj1, pj2, -SumTran)
        if Gline == "P":
            LineTop_L = [0, 0]
            LineTop_R = [0, 0]
            LineTop_R[0] = pj1[0] + 100
            LineTop_R[1] = pj1[1] + 100 * math.tan(math.radians(float(Angle[0]) - 90))
            LineTop_L[0] = pj1[0] - 100
            LineTop_L[1] = pj1[1] - 100 * math.tan(math.radians(float(Angle[0]) - 90))

            p1_long = LineTop_L.copy()
            p2_long = LineTop_R.copy()
            p = DefMath.Intersec_line_line(p1_long, p2_long, p1_tran, p2_tran)
            solid_hole = DefIFC.Draw_Solid_Bolt(ifc_file, p, 26.5, gap_cen_to_head, gap_cen_to_nut, pal1, pal2, pal3)
            Solid_HoleL_SPL.append(solid_hole)
            SumLong = 0
            for i_1 in range(0, len(pitchj_new)):
                SumLong += float(pitchj_new[i_1])
                p1_long = LineTop_L.copy()
                p1_long[1] = LineTop_L[1] - SumLong
                p2_long = LineTop_R.copy()
                p2_long[1] = LineTop_R[1] - SumLong
                p = DefMath.Intersec_line_line(p1_long, p2_long, p1_tran, p2_tran)
                solid_hole = DefIFC.Draw_Solid_Bolt(
                    ifc_file, p, 26.5, gap_cen_to_head, gap_cen_to_nut, pal1, pal2, pal3
                )
                Solid_HoleL_SPL.append(solid_hole)

        elif Gline == "T":
            LineTop_L = [0, 0]
            LineTop_R = [0, 0]
            LineTop_R[0] = pj1[0] + 100
            LineTop_R[1] = pj1[1] + 100 * math.tan(math.radians(float(Angle[0]) - 90))
            LineTop_L[0] = pj1[0] - 100
            LineTop_L[1] = pj1[1] - 100 * math.tan(math.radians(float(Angle[0]) - 90))

            p1_long = LineTop_L.copy()
            p2_long = LineTop_R.copy()
            p = DefMath.Intersec_line_line(p1_long, p2_long, p1_tran, p2_tran)
            solid_hole = DefIFC.Draw_Solid_Bolt(ifc_file, p, 26.5, gap_cen_to_head, gap_cen_to_nut, pal1, pal2, pal3)

            Solid_HoleL_SPL.append(solid_hole)
            SumLong = 0

            for i_1 in range(0, len(pitchj_new) - 1):
                SumLong += float(pitchj_new[i_1])
                p1_long = pj1.copy()
                p1_long[0] = pj1[0] - 100
                p1_long[1] = pj1[1] - SumLong
                p2_long = pj1.copy()
                p1_long[0] = pj1[0] + 100
                p2_long[1] = pj1[1] - SumLong
                p = DefMath.Intersec_line_line(p1_long, p2_long, p1_tran, p2_tran)
                solid_hole = DefIFC.Draw_Solid_Bolt(
                    ifc_file, p, 26.5, gap_cen_to_head, gap_cen_to_nut, pal1, pal2, pal3
                )
                Solid_HoleL_SPL.append(solid_hole)

            if len(pitchj_new) == 1 and pitchj_new[0] == str(0):
                LineBot_L = [0, 0]
                LineBot_R = [0, 0]
                LineBot_R[0] = pj1[0] + 100
                LineBot_R[1] = pj1[1] - 100 * math.tan(math.radians(float(Angle[1]) - 90))
                LineBot_L[0] = pj1[0] - 100
                LineBot_L[1] = pj1[1] + 100 * math.tan(math.radians(float(Angle[1]) - 90))
            else:
                LineBot_L = [0, 0]
                LineBot_R = [0, 0]
                LineBot_R[0] = pj2[0] + 100
                LineBot_R[1] = pj2[1] - 100 * math.tan(math.radians(float(Angle[1]) - 90))
                LineBot_L[0] = pj2[0] - 100
                LineBot_L[1] = pj2[1] + 100 * math.tan(math.radians(float(Angle[1]) - 90))

            p = DefMath.Intersec_line_line(LineBot_R, LineBot_L, p1_tran, p2_tran)
            solid_hole = DefIFC.Draw_Solid_Bolt(ifc_file, p, 26.5, gap_cen_to_head, gap_cen_to_nut, pal1, pal2, pal3)
            Solid_HoleL_SPL.append(solid_hole)

    SumTran = 0
    for i in range(0, len(pitchr)):
        SumTran += float(pitchr[i])
        p1_tran, p2_tran = DefMath.Offset_Line(pj1, pj2, SumTran)
        if Gline == "P":
            LineTop_L = [0, 0]
            LineTop_R = [0, 0]
            LineTop_R[0] = pj1[0] + 100
            LineTop_R[1] = pj1[1] + 100 * math.tan(math.radians(float(Angle[0]) - 90))
            LineTop_L[0] = pj1[0] - 100
            LineTop_L[1] = pj1[1] - 100 * math.tan(math.radians(float(Angle[0]) - 90))

            p1_long = LineTop_L.copy()
            p2_long = LineTop_R.copy()
            p = DefMath.Intersec_line_line(p1_long, p2_long, p1_tran, p2_tran)
            solid_hole = DefIFC.Draw_Solid_Bolt(ifc_file, p, 26.5, gap_cen_to_head, gap_cen_to_nut, pal1, pal2, pal3)
            Solid_HoleR_SPL.append(solid_hole)
            SumLong = 0
            for i_1 in range(0, len(pitchj_new)):
                SumLong += float(pitchj_new[i_1])
                p1_long = LineTop_L.copy()
                p1_long[1] = LineTop_L[1] - SumLong
                p2_long = LineTop_R.copy()
                p2_long[1] = LineTop_R[1] - SumLong
                p = DefMath.Intersec_line_line(p1_long, p2_long, p1_tran, p2_tran)
                solid_hole = DefIFC.Draw_Solid_Bolt(
                    ifc_file, p, 26.5, gap_cen_to_head, gap_cen_to_nut, pal1, pal2, pal3
                )
                Solid_HoleR_SPL.append(solid_hole)

        elif Gline == "T":
            LineTop_L = [0, 0]
            LineTop_R = [0, 0]
            LineTop_R[0] = pj1[0] + 100
            LineTop_R[1] = pj1[1] + 100 * math.tan(math.radians(float(Angle[0]) - 90))
            LineTop_L[0] = pj1[0] - 100
            LineTop_L[1] = pj1[1] - 100 * math.tan(math.radians(float(Angle[0]) - 90))

            p1_long = LineTop_L.copy()
            p2_long = LineTop_R.copy()
            p = DefMath.Intersec_line_line(p1_long, p2_long, p1_tran, p2_tran)
            solid_hole = DefIFC.Draw_Solid_Bolt(ifc_file, p, 26.5, gap_cen_to_head, gap_cen_to_nut, pal1, pal2, pal3)

            Solid_HoleR_SPL.append(solid_hole)
            SumLong = 0

            for i_1 in range(0, len(pitchj_new) - 1):
                SumLong += float(pitchj_new[i_1])
                p1_long = pj1.copy()
                p1_long[0] = pj1[0] - 100
                p1_long[1] = pj1[1] - SumLong
                p2_long = pj1.copy()
                p1_long[0] = pj1[0] + 100
                p2_long[1] = pj1[1] - SumLong
                p = DefMath.Intersec_line_line(p1_long, p2_long, p1_tran, p2_tran)
                solid_hole = DefIFC.Draw_Solid_Bolt(
                    ifc_file, p, 26.5, gap_cen_to_head, gap_cen_to_nut, pal1, pal2, pal3
                )
                Solid_HoleR_SPL.append(solid_hole)

            if len(pitchj_new) == 1 and pitchj_new[0] == str(0):
                LineBot_L = [0, 0]
                LineBot_R = [0, 0]
                LineBot_R[0] = pj1[0] + 100
                LineBot_R[1] = pj1[1] - 100 * math.tan(math.radians(float(Angle[1]) - 90))
                LineBot_L[0] = pj1[0] - 100
                LineBot_L[1] = pj1[1] + 100 * math.tan(math.radians(float(Angle[1]) - 90))
            else:
                LineBot_L = [0, 0]
                LineBot_R = [0, 0]
                LineBot_R[0] = pj2[0] + 100
                LineBot_R[1] = pj2[1] - 100 * math.tan(math.radians(float(Angle[1]) - 90))
                LineBot_L[0] = pj2[0] - 100
                LineBot_L[1] = pj2[1] + 100 * math.tan(math.radians(float(Angle[1]) - 90))

            p = DefMath.Intersec_line_line(LineBot_R, LineBot_L, p1_tran, p2_tran)
            solid_hole = DefIFC.Draw_Solid_Bolt(ifc_file, p, 26.5, gap_cen_to_head, gap_cen_to_nut, pal1, pal2, pal3)
            Solid_HoleR_SPL.append(solid_hole)

    if posjoint == "all":
        return Solid_HoleL_SPL + Solid_HoleR_SPL
    elif posjoint == "S":
        return Solid_HoleR_SPL
    elif posjoint == "E":
        return Solid_HoleL_SPL
    else:
        return []


# ---------------------------Calculate_SPL_Rib（リブ用SPL計算）---------------------------------------------------------------------------------------------
def Calculate_SPL_Rib(
    ifc_all, Member_SPL_data, pj1, pj2, pjPlan, SPL_pitch, posJoint, thick1_rib, thick2_rib, Solid_rib
):
    ifc_file, bridge_span, geom_context = ifc_all

    pj1_2d = [0, 0]
    pj2_2d = [0, 0]
    pj1_2d[0] = 0
    pj1_2d[1] = 0
    pj2_2d[0] = 0
    pj2_2d[1] = -DefMath.Calculate_distance_p2p(pj1, pj2)
    SPL_Pitch_New = Calculate_X_SPL_Pitch(SPL_pitch, DefMath.Calculate_distance_p2p(pj1, pj2), Member_SPL_data, 1)
    arSPL_Pitch = SPL_pitch.split("/")
    arSPL_Pitch_New = SPL_Pitch_New.split("/")

    Pbase_SPL = [0, 0]
    Pbase_SPL[0] = pj1_2d[0]
    Pbase_SPL[1] = pj1_2d[1]
    for i in range(0, len(arSPL_Pitch)):
        if arSPL_Pitch[i] != "X" and DefMath.is_number(arSPL_Pitch[i]) == False:
            NameSPL = arSPL_Pitch[i]
            for spl in Member_SPL_data:
                if spl["Name"] == NameSPL:
                    infor = spl["Infor"]
                    pitchj = spl["PJ"]
                    pitchl = spl["PL"]
                    pitchr = spl["PR"]
                    out = spl["Out"]
                    dhole = spl["Dhole"]
                    solid = spl["Solid"]
                    result = infor, pitchj, pitchl, pitchr, out, dhole, solid
                    Thick, Mat, Side, Angle, Gline = (
                        infor["Thick"],
                        infor["Mat"],
                        infor["Side"],
                        infor["Ang"],
                        infor["GLine"],
                    )
                    break
            result = infor, pitchj, pitchl, pitchr, out, dhole, solid

            if solid:
                if (solid[0] == "A" or solid[0] == "L") and posJoint == "E":
                    Thick, Mat, Side, Angle, Gline = (
                        infor["Thick"],
                        infor["Mat"],
                        infor["Side"],
                        infor["Ang"],
                        infor["GLine"],
                    )
                    if Side == "A" or Side == "T":
                        pj1_3D = DefMath.Offset_point(pj1, pj2, pjPlan, -thick1_rib)
                        pj2_3D = DefMath.Offset_point(pj2, pj1, pjPlan, thick1_rib)
                        pj3_3D = DefMath.Offset_point(pjPlan, pj1, pj2, -thick1_rib)
                    if Side == "L":
                        pj1_3D = DefMath.Offset_point(pj1, pj2, pjPlan, thick1_rib)
                        pj2_3D = DefMath.Offset_point(pj2, pj1, pjPlan, -thick1_rib)
                        pj3_3D = DefMath.Offset_point(pjPlan, pj1, pj2, thick1_rib)
                    elif Side == "F" or Side == "B":
                        pj1_3D = DefMath.Offset_point(pj1, pj2, pjPlan, thick2_rib)
                        pj2_3D = DefMath.Offset_point(pj2, pj1, pjPlan, -thick2_rib)
                        pj3_3D = DefMath.Offset_point(pjPlan, pj1, pj2, thick2_rib)
                    elif Side == "R":
                        pj1_3D = DefMath.Offset_point(pj1, pj2, pjPlan, -thick2_rib)
                        pj2_3D = DefMath.Offset_point(pj2, pj1, pjPlan, thick2_rib)
                        pj3_3D = DefMath.Offset_point(pjPlan, pj1, pj2, -thick2_rib)

                    pal1 = [0, 0, 0]
                    pal1[0] = pj1_3D[0]
                    pal1[1] = pj1_3D[1]
                    pal1[2] = pj1_3D[2]
                    pal2 = DefMath.Offset_point(pj1_3D, pj2_3D, pj3_3D, -100)
                    pal3 = DefMath.Offset_point(pj1_3D, pj2_3D, pal2, -100)

                    solidspl = Draw_3DSolid_SPL(ifc_all, Pbase_SPL, result, arSPL_Pitch_New[i], pal1, pal2, pal3)

                    if solid[1] == "HY":
                        Solid_Hole_SPL = Draw_Solid_Hole_SPL(
                            ifc_file, Pbase_SPL, result, arSPL_Pitch_New[i], pal1, pal2, pal3
                        )
                        if Solid_Hole_SPL:
                            for Solid_Hole in Solid_Hole_SPL:
                                solidspl = ifc_file.createIfcBooleanResult("DIFFERENCE", solidspl, Solid_Hole)

                    color_style = DefIFC.create_color(ifc_file, 206.0, 220.0, 163.0)
                    styled_item = ifc_file.createIfcStyledItem(Item=solidspl, Styles=[color_style])
                    shape_representation = ifc_file.createIfcShapeRepresentation(
                        ContextOfItems=geom_context,
                        RepresentationIdentifier="Body",
                        RepresentationType="Brep",
                        Items=[solidspl],
                    )
                    DefIFC.Add_shape_representation_in_Beam(ifc_file, bridge_span, shape_representation, NameSPL)

                elif (solid[0] == "F" or solid[0] == "R") and posJoint == "S":
                    Thick, Mat, Side, Angle, Gline = (
                        infor["Thick"],
                        infor["Mat"],
                        infor["Side"],
                        infor["Ang"],
                        infor["GLine"],
                    )
                    if Side == "A" or Side == "T":
                        pj1_3D = DefMath.Offset_point(pj1, pj2, pjPlan, thick1_rib)
                        pj2_3D = DefMath.Offset_point(pj2, pj1, pjPlan, -thick1_rib)
                        pj3_3D = DefMath.Offset_point(pjPlan, pj1, pj2, thick1_rib)
                    elif Side == "L":
                        pj1_3D = DefMath.Offset_point(pj1, pj2, pjPlan, -thick1_rib)
                        pj2_3D = DefMath.Offset_point(pj2, pj1, pjPlan, thick1_rib)
                        pj3_3D = DefMath.Offset_point(pjPlan, pj1, pj2, -thick1_rib)
                    elif Side == "F" or Side == "B":
                        pj1_3D = DefMath.Offset_point(pj1, pj2, pjPlan, -thick2_rib)
                        pj2_3D = DefMath.Offset_point(pj2, pj1, pjPlan, thick2_rib)
                        pj3_3D = DefMath.Offset_point(pjPlan, pj1, pj2, -thick2_rib)
                    elif Side == "R":
                        pj1_3D = DefMath.Offset_point(pj1, pj2, pjPlan, thick2_rib)
                        pj2_3D = DefMath.Offset_point(pj2, pj1, pjPlan, -thick2_rib)
                        pj3_3D = DefMath.Offset_point(pjPlan, pj1, pj2, thick2_rib)

                    pal1 = [0, 0, 0]
                    pal1[0] = pj1_3D[0]
                    pal1[1] = pj1_3D[1]
                    pal1[2] = pj1_3D[2]
                    pal2 = DefMath.Offset_point(pj1_3D, pj2_3D, pj3_3D, 100)
                    pal3 = DefMath.Offset_point(pj1_3D, pj2_3D, pal2, -100)

                    solidspl = Draw_3DSolid_SPL(ifc_all, Pbase_SPL, result, arSPL_Pitch_New[i], pal1, pal2, pal3)
                    if solid[1] == "HY":
                        Solid_Hole_SPL = Draw_Solid_Hole_SPL(
                            ifc_file, Pbase_SPL, result, arSPL_Pitch_New[i], pal1, pal2, pal3
                        )
                        if Solid_Hole_SPL:
                            for Solid_Hole in Solid_Hole_SPL:
                                solidspl = ifc_file.createIfcBooleanResult("DIFFERENCE", solidspl, Solid_Hole)

                    color_style = DefIFC.create_color(ifc_file, 206.0, 220.0, 163.0)
                    styled_item = ifc_file.createIfcStyledItem(Item=solidspl, Styles=[color_style])
                    shape_representation = ifc_file.createIfcShapeRepresentation(
                        ContextOfItems=geom_context,
                        RepresentationIdentifier="Body",
                        RepresentationType="Brep",
                        Items=[solidspl],
                    )
                    DefIFC.Add_shape_representation_in_Beam(ifc_file, bridge_span, shape_representation, NameSPL)

                if solid[1] == "HY":
                    Thick, Mat, Side, Angle, Gline = (
                        infor["Thick"],
                        infor["Mat"],
                        infor["Side"],
                        infor["Ang"],
                        infor["GLine"],
                    )
                    if posJoint == "S":
                        pal1 = [0, 0, 0]
                        pal1[0] = pj1[0]
                        pal1[1] = pj1[1]
                        pal1[2] = pj1[2]
                        pal2 = DefMath.Offset_point(pj1, pj2, pjPlan, 100)
                        pal3 = DefMath.Offset_point(pj1, pj2, pal2, -100)
                        Solid_Hole_SPL = Draw_Solid_Hole_SPL(
                            ifc_file, Pbase_SPL, result, arSPL_Pitch_New[i], pal1, pal2, pal3, "S"
                        )
                        if Solid_Hole_SPL:
                            for Solid_Hole in Solid_Hole_SPL:
                                Solid_rib = ifc_file.createIfcBooleanResult("DIFFERENCE", Solid_rib, Solid_Hole)

                    elif posJoint == "E":
                        pal1 = [0, 0, 0]
                        pal1[0] = pj1[0]
                        pal1[1] = pj1[1]
                        pal1[2] = pj1[2]
                        pal2 = DefMath.Offset_point(pj1, pj2, pjPlan, -100)
                        pal3 = DefMath.Offset_point(pj1, pj2, pal2, -100)
                        Solid_Hole_SPL = Draw_Solid_Hole_SPL(
                            ifc_file, Pbase_SPL, result, arSPL_Pitch_New[i], pal1, pal2, pal3, "E"
                        )
                        if Solid_Hole_SPL:
                            for Solid_Hole in Solid_Hole_SPL:
                                Solid_rib = ifc_file.createIfcBooleanResult("DIFFERENCE", Solid_rib, Solid_Hole)
                elif solid[1] == "BY":
                    Thick, Mat, Side, Angle, Gline = (
                        infor["Thick"],
                        infor["Mat"],
                        infor["Side"],
                        infor["Ang"],
                        infor["GLine"],
                    )
                    gap_cen_to_head = thick1_rib + Thick
                    gap_cen_to_nut = thick2_rib + Thick

                    if posJoint == "S":
                        pal1 = [0, 0, 0]
                        pal1[0] = pj1[0]
                        pal1[1] = pj1[1]
                        pal1[2] = pj1[2]
                        pal2 = DefMath.Offset_point(pj1, pj2, pjPlan, 100)
                        pal3 = DefMath.Offset_point(pj1, pj2, pal2, -100)

                        Solid_Hole_SPL = Draw_Solid_Bolt_SPL(
                            ifc_all,
                            Pbase_SPL,
                            result,
                            arSPL_Pitch_New[i],
                            gap_cen_to_head,
                            gap_cen_to_nut,
                            pal1,
                            pal2,
                            pal3,
                            "S",
                        )
                        if Solid_Hole_SPL:
                            for Solid_Hole in Solid_Hole_SPL:
                                shape_representation = ifc_file.createIfcShapeRepresentation(
                                    ContextOfItems=geom_context,
                                    RepresentationIdentifier="Body",
                                    RepresentationType="Brep",
                                    Items=[Solid_Hole],
                                )
                                DefIFC.Add_shape_representation_in_Beam(
                                    ifc_file, bridge_span, shape_representation, "Bolt"
                                )

                    elif posJoint == "E":
                        pal1 = [0, 0, 0]
                        pal1[0] = pj1[0]
                        pal1[1] = pj1[1]
                        pal1[2] = pj1[2]
                        pal2 = DefMath.Offset_point(pj1, pj2, pjPlan, -100)
                        pal3 = DefMath.Offset_point(pj1, pj2, pal2, -100)
                        Solid_Hole_SPL = Draw_Solid_Bolt_SPL(
                            ifc_all,
                            Pbase_SPL,
                            result,
                            arSPL_Pitch_New[i],
                            gap_cen_to_head,
                            gap_cen_to_nut,
                            pal1,
                            pal2,
                            pal3,
                            "E",
                        )
                        if Solid_Hole_SPL:
                            for Solid_Hole in Solid_Hole_SPL:
                                shape_representation = ifc_file.createIfcShapeRepresentation(
                                    ContextOfItems=geom_context,
                                    RepresentationIdentifier="Body",
                                    RepresentationType="Brep",
                                    Items=[Solid_Hole],
                                )
                                DefIFC.Add_shape_representation_in_Beam(
                                    ifc_file, bridge_span, shape_representation, "Bolt"
                                )

            # -----------------------------------------------------------------
            pbase = [0, 0, 0]
            pbase[0] = Pbase_SPL[0]
            pbase[1] = Pbase_SPL[1]
            pbase[2] = 0
            p1 = [0, 0, 0]
            p1[0] = pj1_2d[0]
            p1[1] = pj1_2d[1]
            p1[2] = 0
            p2 = [0, 0, 0]
            p2[0] = pj2_2d[0]
            p2[1] = pj2_2d[1]
            p2[2] = 0
            Angle = infor["Ang"]
            Angle = Angle.split("/")
            GLine_SPL = infor["GLine"]

            if GLine_SPL == "O":
                p = DefMath.Point_on_line(pbase, p2, float(arSPL_Pitch_New[i]) / abs(cos(Angle[0] * pi / 180 - pi / 2)))
            else:
                p = DefMath.Point_on_line(pbase, p2, float(arSPL_Pitch_New[i]))

            Pbase_SPL[0] = p[0]
            Pbase_SPL[1] = p[1]
        else:
            pbase = [0, 0, 0]
            pbase[0] = Pbase_SPL[0]
            pbase[1] = Pbase_SPL[1]
            pbase[2] = 0
            p1 = [0, 0, 0]
            p1[0] = pj1_2d[0]
            p1[1] = pj1_2d[1]
            p1[2] = 0
            p2 = [0, 0, 0]
            p2[0] = pj2_2d[0]
            p2[1] = pj2_2d[1]
            p2[2] = 0
            p = DefMath.Point_on_line(pbase, p2, float(arSPL_Pitch_New[i]))
            Pbase_SPL[0] = p[0]
            Pbase_SPL[1] = p[1]

    return Solid_rib


# ---------------------------Calculate_Hstiff（水平補剛材計算）---------------------------------------------------------------------------------------------
def Calculate_Hstiff(
    ifc_all,
    Data_Panel,
    Senkei_data,
    Mem_Rib_data,
    name_panel,
    infor_hstiff,
    arCoord_mod_panel,
    line_panel,
    sec_panel,
    thick1_panel,
    thick2_panel,
):
    ifc_file, bridge_span, geom_context = ifc_all

    name_point_line_hstiff, name_point_sec_hstiff, face_hstiff, name_hstiff, name_ref_hstiff = (
        infor_hstiff["Line"],
        infor_hstiff["Point"],
        infor_hstiff["Face"],
        infor_hstiff["Name"],
        infor_hstiff["Ref"],
    )

    name_point_line_hstiff = DefStrings.Chuyen_Name_LRib_thanh_Array(name_point_line_hstiff)
    name_hstiff = DefStrings.Chuyen_Name_LRib_thanh_Array(name_hstiff)
    name_point_sec_hstiff = name_point_sec_hstiff.split("-")
    arface_hstiff = []
    if face_hstiff == "ALL":
        arface_hstiff = ["L", "R"]
    else:
        arface_hstiff = [face_hstiff]

    # --------参照リブ----------------------------------------
    for rib in Mem_Rib_data:
        if rib["Name"] == name_ref_hstiff:
            infor = rib["Infor"]
            ang = rib["Ang"]
            extend = rib["Extend"]
            corner = rib["Corner"]
            spl_s = rib["JointS"]
            spl_e = rib["JointE"]
            break

    thick1_rib, thick2_rib, mat_rib, height_rib = infor["Thick1"], infor["Thick2"], infor["Mat"], infor["Width"]
    angs_rib, ange_rib, anga_rib = ang
    extendL_rib, extendR_rib, extendT_rib, extendB_rib = extend
    corner1, corner2, corner3, corner4 = corner
    # --------------------------------------------------------------
    for i in range(len(name_point_line_hstiff)):
        for side in arface_hstiff:
            if side == "L":
                arCoord_Base_Offset = DefMath.Offset_Face(arCoord_mod_panel, -thick1_panel)
            elif side == "R":
                arCoord_Base_Offset = DefMath.Offset_Face(arCoord_mod_panel, thick2_panel)

            indices_SecLines_hstiff = []
            for i_1 in range(sec_panel.index(name_point_sec_hstiff[0]), sec_panel.index(name_point_sec_hstiff[1]) + 1):
                indices_SecLines_hstiff.append(i_1)

            Coords_Hstiff_Mod1 = []
            arCoord1 = []
            arCoord2 = []
            for i_2 in range(0, len(indices_SecLines_hstiff)):
                arCoor1 = arCoord_Base_Offset[line_panel.index(name_point_line_hstiff[i]) + 1]
                arCoor2 = arCoord_Base_Offset[line_panel.index(name_point_line_hstiff[i]) + 2]
                arCoord1.append(arCoor1[indices_SecLines_hstiff[i_2]])
                arCoord2.append(arCoor2[indices_SecLines_hstiff[i_2]])
            Coords_Hstiff_Mod1.append(arCoord1)
            Coords_Hstiff_Mod1.append(arCoord2)

            if side == "L":
                Coords_Hstiff_Mod2 = DefMath.Offset_Face(Coords_Hstiff_Mod1, -height_rib)
            elif side == "R":
                Coords_Hstiff_Mod2 = DefMath.Offset_Face(Coords_Hstiff_Mod1, height_rib)

            Coords_Hstiff_Mod = [Coords_Hstiff_Mod1[0], Coords_Hstiff_Mod2[0]]
            # -----------Extend-------------------------------
            Coords_Hstiff_Out = Coords_Hstiff_Mod.copy()
            if DefMath.is_number(extendL_rib) == True:
                Coords_Hstiff_Out = Calculate_Extend_Coord(Coords_Hstiff_Out, extendL_rib, "A")

            if DefMath.is_number(extendR_rib) == True:
                Coords_Hstiff_Out = Calculate_Extend_Coord(Coords_Hstiff_Out, extendR_rib, "F")
            # -----------Create Solid-------------------------------
            if side == "L":
                Coords_Hstiff_Top = DefMath.Offset_Face(Coords_Hstiff_Out, thick1_rib)
                Coords_Hstiff_Bot = DefMath.Offset_Face(Coords_Hstiff_Out, -thick2_rib)
                solid_Hstiff = DefIFC.Create_brep_from_box_points(ifc_file, Coords_Hstiff_Bot, Coords_Hstiff_Top)
            elif side == "R":
                Coords_Hstiff_Top = DefMath.Offset_Face(Coords_Hstiff_Out, -thick1_rib)
                Coords_Hstiff_Bot = DefMath.Offset_Face(Coords_Hstiff_Out, thick2_rib)
                solid_Hstiff = DefIFC.Create_brep_from_box_points(ifc_file, Coords_Hstiff_Top, Coords_Hstiff_Bot)

            # ------------Corner cut-------------------------------
            if not pd.isnull(corner1) and corner1 != "N":
                pcorner = Coords_Hstiff_Out[0][0]
                pdirX = Coords_Hstiff_Out[0][1]
                pdirY = Coords_Hstiff_Out[1][0]
                solid_corner = Draw_Corner(ifc_file, corner1, pcorner, pdirX, pdirY)

                solid_Hstiff = ifc_file.createIfcBooleanResult("DIFFERENCE", solid_Hstiff, solid_corner)

            if not pd.isnull(corner2) and corner2 != "N":
                pcorner = Coords_Hstiff_Out[0][-1]
                pdirX = Coords_Hstiff_Out[0][-2]
                pdirY = Coords_Hstiff_Out[1][-1]
                solid_corner = Draw_Corner(ifc_file, corner2, pcorner, pdirX, pdirY)

                solid_Hstiff = ifc_file.createIfcBooleanResult("DIFFERENCE", solid_Hstiff, solid_corner)

            if not pd.isnull(corner3) and corner3 != "N":
                pcorner = Coords_Hstiff_Out[-1][0]
                pdirX = Coords_Hstiff_Out[-1][1]
                pdirY = Coords_Hstiff_Out[-2][0]
                solid_corner = Draw_Corner(ifc_file, corner3, pcorner, pdirX, pdirY)

                solid_Hstiff = ifc_file.createIfcBooleanResult("DIFFERENCE", solid_Hstiff, solid_corner)

            if not pd.isnull(corner4) and corner4 != "N":
                pcorner = Coords_Hstiff_Out[-1][-1]
                pdirX = Coords_Hstiff_Out[-1][-2]
                pdirY = Coords_Hstiff_Out[-2][-1]
                solid_corner = Draw_Corner(ifc_file, corner4, pcorner, pdirX, pdirY)

                solid_Hstiff = ifc_file.createIfcBooleanResult("DIFFERENCE", solid_Hstiff, solid_corner)

            color_style = DefIFC.create_color(ifc_file, 164.0, 206.0, 218.0)
            styled_item = ifc_file.createIfcStyledItem(Item=solid_Hstiff, Styles=[color_style])
            shape_representation = ifc_file.createIfcShapeRepresentation(
                ContextOfItems=geom_context,
                RepresentationIdentifier="Body",
                RepresentationType="Brep",
                Items=[solid_Hstiff],
            )
            DefIFC.Add_shape_representation_in_Beam(ifc_file, bridge_span, shape_representation, name_hstiff[i])


# ---------------------------Calculate_Vstiff（垂直補剛材計算）---------------------------------------------------------------------------------------------
def Calculate_Vstiff(
    ifc_all,
    Data_Panel,
    Senkei_data,
    Mem_Rib_data,
    name_panel,
    infor_vstiff,
    arCoord_mod_panel,
    sec_panel,
    thick1_panel,
    thick2_panel,
):
    """
    垂直補剛材（Vstiff）を計算して描画する

    垂直補剛材の位置、サイズ、形状を計算し、IFCソリッドとして生成する。
    コーナーカットなどの処理も含む。

    Args:
        ifc_all: (ifc_file, bridge_span, geom_context)のタプル
        Data_Panel: パネルデータ
        Senkei_data: 線形データ
        Mem_Rib_data: リブメンバーデータ
        name_panel: パネル名
        infor_vstiff: 補剛材情報（線、点、面、名称、参照など）
        arCoord_mod_panel: パネルの修正座標
        sec_panel: パネルの断面名称リスト
        thick1_panel: パネルの厚さ1
        thick2_panel: パネルの厚さ2
    """

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
            if side == "L":
                arCoord_Base_Offset = DefMath.Offset_Face(arCoord_mod_panel, -thick1_panel)
            elif side == "R":
                arCoord_Base_Offset = DefMath.Offset_Face(arCoord_mod_panel, thick2_panel)

            index = sec_panel.index(name_point_line_vstiff[i])
            P1Mod = arCoord_Base_Offset[0][index]
            P2Mod = arCoord_Base_Offset[-1][index]

            if DefMath.is_number(extendT_rib) == True:
                p = DefMath.Point_on_line(P1Mod, P2Mod, -extendT_rib)
                P1Mod = p
            elif extendT_rib == "Auto":
                P1Mod, P2Mod = Extend_Vstiff_Auto_Face_FLG(Data_Panel, Senkei_data, name_panel, P1Mod, P2Mod, "T")

            if DefMath.is_number(extendB_rib) == True:
                p = DefMath.Point_on_line(P2Mod, P1Mod, -extendB_rib)
                P2Mod = p
            elif extendB_rib == "Auto":
                P1Mod, P2Mod = Extend_Vstiff_Auto_Face_FLG(Data_Panel, Senkei_data, name_panel, P1Mod, P2Mod, "B")

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

            # -----------Create Solid-------------------------------
            Solid_Vstiff = Draw_3DSolid_Vstiff(
                ifc_file,
                DefMath.Calculate_distance_p2p(P1Mod, P2Mod),
                height_rib,
                thick1_rib,
                thick2_rib,
                side,
                p1al,
                p2al,
                p3al,
            )

            # ------------Corner cut-------------------------------
            if not pd.isnull(corner1) and corner1 != "N":
                pcorner = P1Mod
                pdirX = P3Mod
                pdirY = P2Mod
                solid_corner = Draw_Corner(ifc_file, corner1, pcorner, pdirX, pdirY)

                Solid_Vstiff = ifc_file.createIfcBooleanResult("DIFFERENCE", Solid_Vstiff, solid_corner)

            if not pd.isnull(corner2) and corner2 != "N":
                pcorner = P2Mod
                pdirX = P4Mod
                pdirY = P1Mod
                solid_corner = Draw_Corner(ifc_file, corner2, pcorner, pdirX, pdirY)

                Solid_Vstiff = ifc_file.createIfcBooleanResult("DIFFERENCE", Solid_Vstiff, solid_corner)

            if not pd.isnull(corner3) and corner3 != "N":
                pcorner = P3Mod
                pdirX = P1Mod
                pdirY = P4Mod
                solid_corner = Draw_Corner(ifc_file, corner3, pcorner, pdirX, pdirY)

                Solid_Vstiff = ifc_file.createIfcBooleanResult("DIFFERENCE", Solid_Vstiff, solid_corner)

            if not pd.isnull(corner4) and corner4 != "N":
                pcorner = P4Mod
                pdirX = P2Mod
                pdirY = P3Mod
                solid_corner = Draw_Corner(ifc_file, corner4, pcorner, pdirX, pdirY)

                Solid_Vstiff = ifc_file.createIfcBooleanResult("DIFFERENCE", Solid_Vstiff, solid_corner)

            color_style = DefIFC.create_color(ifc_file, 164.0, 206.0, 218.0)
            styled_item = ifc_file.createIfcStyledItem(Item=Solid_Vstiff, Styles=[color_style])
            shape_representation = ifc_file.createIfcShapeRepresentation(
                ContextOfItems=geom_context,
                RepresentationIdentifier="Body",
                RepresentationType="Brep",
                Items=[Solid_Vstiff],
            )
            DefIFC.Add_shape_representation_in_Beam(ifc_file, bridge_span, shape_representation, name_vstiff[i])


# ---------------------------Calculate_LRib（縦リブ計算）---------------------------------------------------------------------------------------------
def Calculate_LRib(
    ifc_all,
    Mem_Rib_data,
    Member_SPL_data,
    infor_lrib,
    arCoordGrid_LRib,
    linesGrid,
    secsGrid,
    thick1_panel,
    thick2_panel,
):
    """
    Long Rib（縦リブ）を計算して描画する

    縦リブの位置、サイズ、形状を計算し、IFCソリッドとして生成する。
    参照リブの情報を使用してリブの形状を決定する。

    Args:
        ifc_all: (ifc_file, bridge_span, geom_context)のタプル
        Mem_Rib_data: リブメンバーデータ
        Member_SPL_data: メンバーSPLデータ
        infor_lrib: 縦リブ情報（線、点、面、名称、参照など）
        arCoordGrid_LRib: 縦リブの座標グリッド
        linesGrid: 線のグリッドリスト
        secsGrid: 断面のグリッドリスト
        thick1_panel: パネルの厚さ1
        thick2_panel: パネルの厚さ2
    """

    ifc_file, bridge_span, geom_context = ifc_all

    name_point_line_lrib, name_point_sec_lrib, face_lrib, name_lrib, name_ref_lrib = (
        infor_lrib["Line"],
        infor_lrib["Point"],
        infor_lrib["Face"],
        infor_lrib["Name"],
        infor_lrib["Ref"],
    )
    name_point_line_lrib = DefStrings.Chuyen_Name_LRib_thanh_Array(name_point_line_lrib)
    name_lrib = DefStrings.Chuyen_Name_LRib_thanh_Array(name_lrib)
    name_point_sec_lrib = name_point_sec_lrib.split("-")

    # --------参照リブ----------------------------------------
    for rib in Mem_Rib_data:
        if rib["Name"] == name_ref_lrib:
            infor = rib["Infor"]
            ang = rib["Ang"]
            extend = rib["Extend"]
            corner = rib["Corner"]
            spl_s = rib["JointS"]
            spl_e = rib["JointE"]
            break

    thick1_rib, thick2_rib, mat_rib, height_rib = infor["Thick1"], infor["Thick2"], infor["Mat"], infor["Width"]
    angs_rib, ange_rib, anga_rib = ang
    extendL_rib, extendR_rib, extendT_rib, extendB_rib = extend
    corner1, corner2, corner3, corner4 = corner
    # --------------------------------------------------------------
    if DefMath.is_number(thick1_rib) == True:
        # リブの配置
        for i in range(len(name_point_line_lrib)):
            indices_SecLines_LRib = []
            for i_1 in range(secsGrid.index(name_point_sec_lrib[0]), secsGrid.index(name_point_sec_lrib[1]) + 1):
                indices_SecLines_LRib.append(i_1)

            Coords_LRib_Mod1 = []
            arCoord1 = []
            arCoord2 = []
            for i_2 in range(0, len(indices_SecLines_LRib)):
                arCoor1 = arCoordGrid_LRib[linesGrid.index(name_point_line_lrib[i]) + 1]
                arCoor2 = arCoordGrid_LRib[linesGrid.index(name_point_line_lrib[i]) + 2]
                arCoord1.append(arCoor1[indices_SecLines_LRib[i_2]])
                arCoord2.append(arCoor2[indices_SecLines_LRib[i_2]])
            Coords_LRib_Mod1.append(arCoord1)
            Coords_LRib_Mod1.append(arCoord2)
            if face_lrib == "B":
                Coords_LRib_Mod1 = DefMath.Offset_Face(Coords_LRib_Mod1, -thick2_panel)
            elif face_lrib == "T":
                Coords_LRib_Mod1 = DefMath.Offset_Face(Coords_LRib_Mod1, thick1_panel)

            if face_lrib == "B":
                Coords_LRib_Mod2 = DefMath.Offset_Face(Coords_LRib_Mod1, -height_rib)
            elif face_lrib == "T":
                Coords_LRib_Mod2 = DefMath.Offset_Face(Coords_LRib_Mod1, height_rib)

            Coords_LRib_Mod = []
            if face_lrib == "B":
                arCoor1 = Coords_LRib_Mod1[0]
                arCoor2 = Coords_LRib_Mod2[0]
                for i_1 in range(1, len(arCoor2)):
                    pp = DefMath.point_per_plan(arCoor2[i_1], arCoor1[i_1 - 1], arCoor1[i_1], arCoor2[i_1 - 1])
                    arCoor2[i_1] = pp
                Coords_LRib_Mod.append(arCoor1)
                Coords_LRib_Mod.append(arCoor2)
            elif face_lrib == "T":
                arCoor1 = Coords_LRib_Mod2[0]
                arCoor2 = Coords_LRib_Mod1[0]
                for i_1 in range(1, len(arCoor2)):
                    pp = DefMath.point_per_plan(arCoor1[i_1], arCoor2[i_1 - 1], arCoor2[i_1], arCoor1[i_1 - 1])
                    arCoor1[i_1] = pp
                Coords_LRib_Mod.append(arCoor1)
                Coords_LRib_Mod.append(arCoor2)

            # -----------Extend-------------------------------
            Coords_LRib_Out = Coords_LRib_Mod.copy()
            if DefMath.is_number(extendL_rib) == True:
                Coords_LRib_Out = Calculate_Extend_Coord(Coords_LRib_Out, extendL_rib, "A")

            if DefMath.is_number(extendR_rib) == True:
                Coords_LRib_Out = Calculate_Extend_Coord(Coords_LRib_Out, extendR_rib, "F")

            # -----------Create Solid-------------------------------
            Coords_LRib_Left = DefMath.Offset_Face(Coords_LRib_Out, -thick1_rib)
            Coords_LRib_Right = DefMath.Offset_Face(Coords_LRib_Out, thick2_rib)

            solid_rib = DefIFC.Create_brep_from_box_points(ifc_file, Coords_LRib_Left, Coords_LRib_Right)

            # ------------Corner cut-------------------------------
            if not pd.isnull(corner1) and corner1 != "N":
                pcorner = Coords_LRib_Out[0][0]
                pdirX = Coords_LRib_Out[0][1]
                pdirY = Coords_LRib_Out[1][0]
                solid_corner = Draw_Corner(ifc_file, corner1, pcorner, pdirX, pdirY)

                solid_rib = ifc_file.createIfcBooleanResult("DIFFERENCE", solid_rib, solid_corner)

            if not pd.isnull(corner2) and corner2 != "N":
                pcorner = Coords_LRib_Out[0][-1]
                pdirX = Coords_LRib_Out[0][-2]
                pdirY = Coords_LRib_Out[1][-1]
                solid_corner = Draw_Corner(ifc_file, corner2, pcorner, pdirX, pdirY)

                solid_rib = ifc_file.createIfcBooleanResult("DIFFERENCE", solid_rib, solid_corner)

            if not pd.isnull(corner3) and corner3 != "N":
                pcorner = Coords_LRib_Out[-1][0]
                pdirX = Coords_LRib_Out[-1][1]
                pdirY = Coords_LRib_Out[-2][0]
                solid_corner = Draw_Corner(ifc_file, corner3, pcorner, pdirX, pdirY)

                solid_rib = ifc_file.createIfcBooleanResult("DIFFERENCE", solid_rib, solid_corner)

            if not pd.isnull(corner4) and corner4 != "N":
                pcorner = Coords_LRib_Out[-1][-1]
                pdirX = Coords_LRib_Out[-1][-2]
                pdirY = Coords_LRib_Out[-2][-1]
                solid_corner = Draw_Corner(ifc_file, corner4, pcorner, pdirX, pdirY)

                solid_rib = ifc_file.createIfcBooleanResult("DIFFERENCE", solid_rib, solid_corner)

            # ----------------SPL FLG（スプリットプレート・フランジ）-------------------------------
            if spl_s:
                for i_1 in range(len(spl_s)):
                    solid_rib = Calculate_SPL_Rib(
                        ifc_all,
                        Member_SPL_data,
                        Coords_LRib_Mod[0][0],
                        Coords_LRib_Mod[-1][0],
                        Coords_LRib_Mod[0][-1],
                        spl_s[i_1],
                        "S",
                        thick1_rib,
                        thick2_rib,
                        solid_rib,
                    )

            if spl_e:
                for i_1 in range(len(spl_e)):
                    solid_rib = Calculate_SPL_Rib(
                        ifc_all,
                        Member_SPL_data,
                        Coords_LRib_Mod[0][-1],
                        Coords_LRib_Mod[-1][-1],
                        Coords_LRib_Mod[0][0],
                        spl_e[i_1],
                        "E",
                        thick1_rib,
                        thick2_rib,
                        solid_rib,
                    )

            # ---------------------add color for solid-------------------------------
            color_style = DefIFC.create_color(ifc_file, 175.0, 248.0, 235.0)
            styled_item = ifc_file.createIfcStyledItem(Item=solid_rib, Styles=[color_style])
            shape_representation = ifc_file.createIfcShapeRepresentation(
                ContextOfItems=geom_context,
                RepresentationIdentifier="Body",
                RepresentationType="Brep",
                Items=[solid_rib],
            )
            DefIFC.Add_shape_representation_in_Beam(ifc_file, bridge_span, shape_representation, name_lrib[i])
    else:
        # shape rib
        atc_thick1 = thick1_rib.split("x")
        if len(atc_thick1) == 3:
            # U Rib
            for i in range(len(name_point_line_lrib)):
                indices_SecLines_LRib = []
                for i_1 in range(secsGrid.index(name_point_sec_lrib[0]), secsGrid.index(name_point_sec_lrib[1]) + 1):
                    indices_SecLines_LRib.append(i_1)
                Coords_LRib_Mod1 = []
                arCoord1 = []
                arCoord2 = []
                for i_2 in range(0, len(indices_SecLines_LRib)):
                    arCoor1 = arCoordGrid_LRib[linesGrid.index(name_point_line_lrib[i]) + 1]
                    arCoor2 = arCoordGrid_LRib[linesGrid.index(name_point_line_lrib[i]) + 2]
                    arCoord1.append(arCoor1[indices_SecLines_LRib[i_2]])
                    arCoord2.append(arCoor2[indices_SecLines_LRib[i_2]])
                Coords_LRib_Mod1.append(arCoord1)
                Coords_LRib_Mod1.append(arCoord2)
                if face_lrib == "B":
                    Coords_LRib_Mod1 = DefMath.Offset_Face(Coords_LRib_Mod1, -thick2_panel)
                elif face_lrib == "T":
                    Coords_LRib_Mod1 = DefMath.Offset_Face(Coords_LRib_Mod1, thick1_panel)

                Coords_LRib_Mod = Coords_LRib_Mod1[0]

                # -----------Extend-------------------------------
                Coords_LRib_Out = Coords_LRib_Mod.copy()
                if DefMath.is_number(extendL_rib) == True:
                    Coords_LRib_Out[0] = DefMath.Point_on_line(Coords_LRib_Out[0], Coords_LRib_Out[1], -extendL_rib)

                if DefMath.is_number(extendR_rib) == True:
                    Coords_LRib_Out[-1] = DefMath.Point_on_line(Coords_LRib_Out[-1], Coords_LRib_Out[-2], -extendR_rib)

                # ----------------SPL FLG（スプリットプレート・フランジ）-------------------------------
                if spl_s:
                    for i_1 in range(len(spl_s)):
                        solid_rib = Calculate_SPL_Rib(
                            ifc_all,
                            Member_SPL_data,
                            Coords_LRib_Mod[0][0],
                            Coords_LRib_Mod[-1][0],
                            Coords_LRib_Mod[0][-1],
                            spl_s[i_1],
                            "S",
                            thick1_rib,
                            thick2_rib,
                            solid_rib,
                        )

                if spl_e:
                    for i_1 in range(len(spl_e)):
                        solid_rib = Calculate_SPL_Rib(
                            ifc_all,
                            Member_SPL_data,
                            Coords_LRib_Mod[0][-1],
                            Coords_LRib_Mod[-1][-1],
                            Coords_LRib_Mod[0][0],
                            spl_e[i_1],
                            "E",
                            thick1_rib,
                            thick2_rib,
                            solid_rib,
                        )

                ang_deck = DefMath.Angle_between_vectors(
                    Coords_LRib_Mod1[0][0],
                    Coords_LRib_Mod1[1][0],
                    (Coords_LRib_Mod1[0][0][0], Coords_LRib_Mod1[0][0][1], Coords_LRib_Mod1[0][0][2] - 100),
                )
                ang_deck_degre = math.degrees(ang_deck)
                arCoor_profile = DefMath.profile2D_Urib(thick1_rib, [0, 0])
                arcoord_profile = DefMath.rotate_points(arCoor_profile, (0, 0), -ang_deck_degre)
                solid_rib = DefIFC.sweep_profile_along_polyline(ifc_file, arcoord_profile, Coords_LRib_Out)

                color_style = DefIFC.create_color(ifc_file, 175.0, 248.0, 235.0)
                styled_item = ifc_file.createIfcStyledItem(Item=solid_rib, Styles=[color_style])
                shape_representation = ifc_file.createIfcShapeRepresentation(
                    ContextOfItems=geom_context,
                    RepresentationIdentifier="Body",
                    RepresentationType="Brep",
                    Items=[solid_rib],
                )
                DefIFC.Add_shape_representation_in_Beam(ifc_file, bridge_span, shape_representation, name_lrib[i])


# ---------------------------Calculate_SPL（SPL計算）---------------------------------------------------------------------------------------------
def Calculate_SPL(
    ifc_all,
    MainPanel_data,
    Member_SPL_data,
    SPL_Longnames,
    SPL_Secnames,
    SPL_Pitch,
    posJoint,
    arCoord_Mod,
    Longnames,
    Secnames,
    NamePanel,
    Solid_Panel,
):
    ifc_file, bridge_span, geom_context = ifc_all

    for panel in MainPanel_data:
        if panel["Name"] == NamePanel:
            Line_panel = panel["Line"]
            Sec_panel = panel["Sec"]
            Type_panel = panel["Type"]
            Mat_panel = panel["Material"]
            Expand_panel = panel["Expand"]
            break

    Thick1PA, Thick2PA, MatPA = Mat_panel["Thick1"], Mat_panel["Thick2"], Mat_panel["Mat"]
    type_PA = Type_panel["TypePanel"]

    n = Secnames.index(SPL_Secnames)
    SPL_Longnames = SPL_Longnames.split("-")
    m1 = Longnames.index(SPL_Longnames[0])
    m2 = Longnames.index(SPL_Longnames[1])

    pj1 = arCoord_Mod[m1][n]
    pj2 = arCoord_Mod[m2][n]
    pj1_2d = [0, 0]
    pj2_2d = [0, 0]
    pj1_2d[0] = 0
    pj1_2d[1] = 0
    pj2_2d[0] = 0
    pj2_2d[1] = -DefMath.Calculate_distance_p2p(pj1, pj2)

    SPL_Pitch_New = Calculate_X_SPL_Pitch(SPL_Pitch, DefMath.Calculate_distance_p2p(pj1, pj2), Member_SPL_data, 1)

    arSPL_Pitch = SPL_Pitch.split("/")
    arSPL_Pitch_New = SPL_Pitch_New.split("/")

    Pbase_SPL = [0, 0]
    Pbase_SPL[0] = pj1_2d[0]
    Pbase_SPL[1] = pj1_2d[1]
    for i in range(0, len(arSPL_Pitch)):
        if arSPL_Pitch[i] != "X" and DefMath.is_number(arSPL_Pitch[i]) == False:
            NameSPL = arSPL_Pitch[i]
            for spl in Member_SPL_data:
                if spl["Name"] == NameSPL:
                    infor = spl["Infor"]
                    pitchj = spl["PJ"]
                    pitchl = spl["PL"]
                    pitchr = spl["PR"]
                    out = spl["Out"]
                    dhole = spl["Dhole"]
                    solid = spl["Solid"]
                    result = infor, pitchj, pitchl, pitchr, out, dhole, solid
                    Thick, Mat, Side, Angle, Gline = (
                        infor["Thick"],
                        infor["Mat"],
                        infor["Side"],
                        infor["Ang"],
                        infor["GLine"],
                    )
                    break
            if solid:
                if solid[0] == "A" and posJoint == "E":
                    if Side == "T":
                        pj1_3D = DefMath.Offset_point(pj1, pj2, arCoord_Mod[m1][n - 1], -Thick1PA)
                        pj2_3D = DefMath.Offset_point(pj2, pj1, arCoord_Mod[m1][n - 1], Thick1PA)
                        pj3_3D = DefMath.Offset_point(arCoord_Mod[m1][n - 1], pj1, pj2, -Thick1PA)
                    elif Side == "B":
                        pj1_3D = DefMath.Offset_point(pj1, pj2, arCoord_Mod[m1][n - 1], Thick2PA)
                        pj2_3D = DefMath.Offset_point(pj2, pj1, arCoord_Mod[m1][n - 1], -Thick2PA)
                        pj3_3D = DefMath.Offset_point(arCoord_Mod[m1][n - 1], pj1, pj2, Thick2PA)
                    elif Side == "L":
                        pj1_3D = DefMath.Offset_point(pj1, pj2, arCoord_Mod[m1][n - 1], Thick1PA)
                        pj2_3D = DefMath.Offset_point(pj2, pj1, arCoord_Mod[m1][n - 1], -Thick1PA)
                        pj3_3D = DefMath.Offset_point(arCoord_Mod[m1][n - 1], pj1, pj2, Thick1PA)
                    elif Side == "R":
                        pj1_3D = DefMath.Offset_point(pj1, pj2, arCoord_Mod[m1][n - 1], -Thick2PA)
                        pj2_3D = DefMath.Offset_point(pj2, pj1, arCoord_Mod[m1][n - 1], Thick2PA)
                        pj3_3D = DefMath.Offset_point(arCoord_Mod[m1][n - 1], pj1, pj2, -Thick2PA)

                    pal1 = [0, 0, 0]
                    pal1[0] = pj1_3D[0]
                    pal1[1] = pj1_3D[1]
                    pal1[2] = pj1_3D[2]
                    pal2 = DefMath.Offset_point(pj1_3D, pj2_3D, pj3_3D, -100)
                    pal3 = DefMath.Offset_point(pj1_3D, pj2_3D, pal2, -100)

                    solidspl = Draw_3DSolid_SPL(ifc_all, Pbase_SPL, result, arSPL_Pitch_New[i], pal1, pal2, pal3)

                    if solid[1] == "HY":
                        Solid_Hole_SPL = Draw_Solid_Hole_SPL(
                            ifc_all, Pbase_SPL, result, arSPL_Pitch_New[i], pal1, pal2, pal3
                        )
                        if Solid_Hole_SPL:
                            for Solid_Hole in Solid_Hole_SPL:
                                solidspl = ifc_file.createIfcBooleanResult("DIFFERENCE", solidspl, Solid_Hole)

                    color_style = DefIFC.create_color(ifc_file, 206.0, 220.0, 163.0)
                    styled_item = ifc_file.createIfcStyledItem(Item=solidspl, Styles=[color_style])
                    shape_representation = ifc_file.createIfcShapeRepresentation(
                        ContextOfItems=geom_context,
                        RepresentationIdentifier="Body",
                        RepresentationType="Brep",
                        Items=[solidspl],
                    )
                    DefIFC.Add_shape_representation_in_Beam(ifc_file, bridge_span, shape_representation, NameSPL)

                elif solid[0] == "F" and posJoint == "S":
                    if Side == "T":
                        pj1_3D = DefMath.Offset_point(pj1, pj2, arCoord_Mod[m1][n + 1], Thick1PA)
                        pj2_3D = DefMath.Offset_point(pj2, pj1, arCoord_Mod[m1][n + 1], -Thick1PA)
                        pj3_3D = DefMath.Offset_point(arCoord_Mod[m1][n + 1], pj1, pj2, Thick1PA)
                    elif Side == "B":
                        pj1_3D = DefMath.Offset_point(pj1, pj2, arCoord_Mod[m1][n + 1], -Thick2PA)
                        pj2_3D = DefMath.Offset_point(pj2, pj1, arCoord_Mod[m1][n + 1], Thick2PA)
                        pj3_3D = DefMath.Offset_point(arCoord_Mod[m1][n + 1], pj1, pj2, -Thick2PA)
                    elif Side == "L":
                        pj1_3D = DefMath.Offset_point(pj1, pj2, arCoord_Mod[m1][n + 1], -Thick1PA)
                        pj2_3D = DefMath.Offset_point(pj2, pj1, arCoord_Mod[m1][n + 1], Thick1PA)
                        pj3_3D = DefMath.Offset_point(arCoord_Mod[m1][n + 1], pj1, pj2, -Thick1PA)
                    elif Side == "R":
                        pj1_3D = DefMath.Offset_point(pj1, pj2, arCoord_Mod[m1][n + 1], Thick2PA)
                        pj2_3D = DefMath.Offset_point(pj2, pj1, arCoord_Mod[m1][n + 1], -Thick2PA)
                        pj3_3D = DefMath.Offset_point(arCoord_Mod[m1][n + 1], pj1, pj2, Thick2PA)

                    pal1 = [0, 0, 0]
                    pal1[0] = pj1_3D[0]
                    pal1[1] = pj1_3D[1]
                    pal1[2] = pj1_3D[2]
                    pal2 = DefMath.Offset_point(pj1_3D, pj2_3D, pj3_3D, 100)
                    pal3 = DefMath.Offset_point(pj1_3D, pj2_3D, pal2, -100)

                    solidspl = Draw_3DSolid_SPL(ifc_all, Pbase_SPL, result, arSPL_Pitch_New[i], pal1, pal2, pal3)
                    if solid[1] == "HY":
                        Solid_Hole_SPL = Draw_Solid_Hole_SPL(
                            ifc_all, Pbase_SPL, result, arSPL_Pitch_New[i], pal1, pal2, pal3
                        )
                        if Solid_Hole_SPL:
                            for Solid_Hole in Solid_Hole_SPL:
                                solidspl = ifc_file.createIfcBooleanResult("DIFFERENCE", solidspl, Solid_Hole)

                    color_style = DefIFC.create_color(ifc_file, 206.0, 220.0, 163.0)
                    styled_item = ifc_file.createIfcStyledItem(Item=solidspl, Styles=[color_style])
                    shape_representation = ifc_file.createIfcShapeRepresentation(
                        ContextOfItems=geom_context,
                        RepresentationIdentifier="Body",
                        RepresentationType="Brep",
                        Items=[solidspl],
                    )
                    DefIFC.Add_shape_representation_in_Beam(ifc_file, bridge_span, shape_representation, NameSPL)

                if solid[1] == "HY":
                    if posJoint == "S":
                        pal1 = [0, 0, 0]
                        pal1[0] = pj1[0]
                        pal1[1] = pj1[1]
                        pal1[2] = pj1[2]
                        pal2 = DefMath.Offset_point(pj1, pj2, arCoord_Mod[m1][n + 1], 100)
                        pal3 = DefMath.Offset_point(pj1, pj2, pal2, -100)
                        Solid_Hole_SPL = Draw_Solid_Hole_SPL(
                            ifc_all, Pbase_SPL, result, arSPL_Pitch_New[i], pal1, pal2, pal3, "S"
                        )

                        if Solid_Hole_SPL:
                            for Solid_Hole in Solid_Hole_SPL:
                                Solid_Panel = ifc_file.createIfcBooleanResult("DIFFERENCE", Solid_Panel, Solid_Hole)

                    elif posJoint == "E":
                        pal1 = [0, 0, 0]
                        pal1[0] = pj1[0]
                        pal1[1] = pj1[1]
                        pal1[2] = pj1[2]
                        pal2 = DefMath.Offset_point(pj1, pj2, arCoord_Mod[m1][n - 1], -100)
                        pal3 = DefMath.Offset_point(pj1, pj2, pal2, -100)
                        Solid_Hole_SPL = Draw_Solid_Hole_SPL(
                            ifc_all, Pbase_SPL, result, arSPL_Pitch_New[i], pal1, pal2, pal3, "E"
                        )
                        if Solid_Hole_SPL:
                            for Solid_Hole in Solid_Hole_SPL:
                                Solid_Panel = ifc_file.createIfcBooleanResult("DIFFERENCE", Solid_Panel, Solid_Hole)

                elif solid[1] == "BY":
                    if type_PA == "WL":
                        gap_cen_to_head = -Thick1PA - Thick
                        gap_cen_to_nut = -Thick2PA - Thick
                    elif type_PA == "WR" or type_PA == "W":
                        gap_cen_to_head = Thick2PA + Thick
                        gap_cen_to_nut = Thick1PA + Thick
                    else:
                        gap_cen_to_head = Thick1PA + Thick
                        gap_cen_to_nut = Thick2PA + Thick

                    if posJoint == "S":
                        pal1 = [0, 0, 0]
                        pal1[0] = pj1[0]
                        pal1[1] = pj1[1]
                        pal1[2] = pj1[2]
                        pal2 = DefMath.Offset_point(pj1, pj2, arCoord_Mod[m1][n + 1], 100)
                        pal3 = DefMath.Offset_point(pj1, pj2, pal2, -100)

                        Solid_Hole_SPL = Draw_Solid_Bolt_SPL(
                            ifc_all,
                            Pbase_SPL,
                            result,
                            arSPL_Pitch_New[i],
                            gap_cen_to_head,
                            gap_cen_to_nut,
                            pal1,
                            pal2,
                            pal3,
                            "S",
                        )
                        if Solid_Hole_SPL:
                            for Solid_Hole in Solid_Hole_SPL:
                                shape_representation = ifc_file.createIfcShapeRepresentation(
                                    ContextOfItems=geom_context,
                                    RepresentationIdentifier="Body",
                                    RepresentationType="Brep",
                                    Items=[Solid_Hole],
                                )
                                DefIFC.Add_shape_representation_in_Beam(
                                    ifc_file, bridge_span, shape_representation, "Bolt"
                                )

                    elif posJoint == "E":
                        pal1 = [0, 0, 0]
                        pal1[0] = pj1[0]
                        pal1[1] = pj1[1]
                        pal1[2] = pj1[2]
                        pal2 = DefMath.Offset_point(pj1, pj2, arCoord_Mod[m1][n - 1], -100)
                        pal3 = DefMath.Offset_point(pj1, pj2, pal2, -100)
                        Solid_Hole_SPL = Draw_Solid_Bolt_SPL(
                            ifc_all,
                            Pbase_SPL,
                            result,
                            arSPL_Pitch_New[i],
                            gap_cen_to_head,
                            gap_cen_to_nut,
                            pal1,
                            pal2,
                            pal3,
                            "E",
                        )
                        if Solid_Hole_SPL:
                            for Solid_Hole in Solid_Hole_SPL:
                                shape_representation = ifc_file.createIfcShapeRepresentation(
                                    ContextOfItems=geom_context,
                                    RepresentationIdentifier="Body",
                                    RepresentationType="Brep",
                                    Items=[Solid_Hole],
                                )
                                DefIFC.Add_shape_representation_in_Beam(
                                    ifc_file, bridge_span, shape_representation, "Bolt"
                                )

            # -----------------------------------------------------------------
            pbase = [0, 0, 0]
            pbase[0] = Pbase_SPL[0]
            pbase[1] = Pbase_SPL[1]
            pbase[2] = 0
            p1 = [0, 0, 0]
            p1[0] = pj1_2d[0]
            p1[1] = pj1_2d[1]
            p1[2] = 0
            p2 = [0, 0, 0]
            p2[0] = pj2_2d[0]
            p2[1] = pj2_2d[1]
            p2[2] = 0
            Angle = Angle.split("/")

            if Gline == "O":
                p = DefMath.Point_on_line(pbase, p2, float(arSPL_Pitch_New[i]) / abs(cos(Angle[0] * pi / 180 - pi / 2)))
            else:
                p = DefMath.Point_on_line(pbase, p2, float(arSPL_Pitch_New[i]))

            Pbase_SPL[0] = p[0]
            Pbase_SPL[1] = p[1]
        else:
            pbase = [0, 0, 0]
            pbase[0] = Pbase_SPL[0]
            pbase[1] = Pbase_SPL[1]
            pbase[2] = 0
            p1 = [0, 0, 0]
            p1[0] = pj1_2d[0]
            p1[1] = pj1_2d[1]
            p1[2] = 0
            p2 = [0, 0, 0]
            p2[0] = pj2_2d[0]
            p2[1] = pj2_2d[1]
            p2[2] = 0
            p = DefMath.Point_on_line(pbase, p2, float(arSPL_Pitch_New[i]))
            Pbase_SPL[0] = p[0]
            Pbase_SPL[1] = p[1]

    return Solid_Panel
