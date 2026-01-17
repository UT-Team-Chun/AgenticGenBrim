"""
鋼橋IFCモデル生成 - ユーティリティ関数モジュール
座標読み込み、線形計算、拡張計算などの共通ユーティリティ関数
"""

from src.bridge_json_to_ifc.ifc_utils_new.core import DefMath
from src.bridge_json_to_ifc.ifc_utils_new.io import DefStrings
import copy
import math
import numpy as np

# グローバル変数: ログファイル出力関数（DefBridge.pyから設定される）
log_print_func = None


def _log_print(*args, **kwargs):
    """ログファイル出力関数（DEBUG_MODE時のみ出力）"""
    if log_print_func:
        log_print_func(*args, **kwargs)


# ------------------------Calculate Line------------------------
def Calculate_Line(name_new_line, Calculations, Senkei_data):
    """
    計算線形を生成する（OFFSET、MID、Zなどの計算）

    Args:
        name_new_line: 新しい線形の名称
        Calculations: 計算処理の配列
        Senkei_data: 線形データ

    Returns:
        更新されたSenkei_data（新しい線形が追加される）
    """
    coord_polyline = []
    for calculation in Calculations:
        if calculation["Type"] == "OFFSET" or calculation["Type"] == "Z":
            typeCal = calculation["Type"]
            baseline = calculation["BaseLine"]
            distance = calculation["Distance"]
            coordLineBase = []
            for line in Senkei_data:
                if line["Name"] == baseline:
                    for point in line["Point"]:
                        coorpoint = [point["X"], point["Y"], point["Z"]]
                        coordLineBase.append(coorpoint)
                    break

            if typeCal == "OFFSET":
                coordLineNew = DefMath.Offset_Polyline(coordLineBase, distance)
                if coord_polyline:
                    for i in range(0, len(coordLineNew)):
                        coord_polyline[i][0] = coordLineNew[i][0]
                        coord_polyline[i][1] = coordLineNew[i][1]
                else:
                    for i in range(0, len(coordLineNew)):
                        coord_polyline.append(coordLineNew[i])

            elif typeCal == "Z":
                coordLineNew = []
                for i in range(0, len(coordLineBase)):
                    coordLineNew.append([coordLineBase[i][0], coordLineBase[i][1], coordLineBase[i][2] + distance])
                if coord_polyline:
                    for i in range(0, len(coordLineNew)):
                        coord_polyline[i][2] = coordLineNew[i][2]
                else:
                    for i in range(0, len(coordLineNew)):
                        coord_polyline.append(coordLineNew[i])

        elif calculation["Type"] == "MID":
            typeCal = calculation["Type"]
            baseline1 = calculation["BaseLine1"]
            baseline2 = calculation["BaseLine2"]
            baseline = baseline1
            coordLine1Base = []
            for line in Senkei_data:
                if line["Name"] == baseline1:
                    for point in line["Point"]:
                        coorpoint = [point["X"], point["Y"], point["Z"]]
                        coordLine1Base.append(coorpoint)
                    break

            coordLine2Base = []
            for line in Senkei_data:
                if line["Name"] == baseline2:
                    for point in line["Point"]:
                        coorpoint = [point["X"], point["Y"], point["Z"]]
                        coordLine2Base.append(coorpoint)
                    break

            coordLineNew = []
            for i in range(0, len(coordLine1Base)):
                x = (coordLine1Base[i][0] + coordLine2Base[i][0]) / 2
                y = (coordLine1Base[i][1] + coordLine2Base[i][1]) / 2
                z = (coordLine1Base[i][2] + coordLine2Base[i][2]) / 2
                coordLineNew.append([x, y, z])
            if coord_polyline:
                for i in range(0, len(coordLineNew)):
                    coord_polyline[i][2] = coordLineNew[i][2]
            else:
                for i in range(0, len(coordLineNew)):
                    coord_polyline.append(coordLineNew[i])

    arpoint_line_new = []
    for line in Senkei_data:
        if line["Name"] == name_new_line:
            for point in line["Point"]:
                arpoint_line_new.append(point["Name"])
            break

    if len(arpoint_line_new) == 0:
        for i in range(0, len(coord_polyline)):
            arpoint_line_new.append(f"P{i + 1}")

    arpoint_line_new_data = []
    for i in range(0, len(coord_polyline)):
        arpoint_line_new_data.append(
            {
                "Name": arpoint_line_new[i],
                "X": coord_polyline[i][0],
                "Y": coord_polyline[i][1],
                "Z": coord_polyline[i][2],
            }
        )

    line_new = {"Name": name_new_line, "Point": arpoint_line_new_data}
    Senkei_data.append(line_new)

    return Senkei_data


def Load_Coordinate_Panel(Senkei_data, line_panel, sec_panel):
    """
    パネルの座標を読み込む

    Args:
        Senkei_data: 線形データ
        line_panel: 線形名の配列
        sec_panel: 断面点名の配列

    Returns:
        座標線の配列（各線は点の配列）
    """
    coordLines = []
    for i in range(0, len(line_panel)):
        for line in Senkei_data:
            if line["Name"] == line_panel[i]:
                coordLine = []
                for i_1 in range(0, len(sec_panel)):
                    for point in line["Point"]:
                        if point["Name"] == sec_panel[i_1]:
                            coorpoint = [point["X"], point["Y"], point["Z"]]
                            coordLine.append(coorpoint)
                            break
                coordLines.append(coordLine)
                break

    return coordLines


def Load_Coordinate_Point(Senkei_data, NameLong, NameSec):
    """
    指定された線形名と断面点名から座標点を取得する

    Args:
        Senkei_data: 線形データ
        NameLong: 線形名
        NameSec: 断面点名

    Returns:
        座標点 [X, Y, Z] または None（見つからない場合）
    """
    CoordPoint = None
    for line in Senkei_data:
        if line["Name"] == NameLong:
            for point in line["Point"]:
                if point["Name"] == NameSec:
                    CoordPoint = [point["X"], point["Y"], point["Z"]]
                    break
            if CoordPoint is not None:
                break
    return CoordPoint


def Load_Coordinate_PolLine(Senkei_data, NameLong):
    """
    指定された線形名からポリライン座標を取得する

    Args:
        Senkei_data: 線形データ
        NameLong: 線形名

    Returns:
        座標点の配列
    """
    coordLine = []
    for line in Senkei_data:
        if line["Name"] == NameLong:
            for point in line["Point"]:
                coorpoint = [point["X"], point["Y"], point["Z"]]
                coordLine.append(coorpoint)
            break
    return coordLine


