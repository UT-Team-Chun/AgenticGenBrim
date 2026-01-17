"""
ExcelファイルからJSONファイルへのデータ変換モジュール
Excelファイルの各シートからデータを読み込み、構造化されたJSON形式で保存する
"""

import json
import re

import pandas as pd

from src.bridge_json_to_ifc.ifc_utils_new.io import DefExcel


def Convert_DataInput_From_Excel_To_Json(Location, NameFile):
    """
    Excelファイルからデータを読み込み、JSONファイルに変換する

    Args:
        Location: Excelファイルのディレクトリパス
        NameFile: Excelファイル名

    Returns:
        変換されたデータの辞書形式
        {
            "Infor": 橋梁情報,
            "Senkei": 線形データ,
            "Calculate": 計算線形データ,
            "MainPanel": メインパネルデータ,
            "SubPanel": サブパネルデータ,
            ...
        }
    """
    linkfile = Location + NameFile

    # -------------Infor------------------------------------------------
    Ws_infor = pd.read_excel(linkfile, sheet_name="Infor", header=None)
    Infor_data = DefExcel.Load_Sheet_Infor(Ws_infor)

    # -------------Senkei------------------------------------------------
    Ws_Senkei = pd.read_excel(linkfile, sheet_name="Senkei", header=None)
    Senkei_data = DefExcel.Load_Sheet_Senkei(Ws_Senkei)
    # --------------Calculate Line---------------------------------------
    try:
        Ws_Calculate_Line = pd.read_excel(linkfile, sheet_name="Calculate_Line", header=None)
        Calculate_Line = DefExcel.Load_Sheet_Calculate(Ws_Calculate_Line)
    except ValueError:
        Calculate_Line = []

    # -------------Mainpanel------------------------------------------------
    Ws_MainPanel_Line = pd.read_excel(linkfile, sheet_name="MainPanel_Line", header=None)
    MainPanel_Line = DefExcel.Load_Sheet_MainPanel_Line(Ws_MainPanel_Line, Senkei_data)

    Ws_MainPanel_Rec = pd.read_excel(linkfile, sheet_name="MainPanel_Rec", header=None)
    MainPanel_Rec = DefExcel.Load_Sheet_MainPanel_Rec(Ws_MainPanel_Rec)

    # デフォルト値を定義（材料と延長）
    default_material = {"Thick1": 4.5, "Thick2": 4.5, "Mat": "SM400A"}
    default_expand = {"E1": 0, "E2": 0, "E3": 0, "E4": 0}

    # MainPanel_LineとMainPanel_Recをマージ
    MainPanel_data1 = merge_lists_by_name(
        MainPanel_Line, MainPanel_Rec, {"Material": default_material, "Expand": default_expand}
    )

    # Excelファイルから"MainPanel_Mark"シートのデータを読み込む
    Ws_MainPanel_Mark = pd.read_excel(linkfile, sheet_name="MainPanel_Mark", header=None)
    MainPanel_Mark = DefExcel.Load_Sheet_MainPanel_Mark(Ws_MainPanel_Mark)

    # MainPanel_Markのデフォルト値を定義
    default_mark = {
        "Jbut": {},
        "Corner": [],
        "Lrib": [],
        "Vstiff": [],
        "Hstiff": [],
        "Atm": [],
        "Cutout": [],
        "Stud": [],
    }

    # MainPanel_data1とMainPanel_Markをマージ
    MainPanel_data2 = merge_lists_by_name(MainPanel_data1, MainPanel_Mark, default_mark)

    # 最終結果
    MainPanel_data = MainPanel_data2

    # -------------Subpanel------------------------------------------------
    try:
        Ws_SubPanel_Line = pd.read_excel(linkfile, sheet_name="SubPanel_Line", header=None)
        SubPanel_Line = DefExcel.Load_Sheet_SubPanel_Line(Ws_SubPanel_Line)
        Ws_SubPanel_Rec = pd.read_excel(linkfile, sheet_name="SubPanel_Rec", header=None)
        SubPanel_Rec = DefExcel.Load_Sheet_SubPanel_Rec(Ws_SubPanel_Rec)

        # デフォルト値を定義
        default_material = {"Thick1": 4.5, "Thick2": 4.5, "Mat": "SM400A"}
        default_out = {}
        default_expand = {"E1": 0, "E2": 0, "E3": 0, "E4": 0}
        # SubPanel_LineとSubPanel_Recをマージ
        SubPanel_data = merge_lists_by_name(
            SubPanel_Line, SubPanel_Rec, {"Material": default_material, "Out": default_out, "Expand": default_expand}
        )

        Ws_SubPanel_Mark = pd.read_excel(linkfile, sheet_name="SubPanel_Mark", header=None)
        SubPanel_Mark = DefExcel.Load_Sheet_SubPanel_Mark(Ws_SubPanel_Mark)

        for panel in SubPanel_data:
            # sub_panel_marks内で名前が一致するpanelを検索
            mark_panel = next((mp for mp in SubPanel_Mark if mp["Name"] == panel["Name"]), None)
            if mark_panel:
                for part in panel.get("Part", []):
                    # part["Name"]と一致する名前のmarkPartを検索
                    mark_part = next(
                        (mpart for mpart in mark_panel.get("MarkPart", []) if mpart["Name"] == part["Name"]), None
                    )
                    if mark_part:
                        # mark_partのキーをpartの同じレベルに追加（既存のキーは上書きされる）
                        part.update(mark_part)
    except ValueError:
        SubPanel_data = []
    # -------------Taikeikou------------------------------------------------
    try:
        Ws_Taikeikou = pd.read_excel(linkfile, sheet_name="Taikeikou", header=None)
        Taikeikou_data = DefExcel.Load_Sheet_Taikeikou(Ws_Taikeikou)
    except ValueError:
        Taikeikou_data = []
    # -------------Yokokou------------------------------------------------
    try:
        Ws_Yokokou = pd.read_excel(linkfile, sheet_name="Yokokou", header=None)
        Yokokou_data = DefExcel.Load_Sheet_Yokokou(Ws_Yokokou)
    except ValueError:
        Yokokou_data = []

    # -------------Shouban------------------------------------------------
    try:
        Ws_Shouban = pd.read_excel(linkfile, sheet_name="Shouban", header=None)
        Shouban_data = DefExcel.Load_Sheet_Shouban(Ws_Shouban)
    except ValueError:
        Shouban_data = []

    # -------------Member SPL------------------------------------------------
    try:
        Ws_Member_Spl = pd.read_excel(linkfile, sheet_name="Member_Spl", header=None)
        Member_Spl_data = DefExcel.Load_Sheet_Member_SPL(Ws_Member_Spl)
    except ValueError:
        Member_Spl_data = []

    # -------------Member Rib------------------------------------------------
    try:
        Ws_Member_Rib = pd.read_excel(linkfile, sheet_name="Member_Rib", header=None)
        Member_Rib_data = DefExcel.Load_Sheet_Member_Rib(Ws_Member_Rib)
    except ValueError:
        Member_Rib_data = []

    # -------------Member Data------------------------------------------------
    try:
        Ws_Member_Data = pd.read_excel(linkfile, sheet_name="Member_Data", header=None)
        Member_data = DefExcel.Load_Sheet_Member_Data(Ws_Member_Data)
    except ValueError:
        Member_data = []

    # ----------------------------------------------------------------------
    Data_Json = {
        "Infor": Infor_data,
        "Senkei": Senkei_data,
        "Calculate": Calculate_Line,
        "MainPanel": MainPanel_data,
        "SubPanel": SubPanel_data,
        "Taikeikou": Taikeikou_data,
        "Yokokou": Yokokou_data,
        "Shouban": Shouban_data,
        "MemberSPL": Member_Spl_data,
        "MemberRib": Member_Rib_data,
        "MemberData": Member_data,
    }

    # データをJSON形式に変換
    json_pretty = json.dumps(Data_Json, ensure_ascii=False, indent=4)
    # 複数行に印刷される配列を含むパターンを検索
    pattern = re.compile(r'\[\s*\n((?:\s*(?:"[^"]*"|[\d\.\-]+)\s*(?:,\s*\n)?)+)\s*\]', re.DOTALL)

    json_inline = pattern.sub(collapse_array, json_pretty)

    atc = NameFile.split(".")
    with open(Location + atc[0] + ".json", "w", encoding="utf-8") as f:
        f.write(json_inline)

    return Data_Json


def collapse_array(match):
    """
    JSON配列をインライン形式に変換する
    複数行の配列を1行にまとめる
    """
    inner = match.group(1)
    # 改行文字と余分な空白を削除
    inner = " ".join(inner.split())
    # カンマの後の空白を削除（必要な場合）
    inner = inner.replace(", ", ",")
    return "[" + inner + "]"


def merge_lists_by_name(source_list, merge_list, default_values):
    """
    2つの辞書リストを"Name"属性でマージする

    merge_list内に同じ"Name"の要素が見つかった場合、2つの辞書をマージする。
    見つからない場合は、default_valuesに従ってキーを補完する。

    Args:
        source_list: ソースリスト（マージのベースとなるリスト）
        merge_list: マージするリスト
        default_values: デフォルト値の辞書

    Returns:
        マージされたリスト
    """
    merged = []
    for item in source_list:
        rec = next((r for r in merge_list if r["Name"] == item["Name"]), None)
        if rec:
            merged_item = {**item, **rec}
        else:
            merged_item = {**item, **default_values}
        merged.append(merged_item)
    return merged
