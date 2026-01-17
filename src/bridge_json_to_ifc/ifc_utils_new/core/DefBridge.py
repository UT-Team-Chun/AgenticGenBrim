"""
鋼橋IFCモデル生成のメインモジュール
ExcelまたはJSONファイルから鋼橋の3Dモデルを読み込み、IFC形式で出力する
パネル、リブ、補剛材、ボルト、穴などの橋梁部材を生成する
"""

from src.bridge_json_to_ifc.ifc_utils_new.core import DefIFC, DefMath
from src.bridge_json_to_ifc.ifc_utils_new.io import DefJson, DefStrings
from src.bridge_json_to_ifc.ifc_utils_new.utils import DefBridgeUtils
import json
import re
import os
import copy
import math
from math import pi, cos
import numpy as np
import pandas as pd
from colorama import init, Fore, Style
import ifcopenshell

# DefBridgeUtils.pyの関数をインポート
from src.bridge_json_to_ifc.ifc_utils_new.utils.DefBridgeUtils import (
    Calculate_Line,
    Load_Coordinate_Panel,
    Calculate_Extend,
    Calculate_Extend_Coord,
    Calculate_Coord_Face,
    Devide_Pitch_Polyline,
    Combined_Sort_Coord_And_NameSec,
    Load_Coordinate_Point,
    Load_Coordinate_PolLine,
    Calculate_points_Sub_Panel,
    Find_number_block_MainPanel,
    Find_number_block_MainPanel_Have_Vstiff,
    # 座標延長関数
    Extend_Dia_Number,
    Extend_Dia_Face,
    Extend_FLG,
    Calculate_Coord_FLG,
)

# DefComponent.pyの関数をインポート
from src.bridge_json_to_ifc.ifc_utils_new.components.DefComponent import (
    Calculate_Shouban,
    Calculate_Bearing,
    Calculate_Guardrail,
    Draw_Corner,
    Draw_Solid_CutOut,
    Draw_Stiff_CutOut,
    Calculate_ATM,
    Calculate_Stud,
    Draw_Solid_Hole,
    Draw_Solid_LongHole,
)

# DefPanel.pyの関数をインポート
from src.bridge_json_to_ifc.ifc_utils_new.components.DefPanel import Check_break_mainpanle, Devide_Coord_FLG_mainpanel_break

# DefStiffener.pyの関数をインポート
from src.bridge_json_to_ifc.ifc_utils_new.components.DefStiffener import (
    Draw_3DSolid_Vstiff,
    Devide_Pitch_Vstiff,
    Extend_Vstiff_Auto_Face_FLG,
    Devide_Coord_LRib,
    Calculate_X_SPL_Pitch,
    Draw_3DSolid_Vstiff_Taikeikou,
    Calculate_Vstiff_Subpanel,
    Calculate_SPL_SubPanel,
    Draw_3DSolid_SPL,
    Draw_Solid_Hole_SPL,
    Draw_Solid_Bolt_SPL,
    Calculate_SPL_Rib,
    Calculate_Hstiff,
    Calculate_Vstiff,
    Calculate_LRib,
    Calculate_SPL,
)

# DefSlot.pyの関数をインポート
from src.bridge_json_to_ifc.ifc_utils_new.components.DefSlot import (
    Draw_3DSolid_Slot_WebSection,
    Draw_Slot_HStiff,
    Draw_Slot_LRib,
    Draw_3Dsolid_Slot,
)

# DefBracing.pyの関数をインポート
from src.bridge_json_to_ifc.ifc_utils_new.components.DefBracing import (
    Calculate_Yokokou,
    Calculate_Taikeikou,
    Calculate_Yokokou_Structural,
    Calculate_Yokokou_LateralBracing,
    Draw_Guss_Yokokou,
    Draw_3DSlot_For_Guss_Yokokou,
    Draw_3DSlot_follow_VStiff_MainPanel_For_Guss,
    Draw_Shape_Yokokou,
    Calculate_Point_Cross_Yokokou,
    Calculate_Point_Taikeikou,
    # 対傾構関連
    Calculate_Shape_Taikeikou_For_Yokokou,
    Draw_3DSlot_follow_Stiff_Taikeikou_For_Guss,
    Calculate_Point_Vstiff_Taikeikou,
    Calculate_Length_Bolt_Taikeikou,
    Caculate_Coord_Hole_Taikeikou,
    Draw_3DSolid_Bolt_Taikeikou,
    # 横構関連
    Calculate_PointMod_Guss_follow_Yokokou,
    Draw_3DSolid_Bolt_Yokokou,
    Caculate_Coord_Hole_Yokokou,
    Calculate_DistModX_Shape,
    Calculate_Pse_Shape,
)

# DefPanel.pyの関数をインポート（横桁関連はDefPanel.pyに移動済み）
from src.bridge_json_to_ifc.ifc_utils_new.components.DefPanel import Calculate_Yokogeta, Extend_Yokoketa_Face, Extend_Yokoketa_Face_FLG

# DefMainPanel.pyの関数をインポート
from src.bridge_json_to_ifc.ifc_utils_new.core.DefMainPanel import (
    Draw_solid_Web_mainpanel_break_FLG,
    Draw_solid_FLG_mainpanel_break,
    get_non_duplicate_indices,
    apply_indices_to_coord_lines,
    remove_consecutive_duplicate_points,
)

# DefSubPanel.pyの関数をインポート
from src.bridge_json_to_ifc.ifc_utils_new.core.DefSubPanel import Calculate_Part_SubPanel, Calculate_FLG_Subpanel

# DefGusset.pyの関数をインポート
from src.bridge_json_to_ifc.ifc_utils_new.components.DefGusset import (
    Draw_3DSolid_Guss,
    Calculate_edge_Guss_Constant,
    Calculate_edge_Guss_P,
    Calculate_Face_Guss_follow_Yokokou,
    Calculate_Face_Base_Guss_follow_Yokokou,
    Calculate_Face_Base_Guss_follow_Taikeikou,
    Calculate_Face_Base_Guss_follow_SubPanel,
    Calculate_PointFLG_Subpanel_for_Guss_Yokokou,
)

# グローバル変数: ログファイル出力関数
log_print_func = None
# デバッグモード（Trueの場合、詳細ログをファイルとコンソールに出力）
DEBUG_MODE = False


def _log_print(*args, **kwargs):
    """通常ログ出力（コンソール出力なし、ファイルのみ）"""
    if log_print_func and DEBUG_MODE:
        log_print_func(*args, **kwargs)


def _debug_print(*args, **kwargs):
    """デバッグログ出力（DEBUG_MODE時のみ出力）"""
    if DEBUG_MODE and log_print_func:
        log_print_func(*args, **kwargs)


def _progress_print(*args, **kwargs):
    """進捗ログ出力（常にコンソールとファイルに出力）"""
    print(*args, **kwargs)
    if log_print_func:
        # log_print_funcはprintを含むのでファイルのみに出力
        pass


# =============================================================================
# BridgeContext: 橋梁モデル生成に必要なコンテキストを保持するクラス
# =============================================================================
class BridgeContext:
    """
    橋梁IFCモデル生成に必要なコンテキストを保持するクラス

    Attributes:
        ifc_file: IFCファイルオブジェクト
        bridge_span: 橋梁スパン
        geom_context: ジオメトリコンテキスト
        data_json: JSONから読み込んだ橋梁データ
        side_export: エクスポート側の情報（1: 上側のみ, -1: 下側のみ, 2: 両側）
        name_bridge: 橋梁名
        location: ファイルディレクトリパス
    """

    def __init__(self, ifc_file, bridge_span, geom_context, data_json, location):
        self.ifc_file = ifc_file
        self.bridge_span = bridge_span
        self.geom_context = geom_context
        self.data_json = data_json
        self.location = location

        # 基本情報を抽出
        infor_data = data_json.get("Infor", {})
        self.name_bridge = infor_data.get("NameBridge", "")
        self.side_export = infor_data.get("SideExport", 2)

    @property
    def ifc_all(self):
        """ifc_file, bridge_span, geom_contextのタプルを返す（後方互換性のため）"""
        return (self.ifc_file, self.bridge_span, self.geom_context)

    # データアクセサ
    @property
    def senkei_data(self):
        return self.data_json.get("Senkei", [])

    @property
    def main_panel_data(self):
        return self.data_json.get("MainPanel", [])

    @property
    def sub_panel_data(self):
        return self.data_json.get("SubPanel", [])

    @property
    def taikeikou_data(self):
        return self.data_json.get("Taikeikou", [])

    @property
    def yokokou_data(self):
        return self.data_json.get("Yokokou", [])

    @property
    def yokogeta_data(self):
        return self.data_json.get("Yokogeta", [])

    @property
    def shouban_data(self):
        return self.data_json.get("Shouban", [])

    @property
    def bearing_data(self):
        return self.data_json.get("Bearing", [])

    @property
    def member_data(self):
        return self.data_json.get("MemberData", {})

    @property
    def member_rib_data(self):
        return self.data_json.get("MemberRib", {})

    @property
    def member_spl_data(self):
        return self.data_json.get("MemberSPL", {})


