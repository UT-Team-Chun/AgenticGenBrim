"""
鋼橋IFCモデル生成 - サブパネル計算モジュール
サブパネル（ダイアフラム等）の座標計算と生成関数
"""

import numpy as np
import pandas as pd

from src.bridge_json_to_ifc.ifc_utils_new.components.DefComponent import Draw_Corner, Draw_Solid_CutOut
from src.bridge_json_to_ifc.ifc_utils_new.components.DefStiffener import (
    Calculate_SPL_Rib,
    Calculate_SPL_SubPanel,
    Calculate_Vstiff_Subpanel,
)
from src.bridge_json_to_ifc.ifc_utils_new.core import DefIFC, DefMath
from src.bridge_json_to_ifc.ifc_utils_new.io import DefStrings
from src.bridge_json_to_ifc.ifc_utils_new.utils.DefBridgeUtils import (
    Find_number_block_MainPanel,
)

# グローバル変数: ログファイル出力関数
log_print_func = None


def _log_print(*args, **kwargs):
    """ログファイル出力関数（DEBUG_MODE時のみ出力）"""
    if log_print_func:
        log_print_func(*args, **kwargs)


def Calculate_Part_SubPanel(
    ifc_all,
    Data_MainPanel,
    Senkei_data,
    Member_SPL_data,
    Mem_Rib_data,
    Member_Data,
    name_subpanel,
    girder_subpanel,
    sec_subpanel,
    part_subpanel,
    arNamePoint,
    arCoordPoint,
    data_part,
    side_export,
):
    """
    サブパネルの部品を計算して生成する

    ダイアフラムなどのサブパネル部品の座標を計算し、3Dソリッドを生成する。
    コーナーカット、スロット、ジョイント、補剛材、フランジの処理も含む。

    Args:
        ifc_all: (ifc_file, bridge_span, geom_context)のタプル
        Data_MainPanel: メインパネルデータの配列
        Senkei_data: 線形データ
        Member_SPL_data: 継手部材データ
        Mem_Rib_data: リブ部材データ
        Member_Data: 部材データ
        name_subpanel: サブパネル名称
        girder_subpanel: 桁名（例: "G1" または "G1-G2"）
        sec_subpanel: 断面範囲
        part_subpanel: 部品データの配列
        arNamePoint: 点名称の配列
        arCoordPoint: 座標点の配列
        data_part: 部品詳細データ
        side_export: 出力側面指定（2:両面, 1:表面のみ, -1:裏面のみ）
    """
    # 遅延インポート（循環依存回避）
    from src.bridge_json_to_ifc.ifc_utils_new.core.DefBridge import (
        Calculate_FLG_Subpanel,
        Draw_3DSolid_Slot_WebSection,
        Extend_Dia_Face,
        Extend_Dia_Number,
        Extend_Yokoketa_Face,
        Extend_Yokoketa_Face_FLG,
    )

    ifc_file, bridge_span, geom_context = ifc_all
    argirder_subpanel = girder_subpanel.split("-")
    if len(argirder_subpanel) == 1:
        girder1_dia = argirder_subpanel[0]
        girder2_dia = argirder_subpanel[0]
    else:
        girder1_dia = argirder_subpanel[0]
        girder2_dia = argirder_subpanel[1]

    number_block_list = Find_number_block_MainPanel(Data_MainPanel, sec_subpanel)
    # number_blockはリストで返されるので、最初の要素を使用
    number_block = number_block_list[0] if number_block_list else "1"
    headname1_block_mainpanel = girder1_dia + "B" + number_block
    headname2_block_mainpanel = girder2_dia + "B" + number_block
    (
        name_part,
        material_part,
        out_part,
        extends_part,
        corner_part,
        slot_part,
        joint_part,
        cutout_part,
        stiff_part,
        flg_part,
    ) = data_part
    thicka_part, thickf_part, mat_part = material_part["Thick1"], material_part["Thick2"], material_part["Mat"]
    outL, outR, outT, outB = out_part["L"], out_part["R"], out_part["T"], out_part["B"]
    outR.reverse()
    outT.reverse()
    extend_part = extends_part["L"], extends_part["R"], extends_part["T"], extends_part["B"]
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

    if len(argirder_subpanel) == 1:
        arCoord_Top_Out, arCoord_Bot_Out, arCoord_Left_Out, arCoord_Right_Out = Extend_Dia_Face(
            Data_MainPanel,
            Senkei_data,
            headname1_block_mainpanel,
            arCoord_Top,
            arCoord_Bot,
            arCoord_Left,
            arCoord_Right,
            extend_part,
        )
        arCoord_Top_Out, arCoord_Bot_Out, arCoord_Left_Out, arCoord_Right_Out = Extend_Yokoketa_Face_FLG(
            Mem_Rib_data,
            flg_part,
            name_part,
            arCoord_Top_Out,
            arCoord_Bot_Out,
            arCoord_Left_Out,
            arCoord_Right_Out,
            outT,
            outB,
            arNamePoint,
            arCoordPoint,
        )
    else:
        arCoord1_Top_Out, arCoord1_Bot_Out, arCoord1_Left_Out, arCoord1_Right_Out = Extend_Yokoketa_Face_FLG(
            Mem_Rib_data,
            flg_part,
            name_part,
            arCoord_Top,
            arCoord_Bot,
            arCoord_Left,
            arCoord_Right,
            outT,
            outB,
            arNamePoint,
            arCoordPoint,
        )

        arCoord2_Top_Out, arCoord2_Bot_Out, arCoord2_Left_Out, arCoord2_Right_Out = Extend_Yokoketa_Face(
            Data_MainPanel,
            Senkei_data,
            headname1_block_mainpanel,
            headname2_block_mainpanel,
            arCoord_Top,
            arCoord_Bot,
            arCoord_Left,
            arCoord_Right,
            extend_part,
        )

        arCoord_Left_Out = arCoord2_Left_Out
        arCoord_Right_Out = arCoord2_Right_Out
        arCoord_Top_Out = []
        if len(arCoord_Top) == 2:
            for i in range(len(arCoord_Top)):
                if not np.array_equal(arCoord1_Top_Out[i], arCoord_Top[i]):
                    arCoord_Top_Out.append(arCoord1_Top_Out[i])
                elif not np.array_equal(arCoord2_Top_Out[i], arCoord_Top[i]):
                    arCoord_Top_Out.append(arCoord2_Top_Out[i])
                else:
                    arCoord_Top_Out.append(arCoord_Top[i])
        else:
            for i in range(len(arCoord1_Top_Out)):
                if i == 0 or i == len(arCoord1_Top_Out) - 1:
                    if arCoord2_Top_Out[i][2] > arCoord1_Top_Out[i][2]:
                        arCoord_Top_Out.append(arCoord1_Top_Out[i])
                    else:
                        arCoord_Top_Out.append(arCoord2_Top_Out[i])
                else:
                    if (
                        abs(arCoord1_Top_Out[i][0] - arCoord2_Top_Out[i][0]) < 0.3
                        and abs(arCoord1_Top_Out[i][1] - arCoord2_Top_Out[i][1]) < 0.3
                        and abs(arCoord1_Top_Out[i][2] - arCoord2_Top_Out[i][2]) < 0.3
                    ):
                        arCoord_Top_Out.append(arCoord2_Top_Out[i])
                    else:
                        if i == 1:
                            if name_part == "P1":
                                if len(part_subpanel) == 1:
                                    arCoord_Top_Out.append(arCoord2_Top_Out[i])
                                    arCoord_Top_Out.append(arCoord1_Top_Out[i])
                                else:
                                    arCoord_Top_Out.append(arCoord1_Top_Out[i])
                                    arCoord_Top_Out.append(arCoord2_Top_Out[i])
                            else:
                                arCoord_Top_Out.append(arCoord2_Top_Out[i])
                                arCoord_Top_Out.append(arCoord1_Top_Out[i])
                        elif i == len(arCoord1_Top_Out) - 2:
                            arCoord_Top_Out.append(arCoord1_Top_Out[i])
                            arCoord_Top_Out.append(arCoord2_Top_Out[i])

        arCoord_Bot_Out = []
        if len(arCoord_Bot) == 2:
            for i in range(len(arCoord1_Bot_Out)):
                if not np.array_equal(arCoord1_Bot_Out[i], arCoord_Bot[i]):
                    arCoord_Bot_Out.append(arCoord1_Bot_Out[i])
                elif not np.array_equal(arCoord2_Bot_Out[i], arCoord_Bot[i]):
                    arCoord_Bot_Out.append(arCoord2_Bot_Out[i])
                else:
                    arCoord_Bot_Out.append(arCoord_Bot[i])
        else:
            for i in range(len(arCoord1_Bot_Out)):
                if i == 0 or i == len(arCoord1_Bot_Out) - 1:
                    if arCoord2_Bot_Out[i][2] < arCoord1_Bot_Out[i][2]:
                        arCoord_Bot_Out.append(arCoord1_Bot_Out[i])
                    else:
                        arCoord_Bot_Out.append(arCoord2_Bot_Out[i])
                else:
                    if (
                        abs(arCoord1_Bot_Out[i][0] - arCoord2_Bot_Out[i][0]) < 0.3
                        and abs(arCoord1_Bot_Out[i][1] - arCoord2_Bot_Out[i][1]) < 0.3
                        and abs(arCoord1_Bot_Out[i][2] - arCoord2_Bot_Out[i][2]) < 0.3
                    ):
                        arCoord_Bot_Out.append(arCoord2_Bot_Out[i])
                    else:
                        if i == len(arCoord1_Bot_Out) - 2:
                            arCoord_Bot_Out.append(arCoord1_Bot_Out[i])
                            arCoord_Bot_Out.append(arCoord2_Bot_Out[i])
                        elif i == 1:
                            arCoord_Bot_Out.append(arCoord2_Bot_Out[i])
                            arCoord_Bot_Out.append(arCoord1_Bot_Out[i])

    # 2D変換
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

    arCoord_Top_Out, arCoord_Bot_Out, arCoord_Left_Out, arCoord_Right_Out = Extend_Dia_Number(
        arCoord_Top_Out, arCoord_Bot_Out, arCoord_Left_Out, arCoord_Right_Out, extend_part
    )

    arPoint = []
    for i in range(0, len(arCoord_Left_Out)):
        arPoint.append(arCoord_Left_Out[i])
    for i in range(0, len(arCoord_Bot_Out)):
        arPoint.append(arCoord_Bot_Out[i])
    for i in range(0, len(arCoord_Right_Out)):
        arPoint.append(arCoord_Right_Out[i])
    for i in range(0, len(arCoord_Top_Out)):
        arPoint.append(arCoord_Top_Out[i])

    pal1 = p1_3d
    pal2 = DefMath.Offset_point(p1_3d, p2_3d, p3_3d, 100)
    pal3 = p2_3d

    if side_export == 2:
        Solid_Sub_Panel_A = DefIFC.extrude_profile_and_align(ifc_file, arPoint, thicka_part, pal1, pal2, pal3)
        Solid_Sub_Panel_F = DefIFC.extrude_profile_and_align(ifc_file, arPoint, -thickf_part, pal1, pal2, pal3)
    elif side_export == -1:
        Solid_Sub_Panel_A = DefIFC.extrude_profile_and_align(ifc_file, arPoint, thicka_part, pal1, pal2, pal3)
        Solid_Sub_Panel_F = None
    elif side_export == 1:
        Solid_Sub_Panel_A = None
        Solid_Sub_Panel_F = DefIFC.extrude_profile_and_align(ifc_file, arPoint, -thickf_part, pal1, pal2, pal3)

    # コーナーカット
    if corner_part:
        corner1, corner2, corner3, corner4 = corner_part
        if not pd.isnull(corner1) and corner1 != "N":
            pcorner = DefMath.Transform_point_face2face(arCoord_Top_Out[-1], p1_2d, p2_2d, p3_2d, p1_3d, p2_3d, p3_3d)
            pdirX = DefMath.Transform_point_face2face(arCoord_Top_Out[-2], p1_2d, p2_2d, p3_2d, p1_3d, p2_3d, p3_3d)
            pdirY = DefMath.Transform_point_face2face(arCoord_Left_Out[1], p1_2d, p2_2d, p3_2d, p1_3d, p2_3d, p3_3d)

            if Solid_Sub_Panel_A is not None:
                solid_corner1 = Draw_Corner(ifc_file, corner1, pcorner, pdirX, pdirY)
                Solid_Sub_Panel_A = ifc_file.createIfcBooleanResult("DIFFERENCE", Solid_Sub_Panel_A, solid_corner1)

            if Solid_Sub_Panel_F is not None:
                solid_corner2 = Draw_Corner(ifc_file, corner1, pcorner, pdirX, pdirY)
                Solid_Sub_Panel_F = ifc_file.createIfcBooleanResult("DIFFERENCE", Solid_Sub_Panel_F, solid_corner2)

        if not pd.isnull(corner2) and corner2 != "N":
            pcorner = DefMath.Transform_point_face2face(arCoord_Top_Out[0], p1_2d, p2_2d, p3_2d, p1_3d, p2_3d, p3_3d)
            pdirX = DefMath.Transform_point_face2face(arCoord_Top_Out[1], p1_2d, p2_2d, p3_2d, p1_3d, p2_3d, p3_3d)
            pdirY = DefMath.Transform_point_face2face(arCoord_Right_Out[-2], p1_2d, p2_2d, p3_2d, p1_3d, p2_3d, p3_3d)

            if Solid_Sub_Panel_A is not None:
                solid_corner1 = Draw_Corner(ifc_file, corner2, pcorner, pdirX, pdirY)
                Solid_Sub_Panel_A = ifc_file.createIfcBooleanResult("DIFFERENCE", Solid_Sub_Panel_A, solid_corner1)

            if Solid_Sub_Panel_F is not None:
                solid_corner2 = Draw_Corner(ifc_file, corner2, pcorner, pdirX, pdirY)
                Solid_Sub_Panel_F = ifc_file.createIfcBooleanResult("DIFFERENCE", Solid_Sub_Panel_F, solid_corner2)

        if not pd.isnull(corner3) and corner3 != "N":
            pcorner = DefMath.Transform_point_face2face(arCoord_Bot_Out[-1], p1_2d, p2_2d, p3_2d, p1_3d, p2_3d, p3_3d)
            pdirX = DefMath.Transform_point_face2face(arCoord_Bot_Out[-2], p1_2d, p2_2d, p3_2d, p1_3d, p2_3d, p3_3d)
            pdirY = DefMath.Transform_point_face2face(arCoord_Right_Out[1], p1_2d, p2_2d, p3_2d, p1_3d, p2_3d, p3_3d)

            if Solid_Sub_Panel_A is not None:
                solid_corner1 = Draw_Corner(ifc_file, corner3, pcorner, pdirX, pdirY)
                Solid_Sub_Panel_A = ifc_file.createIfcBooleanResult("DIFFERENCE", Solid_Sub_Panel_A, solid_corner1)

            if Solid_Sub_Panel_F is not None:
                solid_corner2 = Draw_Corner(ifc_file, corner3, pcorner, pdirX, pdirY)
                Solid_Sub_Panel_F = ifc_file.createIfcBooleanResult("DIFFERENCE", Solid_Sub_Panel_F, solid_corner2)

        if not pd.isnull(corner4) and corner4 != "N":
            pcorner = DefMath.Transform_point_face2face(arCoord_Bot_Out[0], p1_2d, p2_2d, p3_2d, p1_3d, p2_3d, p3_3d)
            pdirX = DefMath.Transform_point_face2face(arCoord_Bot_Out[1], p1_2d, p2_2d, p3_2d, p1_3d, p2_3d, p3_3d)
            pdirY = DefMath.Transform_point_face2face(arCoord_Left_Out[-2], p1_2d, p2_2d, p3_2d, p1_3d, p2_3d, p3_3d)

            if Solid_Sub_Panel_A is not None:
                solid_corner1 = Draw_Corner(ifc_file, corner4, pcorner, pdirX, pdirY)
                Solid_Sub_Panel_A = ifc_file.createIfcBooleanResult("DIFFERENCE", Solid_Sub_Panel_A, solid_corner1)

            if Solid_Sub_Panel_F is not None:
                solid_corner2 = Draw_Corner(ifc_file, corner4, pcorner, pdirX, pdirY)
                Solid_Sub_Panel_F = ifc_file.createIfcBooleanResult("DIFFERENCE", Solid_Sub_Panel_F, solid_corner2)

    # スロット処理
    if slot_part:
        slotL, slotR, slotT, slotB = slot_part
        if not pd.isnull(slotT):
            if Solid_Sub_Panel_A is not None:
                solid_slot = Draw_3DSolid_Slot_WebSection(
                    ifc_all,
                    Data_MainPanel,
                    Senkei_data,
                    Mem_Rib_data,
                    Member_Data,
                    headname1_block_mainpanel,
                    headname2_block_mainpanel,
                    slotT,
                    "T",
                    p1_3d,
                    p2_3d,
                    p3_3d,
                )
                if solid_slot is not None:
                    Solid_Sub_Panel_A = ifc_file.createIfcBooleanResult("DIFFERENCE", Solid_Sub_Panel_A, solid_slot)

            if Solid_Sub_Panel_F is not None:
                solid_slot = Draw_3DSolid_Slot_WebSection(
                    ifc_all,
                    Data_MainPanel,
                    Senkei_data,
                    Mem_Rib_data,
                    Member_Data,
                    headname1_block_mainpanel,
                    headname2_block_mainpanel,
                    slotT,
                    "T",
                    p1_3d,
                    p2_3d,
                    p3_3d,
                )
                if solid_slot is not None:
                    Solid_Sub_Panel_F = ifc_file.createIfcBooleanResult("DIFFERENCE", Solid_Sub_Panel_F, solid_slot)

        if not pd.isnull(slotB):
            if Solid_Sub_Panel_A is not None:
                solid_slot = Draw_3DSolid_Slot_WebSection(
                    ifc_all,
                    Data_MainPanel,
                    Senkei_data,
                    Mem_Rib_data,
                    Member_Data,
                    headname1_block_mainpanel,
                    headname2_block_mainpanel,
                    slotB,
                    "B",
                    p1_3d,
                    p2_3d,
                    p3_3d,
                )
                if solid_slot is not None:
                    Solid_Sub_Panel_A = ifc_file.createIfcBooleanResult("DIFFERENCE", Solid_Sub_Panel_A, solid_slot)

            if Solid_Sub_Panel_F is not None:
                solid_slot = Draw_3DSolid_Slot_WebSection(
                    ifc_all,
                    Data_MainPanel,
                    Senkei_data,
                    Mem_Rib_data,
                    Member_Data,
                    headname1_block_mainpanel,
                    headname2_block_mainpanel,
                    slotB,
                    "B",
                    p1_3d,
                    p2_3d,
                    p3_3d,
                )
                if solid_slot is not None:
                    Solid_Sub_Panel_F = ifc_file.createIfcBooleanResult("DIFFERENCE", Solid_Sub_Panel_F, solid_slot)

        if not pd.isnull(slotL):
            if Solid_Sub_Panel_A is not None:
                solid_slot = Draw_3DSolid_Slot_WebSection(
                    ifc_all,
                    Data_MainPanel,
                    Senkei_data,
                    Mem_Rib_data,
                    Member_Data,
                    headname1_block_mainpanel,
                    headname2_block_mainpanel,
                    slotL,
                    "L",
                    p1_3d,
                    p2_3d,
                    p3_3d,
                )
                if solid_slot is not None:
                    Solid_Sub_Panel_A = ifc_file.createIfcBooleanResult("DIFFERENCE", Solid_Sub_Panel_A, solid_slot)

            if Solid_Sub_Panel_F is not None:
                solid_slot = Draw_3DSolid_Slot_WebSection(
                    ifc_all,
                    Data_MainPanel,
                    Senkei_data,
                    Mem_Rib_data,
                    Member_Data,
                    headname1_block_mainpanel,
                    headname2_block_mainpanel,
                    slotL,
                    "L",
                    p1_3d,
                    p2_3d,
                    p3_3d,
                )
                if solid_slot is not None:
                    Solid_Sub_Panel_F = ifc_file.createIfcBooleanResult("DIFFERENCE", Solid_Sub_Panel_F, solid_slot)

        if not pd.isnull(slotR):
            if Solid_Sub_Panel_A is not None:
                solid_slot = Draw_3DSolid_Slot_WebSection(
                    ifc_all,
                    Data_MainPanel,
                    Senkei_data,
                    Mem_Rib_data,
                    Member_Data,
                    headname1_block_mainpanel,
                    headname2_block_mainpanel,
                    slotR,
                    "R",
                    p1_3d,
                    p2_3d,
                    p3_3d,
                )
                if solid_slot is not None:
                    Solid_Sub_Panel_A = ifc_file.createIfcBooleanResult("DIFFERENCE", Solid_Sub_Panel_A, solid_slot)

            if Solid_Sub_Panel_F is not None:
                solid_slot = Draw_3DSolid_Slot_WebSection(
                    ifc_all,
                    Data_MainPanel,
                    Senkei_data,
                    Mem_Rib_data,
                    Member_Data,
                    headname1_block_mainpanel,
                    headname2_block_mainpanel,
                    slotR,
                    "R",
                    p1_3d,
                    p2_3d,
                    p3_3d,
                )
                if solid_slot is not None:
                    Solid_Sub_Panel_F = ifc_file.createIfcBooleanResult("DIFFERENCE", Solid_Sub_Panel_F, solid_slot)

    # ジョイント処理
    if joint_part:
        mats_part = thicka_part, thickf_part, mat_part
        jbut_s = joint_part["S"]
        jbut_e = joint_part["E"]
        if jbut_s:
            for i_2 in range(0, len(jbut_s), 2):
                SPL_point = jbut_s[i_2]
                SPL_Pitch = jbut_s[i_2 + 1]

                if Solid_Sub_Panel_A is not None:
                    Solid_Sub_Panel_A = Calculate_SPL_SubPanel(
                        ifc_all,
                        Member_SPL_data,
                        arCoord_Top,
                        arNamePoint,
                        arCoordPoint,
                        SPL_point,
                        SPL_Pitch,
                        "S",
                        mats_part,
                        Solid_Sub_Panel_A,
                    )
                else:
                    Solid_Sub_Panel_F = Calculate_SPL_SubPanel(
                        ifc_all,
                        Member_SPL_data,
                        arCoord_Top,
                        arNamePoint,
                        arCoordPoint,
                        SPL_point,
                        SPL_Pitch,
                        "S",
                        mats_part,
                        Solid_Sub_Panel_F,
                    )

        if jbut_e:
            for i_2 in range(0, len(jbut_e), 2):
                SPL_point = jbut_e[i_2]
                SPL_Pitch = jbut_e[i_2 + 1]

                if Solid_Sub_Panel_A is not None:
                    Solid_Sub_Panel_A = Calculate_SPL_SubPanel(
                        ifc_all,
                        Member_SPL_data,
                        arCoord_Top,
                        arNamePoint,
                        arCoordPoint,
                        SPL_point,
                        SPL_Pitch,
                        "E",
                        mats_part,
                        Solid_Sub_Panel_A,
                    )
                else:
                    Solid_Sub_Panel_F = Calculate_SPL_SubPanel(
                        ifc_all,
                        Member_SPL_data,
                        arCoord_Top,
                        arNamePoint,
                        arCoordPoint,
                        SPL_point,
                        SPL_Pitch,
                        "E",
                        mats_part,
                        Solid_Sub_Panel_F,
                    )

    # カットアウト処理
    if cutout_part:
        for i_2 in range(0, len(cutout_part), 4):
            atc = cutout_part[i_2].split("-")
            name_p1dir_cutout = atc[0]
            name_p2dir_cutout = atc[1]
            pitch_cutout = cutout_part[i_2 + 1]
            face_cutout = cutout_part[i_2 + 2]
            ref_cutout = cutout_part[i_2 + 3]

            index = arNamePoint.index(name_p1dir_cutout)
            p1dir_hole = arCoordPoint[index]
            index = arNamePoint.index(name_p2dir_cutout)
            p2dir_hole = arCoordPoint[index]

            pitch_cutout = DefStrings.Xu_Ly_Pitch_va_Tim_X(
                pitch_cutout, DefMath.Calculate_distance_p2p(p1dir_hole, p2dir_hole)
            )
            arpitch = pitch_cutout.split("/")
            sumpitch = 0
            for i_3 in range(len(arpitch) - 1):
                sumpitch += float(arpitch[i_3])
                Pbase_cutout = DefMath.Point_on_parallel_line(p1dir_hole, p1dir_hole, p2dir_hole, sumpitch)

                if Solid_Sub_Panel_A is not None:
                    solid_hole = Draw_Solid_CutOut(
                        ifc_all,
                        Member_Data,
                        Mem_Rib_data,
                        ref_cutout,
                        face_cutout,
                        thicka_part,
                        thickf_part,
                        Pbase_cutout,
                        p2dir_hole,
                        p1_3d,
                        p2_3d,
                        p3_3d,
                    )
                    if solid_hole is not None:
                        Solid_Sub_Panel_A = ifc_file.createIfcBooleanResult("DIFFERENCE", Solid_Sub_Panel_A, solid_hole)

                if Solid_Sub_Panel_F is not None:
                    solid_hole = Draw_Solid_CutOut(
                        ifc_all,
                        Member_Data,
                        Mem_Rib_data,
                        ref_cutout,
                        face_cutout,
                        thicka_part,
                        thickf_part,
                        Pbase_cutout,
                        p2dir_hole,
                        p1_3d,
                        p2_3d,
                        p3_3d,
                    )
                    if solid_hole is not None:
                        Solid_Sub_Panel_F = ifc_file.createIfcBooleanResult("DIFFERENCE", Solid_Sub_Panel_F, solid_hole)

    # 補剛材処理
    if stiff_part:
        for i_2 in range(0, len(stiff_part)):
            point_stiff = stiff_part[i_2]["Point"]
            face_stiff = stiff_part[i_2]["Side"]
            name_stiff = stiff_part[i_2]["Name"]
            ref_stiff = stiff_part[i_2]["Ref"]
            atc = point_stiff.split("-")
            name_p1mod_stiff = atc[0]
            name_p2mod_stiff = atc[1]
            index = arNamePoint.index(name_p1mod_stiff)
            p1mod_stiff = arCoordPoint[index]
            index = arNamePoint.index(name_p2mod_stiff)
            p2mod_stiff = arCoordPoint[index]

            Calculate_Vstiff_Subpanel(
                ifc_all,
                Mem_Rib_data,
                p1mod_stiff,
                p2mod_stiff,
                name_stiff,
                ref_stiff,
                face_stiff,
                thicka_part,
                thickf_part,
                p1_3d,
                p2_3d,
                p3_3d,
            )

    # フランジ処理
    if flg_part:
        uflg_part = flg_part["UFLG"]
        lflg_part = flg_part["LFLG"]
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
                if len(part_subpanel) == 1:
                    name_flg = name_subpanel + "-UFLG"
                else:
                    name_flg = name_subpanel + "-" + name_part[1:] + "-UFLG"
                Calculate_FLG_Subpanel(
                    ifc_all,
                    Data_MainPanel,
                    Senkei_data,
                    Mem_Rib_data,
                    Member_SPL_data,
                    arpoint_flg,
                    ref_flg,
                    name_flg,
                    pdir,
                    arNamePoint,
                    arCoordPoint,
                    headname1_block_mainpanel,
                    headname2_block_mainpanel,
                    side_export,
                )
        if lflg_part:
            for i_2 in range(0, len(lflg_part), 2):
                namepoint_flg = lflg_part[i_2]
                ref_flg = lflg_part[i_2 + 1]
                if namepoint_flg == "Auto":
                    arpoint_flg = outB
                else:
                    arpoint_flg = namepoint_flg.split("-")

                pdir = arCoord_Top[-1]
                if len(part_subpanel) == 1:
                    name_flg = name_subpanel + "-LFLG"
                else:
                    name_flg = name_subpanel + "-" + name_part[1:] + "-LFLG"
                Calculate_FLG_Subpanel(
                    ifc_all,
                    Data_MainPanel,
                    Senkei_data,
                    Mem_Rib_data,
                    Member_SPL_data,
                    arpoint_flg,
                    ref_flg,
                    name_flg,
                    pdir,
                    arNamePoint,
                    arCoordPoint,
                    headname1_block_mainpanel,
                    headname2_block_mainpanel,
                    side_export,
                )

    # 出力
    color_style = DefIFC.create_color(ifc_file, 174.0, 249.0, 240.0)

    if Solid_Sub_Panel_A is not None:
        styled_item = ifc_file.createIfcStyledItem(Item=Solid_Sub_Panel_A, Styles=[color_style])
        shape_representation = ifc_file.createIfcShapeRepresentation(
            ContextOfItems=geom_context,
            RepresentationIdentifier="Body",
            RepresentationType="Brep",
            Items=[Solid_Sub_Panel_A],
        )
        if len(part_subpanel) == 1:
            DefIFC.Add_shape_representation_in_Beam(ifc_file, bridge_span, shape_representation, name_subpanel)
        else:
            DefIFC.Add_shape_representation_in_Beam(
                ifc_file, bridge_span, shape_representation, name_subpanel + "-" + name_part[1:]
            )

    if Solid_Sub_Panel_F is not None:
        styled_item = ifc_file.createIfcStyledItem(Item=Solid_Sub_Panel_F, Styles=[color_style])
        shape_representation = ifc_file.createIfcShapeRepresentation(
            ContextOfItems=geom_context,
            RepresentationIdentifier="Body",
            RepresentationType="Brep",
            Items=[Solid_Sub_Panel_F],
        )
        if len(part_subpanel) == 1:
            DefIFC.Add_shape_representation_in_Beam(ifc_file, bridge_span, shape_representation, name_subpanel)
        else:
            DefIFC.Add_shape_representation_in_Beam(
                ifc_file, bridge_span, shape_representation, name_subpanel + "-" + name_part[1:]
            )