def Calculate_points_Sub_Panel(Senkei_data, points, NameSec):
    """
    サブパネルの点座標を計算する

    Args:
        Senkei_data: 線形データ
        points: 点定義の配列
        NameSec: 断面点名

    Returns:
        tuple: (arNamePoint, arCoordPoint)
            - arNamePoint: 点名称の配列
            - arCoordPoint: 座標点の配列
    """
    arNamePoint = []
    arCoordPoint = []
    for point in points:
        if len(point) == 2:
            arNamePoint.append(str(point[0]))
            CoorPoint = Load_Coordinate_Point(Senkei_data, point[1], NameSec)
            arCoordPoint.append(CoorPoint)
        else:
            if point[1] == "XYZ":
                arname = DefStrings.Chuyen_Name_LRib_thanh_Array(point[0])

                namep1 = str(point[2])
                if namep1 in arNamePoint:
                    index = arNamePoint.index(namep1)
                    p1 = arCoordPoint[index]
                else:
                    p1 = Load_Coordinate_Point(Senkei_data, namep1, NameSec)

                namep2 = str(point[3])
                if namep2 in arNamePoint:
                    index = arNamePoint.index(namep2)
                    p2 = arCoordPoint[index]
                else:
                    p2 = Load_Coordinate_Point(Senkei_data, namep2, NameSec)

                pitch = point[4]
                pitch = DefStrings.Xu_Ly_Pitch_va_Tim_X(pitch, DefMath.Calculate_distance_p2p(p1, p2))
                arpitch = pitch.split("/")
                distance = 0
                for i in range(len(arname)):
                    arNamePoint.append(str(arname[i]))
                    distance += float(arpitch[i])
                    p = DefMath.Point_on_line(p1, p2, distance)
                    arCoordPoint.append(p)
            elif point[1] == "XY":
                arname = DefStrings.Chuyen_Name_LRib_thanh_Array(point[0])

                namep1 = str(point[2])
                if namep1 in arNamePoint:
                    index = arNamePoint.index(namep1)
                    p1 = arCoordPoint[index]
                else:
                    p1 = Load_Coordinate_Point(Senkei_data, namep1, NameSec)

                namep2 = str(point[3])
                if namep2 in arNamePoint:
                    index = arNamePoint.index(namep2)
                    p2 = arCoordPoint[index]
                else:
                    p2 = Load_Coordinate_Point(Senkei_data, namep2, NameSec)

                p1_2d = p1.copy()
                p1_2d[2] = 0
                p2_2d = p2.copy()
                p2_2d[2] = 0

                pitch = point[4]
                pitch = DefStrings.Xu_Ly_Pitch_va_Tim_X(pitch, DefMath.Calculate_distance_p2p(p1_2d, p2_2d))
                arpitch = pitch.split("/")
                distance = 0
                for i in range(len(arname)):
                    arNamePoint.append(str(arname[i]))
                    distance += float(arpitch[i])
                    p = DefMath.Point_on_line(p1_2d, p2_2d, distance)
                    ppl1 = p.copy()
                    ppl2 = p.copy()
                    ppl2[0] += 100
                    ppl3 = p.copy()
                    ppl3[2] += 100

                    p = DefMath.Intersection_line_plane(ppl1, ppl2, ppl3, p1, p2)
                    arCoordPoint.append(p)
            elif point[1] == "ILP":
                NameLine = point[2]
                NamePlan = point[3]
                arPointPlan = NamePlan.split("-")
                coordLine = Load_Coordinate_PolLine(Senkei_data, NameLine)

                if str(arPointPlan[0]) in arNamePoint:
                    index = arNamePoint.index(str(arPointPlan[0]))
                    p1Plan = arCoordPoint[index]
                else:
                    p1Plan = Load_Coordinate_Point(Senkei_data, str(arPointPlan[0]), NameSec)

                if str(arPointPlan[1]) in arNamePoint:
                    index = arNamePoint.index(str(arPointPlan[1]))
                    p2Plan = arCoordPoint[index]
                else:
                    p2Plan = Load_Coordinate_Point(Senkei_data, str(arPointPlan[1]), NameSec)

                if str(arPointPlan[2]) in arNamePoint:
                    index = arNamePoint.index(str(arPointPlan[2]))
                    p3Plan = arCoordPoint[index]
                else:
                    p3Plan = Load_Coordinate_Point(Senkei_data, str(arPointPlan[2]), NameSec)

                for i in range(0, len(coordLine) - 1):
                    p1Line = coordLine[i]
                    p2Line = coordLine[i + 1]

                    p = DefMath.Intersection_plane_segment(p1Plan, p2Plan, p3Plan, p1Line, p2Line)
                    if p is not None:
                        arCoordPoint.append(p)
                        arNamePoint.append(str(point[0]))
                        break

    return arNamePoint, arCoordPoint


def Calculate_Extend(MainPanel_data, Senkei_data, name_panel, arCoordLines, ExtendA, ExtendF, ExtendT, ExtendB):
    """
    パネルの拡張座標を計算する

    Args:
        MainPanel_data: メインパネルデータ
        Senkei_data: 線形データ
        name_panel: パネル名
        arCoordLines: 座標線の配列
        ExtendA: 左側延長（数値または"A"）
        ExtendF: 右側延長（数値または"A"）
        ExtendT: 上側延長（数値または"A"）
        ExtendB: 下側延長（数値または"A"）

    Returns:
        拡張後の座標線の配列
    """
    arCoordLines_Base = copy.deepcopy(arCoordLines)
    arCoordLines_New = copy.deepcopy(arCoordLines)
    if DefMath.is_number(ExtendA) == True:
        arCoordLines_New = Calculate_Extend_Coord(arCoordLines_Base, ExtendA, "A")

    arCoordLines_Base = arCoordLines_New
    if DefMath.is_number(ExtendF) == True:
        arCoordLines_New = Calculate_Extend_Coord(arCoordLines_Base, ExtendF, "F")

    arCoordLines_Base = arCoordLines_New
    if DefMath.is_number(ExtendT) == True:
        arCoordLines_New = Calculate_Extend_Coord(arCoordLines_Base, ExtendT, "T")
    else:
        arCoordLines_New = Calculate_Coord_Face(MainPanel_data, Senkei_data, name_panel, arCoordLines_Base, "T")

    arCoordLines_Base = arCoordLines_New
    if DefMath.is_number(ExtendB) == True:
        arCoordLines_New = Calculate_Extend_Coord(arCoordLines_Base, ExtendB, "B")
    else:
        arCoordLines_New = Calculate_Coord_Face(MainPanel_data, Senkei_data, name_panel, arCoordLines_Base, "B")

    return arCoordLines_New