# =============================================================================
# ログ設定関数
# =============================================================================
def _setup_logging(location, debug_mode):
    """
    ログ設定を初期化する

    Args:
        location: ログファイルの出力ディレクトリ
        debug_mode: デバッグモードフラグ

    Returns:
        log_file: ログファイルオブジェクト（DEBUG_MODEがFalseの場合はNone）
    """
    global log_print_func

    log_file = None

    if debug_mode:
        import datetime

        log_filename = location + "debug_log_" + datetime.datetime.now().strftime("%Y%m%d_%H%M%S") + ".txt"
        log_file = open(log_filename, "w", encoding="utf-8")

        def log_print(*args, **kwargs):
            """ログファイルのみに出力（コンソール出力なし）"""
            print(*args, file=log_file, **kwargs)
            log_file.flush()

        log_print_func = log_print

        # 他モジュールのログ関数も設定
        DefBridgeUtils.log_print_func = log_print
        from src.bridge_json_to_ifc.ifc_utils_new.components import DefPanel, DefBracing, DefComponent

        DefPanel.log_print_func = log_print
        DefBracing.log_print_func = log_print
        DefComponent.log_print_func = log_print
        DefIFC.log_print_func = log_print
    else:
        # デバッグモードオフ：ログ関数を無効化
        log_print_func = None
        DefBridgeUtils.log_print_func = None
        from src.bridge_json_to_ifc.ifc_utils_new.components import DefPanel, DefBracing, DefComponent

        DefPanel.log_print_func = None
        DefBracing.log_print_func = None
        DefComponent.log_print_func = None
        DefIFC.log_print_func = None

    return log_file