def Calculate_FLG_Subpanel(
    ifc_all,
    Data_Panel,
    Senkei_data,
    Mem_Rib_data,
    Member_SPL_data,
    arpoint_flg,
    ref_flg,
    name_flg,
    pdir,
    arNamePoint,
    arCoordPoint,
    headname1_block_mainpanel,
    headname2_block_mainpanel,
    side_export,
):
    """
    サブパネルのフランジを計算して生成する

    Args:
        ifc_all: (ifc_file, bridge_span, geom_context)のタプル
        Data_Panel: パネルデータの配列
        Senkei_data: 線形データ
        Mem_Rib_data: リブ部材データ
        Member_SPL_data: 継手部材データ
        arpoint_flg: フランジ点名称の配列
        ref_flg: 参照リブ名称
        name_flg: フランジ名称
        pdir: 方向点
        arNamePoint: 点名称の配列
        arCoordPoint: 座標点の配列
        headname1_block_mainpanel: 桁1のブロック名称
        headname2_block_mainpanel: 桁2のブロック名称
        side_export: 出力側面指定
    """
    # 遅延インポート
    from src.bridge_json_to_ifc.ifc_utils_new.core.DefBridge import Calculate_Coord_FLG, Extend_FLG

    ifc_file, bridge_span, geom_context = ifc_all

    arCoord_flg = []
    for i in range(len(arpoint_flg)):
        index = arNamePoint.index(arpoint_flg[i])
        arCoord_flg.append(arCoordPoint[index])

    # 参照リブ取得
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

    arCoorMod_A, arCoorMod_F = Calculate_Coord_FLG(
        arCoord_flg, pdir, height_rib / 2, height_rib / 2, anga_rib, 180 - anga_rib, angs_rib, ange_rib
    )
    arCoordFLG = [arCoorMod_F, arCoord_flg, arCoorMod_A]
    arCoordFLG_Out = arCoordFLG.copy()
    arCoordFLG_Out = Extend_FLG(
        Data_Panel, Senkei_data, arCoordFLG_Out, extend, headname1_block_mainpanel, headname2_block_mainpanel
    )
    arCoordFLGT_Out = DefMath.Offset_Face(arCoordFLG_Out, thick1_rib)
    arCoordFLGB_Out = DefMath.Offset_Face(arCoordFLG_Out, -thick2_rib)
    arCoordFLGM_Out = DefMath.Calculate_Coord_Mid(arCoordFLGT_Out, arCoordFLGB_Out)

    if side_export == 2:
        Solid1_FLG = DefIFC.Create_brep_from_box_points(ifc_file, arCoordFLGB_Out, arCoordFLGM_Out)
        Solid2_FLG = DefIFC.Create_brep_from_box_points(ifc_file, arCoordFLGM_Out, arCoordFLGT_Out)
    elif side_export == 1:
        Solid1_FLG = DefIFC.Create_brep_from_box_points(ifc_file, arCoordFLGB_Out, arCoordFLGM_Out)
        Solid2_FLG = None
    elif side_export == -1:
        Solid1_FLG = None
        Solid2_FLG = DefIFC.Create_brep_from_box_points(ifc_file, arCoordFLGM_Out, arCoordFLGT_Out)

    # コーナーカット
    if not pd.isnull(corner1) and corner1 != "N":
        pcorner = arCoorMod_F[0]
        pdirX = arCoorMod_F[1]
        pdirY = arCoorMod_A[0]
        if Solid1_FLG is not None:
            solid_corner1 = Draw_Corner(ifc_file, corner1, pcorner, pdirX, pdirY)
            Solid1_FLG = ifc_file.createIfcBooleanResult("DIFFERENCE", Solid1_FLG, solid_corner1)
        if Solid2_FLG is not None:
            solid_corner2 = Draw_Corner(ifc_file, corner1, pcorner, pdirX, pdirY)
            Solid2_FLG = ifc_file.createIfcBooleanResult("DIFFERENCE", Solid2_FLG, solid_corner2)

    if not pd.isnull(corner2) and corner2 != "N":
        pcorner = arCoorMod_F[-1]
        pdirX = arCoorMod_F[-2]
        pdirY = arCoorMod_A[-1]
        if Solid1_FLG is not None:
            solid_corner1 = Draw_Corner(ifc_file, corner2, pcorner, pdirX, pdirY)
            Solid1_FLG = ifc_file.createIfcBooleanResult("DIFFERENCE", Solid1_FLG, solid_corner1)
        if Solid2_FLG is not None:
            solid_corner2 = Draw_Corner(ifc_file, corner2, pcorner, pdirX, pdirY)
            Solid2_FLG = ifc_file.createIfcBooleanResult("DIFFERENCE", Solid2_FLG, solid_corner2)

    if not pd.isnull(corner3) and corner3 != "N":
        pcorner = arCoorMod_A[-1]
        pdirX = arCoorMod_A[-2]
        pdirY = arCoorMod_F[-1]
        if Solid1_FLG is not None:
            solid_corner1 = Draw_Corner(ifc_file, corner3, pcorner, pdirX, pdirY)
            Solid1_FLG = ifc_file.createIfcBooleanResult("DIFFERENCE", Solid1_FLG, solid_corner1)
        if Solid2_FLG is not None:
            solid_corner2 = Draw_Corner(ifc_file, corner3, pcorner, pdirX, pdirY)
            Solid2_FLG = ifc_file.createIfcBooleanResult("DIFFERENCE", Solid2_FLG, solid_corner2)

    if not pd.isnull(corner4) and corner4 != "N":
        pcorner = arCoorMod_A[0]
        pdirX = arCoorMod_A[1]
        pdirY = arCoorMod_F[0]
        if Solid1_FLG is not None:
            solid_corner1 = Draw_Corner(ifc_file, corner4, pcorner, pdirX, pdirY)
            Solid1_FLG = ifc_file.createIfcBooleanResult("DIFFERENCE", Solid1_FLG, solid_corner1)
        if Solid2_FLG is not None:
            solid_corner2 = Draw_Corner(ifc_file, corner4, pcorner, pdirX, pdirY)
            Solid2_FLG = ifc_file.createIfcBooleanResult("DIFFERENCE", Solid2_FLG, solid_corner2)

    # SPL処理
    if spl_s:
        for i in range(len(spl_s)):
            if Solid1_FLG is not None:
                Solid1_FLG = Calculate_SPL_Rib(
                    ifc_all,
                    Member_SPL_data,
                    arCoorMod_F[0],
                    arCoorMod_A[0],
                    arCoorMod_F[1],
                    spl_s[i],
                    "S",
                    thick1_rib,
                    thick2_rib,
                    Solid1_FLG,
                )
            else:
                Solid2_FLG = Calculate_SPL_Rib(
                    ifc_all,
                    Member_SPL_data,
                    arCoorMod_F[0],
                    arCoorMod_A[0],
                    arCoorMod_F[1],
                    spl_s[i],
                    "S",
                    thick1_rib,
                    thick2_rib,
                    Solid2_FLG,
                )

    if spl_e:
        for i in range(len(spl_e)):
            if Solid1_FLG is not None:
                Solid1_FLG = Calculate_SPL_Rib(
                    ifc_all,
                    Member_SPL_data,
                    arCoorMod_F[-1],
                    arCoorMod_A[-1],
                    arCoorMod_F[-2],
                    spl_e[i],
                    "E",
                    thick1_rib,
                    thick2_rib,
                    Solid1_FLG,
                )
            else:
                Solid2_FLG = Calculate_SPL_Rib(
                    ifc_all,
                    Member_SPL_data,
                    arCoorMod_F[-1],
                    arCoorMod_A[-1],
                    arCoorMod_F[-2],
                    spl_e[i],
                    "E",
                    thick1_rib,
                    thick2_rib,
                    Solid2_FLG,
                )

    # 出力
    color_style = DefIFC.create_color(ifc_file, 174.0, 249.0, 240.0)
    if Solid1_FLG is not None:
        styled_item = ifc_file.createIfcStyledItem(Item=Solid1_FLG, Styles=[color_style])
        shape_representation = ifc_file.createIfcShapeRepresentation(
            ContextOfItems=geom_context, RepresentationIdentifier="Body", RepresentationType="Brep", Items=[Solid1_FLG]
        )
        DefIFC.Add_shape_representation_in_Beam(ifc_file, bridge_span, shape_representation, name_flg)

    if Solid2_FLG is not None:
        styled_item = ifc_file.createIfcStyledItem(Item=Solid2_FLG, Styles=[color_style])
        shape_representation = ifc_file.createIfcShapeRepresentation(
            ContextOfItems=geom_context, RepresentationIdentifier="Body", RepresentationType="Brep", Items=[Solid2_FLG]
        )
        DefIFC.Add_shape_representation_in_Beam(ifc_file, bridge_span, shape_representation, name_flg)