def Calculate_Extend_Coord(arCoordLines, Distance, Pos):
    """
    座標線を指定方向に延長する

    Args:
        arCoordLines: 座標線の配列
        Distance: 延長距離（mm）
        Pos: 延長方向（"A"=左、"F"=右、"T"=上、"B"=下、"L"=左、"R"=右）

    Returns:
        延長後の座標線の配列
    """
    arCoordLines_New = copy.deepcopy(arCoordLines)

    if Pos == "A":
        for i in range(0, len(arCoordLines)):
            if i == 0:
                arCoordLine1 = arCoordLines[i]
                arCoordLine2 = arCoordLines[i + 1]
                angle = DefMath.Angle_between_vectors(arCoordLine1[0], arCoordLine1[1], arCoordLine2[0])
                DistanceNew = Distance / abs(math.cos(angle - math.pi / 2))
            else:
                arCoordLine1 = arCoordLines[i]
                arCoordLine2 = arCoordLines[i - 1]
                angle = DefMath.Angle_between_vectors(arCoordLine1[0], arCoordLine1[1], arCoordLine2[0])
                DistanceNew = Distance / abs(math.cos(angle - math.pi / 2))

            arCoordLine = copy.deepcopy(arCoordLines[i])
            p = DefMath.Point_on_line(arCoordLine[0], arCoordLine[1], -DistanceNew)
            arCoordLine[0] = p
            arCoordLines_New[i] = arCoordLine
    elif Pos == "F":
        for i in range(0, len(arCoordLines)):
            if i == 0:
                arCoordLine1 = arCoordLines[i]
                arCoordLine2 = arCoordLines[i + 1]
                angle = DefMath.Angle_between_vectors(arCoordLine1[-1], arCoordLine1[-2], arCoordLine2[-1])
                DistanceNew = Distance / abs(math.cos(angle - math.pi / 2))
            else:
                arCoordLine1 = arCoordLines[i]
                arCoordLine2 = arCoordLines[i - 1]
                angle = DefMath.Angle_between_vectors(arCoordLine1[-1], arCoordLine1[-2], arCoordLine2[-1])
                DistanceNew = Distance / abs(math.cos(angle - math.pi / 2))

            arCoordLine = copy.deepcopy(arCoordLines[i])
            p = DefMath.Point_on_line(arCoordLine[-1], arCoordLine[-2], -DistanceNew)
            arCoordLine[-1] = p
            arCoordLines_New[i] = arCoordLine
    elif Pos == "T" or Pos == "L":
        arCoordLine1 = copy.deepcopy(arCoordLines[0])
        arCoordLine2 = copy.deepcopy(arCoordLines[1])
        arCoordLine = copy.deepcopy(arCoordLines[0])

        for i in range(0, len(arCoordLine1)):
            if i == 0:
                angle = DefMath.Angle_between_vectors(arCoordLine1[i], arCoordLine1[i + 1], arCoordLine2[i])
                DistanceNew = Distance / abs(math.cos(angle - math.pi / 2))
            else:
                angle = DefMath.Angle_between_vectors(arCoordLine1[i], arCoordLine1[i - 1], arCoordLine2[i])
                DistanceNew = Distance / abs(math.cos(angle - math.pi / 2))

            p = DefMath.Point_on_line(arCoordLine1[i], arCoordLine2[i], -DistanceNew)
            arCoordLine[i] = p
        arCoordLines_New[0] = arCoordLine
    elif Pos == "B" or Pos == "R":
        arCoordLine1 = copy.deepcopy(arCoordLines[len(arCoordLines) - 1])
        arCoordLine2 = copy.deepcopy(arCoordLines[len(arCoordLines) - 2])
        arCoordLine = copy.deepcopy(arCoordLines[len(arCoordLines) - 1])
        for i in range(0, len(arCoordLine1)):
            if i == 0:
                angle = DefMath.Angle_between_vectors(arCoordLine1[i], arCoordLine1[i + 1], arCoordLine2[i])
                DistanceNew = Distance / abs(math.cos(angle - math.pi / 2))
            else:
                angle = DefMath.Angle_between_vectors(arCoordLine1[i], arCoordLine1[i - 1], arCoordLine2[i])
                DistanceNew = Distance / abs(math.cos(angle - math.pi / 2))

            p = DefMath.Point_on_line(arCoordLine1[i], arCoordLine2[i], -DistanceNew)
            arCoordLine[i] = p
        arCoordLines_New[len(arCoordLines_New) - 1] = arCoordLine

    return arCoordLines_New


def Calculate_Coord_Face(MainPanel_data, Senkei_data, name_panel, arCoordLines, Pos):
    """
    Webパネルの座標を、UF/LFパネルとの接続面に基づいて計算する

    Args:
        MainPanel_data: メインパネルデータ
        Senkei_data: 線形データ
        name_panel: パネル名
        arCoordLines: 座標線の配列
        Pos: 位置（"T"=上、"B"=下）

    Returns:
        計算後の座標線の配列
    """
    # Load_Coordinate_PanelとCalculate_Extendはこのモジュール内で定義されているので、循環参照を避ける

    arCoordLines_New = copy.deepcopy(arCoordLines)

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
                Break_panel_top = panel["Break"]
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
                    break

        thick1_top, thick2_top, mat_top = Mat_panel_top["Thick1"], Mat_panel_top["Thick2"], Mat_panel_top["Mat"]
        if Break_panel_top:
            arThick = Break_panel_top["Thick"]
            for i in range(0, len(arThick)):
                Thick1, Thick2 = arThick[i].split("/")
                Thick1 = float(Thick1)
                Thick2 = float(Thick2)
                if Thick2 < thick2_top:
                    thick2_top = Thick2

        arCoordLines_Out_top = Load_Coordinate_Panel(Senkei_data, Line_panel_top, Sec_panel_top)
        arCoordLines_Out_top = Calculate_Extend(
            MainPanel_data, Senkei_data, name_panel_top, arCoordLines_Out_top, 100, 100, 0, 0
        )
        arCoordLines_Out_top = DefMath.Offset_Face(arCoordLines_Out_top, -thick2_top)

        arCoordLine_0 = arCoordLines[0]
        arCoordLine_1 = arCoordLines[1]
        arCoordLine = copy.deepcopy(arCoordLines[0])
        for i in range(0, len(arCoordLine)):
            p1_line = arCoordLine_0[i]
            p2_line = arCoordLine_1[i]
            for i_1 in range(len(arCoordLines_Out_top) - 1):
                status_exit = False
                arCoordLines_Out_top_1 = arCoordLines_Out_top[i_1]
                arCoordLines_Out_top_2 = arCoordLines_Out_top[i_1 + 1]
                for i_2 in range(len(arCoordLines_Out_top_1) - 1):
                    p1_plan = arCoordLines_Out_top_1[i_2]
                    p2_plan = arCoordLines_Out_top_1[i_2 + 1]
                    p3_plan = arCoordLines_Out_top_2[i_2]
                    p4_plan = arCoordLines_Out_top_2[i_2 + 1]
                    p = DefMath.Intersection_line_plane(p1_plan, p2_plan, p3_plan, p1_line, p2_line)
                    polygon3d = [p1_plan, p2_plan, p3_plan, p4_plan]
                    polygon3d = DefMath.sort_points_clockwise(polygon3d)
                    if DefMath.is_point_in_polygon_3d(p, polygon3d, p1_plan, p2_plan, p3_plan) == True:
                        arCoordLine[i] = p
                        status_exit = True
                        break
                if status_exit == True:
                    break
        arCoordLines_New[0] = arCoordLine

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
                Break_panel_bot = panel["Break"]
                break
        thick1_bot, thick2_bot, mat_bot = Mat_panel_bot["Thick1"], Mat_panel_bot["Thick2"], Mat_panel_bot["Mat"]
        if Break_panel_bot:
            arThick = Break_panel_bot["Thick"]
            for i in range(0, len(arThick)):
                Thick1, Thick2 = arThick[i].split("/")
                Thick1 = float(Thick1)
                Thick2 = float(Thick2)
                if Thick1 < thick1_bot:
                    thick1_bot = Thick1

        arCoordLines_Out_bot = Load_Coordinate_Panel(Senkei_data, Line_panel_bot, Sec_panel_bot)
        arCoordLines_Out_bot = Calculate_Extend(
            MainPanel_data, Senkei_data, name_panel_bot, arCoordLines_Out_bot, 100, 100, 0, 0
        )
        arCoordLines_Out_bot = DefMath.Offset_Face(arCoordLines_Out_bot, thick1_bot)

        arCoordLine_0 = arCoordLines[-1]
        arCoordLine_1 = arCoordLines[-2]
        arCoordLine = copy.deepcopy(arCoordLines[0])
        for i in range(0, len(arCoordLine)):
            p1_line = arCoordLine_0[i]
            p2_line = arCoordLine_1[i]
            for i_1 in range(len(arCoordLines_Out_bot) - 1):
                status_exit = False
                arCoordLines_Out_bot_1 = arCoordLines_Out_bot[i_1]
                arCoordLines_Out_bot_2 = arCoordLines_Out_bot[i_1 + 1]
                for i_2 in range(len(arCoordLines_Out_bot_1) - 1):
                    p1_plan = arCoordLines_Out_bot_1[i_2]
                    p2_plan = arCoordLines_Out_bot_1[i_2 + 1]
                    p3_plan = arCoordLines_Out_bot_2[i_2]
                    p4_plan = arCoordLines_Out_bot_2[i_2 + 1]
                    p = DefMath.Intersection_line_plane(p1_plan, p2_plan, p3_plan, p1_line, p2_line)
                    polygon3d = [p1_plan, p2_plan, p3_plan, p4_plan]
                    polygon3d = DefMath.sort_points_clockwise(polygon3d)
                    if DefMath.is_point_in_polygon_3d(p, polygon3d, p1_plan, p2_plan, p3_plan) == True:
                        arCoordLine[i] = p
                        status_exit = True
                        break
                if status_exit == True:
                    break
        arCoordLines_New[-1] = arCoordLine

    return arCoordLines_New