# =============================================================================
# データ読み込み関数
# =============================================================================
def _load_bridge_data(location, name_file):
    """
    橋梁データを読み込む

    Args:
        location: ファイルのディレクトリパス
        name_file: ファイル名（.xlsxまたは.json）

    Returns:
        data_json: 読み込んだJSONデータ
    """
    atc = name_file.split(".")
    file_path = location + atc[0] + ".json"

    if os.path.isfile(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            data_json = json.load(f)
    else:
        data_json = DefJson.Convert_DataInput_From_Excel_To_Json(location, name_file)

    return data_json


def _load_damage_info(location):
    """
    損傷情報JSONファイルを読み込む

    Args:
        location: ファイルのディレクトリパス

    Returns:
        damage_info_dict: 損傷情報辞書
    """
    damage_info_file = location + "damage_info.json"
    damage_info_dict = {}

    if not os.path.isfile(damage_info_file):
        return damage_info_dict

    try:
        with open(damage_info_file, "r", encoding="utf-8") as f:
            damage_data = json.load(f)

            # 橋梁情報を表示（あれば）
            if "BridgeInfo" in damage_data:
                bridge_info = damage_data["BridgeInfo"]
                bridge_name = bridge_info.get("BridgeName", "")
                if bridge_name:
                    print(f"橋梁名: {bridge_name}")

            if "DamageInformation" in damage_data:
                for damage_entry in damage_data["DamageInformation"]:
                    element_name = damage_entry.get("ElementName", "")

                    # 新形式: InspectionHistoryから最新の点検結果を取得
                    inspection_history = damage_entry.get("InspectionHistory", [])
                    if inspection_history:
                        # 最新の点検結果（配列の最初）
                        latest_inspection = inspection_history[0]
                        damage_items = latest_inspection.get("DamageItems", [])

                        # 点検情報を損傷情報に追加
                        inspection_meta = {
                            "InspectionDate": latest_inspection.get("InspectionDate", ""),
                            "InspectionYear": latest_inspection.get("InspectionYear", ""),
                            "Inspector": latest_inspection.get("Inspector", ""),
                            "InspectionType": latest_inspection.get("InspectionType", ""),
                            "RepairRecommendation": latest_inspection.get("RepairRecommendation", ""),
                        }

                        # 過去の点検履歴から経緯を作成
                        history_summary = []
                        for hist in inspection_history:
                            year = hist.get("InspectionYear", "")
                            items = hist.get("DamageItems", [])
                            if items:
                                levels = [
                                    f"{item.get('DamageType', '')}:{item.get('DamageLevel', '')}" for item in items
                                ]
                                history_summary.append(f"{year}年({', '.join(levels)})")

                        inspection_meta["HistorySummary"] = (
                            " → ".join(reversed(history_summary)) if history_summary else ""
                        )

                        # 補修履歴
                        repair_history = damage_entry.get("RepairHistory", [])
                        if repair_history:
                            repair_summary = [
                                f"{r.get('RepairDate', '')}: {r.get('RepairType', '')}" for r in repair_history
                            ]
                            inspection_meta["RepairHistory"] = "; ".join(repair_summary)
                        else:
                            inspection_meta["RepairHistory"] = ""

                        if element_name and damage_items:
                            damage_info_dict[element_name] = {
                                "DamageItems": damage_items,
                                "InspectionMeta": inspection_meta,
                            }
                    else:
                        # 旧形式: DamageItemsを直接取得（後方互換）
                        damage_items = damage_entry.get("DamageItems", [])
                        if element_name and damage_items:
                            damage_info_dict[element_name] = {"DamageItems": damage_items, "InspectionMeta": {}}

                if damage_info_dict:
                    print(f"損傷情報を読み込みました: {len(damage_info_dict)}個の要素")
                    # デバッグ: 読み込まれた要素名を表示
                    for elem_name, elem_data in damage_info_dict.items():
                        damage_items = elem_data.get("DamageItems", [])
                        print(f"  - {elem_name}: {len(damage_items)}個の損傷項目")
    except Exception as e:
        import traceback

        print(f"警告: 損傷情報ファイルの読み込みに失敗しました: {e}")
        print(traceback.format_exc())

    return damage_info_dict


def _setup_coordinate_system(data_json):
    """
    座標系を設定する（グローバル変数の設定）

    Args:
        data_json: 橋梁JSONデータ
    """
    global unit_vector_bridge, start_point_bridge, end_point_bridge

    if data_json.get("Senkei"):
        p1 = data_json["Senkei"][0]["Point"][0]
        p2 = data_json["Senkei"][0]["Point"][-1]
        start_point_bridge = np.array([p1["X"], p1["Y"], p1["Z"]])
        end_point_bridge = np.array([p2["X"], p2["Y"], p2["Z"]])
        unit_vector_bridge = DefMath.calculate_unit_vector_bridge(start_point_bridge, end_point_bridge)


def _process_calculate_lines(data_json):
    """
    計算線形を処理する

    Args:
        data_json: 橋梁JSONデータ

    Returns:
        更新されたdata_json
    """
    if data_json.get("Calculate"):
        for newline in data_json["Calculate"]:
            name_new_line = newline["Name"]
            calculations = newline["Calculations"]
            data_json["Senkei"] = Calculate_Line(name_new_line, calculations, data_json["Senkei"])

    return data_json


# =============================================================================
# 各フェーズの生成関数
# =============================================================================


def _generate_main_panels(ctx):
    """
    メインパネルを生成する

    Args:
        ctx: BridgeContext オブジェクト
    """
    ifc_file = ctx.ifc_file
    geom_context = ctx.geom_context
    bridge_span = ctx.bridge_span
    ifc_all = ctx.ifc_all
    Data_Json = ctx.data_json
    side_export = ctx.side_export

    for panel in Data_Json["MainPanel"]:
        Name_panel = panel["Name"]
        Line_panel = panel["Line"]
        Sec_panel = panel["Sec"]
        Type_panel = panel["Type"]
        Mat_panel = panel["Material"]
        Expand_panel = panel["Expand"]
        Jbut_panel = panel["Jbut"]
        Break_panel = panel["Break"]
        Corner_panel = panel["Corner"]
        Lrib_panel = panel["Lrib"]
        Vstiff_panel = panel["Vstiff"]
        Hstiff_panel = panel["Hstiff"]
        Atm_panel = panel["Atm"]
        Cutout_panel = panel["Cutout"]
        Stud_panel = panel["Stud"]
        print(f"  MainPanel - {Name_panel}")

        arCoordLines_Mod = Load_Coordinate_Panel(Data_Json["Senkei"], Line_panel, Sec_panel)
        ExtendL, ExtendR, ExtendT, ExtendB = (
            Expand_panel["E1"],
            Expand_panel["E2"],
            Expand_panel["E3"],
            Expand_panel["E4"],
        )

        arCoordLines_Out = Calculate_Extend(
            Data_Json["MainPanel"],
            Data_Json["Senkei"],
            Name_panel,
            arCoordLines_Mod,
            ExtendL,
            ExtendR,
            ExtendT,
            ExtendB,
        )

        Thick1, Thick2, Mat = Mat_panel["Thick1"], Mat_panel["Thick2"], Mat_panel["Mat"]
        SplitThickness = Mat_panel.get("SplitThickness", False)
        arSolid_Panel1 = []
        arSolid_Panel2 = []

        if (
            Break_panel
            and isinstance(Break_panel, dict)
            and "Lenght" in Break_panel
            and len(Break_panel.get("Lenght", [])) > 0
        ):
            if Type_panel["TypePanel"] == "W" or Type_panel["TypePanel"] == "WL" or Type_panel["TypePanel"] == "WR":
                arSolid_Panel1, arSolid_Panel2 = Draw_solid_Web_mainpanel_break_FLG(
                    ifc_all, Data_Json["MainPanel"], Data_Json["Senkei"], Name_panel, arCoordLines_Mod, side_export
                )
            else:
                arLength = Break_panel["Lenght"]
                arExtend = Break_panel["Extend"]
                arThick = Break_panel["Thick"]
                arSolid_Panel1, arSolid_Panel2 = Draw_solid_FLG_mainpanel_break(
                    ifc_all, arCoordLines_Mod, arLength, arExtend, arThick, Type_panel, side_export, SplitThickness
                )
        else:
            if Type_panel["TypePanel"] == "W" or Type_panel["TypePanel"] == "WL" or Type_panel["TypePanel"] == "WR":
                if (
                    Check_break_mainpanle(Data_Json["MainPanel"], Name_panel, "T") == True
                    and DefMath.is_number(ExtendT) == False
                ) or (
                    Check_break_mainpanle(Data_Json["MainPanel"], Name_panel, "B") == True
                    and DefMath.is_number(ExtendB) == False
                ):
                    arSolid_Panel1, arSolid_Panel2 = Draw_solid_Web_mainpanel_break_FLG(
                        ifc_all, Data_Json["MainPanel"], Data_Json["Senkei"], Name_panel, arCoordLines_Mod, side_export
                    )
                else:
                    arCoordLines_Out_off1 = DefMath.Offset_Face(arCoordLines_Out, -Thick1)
                    arCoordLines_Out_off2 = DefMath.Offset_Face(arCoordLines_Out, Thick2)
                    arCoordLines_mid = DefMath.Calculate_Coord_Mid(arCoordLines_Out_off1, arCoordLines_Out_off2)
                    if side_export == 2:
                        Solid_Panel1 = DefIFC.Create_brep_from_box_points(
                            ifc_file, arCoordLines_Out_off1, arCoordLines_mid
                        )
                        arSolid_Panel1.append(Solid_Panel1)
                        Solid_Panel2 = DefIFC.Create_brep_from_box_points(
                            ifc_file, arCoordLines_mid, arCoordLines_Out_off2
                        )
                        arSolid_Panel2.append(Solid_Panel2)
                    elif side_export == 1:
                        Solid_Panel1 = DefIFC.Create_brep_from_box_points(
                            ifc_file, arCoordLines_Out_off1, arCoordLines_mid
                        )
                        arSolid_Panel1.append(Solid_Panel1)
                        Solid_Panel2 = None
                        arSolid_Panel2.append(Solid_Panel2)
                    elif side_export == -1:
                        Solid_Panel1 = None
                        arSolid_Panel1.append(Solid_Panel1)
                        Solid_Panel2 = DefIFC.Create_brep_from_box_points(
                            ifc_file, arCoordLines_mid, arCoordLines_Out_off2
                        )
                        arSolid_Panel2.append(Solid_Panel2)
            else:
                effective_Thick1 = Thick1
                effective_Thick2 = Thick2
                if not SplitThickness:
                    if Type_panel["TypePanel"] == "UF":
                        effective_Thick2 = 0
                    elif Type_panel["TypePanel"] == "LF":
                        effective_Thick1 = 0

                arCoordLines_Out_off1 = DefMath.Offset_Face(arCoordLines_Out, -effective_Thick2)
                arCoordLines_Out_off2 = DefMath.Offset_Face(arCoordLines_Out, effective_Thick1)
                arCoordLines_mid = DefMath.Calculate_Coord_Mid(arCoordLines_Out_off1, arCoordLines_Out_off2)

                if Type_panel["TypePanel"] == "UF":
                    if len(arCoordLines_Out) > 0 and len(arCoordLines_Out[0]) > 0:
                        center_point = arCoordLines_Out[0][0]
                        if len(arCoordLines_Out_off2) > 0 and len(arCoordLines_Out_off2[0]) > 0:
                            top_point = arCoordLines_Out_off2[0][0]
                            _log_print(f"  [FLANGE DEBUG] {Name_panel}: 上フランジ位置情報")
                            _log_print(f"    [FLANGE DEBUG] 中心線Z座標: {center_point[2]:.2f}mm")
                            _log_print(
                                f"    [FLANGE DEBUG] effective_Thick1: {effective_Thick1}mm, effective_Thick2: {effective_Thick2}mm"
                            )
                            _log_print(f"    [FLANGE DEBUG] 計算される上面Z座標: {top_point[2]:.2f}mm")
                            _log_print(
                                f"    [FLANGE DEBUG] 中心線から上面までの距離: {top_point[2] - center_point[2]:.2f}mm"
                            )

                if side_export == 2:
                    if effective_Thick1 > 0 and effective_Thick2 > 0:
                        Solid_Panel1 = DefIFC.Create_brep_from_box_points(
                            ifc_file, arCoordLines_Out_off1, arCoordLines_mid
                        )
                        arSolid_Panel1.append(Solid_Panel1)
                        Solid_Panel2 = DefIFC.Create_brep_from_box_points(
                            ifc_file, arCoordLines_mid, arCoordLines_Out_off2
                        )
                        arSolid_Panel2.append(Solid_Panel2)
                    elif effective_Thick1 > 0:
                        Solid_Panel1 = None
                        arSolid_Panel1.append(Solid_Panel1)
                        Solid_Panel2 = DefIFC.Create_brep_from_box_points(
                            ifc_file, arCoordLines_Out, arCoordLines_Out_off2
                        )
                        arSolid_Panel2.append(Solid_Panel2)
                    elif effective_Thick2 > 0:
                        Solid_Panel1 = DefIFC.Create_brep_from_box_points(
                            ifc_file, arCoordLines_Out_off1, arCoordLines_Out
                        )
                        arSolid_Panel1.append(Solid_Panel1)
                        Solid_Panel2 = None
                        arSolid_Panel2.append(Solid_Panel2)
                    else:
                        Solid_Panel1 = None
                        Solid_Panel2 = None
                        arSolid_Panel1.append(Solid_Panel1)
                        arSolid_Panel2.append(Solid_Panel2)
                elif side_export == 1:
                    if effective_Thick1 > 0:
                        Solid_Panel1 = DefIFC.Create_brep_from_box_points(
                            ifc_file, arCoordLines_Out, arCoordLines_Out_off2
                        )
                        arSolid_Panel1.append(Solid_Panel1)
                    else:
                        Solid_Panel1 = None
                        arSolid_Panel1.append(Solid_Panel1)
                    Solid_Panel2 = None
                    arSolid_Panel2.append(Solid_Panel2)
                elif side_export == -1:
                    Solid_Panel1 = None
                    arSolid_Panel1.append(Solid_Panel1)
                    if effective_Thick2 > 0:
                        Solid_Panel2 = DefIFC.Create_brep_from_box_points(
                            ifc_file, arCoordLines_Out_off1, arCoordLines_Out
                        )
                        arSolid_Panel2.append(Solid_Panel2)
                    else:
                        Solid_Panel2 = None
                        arSolid_Panel2.append(Solid_Panel2)

        # SPL処理
        if Jbut_panel:
            jbut_s = Jbut_panel["S"]
            jbut_e = Jbut_panel["E"]
            if jbut_s:
                for i_1 in range(0, len(jbut_s), 2):
                    SPL_Line = jbut_s[i_1]
                    SPL_Pitch = jbut_s[i_1 + 1]
                    Solid_Panel1 = arSolid_Panel1[0]
                    Solid_Panel2 = arSolid_Panel2[0]
                    if Solid_Panel1 != None:
                        Solid_Panel1 = Calculate_SPL(
                            ifc_all,
                            Data_Json["MainPanel"],
                            Data_Json["MemberSPL"],
                            SPL_Line,
                            Sec_panel[0],
                            SPL_Pitch,
                            "S",
                            arCoordLines_Mod,
                            Line_panel,
                            Sec_panel,
                            Name_panel,
                            Solid_Panel1,
                        )
                    else:
                        Solid_Panel2 = Calculate_SPL(
                            ifc_all,
                            Data_Json["MainPanel"],
                            Data_Json["MemberSPL"],
                            SPL_Line,
                            Sec_panel[0],
                            SPL_Pitch,
                            "S",
                            arCoordLines_Mod,
                            Line_panel,
                            Sec_panel,
                            Name_panel,
                            Solid_Panel2,
                        )

            if jbut_e:
                for i_1 in range(0, len(jbut_e), 2):
                    SPL_Line = jbut_e[i_1]
                    SPL_Pitch = jbut_e[i_1 + 1]
                    Solid_Panel1 = arSolid_Panel1[-1]
                    Solid_Panel2 = arSolid_Panel2[-1]
                    if Solid_Panel1 != None:
                        Solid_Panel1 = Calculate_SPL(
                            ifc_all,
                            Data_Json["MainPanel"],
                            Data_Json["MemberSPL"],
                            SPL_Line,
                            Sec_panel[-1],
                            SPL_Pitch,
                            "E",
                            arCoordLines_Mod,
                            Line_panel,
                            Sec_panel,
                            Name_panel,
                            Solid_Panel1,
                        )
                    else:
                        Solid_Panel2 = Calculate_SPL(
                            ifc_all,
                            Data_Json["MainPanel"],
                            Data_Json["MemberSPL"],
                            SPL_Line,
                            Sec_panel[-1],
                            SPL_Pitch,
                            "E",
                            arCoordLines_Mod,
                            Line_panel,
                            Sec_panel,
                            Name_panel,
                            Solid_Panel2,
                        )

        # Corner処理
        if Corner_panel:
            corner1, corner2, corner3, corner4 = Corner_panel

            if not pd.isnull(corner1) and corner1 != "N":
                Solid_Panel1 = arSolid_Panel1[0]
                Solid_Panel2 = arSolid_Panel2[0]
                pcorner = arCoordLines_Out[0][0]
                pdirX = arCoordLines_Out[0][1]
                pdirY = arCoordLines_Out[1][0]

                if Solid_Panel1 != None:
                    solid_corner = Draw_Corner(ifc_file, corner1, pcorner, pdirX, pdirY)
                    Solid_Panel1 = ifc_file.createIfcBooleanResult("DIFFERENCE", Solid_Panel1, solid_corner)

                if Solid_Panel2 != None:
                    solid_corner = Draw_Corner(ifc_file, corner1, pcorner, pdirX, pdirY)
                    Solid_Panel2 = ifc_file.createIfcBooleanResult("DIFFERENCE", Solid_Panel2, solid_corner)

            if not pd.isnull(corner2) and corner2 != "N":
                Solid_Panel1 = arSolid_Panel1[-1]
                Solid_Panel2 = arSolid_Panel2[-1]
                pcorner = arCoordLines_Out[0][-1]
                pdirX = arCoordLines_Out[0][-2]
                pdirY = arCoordLines_Out[1][-1]

                if Solid_Panel1 != None:
                    solid_corner = Draw_Corner(ifc_file, corner2, pcorner, pdirX, pdirY)
                    Solid_Panel1 = ifc_file.createIfcBooleanResult("DIFFERENCE", Solid_Panel1, solid_corner)

                if Solid_Panel2 != None:
                    solid_corner = Draw_Corner(ifc_file, corner2, pcorner, pdirX, pdirY)
                    Solid_Panel2 = ifc_file.createIfcBooleanResult("DIFFERENCE", Solid_Panel2, solid_corner)

            if not pd.isnull(corner3) and corner3 != "N":
                Solid_Panel1 = arSolid_Panel1[-1]
                Solid_Panel2 = arSolid_Panel2[-1]
                pcorner = arCoordLines_Out[-1][0]
                pdirX = arCoordLines_Out[-1][1]
                pdirY = arCoordLines_Out[-2][0]

                if Solid_Panel1 != None:
                    solid_corner = Draw_Corner(ifc_file, corner3, pcorner, pdirX, pdirY)
                    Solid_Panel1 = ifc_file.createIfcBooleanResult("DIFFERENCE", Solid_Panel1, solid_corner)

                if Solid_Panel2 != None:
                    solid_corner = Draw_Corner(ifc_file, corner3, pcorner, pdirX, pdirY)
                    Solid_Panel2 = ifc_file.createIfcBooleanResult("DIFFERENCE", Solid_Panel2, solid_corner)

            if not pd.isnull(corner4) and corner4 != "N":
                Solid_Panel1 = arSolid_Panel1[0]
                Solid_Panel2 = arSolid_Panel2[0]
                pcorner = arCoordLines_Out[-1][-1]
                pdirX = arCoordLines_Out[-1][-2]
                pdirY = arCoordLines_Out[-2][-1]

                if Solid_Panel1 != None:
                    solid_corner = Draw_Corner(ifc_file, corner4, pcorner, pdirX, pdirY)
                    Solid_Panel1 = ifc_file.createIfcBooleanResult("DIFFERENCE", Solid_Panel1, solid_corner)

                if Solid_Panel2 != None:
                    solid_corner = Draw_Corner(ifc_file, corner4, pcorner, pdirX, pdirY)
                    Solid_Panel2 = ifc_file.createIfcBooleanResult("DIFFERENCE", Solid_Panel2, solid_corner)

        # LRib処理
        if Lrib_panel:
            Line_LRib, Pitch_LRib, NamePoint_LRib = Lrib_panel[0]
            NamePoint_LRib = DefStrings.Chuyen_Name_LRib_thanh_Array(NamePoint_LRib)
            Line_LRib = Line_LRib.split("-")
            arCoordLines_Lrib = Load_Coordinate_Panel(Data_Json["Senkei"], Line_LRib, Sec_panel)
            arCoordLines_Lrib = Devide_Coord_LRib(arCoordLines_Lrib, Pitch_LRib)
            for i_1 in range(1, len(Lrib_panel)):
                Calculate_LRib(
                    ifc_all,
                    Data_Json["MemberRib"],
                    Data_Json["MemberSPL"],
                    Lrib_panel[i_1],
                    arCoordLines_Lrib,
                    NamePoint_LRib,
                    Sec_panel,
                    Thick1,
                    Thick2,
                )

        # Vstiff処理
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

            for i_1 in range(1, len(Vstiff_panel)):
                Calculate_Vstiff(
                    ifc_all,
                    Data_Json["MainPanel"],
                    Data_Json["Senkei"],
                    Data_Json["MemberRib"],
                    Name_panel,
                    Vstiff_panel[i_1],
                    arCoordLines_Mod_new,
                    sec_panel_new,
                    Thick1,
                    Thick2,
                )

        # Hstiff処理
        if Hstiff_panel:
            Line_Hstiff, Pitch_Hstiff, NamePoint_Hstiff = Hstiff_panel[0]
            NamePoint_Hstiff = DefStrings.Chuyen_Name_LRib_thanh_Array(NamePoint_Hstiff)
            Line_Hstiff = Line_Hstiff.split("-")
            arCoordLines_Hstiff = Load_Coordinate_Panel(Data_Json["Senkei"], Line_Hstiff, Sec_panel)
            arCoordLines_Hstiff = Devide_Coord_LRib(arCoordLines_Hstiff, Pitch_Hstiff)
            if Vstiff_panel:
                if Vstiff_panel[0]:
                    type_devide, pitch_top, pitch_bot, namepoint = Vstiff_panel[0]
                    namepoint = DefStrings.Chuyen_Name_LRib_thanh_Array(namepoint)
                    arCoordLines_Hstiff_New, PosVstiff = Devide_Pitch_Vstiff(arCoordLines_Hstiff, Vstiff_panel[0])
                    arCoordLines_Hstiff, sec_panel_new = Combined_Sort_Coord_And_NameSec(
                        arCoordLines_Hstiff_New, namepoint, arCoordLines_Hstiff, Sec_panel
                    )
                else:
                    sec_panel_new = Sec_panel

                for i_1 in range(1, len(Hstiff_panel)):
                    Calculate_Hstiff(
                        ifc_all,
                        Data_Json["MainPanel"],
                        Data_Json["Senkei"],
                        Data_Json["MemberRib"],
                        Name_panel,
                        Hstiff_panel[i_1],
                        arCoordLines_Hstiff,
                        NamePoint_Hstiff,
                        sec_panel_new,
                        Thick1,
                        Thick2,
                    )

        # ATM処理
        if Atm_panel:
            for i_1 in range(0, len(Atm_panel), 2):
                pitchlong_atm, pitchtran_atm = Atm_panel[i_1]
                dirPitchLong_atm, PitchLong_atm = pitchlong_atm
                Line_atm, PitchTran_atm = pitchtran_atm
                Line_atm = Line_atm.split("-")
                arCoordLines_atm = Load_Coordinate_Panel(Data_Json["Senkei"], Line_atm, Sec_panel)
                arCoordLines_atm = Devide_Coord_LRib(arCoordLines_atm, PitchTran_atm)
                ang_atm, faces_atm, name_atm, ref_atm = (
                    Atm_panel[i_1 + 1]["Angle"],
                    Atm_panel[i_1 + 1]["Face"],
                    Atm_panel[i_1 + 1]["Name"],
                    Atm_panel[i_1 + 1]["Ref"],
                )
                ang1_atm, ang2_atm = ang_atm
                for i_2 in range(0, len(arCoordLines_atm)):
                    if i_2 != 0 and i_2 != len(arCoordLines_atm) - 1:
                        arCoordLine_atm = arCoordLines_atm[i_2]
                        arcoord_atm, arPoscoord_atm = Devide_Pitch_Polyline(
                            arCoordLine_atm, PitchLong_atm, dirPitchLong_atm
                        )

                        for i_3 in range(0, len(arcoord_atm)):
                            pm1 = arCoordLines_atm[i_2 - 1][arPoscoord_atm[i_3]]
                            pm2 = arCoordLines_atm[i_2 + 1][arPoscoord_atm[i_3]]
                            pm3 = arCoordLines_atm[i_2 - 1][arPoscoord_atm[i_3] + 1]
                            normalvector = DefMath.Normal_vector(pm1, pm2, pm3)

                            if ang1_atm == "V":
                                pmc1 = arcoord_atm[i_3].copy()
                                pmc2 = [pmc1[0], pmc1[1], pmc1[2] + 1000]
                                pmc3 = [pmc1[0], pmc1[1] + 1000, pmc1[2]]
                            elif float(ang1_atm) == 90 or float(ang1_atm) == 0:
                                pmc1 = arcoord_atm[i_3].copy()
                                pmc2 = pmc1 + 100 * normalvector
                                pmc3 = DefMath.rotate_point_around_axis(
                                    pmc1, pmc2, arCoordLines_atm[i_2][arPoscoord_atm[i_3] + 1], 90
                                )

                            pp1 = DefMath.Intersection_line_plane(
                                pmc1,
                                pmc2,
                                pmc3,
                                arCoordLines_atm[i_2 - 1][arPoscoord_atm[i_3]],
                                arCoordLines_atm[i_2 - 1][arPoscoord_atm[i_3] + 1],
                            )

                            if ang2_atm == "V":
                                if float(ang1_atm) == 90:
                                    pp1 = DefMath.Intersection_line_plane(
                                        pmc1,
                                        pmc2,
                                        pmc3,
                                        arCoordLines_atm[i_2 + 1][arPoscoord_atm[i_3]],
                                        arCoordLines_atm[i_2 + 1][arPoscoord_atm[i_3] + 1],
                                    )
                                    pal1 = arcoord_atm[i_3].copy()
                                    pal3 = [pal1[0], pal1[1], pal1[2] + 100]
                                    pal2 = DefMath.Offset_point(pal1, pp1, pal3, 100)
                                    pal3 = pp1
                                elif float(ang1_atm) == 0:
                                    pal1 = arcoord_atm[i_3].copy()
                                    pal3 = arCoordLines_atm[i_2][arPoscoord_atm[i_3]]
                                    pro = [pal1[0], pal1[1], pal1[2] + 100]
                                    pal2 = DefMath.Offset_point(pal1, pal3, pro, 100)

                            elif float(ang2_atm) == 90:
                                if ang1_atm == "V":
                                    pal1 = arcoord_atm[i_3].copy()
                                    pal3 = pal1 + 100 * normalvector
                                    pal2 = DefMath.Offset_point(pal1, pp1, pal3, -100)
                                elif float(ang1_atm) == 90:
                                    pp1 = DefMath.Intersection_line_plane(
                                        pmc1,
                                        pmc2,
                                        pmc3,
                                        arCoordLines_atm[i_2 + 1][arPoscoord_atm[i_3]],
                                        arCoordLines_atm[i_2 + 1][arPoscoord_atm[i_3] + 1],
                                    )
                                    pal1 = arcoord_atm[i_3].copy()
                                    pal3 = pal1 + 100 * normalvector
                                    pal2 = DefMath.Offset_point(pal1, pp1, pal3, 100)
                                    pal3 = pp1
                                elif float(ang1_atm) == 0:
                                    pal1 = arcoord_atm[i_3].copy()
                                    pal3 = arCoordLines_atm[i_2][arPoscoord_atm[i_3]]
                                    pro = pal1 + 100 * normalvector
                                    pal2 = DefMath.Offset_point(pal1, pal3, pro, 100)
                            else:
                                if DefMath.is_number(ang2_atm):
                                    if float(ang1_atm) == 0:
                                        pal1 = arcoord_atm[i_3].copy()
                                        pal3 = arCoordLines_atm[i_2][arPoscoord_atm[i_3]]
                                        pro = pal1 + 100 * normalvector
                                        if i_1 % 2 == 0:
                                            pro = DefMath.rotate_point_around_axis(
                                                pal1, pal3, pro, 90 - float(ang2_atm)
                                            )
                                        else:
                                            pro = DefMath.rotate_point_around_axis(
                                                pal1, pal3, pro, float(ang2_atm) - 90
                                            )

                                        pal2 = DefMath.Offset_point(pal1, pal3, pro, 100)

                            if faces_atm == "L":
                                pal1 = pal1 - Thick1 * normalvector
                                pal2 = pal2 - Thick1 * normalvector
                            elif faces_atm == "R":
                                pal1 = pal1 + Thick2 * normalvector
                                pal2 = pal2 + Thick2 * normalvector
                            elif faces_atm == "T":
                                pal1 = pal1 + Thick1 * normalvector
                                pal2 = pal2 + Thick1 * normalvector
                            elif faces_atm == "B":
                                pal1 = pal1 - Thick2 * normalvector
                                pal2 = pal2 - Thick2 * normalvector

                            Calculate_ATM(ifc_all, Data_Json["MemberData"], name_atm, ref_atm, pal1, pal2, pal3)

        # Cutout処理
        if Cutout_panel:
            for i_1 in range(0, len(Cutout_panel), 2):
                pitchlong_cutout, pitchtran_cutout = Cutout_panel[i_1]
                sec_cutout, PitchLong_cutout = pitchlong_cutout
                sec_cutout = sec_cutout.split("-")
                Line_cutout, PitchTran_cutout = pitchtran_cutout
                Line_cutout = Line_cutout.split("-")
                arCoordLines_cutout = Load_Coordinate_Panel(Data_Json["Senkei"], Line_cutout, sec_cutout)
                arCoordLines_cutout = Devide_Coord_LRib(arCoordLines_cutout, PitchTran_cutout)
                faces_cutout, ref_cutout = Cutout_panel[i_1 + 1]["Face"], Cutout_panel[i_1 + 1]["Ref"]

                for i_2 in range(0, len(arCoordLines_cutout)):
                    if i_2 != 0 and i_2 != len(arCoordLines_cutout) - 1:
                        arCoordLine_cutout = arCoordLines_cutout[i_2]
                        arcoord_atm, arPoscoord_cutout = Devide_Pitch_Polyline(
                            arCoordLine_cutout, PitchLong_cutout, "XY"
                        )
                        for i_3 in range(0, len(arcoord_atm)):
                            pbase = arcoord_atm[i_3]
                            pdir = DefMath.Point_on_parallel_line(
                                pbase,
                                arCoordLines_cutout[0][arPoscoord_cutout[i_3]],
                                arCoordLines_cutout[-1][arPoscoord_cutout[i_3]],
                                100,
                            )
                            p1_3d = arCoordLines_cutout[-1][arPoscoord_cutout[i_3]]
                            p2_3d = arCoordLines_cutout[-1][arPoscoord_cutout[i_3] + 1]
                            p3_3d = arCoordLines_cutout[0][arPoscoord_cutout[i_3]]

                            for Solid_Panel1 in arSolid_Panel1:
                                if Solid_Panel1 != None:
                                    solid_hole1 = Draw_Solid_CutOut(
                                        ifc_all,
                                        Data_Json["MemberData"],
                                        Data_Json["MemberRib"],
                                        ref_cutout,
                                        faces_cutout,
                                        Thick1,
                                        Thick2,
                                        pbase,
                                        pdir,
                                        p1_3d,
                                        p2_3d,
                                        p3_3d,
                                    )
                                    Solid_Panel1 = ifc_file.createIfcBooleanResult(
                                        "DIFFERENCE", Solid_Panel1, solid_hole1
                                    )

                            for Solid_Panel2 in arSolid_Panel2:
                                if Solid_Panel2 != None:
                                    solid_hole2 = Draw_Solid_CutOut(
                                        ifc_all,
                                        Data_Json["MemberData"],
                                        Data_Json["MemberRib"],
                                        ref_cutout,
                                        faces_cutout,
                                        Thick1,
                                        Thick2,
                                        pbase,
                                        pdir,
                                        p1_3d,
                                        p2_3d,
                                        p3_3d,
                                    )
                                    Solid_Panel2 = ifc_file.createIfcBooleanResult(
                                        "DIFFERENCE", Solid_Panel2, solid_hole2
                                    )

        # Stud処理
        if Stud_panel:
            for i_1 in range(0, len(Stud_panel), 2):
                pitchlong_stud, pitchtran_stud = Stud_panel[i_1]
                dirPitchLong_stud, PitchLong_stud = pitchlong_stud
                Line_stud, PitchTran_stud = pitchtran_stud
                Line_stud = Line_stud.split("-")
                arCoordLines_stud = Load_Coordinate_Panel(Data_Json["Senkei"], Line_stud, Sec_panel)
                arCoordLines_stud = Devide_Coord_LRib(arCoordLines_stud, PitchTran_stud)
                faces_stud, ref_stud = Stud_panel[i_1 + 1]["Face"], Stud_panel[i_1 + 1]["Ref"]
                for i_2 in range(0, len(arCoordLines_stud)):
                    if i_2 != 0 and i_2 != len(arCoordLines_stud) - 1:
                        arCoordLine_stud = arCoordLines_stud[i_2]
                        arcoord_stud, arPoscoord_stud = Devide_Pitch_Polyline(
                            arCoordLine_stud, PitchLong_stud, dirPitchLong_stud
                        )

                        for i_3 in range(0, len(arcoord_stud)):
                            pm1 = arCoordLines_stud[i_2 - 1][arPoscoord_stud[i_3]]
                            pm2 = arCoordLines_stud[i_2 + 1][arPoscoord_stud[i_3]]
                            pm3 = arCoordLines_stud[i_2 - 1][arPoscoord_stud[i_3] + 1]
                            normalvector = DefMath.Normal_vector(pm1, pm2, pm3)

                            pmc1 = arcoord_stud[i_3].copy()
                            pmc2 = pmc1 + 100 * normalvector
                            pmc3 = DefMath.rotate_point_around_axis(
                                pmc1, pmc2, arCoordLines_stud[i_2][arPoscoord_stud[i_3] + 1], 90
                            )

                            pp1 = DefMath.Intersection_line_plane(
                                pmc1,
                                pmc2,
                                pmc3,
                                arCoordLines_stud[i_2 - 1][arPoscoord_stud[i_3]],
                                arCoordLines_stud[i_2 - 1][arPoscoord_stud[i_3] + 1],
                            )

                            pal1 = arcoord_stud[i_3].copy()
                            pal2 = pal1 + 100 * normalvector
                            pal3 = DefMath.Offset_point(pal1, pal2, pp1, -100)

                            if faces_stud == "L":
                                pal1 = pal1 - Thick1 * normalvector
                                pal3 = pal3 - Thick1 * normalvector
                            elif faces_stud == "R":
                                pal1 = pal1 + Thick2 * normalvector
                                pal3 = pal3 + Thick2 * normalvector
                            elif faces_stud == "T":
                                pal1 = pal1 + Thick1 * normalvector
                                pal3 = pal3 + Thick1 * normalvector
                            elif faces_stud == "B":
                                pal1 = pal1 - Thick2 * normalvector
                                pal3 = pal3 - Thick2 * normalvector

                            Calculate_Stud(ifc_all, Data_Json["MemberData"], ref_stud, pal1, pal2, pal3)

        # パネルをIFCに追加
        color_style = DefIFC.create_color(ifc_file, 172.0, 207.0, 236.0)

        panel1_count = 0
        panel2_count = 0
        num_segments = max(len(arSolid_Panel1), len(arSolid_Panel2))
        for idx, Solid_Panel1 in enumerate(arSolid_Panel1):
            if Solid_Panel1 != None:
                styled_item = ifc_file.createIfcStyledItem(Item=Solid_Panel1, Styles=[color_style])
                shape_representation = ifc_file.createIfcShapeRepresentation(
                    ContextOfItems=geom_context,
                    RepresentationIdentifier="Body",
                    RepresentationType="Brep",
                    Items=[Solid_Panel1],
                )
                segment_name = f"{Name_panel}_T0_X{idx}"
                DefIFC.Add_shape_representation_in_Beam(ifc_file, bridge_span, shape_representation, segment_name)
                panel1_count += 1

        for idx, Solid_Panel2 in enumerate(arSolid_Panel2):
            if Solid_Panel2 != None:
                styled_item = ifc_file.createIfcStyledItem(Item=Solid_Panel2, Styles=[color_style])
                shape_representation = ifc_file.createIfcShapeRepresentation(
                    ContextOfItems=geom_context,
                    RepresentationIdentifier="Body",
                    RepresentationType="Brep",
                    Items=[Solid_Panel2],
                )
                segment_name = f"{Name_panel}_T1_X{idx}"
                DefIFC.Add_shape_representation_in_Beam(ifc_file, bridge_span, shape_representation, segment_name)
                panel2_count += 1


def _generate_sub_panels(ctx):
    """
    サブパネルを生成する

    Args:
        ctx: BridgeContext オブジェクト
    """
    ifc_all = ctx.ifc_all
    Data_Json = ctx.data_json
    side_export = ctx.side_export

    for subpanel in Data_Json["SubPanel"]:
        name_subpanel = subpanel["Name"]
        girder_subpanel = subpanel["Girder"]
        sec_subpanel = subpanel["Sec"]
        point_subpanel = subpanel["Point"]
        part_subpanel = subpanel["Part"]
        print(f"  SubPanel - {name_subpanel}")
        arNamePoint, arCoordPoint = Calculate_points_Sub_Panel(Data_Json["Senkei"], point_subpanel, sec_subpanel)
        number_block = Find_number_block_MainPanel(Data_Json["MainPanel"], sec_subpanel)
        for partsub in part_subpanel:
            name_part = partsub["Name"]
            material_part = partsub["Material"]
            out_part = partsub["Out"]
            extend_part = partsub["Extend"]
            corner_part = partsub["Corner"]
            slot_part = partsub["Slot"]
            joint_part = partsub["Joint"]
            cutout_part = partsub["Cutout"]
            stiff_part = partsub["Stiff"]
            flg_part = partsub["FLG"]

            data_part = (
                name_part,
                material_part,
                out_part,
                extend_part,
                corner_part,
                slot_part,
                joint_part,
                cutout_part,
                stiff_part,
                flg_part,
            )
            Calculate_Part_SubPanel(
                ifc_all,
                Data_Json["MainPanel"],
                Data_Json["Senkei"],
                Data_Json["MemberSPL"],
                Data_Json["MemberRib"],
                Data_Json["MemberData"],
                name_subpanel,
                girder_subpanel,
                sec_subpanel,
                part_subpanel,
                arNamePoint,
                arCoordPoint,
                data_part,
                side_export,
            )


def _generate_taikeikou(ctx):
    """
    対傾構を生成する

    Args:
        ctx: BridgeContext オブジェクト
    """
    ifc_all = ctx.ifc_all
    Data_Json = ctx.data_json

    for taikeikou in Data_Json["Taikeikou"]:
        name_taikeikou = taikeikou["Name"]
        type_taikeikou = taikeikou["Type"]
        girder_taikeikou = taikeikou["Girder"]
        point_taikeikou = taikeikou["Point"]
        distmod_taikeikou = taikeikou["Distmod"]
        hole_taikeikou = taikeikou["Hole"]
        vstiff_taikeikou = taikeikou["Vstiff"]
        shape_taikeikou = taikeikou["Shape"]
        guss_taikeikou = taikeikou["Guss"]
        section_taikeikou_raw = taikeikou.get("Section", "C1")

        if isinstance(section_taikeikou_raw, str) and "," in section_taikeikou_raw:
            sections_list = [s.strip() for s in section_taikeikou_raw.split(",") if s.strip()]

            for section_idx, section_taikeikou in enumerate(sections_list):
                if len(sections_list) == 1:
                    taikeikou_name = name_taikeikou
                else:
                    taikeikou_name = f"{name_taikeikou}_{section_taikeikou}"

                infor_Taikeikou = (
                    taikeikou_name,
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
                print(f"  Taikeikou - {taikeikou_name}")
                _log_print(f"    [Taikeikou] セクション名ベース指定: {section_taikeikou}")

                number_block = None
                for panel in Data_Json["MainPanel"]:
                    Type_panel = panel["Type"]
                    if Type_panel["Girder"] == girder_taikeikou[0]:
                        number_block = Type_panel["Block"]
                        break

                if number_block is None:
                    _log_print(
                        f"    [Taikeikou] 警告: 桁 '{girder_taikeikou[0]}' のブロック番号が見つかりません。デフォルト値 '1' を使用します。"
                    )
                    number_block = "1"

                try:
                    Calculate_Taikeikou(
                        ifc_all, Data_Json["MainPanel"], Data_Json["Senkei"], number_block, infor_Taikeikou
                    )
                except Exception as e:
                    _log_print(f"    [Taikeikou] エラー: {str(e)}")
                    raise

        else:
            section_taikeikou = section_taikeikou_raw
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
            print(f"  Taikeikou - {name_taikeikou}")
            _log_print(f"    [Taikeikou] セクション名ベース指定: {section_taikeikou}")
            number_block = None
            for panel in Data_Json["MainPanel"]:
                Type_panel = panel["Type"]
                if Type_panel["Girder"] == girder_taikeikou[0]:
                    number_block = Type_panel["Block"]
                    break

            if number_block is None:
                _log_print(
                    f"    [Taikeikou] 警告: 桁 '{girder_taikeikou[0]}' のブロック番号が見つかりません。デフォルト値 '1' を使用します。"
                )
                number_block = "1"

            try:
                Calculate_Taikeikou(ifc_all, Data_Json["MainPanel"], Data_Json["Senkei"], number_block, infor_Taikeikou)
            except Exception as e:
                _log_print(f"    [Taikeikou] エラー: {str(e)}")
                raise


def _generate_yokokou(ctx):
    """
    横構を生成する

    Args:
        ctx: BridgeContext オブジェクト
    """
    ifc_all = ctx.ifc_all
    Data_Json = ctx.data_json

    for yokokou in Data_Json["Yokokou"]:
        name_yokokou = yokokou["Name"]
        type_yokokou = yokokou["Type"]
        girder_yokokou = yokokou["Girder"]
        point_yokokou = yokokou["Point"]
        shape_yokokou = yokokou["Shape"]
        guss_yokokou = yokokou["Guss"]
        infor_yokokou = name_yokokou, type_yokokou, girder_yokokou, point_yokokou, shape_yokokou, guss_yokokou
        print(f"  Yokogeta - {name_yokokou}")

        Calculate_Yokokou(
            ifc_all,
            Data_Json["Senkei"],
            Data_Json["MainPanel"],
            Data_Json["SubPanel"],
            Data_Json["Taikeikou"],
            Data_Json["MemberData"],
            Data_Json["MemberRib"],
            infor_yokokou,
        )

    # Yokokou_Structural
    if "Yokokou_Structural" in Data_Json:
        for yokokou_structural in Data_Json["Yokokou_Structural"]:
            name_yokokou = yokokou_structural["Name"]
            position_type = yokokou_structural.get("Position", "Bottom")
            girder_list = yokokou_structural["Girder"]
            section_range = yokokou_structural.get("SectionRange", ["S1", "E1"])
            z_offset = yokokou_structural.get("ZOffset", 0)
            truss_info = yokokou_structural.get("Truss", {})
            hole_info = yokokou_structural.get("Hole", {})
            guss_list = yokokou_structural.get("Guss", [])
            infor_yokokou_structural = (
                name_yokokou,
                position_type,
                girder_list,
                section_range,
                z_offset,
                truss_info,
                hole_info,
                guss_list,
            )
            print(f"  Yokokou_Structural - {name_yokokou}")

            try:
                Calculate_Yokokou_Structural(
                    ifc_all, Data_Json["Senkei"], Data_Json["MainPanel"], infor_yokokou_structural
                )
            except Exception as e:
                _log_print(f"    [Yokokou_Structural] エラー: {str(e)}")
                raise

    # Yokokou_LateralBracing
    if "Yokokou_LateralBracing" in Data_Json:
        for yokokou_lb in Data_Json["Yokokou_LateralBracing"]:
            name_lb = yokokou_lb["Name"]
            level_lb = yokokou_lb.get("Level", "Bottom")
            member_info = yokokou_lb.get("Member", {})
            shape_info = yokokou_lb.get("Shape", [])
            pitch_info = yokokou_lb.get("Pitch", [0, "X", 0])
            z_offset = yokokou_lb.get("ZOffset", 0)
            y_offset = yokokou_lb.get("YOffset", 0)
            hole_info = yokokou_lb.get("Hole", {})
            guss_list = yokokou_lb.get("Guss", [])
            infor_lb = (
                name_lb,
                level_lb,
                member_info,
                shape_info,
                pitch_info,
                z_offset,
                y_offset,
                hole_info,
                guss_list,
            )
            print(f"  Yokokou_LateralBracing - {name_lb}")

            try:
                Calculate_Yokokou_LateralBracing(ifc_all, Data_Json["Senkei"], Data_Json["MainPanel"], infor_lb)
            except Exception as e:
                _log_print(f"    [Yokokou_LateralBracing] エラー: {str(e)}")
                raise


def _generate_yokogeta(ctx):
    """
    横桁を生成する

    Args:
        ctx: BridgeContext オブジェクト
    """
    ifc_all = ctx.ifc_all
    Data_Json = ctx.data_json

    if "Yokogeta" not in Data_Json:
        return

    for yokogeta in Data_Json["Yokogeta"]:
        name_yokogeta = yokogeta["Name"]
        girder_list = yokogeta["Girder"]
        section = yokogeta["Section"]
        reference = yokogeta.get("Reference", "Top")
        height = yokogeta.get("Height", 800)
        z_offset = yokogeta.get("ZOffset", 0)
        web_info = yokogeta.get("Web", {"Thick": 12, "Mat": "SM400A"})
        uflange_info = yokogeta.get("UFlange", {"Thick": 16, "Width": 200, "Mat": "SM400A"})
        lflange_info = yokogeta.get("LFlange", {"Thick": 16, "Width": 200, "Mat": "SM400A"})
        break_info = yokogeta.get("Break", {"Count": 1})
        infor_yokogeta = (
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
        )
        print(f"  Yokogeta - {name_yokogeta}")

        try:
            Calculate_Yokogeta(ifc_all, Data_Json["Senkei"], Data_Json["MainPanel"], infor_yokogeta)
        except Exception as e:
            _log_print(f"    [Yokogeta] エラー: {str(e)}")
            raise


def _generate_shouban_and_guardrail(ctx):
    """
    床版と高欄を生成する

    Args:
        ctx: BridgeContext オブジェクト
    """
    ifc_all = ctx.ifc_all
    Data_Json = ctx.data_json

    for shouban in Data_Json["Shouban"]:
        name_shouban = shouban["Name"]
        line_shouban = shouban["Line"]
        sec_shouban = shouban["Sec"]
        overhang_left = shouban.get("OverhangLeft", 0)
        overhang_right = shouban.get("OverhangRight", 0)
        deck_thickness = shouban.get("Thickness", 200.0)
        z_offset = shouban.get("ZOffset", 0.0)
        break_info = shouban.get("Break", {})
        break_thick = break_info.get("Thick", 1)
        break_x = break_info.get("X", 1)
        break_y = break_info.get("Y", 1)
        no_thick_break_for_flange = break_info.get("NoThickBreakForFlange", False)
        infor_shouban = (
            name_shouban,
            line_shouban,
            sec_shouban,
            overhang_left,
            overhang_right,
            break_thick,
            break_x,
            break_y,
            no_thick_break_for_flange,
            deck_thickness,
            z_offset,
        )
        print(f"  Shouban - {name_shouban}")
        _log_print(f"  OverhangLeft: {overhang_left}mm, OverhangRight: {overhang_right}mm")
        _log_print(f"  Thickness: {deck_thickness}mm, ZOffset: {z_offset}mm")
        _log_print(
            f"  Break: Thick={break_thick}, X={break_x}, Y={break_y}, NoThickBreakForFlange={no_thick_break_for_flange}"
        )

        Calculate_Shouban(ifc_all, Data_Json["Senkei"], Data_Json["MainPanel"], infor_shouban)

        # Guardrail（高欄）
        guardrail_info = shouban.get("Guardrail", {})
        if guardrail_info:
            left_guardrail = guardrail_info.get("Left", {})
            right_guardrail = guardrail_info.get("Right", {})
            left_width = float(left_guardrail.get("Width", 0))
            left_height = float(left_guardrail.get("Height", 0))
            right_width = float(right_guardrail.get("Width", 0))
            right_height = float(right_guardrail.get("Height", 0))

            left_break = left_guardrail.get("Break", False)
            right_break = right_guardrail.get("Break", False)

            if left_width > 0 and left_height > 0 or right_width > 0 and right_height > 0:
                infor_guardrail = (
                    name_shouban,
                    line_shouban,
                    sec_shouban,
                    overhang_left,
                    overhang_right,
                    left_width,
                    left_height,
                    right_width,
                    right_height,
                    left_break,
                    right_break,
                )
                print(f"  Guardrail - {name_shouban}")
                _log_print(f"  Left: Width={left_width}mm, Height={left_height}mm, Break={left_break}")
                _log_print(f"  Right: Width={right_width}mm, Height={right_height}mm, Break={right_break}")

                try:
                    Calculate_Guardrail(ifc_all, Data_Json["Senkei"], Data_Json["MainPanel"], infor_guardrail)
                except Exception as e:
                    _log_print(f"    [Guardrail] エラー: {str(e)}")
                    import traceback

                    _log_print(f"    [Guardrail] トレースバック:\n{traceback.format_exc()}")
                    raise


def _generate_bearing(ctx):
    """
    支承を生成する

    Args:
        ctx: BridgeContext オブジェクト
    """
    ifc_all = ctx.ifc_all
    Data_Json = ctx.data_json

    if "Bearing" not in Data_Json:
        return

    for bearing in Data_Json["Bearing"]:
        name_bearing = bearing["Name"]
        girder_bearing = bearing["Girder"]
        section_bearing = bearing["Section"]
        type_bearing = bearing["Type"]
        shape_bearing = bearing["Shape"]
        position_bearing = bearing.get("Position", {})
        line_bearing = position_bearing.get("Line", f"BG{girder_bearing[-1]}")
        offset_z = position_bearing.get("OffsetZ", 0)
        offset_y = position_bearing.get("OffsetY", 0)
        local_offset_x = position_bearing.get("LocalOffsetX", 0)
        local_offset_y = position_bearing.get("LocalOffsetY", 0)

        infor_bearing = (
            name_bearing,
            girder_bearing,
            section_bearing,
            type_bearing,
            shape_bearing,
            line_bearing,
            offset_z,
            offset_y,
            local_offset_x,
            local_offset_y,
        )
        print(f"  Bearing - {name_bearing}")
        _log_print(
            f"  Type: {type_bearing}, Girder: {girder_bearing}, Section: {section_bearing}, Line: {line_bearing}"
        )
        _log_print(f"  OffsetZ: {offset_z}mm, OffsetY: {offset_y}mm")

        try:
            Calculate_Bearing(ifc_all, Data_Json["Senkei"], Data_Json["MainPanel"], infor_bearing)
        except Exception as e:
            _log_print(f"    [Bearing] エラー: {str(e)}")
            import traceback

            _log_print(f"    [Bearing] トレースバック:\n{traceback.format_exc()}")
            raise


def _save_ifc_file(ctx, output_ifc_name):
    """
    IFCファイルを保存する

    Args:
        ctx: BridgeContext オブジェクト
        output_ifc_name: 出力IFCファイル名
    """
    ifc_file = ctx.ifc_file
    location = ctx.location

    if output_ifc_name:
        if os.path.isabs(output_ifc_name):
            output_file = output_ifc_name
        else:
            output_file = location + output_ifc_name
    else:
        output_file = location + "Girder.ifc"

    _log_print("=" * 60)
    all_beams = ifc_file.by_type("IfcBeam")
    _log_print(f"IFCファイル内のIfcBeam数: {len(all_beams)}")
    for beam in all_beams:
        _log_print(
            f"  - Beam: Name={beam.Name}, GlobalId={beam.GlobalId}, Representation={beam.Representation is not None}"
        )
        if beam.Representation:
            _log_print(
                f"    Representations数: {len(beam.Representation.Representations) if hasattr(beam.Representation, 'Representations') else 'N/A'}"
            )
    ifc_file.write(output_file)
    _log_print(f"IFCファイル保存完了: {output_file}")
    _log_print("=" * 60)


# =============================================================================
# メイン処理関数（オーケストレーター）
# =============================================================================
def RunBridge(Location, NameFile, OutputIFCName=None):
    """
    メイン処理関数（オーケストレーター）
    ExcelまたはJSONファイルから鋼橋データを読み込み、IFCモデルを生成する

    Args:
        Location: ファイルのディレクトリパス
        NameFile: ファイル名（.xlsxまたは.json）
        OutputIFCName: 出力IFCファイル名（省略時は'Girder.ifc'）

    処理フロー:
        1. ログ設定
        2. IFCファイルのセットアップ
        3. データ読み込み
        4. 座標系設定
        5. 計算線形の処理
        6. 各部材の生成（メインパネル、サブパネル、対傾構、横構、横桁、床版、支承）
        7. IFCファイルの保存
    """
    global log_print_func, DEBUG_MODE

    # 1. ログ設定
    log_file = _setup_logging(Location, DEBUG_MODE)

    # 進捗メッセージ
    print(f"IFCモデル生成開始: {Location}{NameFile}")

    try:
        # 2. IFCファイルのセットアップ
        ifc_file, bridge_span, geom_context = DefIFC.SetupIFC()

        # 3. データ読み込み
        Data_Json = _load_bridge_data(Location, NameFile)

        # 4. BridgeContextの作成
        ctx = BridgeContext(ifc_file, bridge_span, geom_context, Data_Json, Location)

        # 5. 損傷情報の読み込み
        damage_info_dict = _load_damage_info(Location)
        if damage_info_dict:
            DefIFC.load_damage_info(damage_info_dict)

        # 6. 座標系設定
        _setup_coordinate_system(Data_Json)

        # 7. 計算線形の処理
        _process_calculate_lines(Data_Json)

        # 8. 各部材の生成
        _generate_main_panels(ctx)
        _generate_sub_panels(ctx)
        _generate_taikeikou(ctx)
        _generate_yokokou(ctx)
        _generate_yokogeta(ctx)
        _generate_shouban_and_guardrail(ctx)
        _generate_bearing(ctx)

        # 9. IFCファイルの保存
        _save_ifc_file(ctx, OutputIFCName)
    finally:
        # ログファイルを閉じる（DEBUG_MODEがTrueの場合のみ）
        if "log_file" in locals() and log_file is not None:
            log_file.close()
