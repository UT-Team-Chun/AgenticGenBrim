"""
鋼橋IFCモデル生成 - スロット生成モジュール
スロット（切り欠き）生成関連関数
"""


from src.bridge_json_to_ifc.ifc_utils_new.core import DefIFC, DefMath
from src.bridge_json_to_ifc.ifc_utils_new.io import DefStrings
from src.bridge_json_to_ifc.ifc_utils_new.utils import DefBridgeUtils

# グローバル変数: ログファイル出力関数（DefBridge.pyから設定される）
log_print_func = None


def _log_print(*args, **kwargs):
    """ログファイル出力関数（DEBUG_MODE時のみ出力）"""
    if log_print_func:
        log_print_func(*args, **kwargs)


def Draw_3DSolid_Slot_WebSection(
    ifc_all,
    MainPanel_data,
    Senkei_data,
    Mem_Rib_data,
    Member_Data,
    headname1_block_mainpanel,
    headname2_block_mainpanel,
    Name_Slot,
    pos,
    P1_Dia,
    P2_Dia,
    P3_Dia,
):
    # 遅延インポートで循環依存を回避
    from src.bridge_json_to_ifc.ifc_utils_new.components import DefStiffener

    solid_slot_original = None
    ifc_file, bridge_span, geom_context = ifc_all
    if Name_Slot != "N":
        if pos == "T":
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
                    Lrib_panel = panel["Lrib"]
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
                        Lrib_panel = panel["Lrib"]
                        dem += 1
                        break
            if dem != 0:
                thick1_panel, thick2_panel, mat_panel = (
                    Mat_mainpanel["Thick1"],
                    Mat_mainpanel["Thick2"],
                    Mat_mainpanel["Mat"],
                )
                if Lrib_panel:
                    Line_LRib, Pitch_LRib, NamePoint_LRib = Lrib_panel[0]
                    NamePoint_LRib = DefStrings.Chuyen_Name_LRib_thanh_Array(NamePoint_LRib)
                    Line_LRib = Line_LRib.split("-")
                    arCoordLines_Lrib = DefBridgeUtils.Load_Coordinate_Panel(Senkei_data, Line_LRib, Sec_mainpanel)
                    arCoordLines_Lrib = DefStiffener.Devide_Coord_LRib(arCoordLines_Lrib, Pitch_LRib)
                    for i_1 in range(1, len(Lrib_panel)):
                        solid_slot = Draw_Slot_LRib(
                            ifc_all,
                            Name_Slot,
                            Mem_Rib_data,
                            Member_Data,
                            Lrib_panel[i_1],
                            arCoordLines_Lrib,
                            NamePoint_LRib,
                            Sec_mainpanel,
                            thick1_panel,
                            thick2_panel,
                            P1_Dia,
                            P2_Dia,
                            P3_Dia,
                        )
                        if solid_slot_original is not None:
                            if solid_slot is not None:
                                solid_slot_original = ifc_file.createIfcBooleanResult(
                                    "UNION", solid_slot_original, solid_slot
                                )
                        else:
                            if solid_slot is not None:
                                solid_slot_original = solid_slot

            # face 2
            if headname1_block_mainpanel != headname2_block_mainpanel:
                name_mainpanel = headname2_block_mainpanel + "UF"
                dem = 0
                for panel in MainPanel_data:
                    if panel["Name"] == name_mainpanel:
                        Line_mainpanel = panel["Line"]
                        Sec_mainpanel = panel["Sec"]
                        Type_mainpanel = panel["Type"]
                        Mat_mainpanel = panel["Material"]
                        Expand_mainpanel = panel["Expand"]
                        Lrib_panel = panel["Lrib"]
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
                            Lrib_panel = panel["Lrib"]
                            dem += 1
                            break
                if dem != 0:
                    thick1_panel, thick2_panel, mat_panel = (
                        Mat_mainpanel["Thick1"],
                        Mat_mainpanel["Thick2"],
                        Mat_mainpanel["Mat"],
                    )
                    if Lrib_panel:
                        Line_LRib, Pitch_LRib, NamePoint_LRib = Lrib_panel[0]
                        NamePoint_LRib = DefStrings.Chuyen_Name_LRib_thanh_Array(NamePoint_LRib)
                        Line_LRib = Line_LRib.split("-")
                        arCoordLines_Lrib = DefBridgeUtils.Load_Coordinate_Panel(Senkei_data, Line_LRib, Sec_mainpanel)
                        arCoordLines_Lrib = DefStiffener.Devide_Coord_LRib(arCoordLines_Lrib, Pitch_LRib)
                        for i_1 in range(1, len(Lrib_panel)):
                            solid_slot = Draw_Slot_LRib(
                                ifc_all,
                                Name_Slot,
                                Mem_Rib_data,
                                Member_Data,
                                Lrib_panel[i_1],
                                arCoordLines_Lrib,
                                NamePoint_LRib,
                                Sec_mainpanel,
                                thick1_panel,
                                thick2_panel,
                                P1_Dia,
                                P2_Dia,
                                P3_Dia,
                            )
                            if solid_slot_original is not None:
                                if solid_slot is not None:
                                    solid_slot_original = ifc_file.createIfcBooleanResult(
                                        "UNION", solid_slot_original, solid_slot
                                    )
                            else:
                                if solid_slot is not None:
                                    solid_slot_original = solid_slot

        elif pos == "B":
            # face 1
            name_mainpanel = headname1_block_mainpanel + "LF"
            dem = 0
            for panel in MainPanel_data:
                if panel["Name"] == name_mainpanel:
                    Line_mainpanel = panel["Line"]
                    Sec_mainpanel = panel["Sec"]
                    Type_mainpanel = panel["Type"]
                    Mat_mainpanel = panel["Material"]
                    Expand_mainpanel = panel["Expand"]
                    Lrib_panel = panel["Lrib"]
                    dem += 1
                    break
            if dem != 0:
                thick1_panel, thick2_panel, mat_panel = (
                    Mat_mainpanel["Thick1"],
                    Mat_mainpanel["Thick2"],
                    Mat_mainpanel["Mat"],
                )
                if Lrib_panel:
                    Line_LRib, Pitch_LRib, NamePoint_LRib = Lrib_panel[0]
                    NamePoint_LRib = DefStrings.Chuyen_Name_LRib_thanh_Array(NamePoint_LRib)
                    Line_LRib = Line_LRib.split("-")
                    arCoordLines_Lrib = DefBridgeUtils.Load_Coordinate_Panel(Senkei_data, Line_LRib, Sec_mainpanel)
                    arCoordLines_Lrib = DefStiffener.Devide_Coord_LRib(arCoordLines_Lrib, Pitch_LRib)
                    for i_1 in range(1, len(Lrib_panel)):
                        solid_slot = Draw_Slot_LRib(
                            ifc_all,
                            Name_Slot,
                            Mem_Rib_data,
                            Member_Data,
                            Lrib_panel[i_1],
                            arCoordLines_Lrib,
                            NamePoint_LRib,
                            Sec_mainpanel,
                            thick1_panel,
                            thick2_panel,
                            P1_Dia,
                            P2_Dia,
                            P3_Dia,
                        )
                        if solid_slot_original is not None:
                            if solid_slot is not None:
                                solid_slot_original = ifc_file.createIfcBooleanResult(
                                    "UNION", solid_slot_original, solid_slot
                                )
                        else:
                            if solid_slot is not None:
                                solid_slot_original = solid_slot

            # face 2
            if headname1_block_mainpanel != headname2_block_mainpanel:
                name_mainpanel = headname2_block_mainpanel + "LF"
                for panel in MainPanel_data:
                    if panel["Name"] == name_mainpanel:
                        Line_mainpanel = panel["Line"]
                        Sec_mainpanel = panel["Sec"]
                        Type_mainpanel = panel["Type"]
                        Mat_mainpanel = panel["Material"]
                        Expand_mainpanel = panel["Expand"]
                        Lrib_panel = panel["Lrib"]
                        dem += 1
                        break
                if dem != 0:
                    thick1_panel, thick2_panel, mat_panel = (
                        Mat_mainpanel["Thick1"],
                        Mat_mainpanel["Thick2"],
                        Mat_mainpanel["Mat"],
                    )
                    if Lrib_panel:
                        Line_LRib, Pitch_LRib, NamePoint_LRib = Lrib_panel[0]
                        NamePoint_LRib = DefStrings.Chuyen_Name_LRib_thanh_Array(NamePoint_LRib)
                        Line_LRib = Line_LRib.split("-")
                        arCoordLines_Lrib = DefBridgeUtils.Load_Coordinate_Panel(Senkei_data, Line_LRib, Sec_mainpanel)
                        arCoordLines_Lrib = DefStiffener.Devide_Coord_LRib(arCoordLines_Lrib, Pitch_LRib)
                        for i_1 in range(1, len(Lrib_panel)):
                            solid_slot = Draw_Slot_LRib(
                                ifc_all,
                                Name_Slot,
                                Mem_Rib_data,
                                Member_Data,
                                Lrib_panel[i_1],
                                arCoordLines_Lrib,
                                NamePoint_LRib,
                                Sec_mainpanel,
                                thick1_panel,
                                thick2_panel,
                                P1_Dia,
                                P2_Dia,
                                P3_Dia,
                            )
                            if solid_slot_original is not None:
                                if solid_slot is not None:
                                    solid_slot_original = ifc_file.createIfcBooleanResult(
                                        "UNION", solid_slot_original, solid_slot
                                    )
                            else:
                                if solid_slot is not None:
                                    solid_slot_original = solid_slot

        elif pos == "L":
            # face 1
            name_mainpanel = headname1_block_mainpanel + "WL"
            dem = 0
            for panel in MainPanel_data:
                if panel["Name"] == name_mainpanel:
                    Line_mainpanel = panel["Line"]
                    Sec_mainpanel = panel["Sec"]
                    Type_mainpanel = panel["Type"]
                    Mat_mainpanel = panel["Material"]
                    Expand_mainpanel = panel["Expand"]
                    Vstiff_panel = panel["Vstiff"]
                    Hstiff_panel = panel["Hstiff"]
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
                        Vstiff_panel = panel["Vstiff"]
                        Hstiff_panel = panel["Hstiff"]
                        dem += 1
                        break
            if dem != 0:
                thick1_panel, thick2_panel, mat_panel = (
                    Mat_mainpanel["Thick1"],
                    Mat_mainpanel["Thick2"],
                    Mat_mainpanel["Mat"],
                )
                if Hstiff_panel:
                    Line_Hstiff, Pitch_Hstiff, NamePoint_Hstiff = Hstiff_panel[0]
                    NamePoint_Hstiff = DefStrings.Chuyen_Name_LRib_thanh_Array(NamePoint_Hstiff)
                    Line_Hstiff = Line_Hstiff.split("-")
                    arCoordLines_Hstiff = DefBridgeUtils.Load_Coordinate_Panel(Senkei_data, Line_Hstiff, Sec_mainpanel)
                    arCoordLines_Hstiff = DefStiffener.Devide_Coord_LRib(arCoordLines_Hstiff, Pitch_Hstiff)
                    if Vstiff_panel:
                        if Vstiff_panel[0]:
                            type_devide, pitch_top, pitch_bot, namepoint = Vstiff_panel[0]
                            namepoint = DefStrings.Chuyen_Name_LRib_thanh_Array(namepoint)
                            arCoordLines_Hstiff_New, PosVstiff = DefStiffener.Devide_Pitch_Vstiff(
                                arCoordLines_Hstiff, Vstiff_panel[0]
                            )
                            arCoordLines_Hstiff, sec_panel_new = DefBridgeUtils.Combined_Sort_Coord_And_NameSec(
                                arCoordLines_Hstiff_New, namepoint, arCoordLines_Hstiff, Sec_mainpanel
                            )
                        else:
                            sec_panel_new = Sec_mainpanel

                    for i_1 in range(1, len(Hstiff_panel)):
                        solid_slot = Draw_Slot_HStiff(
                            ifc_all,
                            Name_Slot,
                            Mem_Rib_data,
                            Member_Data,
                            Hstiff_panel[i_1],
                            arCoordLines_Hstiff,
                            NamePoint_Hstiff,
                            sec_panel_new,
                            thick1_panel,
                            thick2_panel,
                            P1_Dia,
                            P2_Dia,
                            P3_Dia,
                        )

                        if solid_slot_original is not None:
                            if solid_slot is not None:
                                solid_slot_original = ifc_file.createIfcBooleanResult(
                                    "UNION", solid_slot_original, solid_slot
                                )
                        else:
                            if solid_slot is not None:
                                solid_slot_original = solid_slot

        elif pos == "R":
            # face 1
            name_mainpanel = headname1_block_mainpanel + "WR"
            dem = 0
            for panel in MainPanel_data:
                if panel["Name"] == name_mainpanel:
                    Line_mainpanel = panel["Line"]
                    Sec_mainpanel = panel["Sec"]
                    Type_mainpanel = panel["Type"]
                    Mat_mainpanel = panel["Material"]
                    Expand_mainpanel = panel["Expand"]
                    Vstiff_panel = panel["Vstiff"]
                    Hstiff_panel = panel["Hstiff"]
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
                        Vstiff_panel = panel["Vstiff"]
                        Hstiff_panel = panel["Hstiff"]
                        dem += 1
                        break
            if dem != 0:
                thick1_panel, thick2_panel, mat_panel = (
                    Mat_mainpanel["Thick1"],
                    Mat_mainpanel["Thick2"],
                    Mat_mainpanel["Mat"],
                )
                vstiffs = Vstiff_panel
                hstiffs = Hstiff_panel
                if hstiffs:
                    Line_Hstiff, Pitch_Hstiff, NamePoint_Hstiff = hstiffs[0]
                    NamePoint_Hstiff = DefStrings.Chuyen_Name_LRib_thanh_Array(NamePoint_Hstiff)
                    Line_Hstiff = Line_Hstiff.split("-")
                    arCoordLines_Hstiff = DefBridgeUtils.Load_Coordinate_Panel(Senkei_data, Line_Hstiff, Sec_mainpanel)
                    arCoordLines_Hstiff = DefStiffener.Devide_Coord_LRib(arCoordLines_Hstiff, Pitch_Hstiff)
                    if vstiffs:
                        if vstiffs[0]:
                            type_devide, pitch_top, pitch_bot, namepoint = vstiffs[0]
                            namepoint = DefStrings.Chuyen_Name_LRib_thanh_Array(namepoint)
                            arCoordLines_Hstiff_New, PosVstiff = DefStiffener.Devide_Pitch_Vstiff(
                                arCoordLines_Hstiff, vstiffs[0]
                            )
                            arCoordLines_Hstiff, sec_panel_new = DefBridgeUtils.Combined_Sort_Coord_And_NameSec(
                                arCoordLines_Hstiff_New, namepoint, arCoordLines_Hstiff, Sec_mainpanel
                            )
                        else:
                            sec_panel_new = Sec_mainpanel

                    for i_1 in range(1, len(hstiffs)):
                        solid_slot = Draw_Slot_HStiff(
                            ifc_all,
                            Name_Slot,
                            Mem_Rib_data,
                            Member_Data,
                            hstiffs[i_1],
                            arCoordLines_Hstiff,
                            NamePoint_Hstiff,
                            sec_panel_new,
                            thick1_panel,
                            thick2_panel,
                            P1_Dia,
                            P2_Dia,
                            P3_Dia,
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


def Draw_Slot_HStiff(
    ifc_all,
    Name_Slot,
    Mem_Rib_data,
    Member_data,
    infor_hstiff,
    arCoord_mod_panel,
    line_panel,
    sec_panel,
    thick1_panel,
    thick2_panel,
    P1_Dia,
    P2_Dia,
    P3_Dia,
):
    solid_slot_original = None
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
                Coords_Hstiff_Out = DefBridgeUtils.Calculate_Extend_Coord(Coords_Hstiff_Out, extendL_rib, "A")

            if DefMath.is_number(extendR_rib) == True:
                Coords_Hstiff_Out = DefBridgeUtils.Calculate_Extend_Coord(Coords_Hstiff_Out, extendR_rib, "F")

            arCoor1 = Coords_Hstiff_Out[0]
            arCoor2 = Coords_Hstiff_Out[1]
            p1_slot = None
            for i_2 in range(len(arCoor1) - 1):
                p = DefMath.Intersection_line_plane(P1_Dia, P2_Dia, P3_Dia, arCoor1[i_2], arCoor1[i_2 + 1])
                if p[0] >= arCoor1[i_2][0] and p[0] <= arCoor1[i_2 + 1][0]:
                    p1_slot = p
                    break
            p2_slot = None
            for i_2 in range(len(arCoor2) - 1):
                p = DefMath.Intersection_line_plane(P1_Dia, P2_Dia, P3_Dia, arCoor2[i_2], arCoor2[i_2 + 1])
                if p[0] >= arCoor2[i_2][0] and p[0] <= arCoor2[i_2 + 1][0]:
                    p2_slot = p
                    break

            if p1_slot is not None and p2_slot is not None:
                pal1_slot = p1_slot.copy()
                normal_p1p2p3 = DefMath.Normal_vector(P1_Dia, P2_Dia, P3_Dia)

                if side == "L":
                    pal2_slot = p1_slot - 100 * normal_p1p2p3
                elif side == "R":
                    pal2_slot = p1_slot + 100 * normal_p1p2p3

                pal3_slot = DefMath.rotate_point_around_axis(p1_slot, pal2_slot, p2_slot, 90)
                # --------Slot tham chieu----------------------------------------
                for slot in Member_data:
                    if slot["Name"] == Name_Slot:
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


def Draw_Slot_LRib(
    ifc_all,
    Name_Slot,
    Mem_Rib_data,
    Member_data,
    infor_lrib,
    arCoordGrid_LRib,
    linesGrid,
    secsGrid,
    thick1_panel,
    thick2_panel,
    P1_Dia,
    P2_Dia,
    P3_Dia,
):
    solid_slot_original = None

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
            Coords_LRib_Mod.append(arCoor1)
            Coords_LRib_Mod.append(arCoor2)
        elif face_lrib == "T":
            arCoor1 = Coords_LRib_Mod2[0]
            arCoor2 = Coords_LRib_Mod1[0]
            Coords_LRib_Mod.append(arCoor1)
            Coords_LRib_Mod.append(arCoor2)

        # -----------Extend-------------------------------
        if DefMath.is_number(extendL_rib) == True:
            Coords_LRib_Out = DefBridgeUtils.Calculate_Extend_Coord(Coords_LRib_Mod, extendL_rib, "A")

        if DefMath.is_number(extendR_rib) == True:
            Coords_LRib_Out = DefBridgeUtils.Calculate_Extend_Coord(Coords_LRib_Out, extendR_rib, "F")

        if face_lrib == "B":
            arCoor1 = Coords_LRib_Out[0]
            arCoor2 = Coords_LRib_Out[1]
        elif face_lrib == "T":
            arCoor1 = Coords_LRib_Out[1]
            arCoor2 = Coords_LRib_Out[0]

        p1_slot = None
        for i_2 in range(len(arCoor1) - 1):
            p = DefMath.Intersection_line_plane(P1_Dia, P2_Dia, P3_Dia, arCoor1[i_2], arCoor1[i_2 + 1])
            if p[0] >= arCoor1[i_2][0] and p[0] <= arCoor1[i_2 + 1][0]:
                p1_slot = p
                break
        p2_slot = None
        for i_2 in range(len(arCoor2) - 1):
            p = DefMath.Intersection_line_plane(P1_Dia, P2_Dia, P3_Dia, arCoor2[i_2], arCoor2[i_2 + 1])
            if p[0] >= arCoor2[i_2][0] and p[0] <= arCoor2[i_2 + 1][0]:
                p2_slot = p
                break

        if p1_slot is not None and p2_slot is not None:
            pal1_slot = p1_slot.copy()
            normal_p1p2p3 = DefMath.Normal_vector(P1_Dia, P2_Dia, P3_Dia)

            if face_lrib == "B":
                pal2_slot = p1_slot + 100 * normal_p1p2p3
            elif face_lrib == "T":
                pal2_slot = p1_slot - 100 * normal_p1p2p3

            pal3_slot = DefMath.rotate_point_around_axis(p1_slot, pal2_slot, p2_slot, 90)

            # --------参照スロット----------------------------------------
            for slot in Member_data:
                if slot["Name"] == Name_Slot:
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


def Draw_3Dsolid_Slot(ifc_file, p1_slot, p2_slot, WideL, WideR, R, pal1_slot, pal2_slot, pal3_slot):
    p1 = [0, 0]
    p1l = [-WideL, 0]
    p1r = [WideR, 0]
    p2 = [0, -DefMath.Calculate_distance_p2p(p1_slot, p2_slot)]
    p2l = [-R / 2, -DefMath.Calculate_distance_p2p(p1_slot, p2_slot)]
    p2r = [R / 2, -DefMath.Calculate_distance_p2p(p1_slot, p2_slot)]

    p1l_ex = DefMath.Point_on_line(p1l, p2l, -100)
    p1r_ex = DefMath.Point_on_line(p1r, p2r, -100)

    points_pol1 = [p1l_ex, p1r_ex]
    points_arc = DefMath.devide_arc_to_points_polyline(p2l, p2r, p2)
    points_arc.reverse()
    points_pol2 = [p1l_ex]
    points_slot = points_pol1 + points_arc + points_pol2

    solid_slot1 = DefIFC.extrude_profile_and_align(ifc_file, points_slot, 100, pal1_slot, pal2_slot, pal3_slot)
    solid_slot2 = DefIFC.extrude_profile_and_align(ifc_file, points_slot, -100, pal1_slot, pal2_slot, pal3_slot)

    solid_slot = ifc_file.createIfcBooleanResult("UNION", solid_slot1, solid_slot2)

    return solid_slot