def Devide_Pitch_Polyline(arCoord_Polyline, Pitch, DirDevide):
    """
    ポリラインをピッチに基づいて分割する

    Args:
        arCoord_Polyline: ポリライン座標の配列
        Pitch: ピッチ文字列
        DirDevide: 分割方向（"XY"または"XYZ"）

    Returns:
        tuple: (arCoordPoint, arPosPoint)
            - arCoordPoint: 分割点の座標配列
            - arPosPoint: 分割点の位置インデックス配列
    """
    arCoordPoint = []
    arPosPoint = []
    if DirDevide == "XY":
        sum_pol = 0
        for i in range(0, len(arCoord_Polyline) - 1):
            p1 = arCoord_Polyline[i].copy()
            p1[2] = 0
            p2 = arCoord_Polyline[i + 1].copy()
            p2[2] = 0
            sum_pol += DefMath.Calculate_distance_p2p(p1, p2)

        Pitch_New = DefStrings.Xu_Ly_Pitch_va_Tim_X(Pitch, sum_pol)
        arPitch = Pitch_New.split("/")
        sumpitch = 0
        for i in range(0, len(arPitch) - 1):
            sumpitch += float(arPitch[i])
            sum = 0
            for i_1 in range(0, len(arCoord_Polyline) - 1):
                p1 = arCoord_Polyline[i_1].copy()
                p1[2] = 0
                p2 = arCoord_Polyline[i_1 + 1].copy()
                p2[2] = 0
                sum += DefMath.Calculate_distance_p2p(p1, p2)
                if sum > float(sumpitch):
                    p = DefMath.Point_on_line(p2, p1, sum - float(sumpitch))
                    pm1 = [p[0], p[1], p[2]]
                    pm2 = [p[0], p[1], p[2] + 1000]
                    pm3 = [p[0], p[1] + 1000, p[2] + 1000]
                    pp = DefMath.Intersection_line_plane(
                        pm1, pm2, pm3, arCoord_Polyline[i_1], arCoord_Polyline[i_1 + 1]
                    )
                    arCoordPoint.append(pp)
                    arPosPoint.append(i_1)
                    break

    elif DirDevide == "XYZ":
        sum_pol = 0
        for i in range(0, len(arCoord_Polyline) - 1):
            p1 = arCoord_Polyline[i].copy()
            p2 = arCoord_Polyline[i + 1].copy()
            sum_pol += DefMath.Calculate_distance_p2p(p1, p2)

        Pitch_New = DefStrings.Xu_Ly_Pitch_va_Tim_X(Pitch, sum_pol)
        arPitch = Pitch_New.split("/")
        sumpitch = 0
        for i in range(0, len(arPitch) - 1):
            sumpitch += float(arPitch[i])
            sum = 0
            for i_1 in range(0, len(arCoord_Polyline) - 1):
                p1 = arCoord_Polyline[i_1].copy()
                p2 = arCoord_Polyline[i_1 + 1].copy()
                sum += DefMath.Calculate_distance_p2p(p1, p2)
                if sum > float(sumpitch):
                    p = DefMath.Point_on_line(p2, p1, sum - float(sumpitch))
                    arCoordPoint.append(p)
                    arPosPoint.append(i_1)
                    break

    return arCoordPoint, arPosPoint


def Combined_Sort_Coord_And_NameSec(coordinates1, names1, coordinates2, names2):
    """
    座標配列と断面名称配列をマージし、X座標でソートする

    Args:
        coordinates1: 座標配列1
        names1: 名称リスト1
        coordinates2: 座標配列2
        names2: 名称リスト2

    Returns:
        tuple: (sorted_coordinates, sorted_names)
            - sorted_coordinates: X座標でソートされた座標配列
            - sorted_names: ソート順に対応した名称リスト
    """
    # 各線の点の順序に従って座標をマージ
    combined_coordinates = np.concatenate((coordinates1, coordinates2), axis=1)

    # 名称をマージ
    combined_names = names1 + names2

    # 最初の線を選択
    first_path = combined_coordinates[0]

    # 最初の線の点をX座標の値でソート
    sorted_indices = np.argsort(first_path[:, 0])

    # 最初の線の点の順序に従って名称をソート
    sorted_names = [combined_names[idx] for idx in sorted_indices]

    # 座標と名称を各線に分割
    num_paths = combined_coordinates.shape[0]

    # ソート済みの座標と名称を含むリストを作成
    sorted_coordinates = []
    for i in range(num_paths):
        coords = combined_coordinates[i]

        # X方向でソート
        sorted_indices = np.argsort(coords[:, 0])
        sorted_coords = coords[sorted_indices]

        # 結果リストに追加
        sorted_coordinates.append(sorted_coords)

    # 結果リストをnumpy配列に変換
    sorted_coordinates = np.array(sorted_coordinates)

    return sorted_coordinates, sorted_names


