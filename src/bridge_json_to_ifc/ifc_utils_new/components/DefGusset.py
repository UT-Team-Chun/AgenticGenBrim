"""
鋼橋IFCモデル生成 - ガセット生成モジュール
ガセット（補強板）生成関連関数
"""

import numpy as np

from src.bridge_json_to_ifc.ifc_utils_new.core import DefIFC, DefMath
from src.bridge_json_to_ifc.ifc_utils_new.io import DefStrings
from src.bridge_json_to_ifc.ifc_utils_new.utils import DefBridgeUtils

# グローバル変数: ログファイル出力関数（DefBridge.pyから設定される）
log_print_func = None

# グローバル変数: 橋梁の方向ベクトル（DefBridge.pyから設定される）
start_point_bridge = None
unit_vector_bridge = None


def _log_print(*args, **kwargs):
    """ログファイル出力関数（DEBUG_MODE時のみ出力）"""
    if log_print_func:
        log_print_func(*args, **kwargs)


def Calculate_edge_Guss_Constant(
    MainPanel_data, Senkei_data, nameWeb_mainpanel, namepoint_guss, coordpoint_guss, distan_edge, pbase, pplan1, pplan2
):
    coordpoint_guss_2d = coordpoint_guss.copy()
    coordpoint_guss_2d[2] = 0
    for panel in MainPanel_data:
        if panel["Name"] == nameWeb_mainpanel:
            Line_mainpanel = panel["Line"]
            Sec_mainpanel = panel["Sec"]
            Type_mainpanel = panel["Type"]
            Mat_mainpanel = panel["Material"]
            Expand_mainpanel = panel["Expand"]
            break
    thick1_panel, thick2_panel, mat_panel = Mat_mainpanel["Thick1"], Mat_mainpanel["Thick2"], Mat_mainpanel["Mat"]
    arCoordLines_mod = DefBridgeUtils.Load_Coordinate_Panel(Senkei_data, Line_mainpanel, Sec_mainpanel)
    # ------------------cut face 1-----------------------------
    arCoordLines_Out = DefMath.Offset_Face(arCoordLines_mod, -thick2_panel)
    arCoordLines_Out = DefBridgeUtils.Calculate_Extend_Coord(arCoordLines_Out, 5, "L")
    arCoordLines_Out = DefBridgeUtils.Calculate_Extend_Coord(arCoordLines_Out, 5, "R")
    arCoordLines_Out_1 = arCoordLines_Out[0]
    index = Sec_mainpanel.index(namepoint_guss)
    ps_line = arCoordLines_Out_1[index]
    ps_line[2] = 0
    if distan_edge > 0:
        pe_line = arCoordLines_Out_1[index + 1]
        pe_line[2] = 0
    else:
        pe_line = arCoordLines_Out_1[index - 1]
        pe_line[2] = 0

    coordpoint_guss_2d_per = DefMath.point_per_line(coordpoint_guss_2d, ps_line, pe_line)
    p1 = DefMath.Point_on_parallel_line(coordpoint_guss_2d_per, ps_line, pe_line, abs(distan_edge))
    # ------------------cut face 2-----------------------------
    arCoordLines_Out = DefMath.Offset_Face(arCoordLines_mod, thick1_panel)
    arCoordLines_Out = DefBridgeUtils.Calculate_Extend_Coord(arCoordLines_Out, 5, "L")
    arCoordLines_Out = DefBridgeUtils.Calculate_Extend_Coord(arCoordLines_Out, 5, "R")
    arCoordLines_Out_1 = arCoordLines_Out[0]
    index = Sec_mainpanel.index(namepoint_guss)
    ps_line = arCoordLines_Out_1[index]
    ps_line[2] = 0
    if distan_edge > 0:
        pe_line = arCoordLines_Out_1[index + 1]
        pe_line[2] = 0
    else:
        pe_line = arCoordLines_Out_1[index - 1]
        pe_line[2] = 0

    coordpoint_guss_2d_per = DefMath.point_per_line(coordpoint_guss_2d, ps_line, pe_line)
    p2 = DefMath.Point_on_parallel_line(coordpoint_guss_2d_per, ps_line, pe_line, abs(distan_edge))

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
    arCoordLines_mod = DefBridgeUtils.Load_Coordinate_Panel(Senkei_data, Line_mainpanel, Sec_mainpanel)
    # ------------------cut face 1-----------------------------
    arCoordLines_Out = DefMath.Offset_Face(arCoordLines_mod, -thick2_panel)
    arCoordLines_Out = DefBridgeUtils.Calculate_Extend_Coord(arCoordLines_Out, 5, "L")
    arCoordLines_Out = DefBridgeUtils.Calculate_Extend_Coord(arCoordLines_Out, 5, "R")
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
    arCoordLines_Out = DefBridgeUtils.Calculate_Extend_Coord(arCoordLines_Out, 5, "L")
    arCoordLines_Out = DefBridgeUtils.Calculate_Extend_Coord(arCoordLines_Out, 5, "R")
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
    # Lazy import to avoid circular dependency
    from src.bridge_json_to_ifc.ifc_utils_new.core.DefBridge import Calculate_Pse_Shape

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
    # Lazy import to avoid circular dependency
    from src.bridge_json_to_ifc.ifc_utils_new.core.DefBridge import Calculate_Point_Cross_Yokokou, Calculate_Pse_Shape

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
                print(f"Chưa khai bảo điểm {namepoint} trong hệ thông yokokou")
                pbs_shape = None

            namepoint = point_shape[1]
            if DefMath.is_number(namepoint) == True:
                index = int(namepoint) - 1
                point = arCoordPoint_Yokokou[index]
                pbe_shape = [point["X"], point["Y"], point["Z"]]
            elif namepoint == "Cross":
                pbe_shape = Calculate_Point_Cross_Yokokou(arCoordPoint_Yokokou, type_yokokou)
            else:
                print(f"Chưa khai bảo điểm {namepoint} trong hệ thông yokokou")
                pbe_shape = None

            namepoint = point_shape[2]
            if DefMath.is_number(namepoint) == True:
                index = int(namepoint) - 1
                point = arCoordPoint_Yokokou[index]
                pplan_shape = [point["X"], point["Y"], point["Z"]]
            elif namepoint == "Cross":
                pplan_shape = Calculate_Point_Cross_Yokokou(arCoordPoint_Yokokou, type_yokokou)
            else:
                print(f"Chưa khai bảo điểm {namepoint} trong hệ thông yokokou")
                pplan_shape = None
        else:
            print(f"Trường hợp type của  yokoko là : {type_yokokou[0]} chưa phát triển.")
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
                if np.dot(pT_fn - start_point_bridge, unit_vector_bridge) > np.dot(
                    pe_shape - start_point_bridge, unit_vector_bridge
                ):
                    pT_fn = pe_shape - bc * normal_shape
                    pS_fn = pe_shape + bc * normal_shape
                break

    return pT_fn, pS_fn