def Find_number_block_MainPanel(Data_MainPanel, Sec_SubPanel):
    """
    メインパネルデータからブロック番号を取得する

    Args:
        Data_MainPanel: メインパネルデータ
        Sec_SubPanel: サブパネルの断面範囲

    Returns:
        ブロック番号のリスト
    """
    number_block = []
    for panel in Data_MainPanel:
        Type_panel = panel["Type"]
        Block_panel = Type_panel["Block"]
        Sec_panel = panel["Sec"]
        if Sec_panel[0] == Sec_SubPanel[0] and Sec_panel[-1] == Sec_SubPanel[-1]:
            if Block_panel not in number_block:
                number_block.append(Block_panel)
    return number_block


def Find_number_block_MainPanel_Have_Vstiff(Senkei_data, Data_MainPanel, Sec_SubPanel):
    """
    垂直補剛材を持つメインパネルのブロック番号を取得する

    Args:
        Senkei_data: 線形データ
        Data_MainPanel: メインパネルデータ
        Sec_SubPanel: 点名称（文字列）または断面範囲（リスト）

    Returns:
        ブロック番号（文字列）
    """
    # 循環依存を避けるため、関数内で遅延インポート
    from src.bridge_json_to_ifc.ifc_utils_new.components.DefStiffener import Devide_Pitch_Vstiff

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


# ----------------------- 座標延長関数（DefBridge.pyから移動）-----------------------


def Extend_Dia_Face(
    MainPanel_data,
    Senkei_data,
    headname_block_mainpanel,
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

    # Top
    if DefMath.is_number(extendT) == False:
        name_mainpanel = headname_block_mainpanel + "UF"
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
            name_mainpanel = headname_block_mainpanel + "DK"
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

            for i in range(len(arCoord_Top_New)):
                if i == 0 or i == len(arCoord_Top_New) - 1:
                    p1_line = arCoord_Top_New[i]
                    p2_line = arCoord_Bot_New[len(arCoord_Bot_New) - 1 - i]
                else:
                    p1_line = arCoord_Top_New[i]
                    p2_line = DefMath.Point_on_parallel_line(
                        arCoord_Top_New[i], arCoord_Top_New[0], arCoord_Bot_New[-1]
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
                            arCoord_Top_New[i] = p
                            status_exit = True
                            break
                    if status_exit == True:
                        break

            arCoord_Left_New[0] = arCoord_Top_New[-1]
            arCoord_Right_New[-1] = arCoord_Top_New[0]

    # Bot
    if DefMath.is_number(extendB) == False:
        name_mainpanel = headname_block_mainpanel + "LF"
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

            for i in range(len(arCoord_Bot_New)):
                if i == 0 or i == len(arCoord_Bot_New) - 1:
                    p1_line = arCoord_Bot_New[i]
                    p2_line = arCoord_Top_New[len(arCoord_Top_New) - 1 - i]
                else:
                    p1_line = arCoord_Bot_New[i]
                    p2_line = DefMath.Point_on_parallel_line(
                        arCoord_Bot_New[i], arCoord_Bot_New[0], arCoord_Top_New[-1]
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
                            arCoord_Bot_New[i] = p
                            status_exit = True
                            break
                    if status_exit == True:
                        break

            arCoord_Left_New[-1] = arCoord_Bot_New[0]
            arCoord_Right_New[0] = arCoord_Bot_New[-1]

    # Left
    if DefMath.is_number(extendL) == False:
        name_mainpanel = headname_block_mainpanel + "WL"
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
            arCoordLines_Out = DefMath.Offset_Face(arCoordLines_Out, thick2_panel)

            for i in range(len(arCoord_Left_New)):
                if i == 0 or i == len(arCoord_Left_New) - 1:
                    p1_line = arCoord_Left_New[i]
                    p2_line = arCoord_Right_New[len(arCoord_Right_New) - 1 - i]
                else:
                    p1_line = arCoord_Left_New[i]
                    p2_line = DefMath.Point_on_parallel_line(
                        arCoord_Left_New[i], arCoord_Left_New[0], arCoord_Right_New[-1]
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
        name_mainpanel = headname_block_mainpanel + "WR"
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
            arCoordLines_Out = DefMath.Offset_Face(arCoordLines_Out, -thick1_panel)

            for i in range(len(arCoord_Right_New)):
                if i == 0 or i == len(arCoord_Right_New) - 1:
                    p1_line = arCoord_Right_New[i]
                    p2_line = arCoord_Left_New[len(arCoord_Left_New) - 1 - i]
                else:
                    p1_line = arCoord_Right_New[i]
                    p2_line = DefMath.Point_on_parallel_line(
                        arCoord_Right_New[i], arCoord_Right_New[0], arCoord_Left_New[-1]
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


def Extend_Dia_Number(arCoord2D_Top, arCoord2D_Bot, arCoord2D_Left, arCoord2D_Right, extend):
    arCoord2D_Top_New = arCoord2D_Top.copy()
    arCoord2D_Bot_New = arCoord2D_Bot.copy()
    arCoord2D_Left_New = arCoord2D_Left.copy()
    arCoord2D_Right_New = arCoord2D_Right.copy()
    extendL, extendR, extendT, extendB = extend
    # Top
    if DefMath.is_number(extendT) == True:
        for i in range(len(arCoord2D_Top_New) - 1):
            p1 = arCoord2D_Top_New[i][:2]
            p2 = arCoord2D_Top_New[i + 1][:2]
            p1o, p2o = DefMath.Offset_Line(p1, p2, -extendT)

            if len(arCoord2D_Top_New) - 1 == 1:
                p = DefMath.Intersec_line_line(p1o, p2o, arCoord2D_Right_New[-1][:2], arCoord2D_Right_New[-2][:2])
                arCoord2D_Top_New[i][0] = p[0]
                arCoord2D_Top_New[i][1] = p[1]
                arCoord2D_Top_New[i][2] = 0
                arCoord2D_Right_New[-1][0] = p[0]
                arCoord2D_Right_New[-1][1] = p[1]
                arCoord2D_Right_New[-1][2] = 0

                p = DefMath.Intersec_line_line(p1o, p2o, arCoord2D_Left_New[0][:2], arCoord2D_Left_New[1][:2])
                arCoord2D_Top_New[i + 1][0] = p[0]
                arCoord2D_Top_New[i + 1][1] = p[1]
                arCoord2D_Top_New[i + 1][2] = 0
                arCoord2D_Left_New[0][0] = p[0]
                arCoord2D_Left_New[0][1] = p[1]
                arCoord2D_Left_New[0][2] = 0

            else:
                if i == 0:
                    p = DefMath.Intersec_line_line(p1o, p2o, arCoord2D_Right_New[-1][:2], arCoord2D_Right_New[-2][:2])
                    arCoord2D_Top_New[i][0] = p[0]
                    arCoord2D_Top_New[i][1] = p[1]
                    arCoord2D_Top_New[i][2] = 0
                    arCoord2D_Right_New[-1][0] = p[0]
                    arCoord2D_Right_New[-1][1] = p[1]
                    arCoord2D_Right_New[-1][2] = 0
                elif i == len(arCoord2D_Top_New) - 2:
                    p = DefMath.Intersec_line_line(p1o, p2o, arCoord2D_Left_New[0][:2], arCoord2D_Left_New[1][:2])
                    arCoord2D_Top_New[i + 1][0] = p[0]
                    arCoord2D_Top_New[i + 1][1] = p[1]
                    arCoord2D_Top_New[i + 1][2] = 0
                    arCoord2D_Left_New[0][0] = p[0]
                    arCoord2D_Left_New[0][1] = p[1]
                    arCoord2D_Left_New[0][2] = 0

                    p1o_1, p2o_1 = DefMath.Offset_Line(arCoord2D_Top_New[i - 1][:2], arCoord2D_Top_New[i][:2], -extendT)
                    if p2o_1.all() == p1o.all():
                        p = p1o
                    else:
                        p = DefMath.Intersec_line_line(p1o, p2o, p1o_1, p2o_1)
                    arCoord2D_Top_New[i][0] = p[0]
                    arCoord2D_Top_New[i][1] = p[1]
                    arCoord2D_Top_New[i][2] = 0
                else:
                    p1o_1, p2o_1 = DefMath.Offset_Line(arCoord2D_Top_New[i - 1][:2], arCoord2D_Top_New[i][:2], -extendT)
                    if p2o_1.all() == p1o.all():
                        p = p1o
                    else:
                        p = DefMath.Intersec_line_line(p1o, p2o, p1o_1, p2o_1)

                    arCoord2D_Top_New[i][0] = p[0]
                    arCoord2D_Top_New[i][1] = p[1]
                    arCoord2D_Top_New[i][2] = 0
    # Bot
    if DefMath.is_number(extendB) == True:
        for i in range(len(arCoord2D_Bot_New) - 1):
            p1 = arCoord2D_Bot_New[i][:2]
            p2 = arCoord2D_Bot_New[i + 1][:2]
            p1o, p2o = DefMath.Offset_Line(p1, p2, -extendB)

            if len(arCoord2D_Bot_New) - 1 == 1:
                p = DefMath.Intersec_line_line(p1o, p2o, arCoord2D_Left_New[-1][:2], arCoord2D_Left_New[-2][:2])
                arCoord2D_Bot_New[i][0] = p[0]
                arCoord2D_Bot_New[i][1] = p[1]
                arCoord2D_Bot_New[i][2] = 0
                arCoord2D_Left_New[-1][0] = p[0]
                arCoord2D_Left_New[-1][1] = p[1]
                arCoord2D_Left_New[-1][2] = 0

                p = DefMath.Intersec_line_line(p1o, p2o, arCoord2D_Right_New[0][:2], arCoord2D_Right_New[1][:2])
                arCoord2D_Bot_New[i + 1][0] = p[0]
                arCoord2D_Bot_New[i + 1][1] = p[1]
                arCoord2D_Bot_New[i + 1][2] = 0
                arCoord2D_Right_New[0][0] = p[0]
                arCoord2D_Right_New[0][1] = p[1]
                arCoord2D_Right_New[0][2] = 0

            else:
                if i == 0:
                    p = DefMath.Intersec_line_line(p1o, p2o, arCoord2D_Left_New[-1][:2], arCoord2D_Left_New[-2][:2])
                    arCoord2D_Bot_New[i][0] = p[0]
                    arCoord2D_Bot_New[i][1] = p[1]
                    arCoord2D_Bot_New[i][2] = 0
                    arCoord2D_Left_New[-1][0] = p[0]
                    arCoord2D_Left_New[-1][1] = p[1]
                    arCoord2D_Left_New[-1][2] = 0
                elif i == len(arCoord2D_Bot_New) - 2:
                    p = DefMath.Intersec_line_line(p1o, p2o, arCoord2D_Right_New[0][:2], arCoord2D_Right_New[1][:2])
                    arCoord2D_Bot_New[i + 1][0] = p[0]
                    arCoord2D_Bot_New[i + 1][1] = p[1]
                    arCoord2D_Bot_New[i + 1][2] = 0
                    arCoord2D_Right_New[0][0] = p[0]
                    arCoord2D_Right_New[0][1] = p[1]
                    arCoord2D_Right_New[0][2] = 0

                    p1o_1, p2o_1 = DefMath.Offset_Line(arCoord2D_Bot_New[i - 1][:2], arCoord2D_Bot_New[i][:2], -extendB)
                    if p2o_1.all() == p1o.all():
                        p = p1o
                    else:
                        p = DefMath.Intersec_line_line(p1o, p2o, p1o_1, p2o_1)
                    arCoord2D_Bot_New[i][0] = p[0]
                    arCoord2D_Bot_New[i][1] = p[1]
                    arCoord2D_Bot_New[i][2] = 0
                else:
                    p1o_1, p2o_1 = DefMath.Offset_Line(arCoord2D_Bot_New[i - 1][:2], arCoord2D_Bot_New[i][:2], -extendB)
                    if p2o_1.all() == p1o.all():
                        p = p1o
                    else:
                        p = DefMath.Intersec_line_line(p1o, p2o, p1o_1, p2o_1)

                    arCoord2D_Bot_New[i][0] = p[0]
                    arCoord2D_Bot_New[i][1] = p[1]
                    arCoord2D_Bot_New[i][2] = 0
    # Left
    if DefMath.is_number(extendL) == True:
        for i in range(len(arCoord2D_Left_New) - 1):
            p1 = arCoord2D_Left_New[i][:2]
            p2 = arCoord2D_Left_New[i + 1][:2]
            p1o, p2o = DefMath.Offset_Line(p1, p2, -extendL)

            if len(arCoord2D_Left_New) - 1 == 1:
                p = DefMath.Intersec_line_line(p1o, p2o, arCoord2D_Bot_New[0][:2], arCoord2D_Bot_New[1][:2])
                arCoord2D_Left_New[i + 1][0] = p[0]
                arCoord2D_Left_New[i + 1][1] = p[1]
                arCoord2D_Left_New[i + 1][2] = 0
                arCoord2D_Bot_New[0][0] = p[0]
                arCoord2D_Bot_New[0][1] = p[1]
                arCoord2D_Bot_New[0][2] = 0

                p = DefMath.Intersec_line_line(p1o, p2o, arCoord2D_Top_New[-1][:2], arCoord2D_Top_New[-2][:2])
                arCoord2D_Left_New[i][0] = p[0]
                arCoord2D_Left_New[i][1] = p[1]
                arCoord2D_Left_New[i][2] = 0
                arCoord2D_Top_New[-1][0] = p[0]
                arCoord2D_Top_New[-1][1] = p[1]
                arCoord2D_Top_New[-1][2] = 0

            else:
                if i == 0:
                    p = DefMath.Intersec_line_line(p1o, p2o, arCoord2D_Top_New[0][:2], arCoord2D_Top_New[1][:2])
                    arCoord2D_Left_New[i][0] = p[0]
                    arCoord2D_Left_New[i][1] = p[1]
                    arCoord2D_Left_New[i][2] = 0
                    arCoord2D_Top_New[-1][0] = p[0]
                    arCoord2D_Top_New[-1][1] = p[1]
                    arCoord2D_Top_New[-1][2] = 0
                elif i == len(arCoord2D_Left_New) - 2:
                    p = DefMath.Intersec_line_line(p1o, p2o, arCoord2D_Bot_New[0][:2], arCoord2D_Bot_New[1][:2])
                    arCoord2D_Left_New[i + 1][0] = p[0]
                    arCoord2D_Left_New[i + 1][1] = p[1]
                    arCoord2D_Left_New[i + 1][2] = 0
                    arCoord2D_Bot_New[0][0] = p[0]
                    arCoord2D_Bot_New[0][1] = p[1]
                    arCoord2D_Bot_New[0][2] = 0

                    p1o_1, p2o_1 = DefMath.Offset_Line(
                        arCoord2D_Left_New[i - 1][:2], arCoord2D_Left_New[i][:2], -extendL
                    )
                    if p2o_1.all() == p1o.all():
                        p = p1o
                    else:
                        p = DefMath.Intersec_line_line(p1o, p2o, p1o_1, p2o_1)
                    arCoord2D_Left_New[i][0] = p[0]
                    arCoord2D_Left_New[i][1] = p[1]
                    arCoord2D_Left_New[i][2] = 0
                else:
                    p1o_1, p2o_1 = DefMath.Offset_Line(
                        arCoord2D_Left_New[i - 1][:2], arCoord2D_Left_New[i][:2], -extendL
                    )
                    if p2o_1.all() == p1o.all():
                        p = p1o
                    else:
                        p = DefMath.Intersec_line_line(p1o, p2o, p1o_1, p2o_1)

                    arCoord2D_Left_New[i][0] = p[0]
                    arCoord2D_Left_New[i][1] = p[1]
                    arCoord2D_Left_New[i][2] = 0
    # Right
    if DefMath.is_number(extendR) == True:
        for i in range(len(arCoord2D_Right_New) - 1):
            p1 = arCoord2D_Right_New[i][:2]
            p2 = arCoord2D_Right_New[i + 1][:2]
            p1o, p2o = DefMath.Offset_Line(p1, p2, -extendR)

            if len(arCoord2D_Right_New) - 1 == 1:
                p = DefMath.Intersec_line_line(p1o, p2o, arCoord2D_Bot_New[-1][:2], arCoord2D_Bot_New[-2][:2])
                arCoord2D_Right_New[i][0] = p[0]
                arCoord2D_Right_New[i][1] = p[1]
                arCoord2D_Right_New[i][2] = 0
                arCoord2D_Bot_New[-1][0] = p[0]
                arCoord2D_Bot_New[-1][1] = p[1]
                arCoord2D_Bot_New[-1][2] = 0

                p = DefMath.Intersec_line_line(p1o, p2o, arCoord2D_Top_New[0][:2], arCoord2D_Top_New[1][:2])
                arCoord2D_Right_New[i + 1][0] = p[0]
                arCoord2D_Right_New[i + 1][1] = p[1]
                arCoord2D_Right_New[i + 1][2] = 0
                arCoord2D_Top_New[0][0] = p[0]
                arCoord2D_Top_New[0][1] = p[1]
                arCoord2D_Top_New[0][2] = 0

            else:
                if i == 0:
                    p = DefMath.Intersec_line_line(p1o, p2o, arCoord2D_Bot_New[-1][:2], arCoord2D_Bot_New[-2][:2])
                    arCoord2D_Right_New[i][0] = p[0]
                    arCoord2D_Right_New[i][1] = p[1]
                    arCoord2D_Right_New[i][2] = 0
                    arCoord2D_Bot_New[-1][0] = p[0]
                    arCoord2D_Bot_New[-1][1] = p[1]
                    arCoord2D_Bot_New[-1][2] = 0
                elif i == len(arCoord2D_Right_New) - 2:
                    p = DefMath.Intersec_line_line(p1o, p2o, arCoord2D_Top_New[0][:2], arCoord2D_Top_New[1][:2])
                    arCoord2D_Right_New[i + 1][0] = p[0]
                    arCoord2D_Right_New[i + 1][1] = p[1]
                    arCoord2D_Right_New[i + 1][2] = 0
                    arCoord2D_Top_New[0][0] = p[0]
                    arCoord2D_Top_New[0][1] = p[1]
                    arCoord2D_Top_New[0][2] = 0

                    p1o_1, p2o_1 = DefMath.Offset_Line(
                        arCoord2D_Right_New[i - 1][:2], arCoord2D_Right_New[i][:2], -extendR
                    )
                    if p2o_1.all() == p1o.all():
                        p = p1o
                    else:
                        p = DefMath.Intersec_line_line(p1o, p2o, p1o_1, p2o_1)
                    arCoord2D_Right_New[i][0] = p[0]
                    arCoord2D_Right_New[i][1] = p[1]
                    arCoord2D_Right_New[i][2] = 0
                else:
                    p1o_1, p2o_1 = DefMath.Offset_Line(
                        arCoord2D_Right_New[i - 1][:2], arCoord2D_Right_New[i][:2], -extendR
                    )
                    if p2o_1.all() == p1o.all():
                        p = p1o
                    else:
                        p = DefMath.Intersec_line_line(p1o, p2o, p1o_1, p2o_1)

                    arCoord2D_Right_New[i][0] = p[0]
                    arCoord2D_Right_New[i][1] = p[1]
                    arCoord2D_Right_New[i][2] = 0

    return arCoord2D_Top_New, arCoord2D_Bot_New, arCoord2D_Left_New, arCoord2D_Right_New


def Extend_FLG(MainPanel_data, Senkei_data, arCoord_FLG, extends, headname1_block_mainpanel, headname2_block_mainpanel):
    extendL, extendR, extendT, extendB = extends
    arCoord_FLG_New = arCoord_FLG.copy()
    # Left
    if DefMath.is_number(extendL) == False:
        if headname1_block_mainpanel == headname2_block_mainpanel:
            name_mainpanel = headname1_block_mainpanel + "WL"
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

                for i in range(len(arCoord_FLG_New)):
                    CoordLine = arCoord_FLG_New[i]
                    p1_line = CoordLine[0]
                    p2_line = CoordLine[1]
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
                                CoordLine[0] = p
                                status_exit = True
                                break
                        if status_exit == True:
                            break
                    arCoord_FLG_New[i] = CoordLine
        else:
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

                for i in range(len(arCoord_FLG_New)):
                    CoordLine = arCoord_FLG_New[i]
                    p1_line = CoordLine[0]
                    p2_line = CoordLine[1]
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
                                CoordLine[0] = p
                                status_exit = True
                                break
                        if status_exit == True:
                            break
                    arCoord_FLG_New[i] = CoordLine
    else:
        arCoord_FLG_New = Calculate_Extend_Coord(arCoord_FLG_New, extendL, "A")

    # Right
    if DefMath.is_number(extendR) == False:
        if headname1_block_mainpanel == headname2_block_mainpanel:
            name_mainpanel = headname2_block_mainpanel + "WR"
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

                for i in range(len(arCoord_FLG_New)):
                    CoordLine = arCoord_FLG_New[i]
                    p1_line = CoordLine[-2]
                    p2_line = CoordLine[-1]
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
                                CoordLine[-1] = p
                                status_exit = True
                                break
                        if status_exit == True:
                            break
                    arCoord_FLG_New[i] = CoordLine
        else:
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

                for i in range(len(arCoord_FLG_New)):
                    CoordLine = arCoord_FLG_New[i]
                    p1_line = CoordLine[-2]
                    p2_line = CoordLine[-1]
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
                                CoordLine[-1] = p
                                status_exit = True
                                break
                        if status_exit == True:
                            break
                    arCoord_FLG_New[i] = CoordLine
    else:
        arCoord_FLG_New = Calculate_Extend_Coord(arCoord_FLG_New, extendR, "F")

    return arCoord_FLG_New


def Calculate_Coord_FLG(arCoorMod, pdir, WideA, WideF, AngA, AngF, AngS, AngE):
    arCoorMod_A = arCoorMod.copy()
    arCoorMod_F = arCoorMod.copy()

    for i in range(len(arCoorMod) - 1):
        if i == 0:
            p1Ro = arCoorMod[i]
            p2Ro = arCoorMod[i + 1]

            p1A = DefMath.Offset_point(arCoorMod[i], arCoorMod[i + 1], pdir, -WideA)
            if p1A[0] > arCoorMod[i][0]:
                p1A = DefMath.Offset_point(arCoorMod[i], arCoorMod[i + 1], pdir, WideA)
            p2A = DefMath.Offset_point(arCoorMod[i + 1], arCoorMod[i], pdir, WideA)
            if p2A[0] > arCoorMod[i + 1][0]:
                p2A = DefMath.Offset_point(arCoorMod[i + 1], arCoorMod[i], pdir, -WideA)
            if AngA != 90:
                p1A = DefMath.rotate_point_around_axis(p1Ro, p2Ro, p1A, -(90 - AngA))
                p2A = DefMath.rotate_point_around_axis(p1Ro, p2Ro, p2A, -(90 - AngA))

            arCoorMod_A[i] = p1A
            arCoorMod_A[i + 1] = p2A

            p1F = DefMath.Offset_point(arCoorMod[i], arCoorMod[i + 1], pdir, -WideF)
            if p1F[0] < arCoorMod[i][0]:
                p1F = DefMath.Offset_point(arCoorMod[i], arCoorMod[i + 1], pdir, WideF)
            p2F = DefMath.Offset_point(arCoorMod[i + 1], arCoorMod[i], pdir, WideF)
            if p2F[0] < arCoorMod[i + 1][0]:
                p2F = DefMath.Offset_point(arCoorMod[i + 1], arCoorMod[i], pdir, -WideF)
            if AngF != 90:
                p1F = DefMath.rotate_point_around_axis(p1Ro, p2Ro, p1F, (90 - AngF))
                p2F = DefMath.rotate_point_around_axis(p1Ro, p2Ro, p2F, (90 - AngF))

            arCoorMod_F[i] = p1F
            arCoorMod_F[i + 1] = p2F

        else:
            p1Ro = arCoorMod[i]
            p2Ro = arCoorMod[i + 1]

            if p1A[0] > arCoorMod[i][0]:
                p1A = DefMath.Offset_point(arCoorMod[i], arCoorMod[i + 1], pdir, WideA)
            p2A = DefMath.Offset_point(arCoorMod[i + 1], arCoorMod[i], pdir, WideA)
            if p2A[0] > arCoorMod[i + 1][0]:
                p2A = DefMath.Offset_point(arCoorMod[i + 1], arCoorMod[i], pdir, -WideA)

            if AngA != 90:
                p1A = DefMath.rotate_point_around_axis(p1Ro, p2Ro, p1A, -(90 - AngA))
                p2A = DefMath.rotate_point_around_axis(p1Ro, p2Ro, p2A, -(90 - AngA))

                p1 = DefMath.Intersection_line_plane(p1A, p2A, arCoorMod[i], arCoorMod_A[i], arCoorMod_A[i - 1])
                p2 = DefMath.Intersection_line_plane(arCoorMod_A[i], arCoorMod_A[i - 1], arCoorMod[i], p1A, p2A)
                p1A = (p1 + p2) / 2

            arCoorMod_A[i] = p1A
            arCoorMod_A[i + 1] = p2A

            p1F = DefMath.Offset_point(arCoorMod[i], arCoorMod[i + 1], pdir, -WideF)
            if p1F[0] < arCoorMod[i][0]:
                p1F = DefMath.Offset_point(arCoorMod[i], arCoorMod[i + 1], pdir, WideF)
            p2F = DefMath.Offset_point(arCoorMod[i + 1], arCoorMod[i], pdir, WideF)
            if p2F[0] < arCoorMod[i + 1][0]:
                p2F = DefMath.Offset_point(arCoorMod[i + 1], arCoorMod[i], pdir, -WideF)

            if AngF != 90:
                p1F = DefMath.rotate_point_around_axis(p1Ro, p2Ro, p1F, (90 - AngF))
                p2F = DefMath.rotate_point_around_axis(p1Ro, p2Ro, p2F, (90 - AngF))

                p1 = DefMath.Intersection_line_plane(p1F, p2F, arCoorMod[i], arCoorMod_F[i], arCoorMod_F[i - 1])
                p2 = DefMath.Intersection_line_plane(arCoorMod_F[i], arCoorMod_F[i - 1], arCoorMod[i], p1F, p2F)
                p1F = (p1 + p2) / 2

            arCoorMod_F[i] = p1F
            arCoorMod_F[i + 1] = p2F

    if AngS != 90:
        p1Ro = arCoorMod[0]
        p2Ro_A = p1Ro - 100 * DefMath.Normal_vector(arCoorMod[0], arCoorMod[1], arCoorMod_A[0])
        p2Ro_F = p1Ro + 100 * DefMath.Normal_vector(arCoorMod[0], arCoorMod[1], arCoorMod_F[0])
        arCoorMod_A[0] = DefMath.rotate_point_around_axis(p1Ro, p2Ro_A, arCoorMod_A[0], -(90 - AngS))
        arCoorMod_F[0] = DefMath.rotate_point_around_axis(p1Ro, p2Ro_F, arCoorMod_F[0], -(90 - AngS))
    if AngE != 90:
        p1Ro = arCoorMod[-1]
        p2Ro_A = p1Ro + 100 * DefMath.Normal_vector(arCoorMod[-1], arCoorMod[-2], arCoorMod_A[-1])
        p2Ro_F = p1Ro - 100 * DefMath.Normal_vector(arCoorMod[-1], arCoorMod[-2], arCoorMod_F[-1])
        arCoorMod_A[-1] = DefMath.rotate_point_around_axis(p1Ro, p2Ro_A, arCoorMod_A[-1], (90 - AngE))
        arCoorMod_F[-1] = DefMath.rotate_point_around_axis(p1Ro, p2Ro_F, arCoorMod_F[-1], (90 - AngE))

    return arCoorMod_A, arCoorMod_F