def Calculate_Face_Base_Guss_follow_Yokokou(
    shape_yokokou, arCoordPoint_Yokokou, type_yokokou, coordpoint_guss, distedge_face
):
    # Lazy import to avoid circular dependency
    from src.bridge_json_to_ifc.ifc_utils_new.core.DefBridge import Calculate_Point_Cross_Yokokou, Calculate_Pse_Shape

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
    # Lazy import to avoid circular dependency
    from src.bridge_json_to_ifc.ifc_utils_new.core.DefBridge import Calculate_Shape_Taikeikou_For_Yokokou

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
            # セクション情報を取得（オプショナル、デフォルトは"C1"）
            section_taikeikou = taikeikou.get("Section", "C1")
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
                section_taikeikou,
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
            arCoordLines_mod = DefBridgeUtils.Load_Coordinate_Panel(Senkei_data, Line_mainpanel, Sec_mainpanel)
            # ------------------cut face 1-----------------------------
            arCoordLines_Out = DefMath.Offset_Face(arCoordLines_mod, -thick2_panel)
            arCoordLines_Out = DefBridgeUtils.Calculate_Extend_Coord(arCoordLines_Out, 5, "L")
            arCoordLines_Out = DefBridgeUtils.Calculate_Extend_Coord(arCoordLines_Out, 5, "R")
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
            arCoordLines_Out = DefBridgeUtils.Calculate_Extend_Coord(arCoordLines_Out, 5, "L")
            arCoordLines_Out = DefBridgeUtils.Calculate_Extend_Coord(arCoordLines_Out, 5, "R")
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
    # Lazy import to avoid circular dependency
    from src.bridge_json_to_ifc.ifc_utils_new.core.DefBridge import (
        Calculate_Coord_FLG,
        Calculate_points_Sub_Panel,
        Extend_FLG,
        Find_number_block_MainPanel,
    )

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

        number_block = Find_number_block_MainPanel(MainPanel_data, sec_subpanel)
        headname1_block_mainpanel = girder1_dia + "B" + number_block
        headname2_block_mainpanel = girder2_dia + "B" + number_block
        if sec_subpanel == namepoint_guss and argirder_subpanel == girder_guss:
            arNamePoint, arCoordPoint = Calculate_points_Sub_Panel(Senkei_data, point_subpanel, sec_subpanel)
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
                    arCoorMod_A, arCoorMod_F = Calculate_Coord_FLG(
                        arCoord_flg, pdir, dimetion_y / 2, dimetion_y / 2, 90, 90, 90, 90
                    )
                    arCoordFLG = [arCoorMod_F, arCoord_flg, arCoorMod_A]
                    arCoordFLG_Out = arCoordFLG.copy()

                    arCoordFLGT_Out = Extend_FLG(
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
                            print("Trường hợp này chưa phát triển !")

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
    # Lazy import to avoid circular dependency
    from src.bridge_json_to_ifc.ifc_utils_new.core.DefBridge import Calculate_Coord_FLG, Extend_FLG

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

    arCoorMod_A, arCoorMod_F = Calculate_Coord_FLG(
        arCoord_flg, pdir, distA, distF, anga_rib, 180 - anga_rib, angs_rib, ange_rib
    )
    arCoordFLG = [arCoorMod_F, arCoord_flg, arCoorMod_A]
    arCoordFLG_Out = arCoordFLG.copy()
    arCoordFLG_Out = Extend_FLG(
        MainPanel_data, Senkei_data, arCoordFLG_Out, extend, headname1_block_mainpanel, headname2_block_mainpanel
    )
    arCoordFLGT_Out = DefMath.Offset_Face(arCoordFLG_Out, thick1_rib)
    arCoordFLGB_Out = DefMath.Offset_Face(arCoordFLG_Out, -thick2_rib)
    arCoordFLGM_Out = DefMath.Calculate_Coord_Mid(arCoordFLGT_Out, arCoordFLGB_Out)

    return arCoordFLGT_Out, arCoordFLGB_Out


def Draw_3DSolid_Guss(
    ifc_all,
    shape_taikeikou,
    vstiff_taikeikou,
    type_taikeikou,
    p1mod_tai,
    p2mod_tai,
    p3mod_tai,
    p4mod_tai,
    p5mod_tai,
    arCoord_hole,
    infor_guss,
    pos_guss,
    p1_3d,
    p2_3d,
    p3_3d,
):
    # Lazy import to avoid circular dependency
    from src.bridge_json_to_ifc.ifc_utils_new.core.DefBridge import Calculate_Pse_Shape

    ifc_file, bridge_span, geom_context = ifc_all
    thick_guss, mat_guss, distMep, DistShape1, DistShape2 = infor_guss[:5]
    typ_taikeikou, gau_gus, gau_shape = type_taikeikou
    ardistmep = distMep.split("/")
    dist_mepT, dist_mepB, dist_mepL, dist_mepR = (
        float(ardistmep[0]),
        float(ardistmep[1]),
        float(ardistmep[2]),
        float(ardistmep[3]),
    )

    p1_mod = arCoord_hole[0][0][:2]
    if pos_guss == "TL":
        if p1_mod[1] < p1mod_tai[1]:
            p1_mod = p1mod_tai[:2]
    elif pos_guss == "TR":
        if p1_mod[1] < p2mod_tai[1]:
            p1_mod = p2mod_tai[:2]
    elif pos_guss == "BL":
        if p1_mod[1] > p4mod_tai[1]:
            p1_mod = p4mod_tai[:2]
    elif pos_guss == "BR":
        if p1_mod[1] > p3mod_tai[1]:
            p1_mod = p3mod_tai[:2]

    p2_mod = arCoord_hole[0][-1][:2]
    p1_mod = np.array(p1_mod, float)
    p2_mod = np.array(p2_mod, float)
    arcoord_guss = []
    shapeT, shapeB, shapeL, shapeR = (
        shape_taikeikou["T"],
        shape_taikeikou["B"],
        shape_taikeikou["L"],
        shape_taikeikou["R"],
    )

    if pos_guss == "TL":
        thick_vstiff = 0
        if vstiff_taikeikou:
            vstiff_left, vstiff_right = vstiff_taikeikou["L"], vstiff_taikeikou["R"]
            if vstiff_left:
                thick_vstiff, mat_vstiff, width_vstiff = vstiff_left
        if gau_gus == "A":
            pal1 = p1_3d + (thick_vstiff / 2) * DefMath.Normal_vector(p1_3d, p2_3d, p3_3d)
            pal2 = p1_3d + (100 + thick_vstiff / 2) * DefMath.Normal_vector(p1_3d, p2_3d, p3_3d)
            pal3 = p2_3d + (thick_vstiff / 2) * DefMath.Normal_vector(p1_3d, p2_3d, p3_3d)
        else:
            pal1 = p1_3d - (thick_vstiff / 2) * DefMath.Normal_vector(p1_3d, p2_3d, p3_3d)
            pal2 = p1_3d + (100 + thick_vstiff / 2) * DefMath.Normal_vector(p1_3d, p2_3d, p3_3d)
            pal3 = p2_3d - (thick_vstiff / 2) * DefMath.Normal_vector(p1_3d, p2_3d, p3_3d)

        # -------------------Tinh 2 diem side----------------
        ps1, pe1 = DefMath.Offset_Line(p1_mod, p2_mod, -dist_mepL)
        p3_mod = p1_mod.copy()
        p3_mod[0] += 100
        ps2, pe2 = DefMath.Offset_Line(p1_mod, p3_mod, dist_mepT)
        ps_side = DefMath.Intersec_line_line(ps1, pe1, ps2, pe2)
        arcoord_guss.append(ps_side)
        p3_mod = p2_mod.copy()
        p3_mod[0] += 100
        ps2, pe2 = DefMath.Offset_Line(p2_mod, p3_mod, -dist_mepB)
        pe_side = DefMath.Intersec_line_line(ps1, pe1, ps2, pe2)
        arcoord_guss.append(pe_side)

        # -------------------Tinh 2 diem side in----------------
        ps1, pe1 = DefMath.Offset_Line(p1_mod, p2_mod, dist_mepR)
        p3_mod = p1_mod.copy()
        p3_mod[0] += 100
        ps2, pe2 = DefMath.Offset_Line(p1_mod, p3_mod, dist_mepT)
        ps_sidein = DefMath.Intersec_line_line(ps1, pe1, ps2, pe2)
        arcoord_guss.append(ps_sidein)
        p3_mod = p2_mod.copy()
        p3_mod[0] += 100
        ps2, pe2 = DefMath.Offset_Line(p2_mod, p3_mod, -dist_mepB)
        pe_sidein = DefMath.Intersec_line_line(ps1, pe1, ps2, pe2)
        arcoord_guss.append(pe_sidein)

        # -------------------Tinh 2 diem shapeL----------------
        P_Shape2_Auto = None
        if DistShape2 == "Auto":
            ps2 = np.array(pe_side).copy()
            pe2 = np.array(pe_side).copy()
            pe2[0] += 100
            P_Shape2_Auto = DefMath.Intersec_line_line(p1mod_tai[:2], p5mod_tai[:2], ps2[:2], pe2[:2])
            arcoord_guss.append(P_Shape2_Auto)
        else:
            P_Shape2_Auto = None
            if DistShape2 != 0:
                type_shape, size_shape, mat_shape, dir_shape, distmodY_shape, pitchmod_shape = shapeL
                p1mod_shape, p2mod_shape = Calculate_Pse_Shape(pitchmod_shape, p1mod_tai, p5mod_tai)
                arcoord_guss.append(DefMath.Point_on_line(p1mod_shape, p2mod_shape, DistShape2))
        # -------------------Tinh 2 diem shapeT----------------
        if DistShape1 == "Auto":
            if P_Shape2_Auto is not None:
                ps1 = np.array(P_Shape2_Auto).copy()
                pe1 = DefMath.Point_on_parallel_line(ps1, pe_side, ps_side, 100)
                ps2 = np.array(ps_sidein).copy()
                pe2 = DefMath.Point_on_parallel_line(ps_sidein, p1mod_tai, p2mod_tai, 100)
                arcoord_guss.append(DefMath.Intersec_line_line(ps1[:2], pe1[:2], ps2[:2], pe2[:2]))
            else:
                print(f"Trường hợp ShapeT =  {DistShape1} mà ShapeL = {DistShape2} chưa phát triển")
        else:
            if DefMath.is_number(DistShape1) == False:
                arDistShape1 = DistShape1.split("/")
                DistShape1 = float(arDistShape1[0])
                luong_nho_shape1 = float(arDistShape1[1])
            else:
                luong_nho_shape1 = 0
            type_shape, size_shape, mat_shape, dir_shape, distmodY_shape, pitchmod_shape = shapeT
            ar_size_shape = size_shape.split("x")
            p1mod_shape, p2mod_shape = Calculate_Pse_Shape(pitchmod_shape, p1mod_tai, p2mod_tai)
            ps1 = DefMath.Point_on_line(p1mod_shape, p2mod_shape, DistShape1)
            pe1 = DefMath.Point_on_parallel_line(ps1, ps_side, pe_side, 100)
            ps2 = np.array(ps_sidein).copy()
            pe2 = DefMath.Point_on_parallel_line(ps_sidein, p1mod_tai, p2mod_tai, 100)
            arcoord_guss.append(DefMath.Intersec_line_line(ps1[:2], pe1[:2], ps2[:2], pe2[:2]))
            if dir_shape == "U":
                ps2, pe2 = DefMath.Offset_Line(
                    p1mod_shape, p2mod_shape, -(float(ar_size_shape[0]) - distmodY_shape + luong_nho_shape1)
                )
            else:
                ps2, pe2 = DefMath.Offset_Line(p1mod_shape, p2mod_shape, -distmodY_shape)
            arcoord_guss.append(DefMath.Intersec_line_line(ps1[:2], pe1[:2], ps2[:2], pe2[:2]))

        # -------------------------------------------------------
        arcoord_guss = DefMath.sort_points_clockwise_2D(arcoord_guss)
        if gau_gus == "A":
            solid_guss = DefIFC.extrude_profile_and_align(ifc_file, arcoord_guss, thick_guss, pal1, pal2, pal3)
        else:
            solid_guss = DefIFC.extrude_profile_and_align(ifc_file, arcoord_guss, -thick_guss, pal1, pal2, pal3)

    elif pos_guss == "TR":
        thick_vstiff = 0
        if vstiff_taikeikou:
            vstiff_left, vstiff_right = vstiff_taikeikou["L"], vstiff_taikeikou["R"]
            if vstiff_left:
                thick_vstiff, mat_vstiff, width_vstiff = vstiff_right
        if gau_gus == "A":
            pal1 = p1_3d + (thick_vstiff / 2) * DefMath.Normal_vector(p1_3d, p2_3d, p3_3d)
            pal2 = p1_3d + (100 + thick_vstiff / 2) * DefMath.Normal_vector(p1_3d, p2_3d, p3_3d)
            pal3 = p2_3d + (thick_vstiff / 2) * DefMath.Normal_vector(p1_3d, p2_3d, p3_3d)
        else:
            pal1 = p1_3d - (thick_vstiff / 2) * DefMath.Normal_vector(p1_3d, p2_3d, p3_3d)
            pal2 = p1_3d + (100 + thick_vstiff / 2) * DefMath.Normal_vector(p1_3d, p2_3d, p3_3d)
            pal3 = p2_3d - (thick_vstiff / 2) * DefMath.Normal_vector(p1_3d, p2_3d, p3_3d)

        # -------------------Tinh 2 diem side----------------
        ps1, pe1 = DefMath.Offset_Line(p1_mod, p2_mod, dist_mepR)
        p3_mod = p1_mod.copy()
        p3_mod[0] += 100
        ps2, pe2 = DefMath.Offset_Line(p1_mod, p3_mod, dist_mepT)
        ps_side = DefMath.Intersec_line_line(ps1, pe1, ps2, pe2)
        arcoord_guss.append(ps_side)
        p3_mod = p2_mod.copy()
        p3_mod[0] += 100
        ps2, pe2 = DefMath.Offset_Line(p2_mod, p3_mod, -dist_mepB)
        pe_side = DefMath.Intersec_line_line(ps1, pe1, ps2, pe2)
        arcoord_guss.append(pe_side)
        # -------------------Tinh 2 diem side in----------------
        ps1, pe1 = DefMath.Offset_Line(p1_mod, p2_mod, -dist_mepL)
        p3_mod = p1_mod.copy()
        p3_mod[0] += 100
        ps2, pe2 = DefMath.Offset_Line(p1_mod, p3_mod, dist_mepT)
        ps_sidein = DefMath.Intersec_line_line(ps1, pe1, ps2, pe2)
        arcoord_guss.append(ps_sidein)
        p3_mod = p2_mod.copy()
        p3_mod[0] += 100
        ps2, pe2 = DefMath.Offset_Line(p2_mod, p3_mod, -dist_mepB)
        pe_sidein = DefMath.Intersec_line_line(ps1, pe1, ps2, pe2)
        arcoord_guss.append(pe_sidein)

        # -------------------Tinh 2 diem shapeR-------------------
        if DistShape2 == "Auto":
            ps2 = np.array(pe_side).copy()
            pe2 = np.array(pe_side).copy()
            pe2[0] -= 100
            P_Shape2_Auto = DefMath.Intersec_line_line(p2mod_tai[:2], p5mod_tai[:2], ps2[:2], pe2[:2])
            arcoord_guss.append(P_Shape2_Auto)
        else:
            P_Shape2_Auto = None
            if DistShape2 != 0:
                type_shape, size_shape, mat_shape, dir_shape, distmodY_shape, pitchmod_shape = shapeR
                p1mod_shape, p2mod_shape = Calculate_Pse_Shape(pitchmod_shape, p2mod_tai, p5mod_tai)
                arcoord_guss.append(DefMath.Point_on_line(p1mod_shape, p2mod_shape, DistShape2))

        # -------------------Tinh 2 diem shapeT-------------------
        if DistShape1 == "Auto":
            if P_Shape2_Auto is not None:
                ps1 = np.array(P_Shape2_Auto).copy()
                pe1 = DefMath.Point_on_parallel_line(ps1, pe_side, ps_side, 100)
                ps2 = np.array(ps_sidein).copy()
                pe2 = DefMath.Point_on_parallel_line(ps_sidein, p1mod_tai, p2mod_tai, 100)
                arcoord_guss.append(DefMath.Intersec_line_line(ps1[:2], pe1[:2], ps2[:2], pe2[:2]))
            else:
                print(f"Trường hợp ShapeT =  {DistShape1} mà ShapeR = {DistShape2} chưa phát triển")
        else:
            if DefMath.is_number(DistShape1) == False:
                arDistShape1 = DistShape1.split("/")
                DistShape1 = float(arDistShape1[0])
                luong_nho_shape1 = float(arDistShape1[1])
            else:
                luong_nho_shape1 = 0
            type_shape, size_shape, mat_shape, dir_shape, distmodY_shape, pitchmod_shape = shapeT
            ar_size_shape = size_shape.split("x")
            p1mod_shape, p2mod_shape = Calculate_Pse_Shape(pitchmod_shape, p1mod_tai, p2mod_tai)
            ps1 = DefMath.Point_on_line(p2mod_shape, p1mod_shape, DistShape1)
            pe1 = DefMath.Point_on_parallel_line(ps1, ps_side, pe_side, 100)
            ps2 = np.array(ps_sidein).copy()
            pe2 = DefMath.Point_on_parallel_line(ps_sidein, p1mod_tai, p2mod_tai, 100)
            arcoord_guss.append(DefMath.Intersec_line_line(ps1[:2], pe1[:2], ps2[:2], pe2[:2]))
            if dir_shape == "U":
                ps2, pe2 = DefMath.Offset_Line(
                    p1mod_shape, p2mod_shape, -(float(ar_size_shape[0]) - distmodY_shape + luong_nho_shape1)
                )
            else:
                ps2, pe2 = DefMath.Offset_Line(p1mod_shape, p2mod_shape, -distmodY_shape)
            arcoord_guss.append(DefMath.Intersec_line_line(ps1[:2], pe1[:2], ps2[:2], pe2[:2]))

        # -------------------------------------------------------
        arcoord_guss = DefMath.sort_points_clockwise_2D(arcoord_guss)
        if gau_gus == "A":
            solid_guss = DefIFC.extrude_profile_and_align(ifc_file, arcoord_guss, thick_guss, pal1, pal2, pal3)
        else:
            solid_guss = DefIFC.extrude_profile_and_align(ifc_file, arcoord_guss, -thick_guss, pal1, pal2, pal3)

    elif pos_guss == "BL":
        thick_vstiff = 0
        if vstiff_taikeikou:
            vstiff_left, vstiff_right = vstiff_taikeikou["L"], vstiff_taikeikou["R"]
            if vstiff_left:
                thick_vstiff, mat_vstiff, width_vstiff = vstiff_left
        if gau_gus == "A":
            pal1 = p1_3d + (thick_vstiff / 2) * DefMath.Normal_vector(p1_3d, p2_3d, p3_3d)
            pal2 = p1_3d + (100 + thick_vstiff / 2) * DefMath.Normal_vector(p1_3d, p2_3d, p3_3d)
            pal3 = p2_3d + (thick_vstiff / 2) * DefMath.Normal_vector(p1_3d, p2_3d, p3_3d)
        else:
            pal1 = p1_3d - (thick_vstiff / 2) * DefMath.Normal_vector(p1_3d, p2_3d, p3_3d)
            pal2 = p1_3d + (100 + thick_vstiff / 2) * DefMath.Normal_vector(p1_3d, p2_3d, p3_3d)
            pal3 = p2_3d - (thick_vstiff / 2) * DefMath.Normal_vector(p1_3d, p2_3d, p3_3d)

        # -------------------Tinh 2 diem side----------------
        ps1, pe1 = DefMath.Offset_Line(p1_mod, p2_mod, dist_mepL)
        p3_mod = p1_mod.copy()
        p3_mod[0] += 100
        ps2, pe2 = DefMath.Offset_Line(p1_mod, p3_mod, -dist_mepB)
        ps_side = DefMath.Intersec_line_line(ps1, pe1, ps2, pe2)
        arcoord_guss.append(ps_side)
        p3_mod = p2_mod.copy()
        p3_mod[0] += 100
        ps2, pe2 = DefMath.Offset_Line(p2_mod, p3_mod, dist_mepT)
        pe_side = DefMath.Intersec_line_line(ps1, pe1, ps2, pe2)
        arcoord_guss.append(pe_side)
        # -------------------Tinh 2 diem side in----------------
        ps1, pe1 = DefMath.Offset_Line(p1_mod, p2_mod, -dist_mepR)
        p3_mod = p1_mod.copy()
        p3_mod[0] += 100
        ps2, pe2 = DefMath.Offset_Line(p1_mod, p3_mod, -dist_mepB)
        ps_sidein = DefMath.Intersec_line_line(ps1, pe1, ps2, pe2)
        arcoord_guss.append(ps_sidein)
        p3_mod = p2_mod.copy()
        p3_mod[0] += 100
        ps2, pe2 = DefMath.Offset_Line(p2_mod, p3_mod, dist_mepT)
        pe_sidein = DefMath.Intersec_line_line(ps1, pe1, ps2, pe2)
        arcoord_guss.append(pe_sidein)

        # -------------------Tinh 2 diem shapeL----------------
        if DistShape2 == "Auto":
            ps2 = np.array(pe_side).copy()
            pe2 = np.array(pe_side).copy()
            pe2[0] += 100
            P_Shape2_Auto = DefMath.Intersec_line_line(p4mod_tai[:2], p5mod_tai[:2], ps2[:2], pe2[:2])
            arcoord_guss.append(P_Shape2_Auto)
        else:
            P_Shape2_Auto = None
            if DistShape2 != 0:
                type_shape, size_shape, mat_shape, dir_shape, distmodY_shape, pitchmod_shape = shapeL
                p1mod_shape, p2mod_shape = Calculate_Pse_Shape(pitchmod_shape, p4mod_tai, p5mod_tai)
                arcoord_guss.append(DefMath.Point_on_line(p1mod_shape, p2mod_shape, DistShape2))

        # -------------------Tinh 2 diem shapeB----------------
        if DistShape1 == "Auto":
            if P_Shape2_Auto is not None:
                ps1 = np.array(P_Shape2_Auto).copy()
                pe1 = DefMath.Point_on_parallel_line(ps1, pe_side, ps_side, 100)
                ps2 = np.array(ps_sidein).copy()
                pe2 = DefMath.Point_on_parallel_line(ps_sidein, p1mod_tai, p2mod_tai, 100)
                arcoord_guss.append(DefMath.Intersec_line_line(ps1[:2], pe1[:2], ps2[:2], pe2[:2]))
            else:
                print(f"Trường hợp ShapeT =  {DistShape1} mà ShapeL = {DistShape2} chưa phát triển")
        else:
            if DefMath.is_number(DistShape1) == False:
                arDistShape1 = DistShape1.split("/")
                DistShape1 = float(arDistShape1[0])
                luong_nho_shape1 = float(arDistShape1[1])
            else:
                luong_nho_shape1 = 0
            type_shape, size_shape, mat_shape, dir_shape, distmodY_shape, pitchmod_shape = shapeB
            ar_size_shape = size_shape.split("x")
            p1mod_shape, p2mod_shape = Calculate_Pse_Shape(pitchmod_shape, p4mod_tai, p3mod_tai)
            ps1 = DefMath.Point_on_line(p1mod_shape, p2mod_shape, DistShape1)
            pe1 = DefMath.Point_on_parallel_line(ps1, ps_side, pe_side, 100)
            ps2 = np.array(ps_sidein).copy()
            pe2 = DefMath.Point_on_parallel_line(ps_sidein, p4mod_tai, p3mod_tai, 100)
            arcoord_guss.append(DefMath.Intersec_line_line(ps1[:2], pe1[:2], ps2[:2], pe2[:2]))
            if dir_shape == "U":
                ps2, pe2 = DefMath.Offset_Line(p1mod_shape, p2mod_shape, distmodY_shape + luong_nho_shape1)
            else:
                ps2, pe2 = DefMath.Offset_Line(
                    p1mod_shape, p2mod_shape, (float(ar_size_shape[0]) - distmodY_shape + luong_nho_shape1)
                )
            arcoord_guss.append(DefMath.Intersec_line_line(ps1[:2], pe1[:2], ps2[:2], pe2[:2]))

        # -------------------------------------------------------
        arcoord_guss = DefMath.sort_points_clockwise_2D(arcoord_guss)
        if gau_gus == "A":
            solid_guss = DefIFC.extrude_profile_and_align(ifc_file, arcoord_guss, thick_guss, pal1, pal2, pal3)
        else:
            solid_guss = DefIFC.extrude_profile_and_align(ifc_file, arcoord_guss, -thick_guss, pal1, pal2, pal3)

    elif pos_guss == "BR":
        thick_vstiff = 0
        if vstiff_taikeikou:
            vstiff_left, vstiff_right = vstiff_taikeikou["L"], vstiff_taikeikou["R"]
            if vstiff_left:
                thick_vstiff, mat_vstiff, width_vstiff = vstiff_right
        if gau_gus == "A":
            pal1 = p1_3d + (thick_vstiff / 2) * DefMath.Normal_vector(p1_3d, p2_3d, p3_3d)
            pal2 = p1_3d + (100 + thick_vstiff / 2) * DefMath.Normal_vector(p1_3d, p2_3d, p3_3d)
            pal3 = p2_3d + (thick_vstiff / 2) * DefMath.Normal_vector(p1_3d, p2_3d, p3_3d)
        else:
            pal1 = p1_3d - (thick_vstiff / 2) * DefMath.Normal_vector(p1_3d, p2_3d, p3_3d)
            pal2 = p1_3d + (100 + thick_vstiff / 2) * DefMath.Normal_vector(p1_3d, p2_3d, p3_3d)
            pal3 = p2_3d - (thick_vstiff / 2) * DefMath.Normal_vector(p1_3d, p2_3d, p3_3d)

        # -------------------Tinh 2 diem side----------------
        ps1, pe1 = DefMath.Offset_Line(p1_mod, p2_mod, -dist_mepR)
        p3_mod = p1_mod.copy()
        p3_mod[0] += 100
        ps2, pe2 = DefMath.Offset_Line(p1_mod, p3_mod, -dist_mepB)
        ps_side = DefMath.Intersec_line_line(ps1, pe1, ps2, pe2)
        arcoord_guss.append(ps_side)
        p3_mod = p2_mod.copy()
        p3_mod[0] += 100
        ps2, pe2 = DefMath.Offset_Line(p2_mod, p3_mod, dist_mepT)
        pe_side = DefMath.Intersec_line_line(ps1, pe1, ps2, pe2)
        arcoord_guss.append(pe_side)
        # -------------------Tinh 2 diem side in----------------
        ps1, pe1 = DefMath.Offset_Line(p1_mod, p2_mod, dist_mepL)
        p3_mod = p1_mod.copy()
        p3_mod[0] += 100
        ps2, pe2 = DefMath.Offset_Line(p1_mod, p3_mod, -dist_mepB)
        ps_sidein = DefMath.Intersec_line_line(ps1, pe1, ps2, pe2)
        arcoord_guss.append(ps_sidein)
        p3_mod = p2_mod.copy()
        p3_mod[0] += 100
        ps2, pe2 = DefMath.Offset_Line(p2_mod, p3_mod, dist_mepT)
        pe_sidein = DefMath.Intersec_line_line(ps1, pe1, ps2, pe2)
        arcoord_guss.append(pe_sidein)

        # -------------------Tinh 2 diem shapeR-------------------
        if DistShape2 == "Auto":
            ps2 = np.array(pe_side).copy()
            pe2 = np.array(pe_side).copy()
            pe2[0] -= 100
            P_Shape2_Auto = DefMath.Intersec_line_line(p3mod_tai[:2], p5mod_tai[:2], ps2[:2], pe2[:2])
            arcoord_guss.append(P_Shape2_Auto)
        else:
            P_Shape2_Auto = None
            if DistShape2 != 0:
                type_shape, size_shape, mat_shape, dir_shape, distmodY_shape, pitchmod_shape = shapeR
                p1mod_shape, p2mod_shape = Calculate_Pse_Shape(pitchmod_shape, p3mod_tai, p5mod_tai)
                arcoord_guss.append(DefMath.Point_on_line(p1mod_shape, p2mod_shape, DistShape2))

        # -------------------Tinh 2 diem shapeB----------------
        if DistShape1 == "Auto":
            if P_Shape2_Auto is not None:
                ps1 = np.array(P_Shape2_Auto).copy()
                pe1 = DefMath.Point_on_parallel_line(ps1, pe_side, ps_side, 100)
                ps2 = np.array(ps_sidein).copy()
                pe2 = DefMath.Point_on_parallel_line(ps_sidein, p1mod_tai, p2mod_tai, 100)
                arcoord_guss.append(DefMath.Intersec_line_line(ps1[:2], pe1[:2], ps2[:2], pe2[:2]))
            else:
                print(f"Trường hợp ShapeT =  {DistShape1} mà ShapeR = {DistShape2} chưa phát triển")
        else:
            if DefMath.is_number(DistShape1) == False:
                arDistShape1 = DistShape1.split("/")
                DistShape1 = float(arDistShape1[0])
                luong_nho_shape1 = float(arDistShape1[1])
            else:
                luong_nho_shape1 = 0
            type_shape, size_shape, mat_shape, dir_shape, distmodY_shape, pitchmod_shape = shapeB
            ar_size_shape = size_shape.split("x")
            p1mod_shape, p2mod_shape = Calculate_Pse_Shape(pitchmod_shape, p4mod_tai, p3mod_tai)
            ps1 = DefMath.Point_on_line(p2mod_shape, p1mod_shape, DistShape1)
            pe1 = DefMath.Point_on_parallel_line(ps1, ps_side, pe_side, 100)
            ps2 = np.array(ps_sidein).copy()
            pe2 = DefMath.Point_on_parallel_line(ps_sidein, p4mod_tai, p3mod_tai, 100)
            arcoord_guss.append(DefMath.Intersec_line_line(ps1[:2], pe1[:2], ps2[:2], pe2[:2]))
            if dir_shape == "U":
                ps2, pe2 = DefMath.Offset_Line(p1mod_shape, p2mod_shape, distmodY_shape + luong_nho_shape1)
            else:
                ps2, pe2 = DefMath.Offset_Line(
                    p1mod_shape, p2mod_shape, (float(ar_size_shape[0]) - distmodY_shape + luong_nho_shape1)
                )
            arcoord_guss.append(DefMath.Intersec_line_line(ps1[:2], pe1[:2], ps2[:2], pe2[:2]))

        # -------------------------------------------------------
        arcoord_guss = DefMath.sort_points_clockwise_2D(arcoord_guss)
        if gau_gus == "A":
            solid_guss = DefIFC.extrude_profile_and_align(ifc_file, arcoord_guss, thick_guss, pal1, pal2, pal3)
        else:
            solid_guss = DefIFC.extrude_profile_and_align(ifc_file, arcoord_guss, -thick_guss, pal1, pal2, pal3)

    elif pos_guss == "MID":
        thick_vstiff = 0
        if vstiff_taikeikou:
            vstiff_left, vstiff_right = vstiff_taikeikou["L"], vstiff_taikeikou["R"]
            if vstiff_left:
                thick_vstiff, mat_vstiff, width_vstiff = vstiff_right
        if gau_gus == "A":
            pal1 = p1_3d + (thick_vstiff / 2) * DefMath.Normal_vector(p1_3d, p2_3d, p3_3d)
            pal2 = p1_3d + (100 + thick_vstiff / 2) * DefMath.Normal_vector(p1_3d, p2_3d, p3_3d)
            pal3 = p2_3d + (thick_vstiff / 2) * DefMath.Normal_vector(p1_3d, p2_3d, p3_3d)
        else:
            pal1 = p1_3d - (thick_vstiff / 2) * DefMath.Normal_vector(p1_3d, p2_3d, p3_3d)
            pal2 = p1_3d + (100 + thick_vstiff / 2) * DefMath.Normal_vector(p1_3d, p2_3d, p3_3d)
            pal3 = p2_3d - (thick_vstiff / 2) * DefMath.Normal_vector(p1_3d, p2_3d, p3_3d)

        # -------------------Tinh diem shapeL----------------
        type_shape, size_shape, mat_shape, dir_shape, distmodY_shape, pitchmod_shape = shapeL
        if typ_taikeikou == "Type1D":
            p1mod_shape, p2mod_shape = Calculate_Pse_Shape(pitchmod_shape, p1mod_tai, p5mod_tai)
        elif typ_taikeikou == "Type1U":
            p1mod_shape, p2mod_shape = Calculate_Pse_Shape(pitchmod_shape, p4mod_tai, p5mod_tai)
        else:
            print(f"Trường hợp type taikeikou là {typ_taikeikou} chưa phát triển")
        p1mod_guss = DefMath.Point_on_line(p2mod_shape, p1mod_shape, DistShape1)
        arcoord_guss.append(p1mod_guss)
        # -------------------Tinh diem shapeR----------------
        type_shape, size_shape, mat_shape, dir_shape, distmodY_shape, pitchmod_shape = shapeR
        if typ_taikeikou == "Type1D":
            p1mod_shape, p2mod_shape = Calculate_Pse_Shape(pitchmod_shape, p2mod_tai, p5mod_tai)
        elif typ_taikeikou == "Type1U":
            p1mod_shape, p2mod_shape = Calculate_Pse_Shape(pitchmod_shape, p3mod_tai, p5mod_tai)
        else:
            print(f"Trường hợp type taikeikou là {typ_taikeikou} chưa phát triển")
        p2mod_guss = DefMath.Point_on_line(p2mod_shape, p1mod_shape, DistShape2)
        arcoord_guss.append(p2mod_guss)
        # ------------------tinh 2 diem canh duoi-------------
        if typ_taikeikou == "Type1D":
            ps2, pe2 = DefMath.Offset_Line(p4mod_tai, p3mod_tai, -float(infor_guss[5]))
        elif typ_taikeikou == "Type1U":
            ps2, pe2 = DefMath.Offset_Line(p1mod_tai, p2mod_tai, float(infor_guss[5]))
        else:
            print(f"Trường hợp type taikeikou là {typ_taikeikou} chưa phát triển")

        arcoord_guss.append(DefMath.point_per_line(p1mod_guss, ps2, pe2))
        arcoord_guss.append(DefMath.point_per_line(p2mod_guss, ps2, pe2))

        # -------------------------------------------------------
        arcoord_guss = DefMath.sort_points_clockwise_2D(arcoord_guss)
        if gau_gus == "A":
            solid_guss = DefIFC.extrude_profile_and_align(ifc_file, arcoord_guss, thick_guss, pal1, pal2, pal3)
        else:
            solid_guss = DefIFC.extrude_profile_and_align(ifc_file, arcoord_guss, -thick_guss, pal1, pal2, pal3)

    return solid_guss
