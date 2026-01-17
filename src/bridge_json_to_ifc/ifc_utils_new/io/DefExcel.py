"""
Excelファイルから鋼橋データを読み込むモジュール
各シート（Infor、Senkei、MainPanel、SubPanelなど）からデータを抽出し、構造化された辞書として返す
"""

import pandas as pd


def RowMax(Ws, numcol):
    """
    指定した列でデータが存在する最後の行番号を取得する

    Args:
        Ws: pandas DataFrame（Excelシート）
        numcol: 列番号（0から開始）

    Returns:
        データが存在する最後の行番号（0ベースインデックス）
    """
    last_row_with_data = Ws[Ws.iloc[:, numcol].notna()].index[-1]  # Excelの1ベースインデックスに対応するため+1を考慮
    return last_row_with_data


def ColMax(Ws, numrow):
    """
    指定した行でデータが存在する最後の列番号を取得する

    Args:
        Ws: pandas DataFrame（Excelシート）
        numrow: 行番号（0から開始）

    Returns:
        データが存在する最後の列番号
    """
    last_col_with_data = Ws.loc[numrow].notna().tolist()[::-1].index(True)  # Excelの1ベースインデックスに対応
    return Ws.shape[1] - last_col_with_data


# --------------Infor（橋梁情報）------------------------------------------
def Load_Sheet_Infor(Ws):
    """
    Inforシートから橋梁の基本情報を読み込む
    橋梁名とエクスポート側（左側/右側）の情報を取得する

    Args:
        Ws: Inforシートのpandas DataFrame

    Returns:
        橋梁情報を含む辞書
        {
            "NameBridge": 橋梁名,
            "SideExport": エクスポート側（2=両側、1=片側など）
        }
    """

    name_bridge = "NoName"
    side_export = 2
    Row_Max = RowMax(Ws, 1) + 1

    for i in range(1, Row_Max):
        if not pd.isnull(Ws.iat[i, 0]):
            cell_value = Ws.iat[i, 0]
            if cell_value == "Name Bridge":
                name_bridge = Ws.iat[i, 1]
            elif cell_value == "Side Export":
                side_export = Ws.iat[i, 1]

    Infor_data = {"NameBridge": name_bridge, "SideExport": side_export}

    return Infor_data


# --------------Senkei（線形）------------------------------------------
def Load_Sheet_Senkei(Ws_Senkei):
    """
    Senkeiシートから線形データを読み込む
    各線形（Line）の座標点（Point）を読み込み、構造化されたデータとして返す

    Args:
        Ws_Senkei: Senkeiシートのpandas DataFrame

    Returns:
        線形データのリスト
        [
            {
                "Name": 線形名,
                "Point": [
                    {"Name": 点名称, "X": X座標(mm), "Y": Y座標(mm), "Z": Z座標(mm)},
                    ...
                ]
            },
            ...
        ]
    """
    Lines = []
    Col_Max = ColMax(Ws_Senkei, 0)
    for i in range(2, Col_Max, 3):
        Row_Max = RowMax(Ws_Senkei, 1)
        nameLine = Ws_Senkei.iat[0, i]
        Points = []
        for i_1 in range(2, Row_Max + 1):
            namesec = Ws_Senkei.iat[i_1, 1]
            Coord_X = Ws_Senkei.iat[i_1, i + 0] * 1000
            Coord_Y = Ws_Senkei.iat[i_1, i + 1] * 1000
            Coord_Z = Ws_Senkei.iat[i_1, i + 2] * 1000
            # 座標をメートルからミリメートルに変換（×1000）
            Point = {"Name": namesec, "X": Coord_X, "Y": Coord_Y, "Z": Coord_Z}
            Points.append(Point)
        Line = {"Name": nameLine, "Point": Points}
        Lines.append(Line)
    return Lines


# --------------Calculate Line（計算線形）---------------------------
def Load_Sheet_Calculate(Ws_Calculate_Line):
    """
    Calculate_Lineシートから計算線形データを読み込む
    既存の線形から新しい線形を計算するための情報（OFFSET、MID、Zなど）を取得する

    Args:
        Ws_Calculate_Line: Calculate_Lineシートのpandas DataFrame

    Returns:
        計算線形データのリスト
        [
            {
                "Name": 新しい線形名,
                "Calculations": [
                    {"Type": "OFFSET"|"Z"|"MID", "BaseLine": 基準線形名, "Distance": 距離},
                    ...
                ]
            },
            ...
        ]
    """
    Calculate_Line = []
    Row_Max = RowMax(Ws_Calculate_Line, 0)
    for i in range(1, Row_Max + 1):
        if not pd.isnull(Ws_Calculate_Line.iat[i, 0]):
            rs = i
            re = -1
            if i != Row_Max:
                for i_1 in range(i + 1, Row_Max + 1):
                    if pd.isnull(Ws_Calculate_Line.iat[i_1, 1]):
                        re = i_1
                        break
            if re == -1:
                re = Ws_Calculate_Line.shape[0]
            name_line = Ws_Calculate_Line.iat[i, 0]
            Calculations = []
            for i_1 in range(rs, re):
                type = Ws_Calculate_Line.iat[i_1, 1]
                if type == "OFFSET" or type == "Z":
                    base = Ws_Calculate_Line.iat[i_1, 2]
                    dist = Ws_Calculate_Line.iat[i_1, 3]
                    cal = {"Type": type, "BaseLine": base, "Distance": dist}
                elif type == "MID":
                    base1 = Ws_Calculate_Line.iat[i_1, 2]
                    base2 = Ws_Calculate_Line.iat[i_1, 3]
                    cal = {"Type": type, "BaseLine1": base1, "BaseLine2": base2}
                Calculations.append(cal)

            data = {"Name": name_line, "Calculations": Calculations}
            Calculate_Line.append(data)

    return Calculate_Line


# --------------Main Panel------------------------------------------
def Load_Sheet_MainPanel_Line(Ws_MainPanel_Line, Senkei_data):
    MainPanel_Line_Data = []
    Row_Max = RowMax(Ws_MainPanel_Line, 1)
    for i in range(1, Row_Max):
        if not pd.isnull(Ws_MainPanel_Line.iat[i, 0]):
            Girder = Ws_MainPanel_Line.iat[i, 0]
            BlockS = int(Ws_MainPanel_Line.iat[i, 2])
            BlockE = int(Ws_MainPanel_Line.iat[i, 3])
            SecS = Ws_MainPanel_Line.iat[i + 1, 2]
            SecE = Ws_MainPanel_Line.iat[i + 1, 3]
            for i_1 in range(BlockS, BlockE + 1):
                n = i + 2
                while n <= Row_Max and not pd.isnull(Ws_MainPanel_Line.iat[n, 1]):
                    # -----------------------Name panel--------------------------------------
                    name_panel = Girder + "B" + str(i_1) + str(Ws_MainPanel_Line.iat[n, 1])
                    # -----------------------Line panel--------------------------------------
                    max_cols = ColMax(Ws_MainPanel_Line, n)
                    lines = []
                    lines.extend(
                        Ws_MainPanel_Line.iat[n, col]
                        for col in range(2, max_cols)
                        if not pd.isnull(Ws_MainPanel_Line.iat[n, col])
                    )
                    line_panel = lines
                    # -----------------------Sec panel--------------------------------------
                    points = next((item["Point"] for item in Senkei_data if item["Name"] == line_panel[0]), None)
                    point_names = [point["Name"] for point in points]
                    point_names_new = []
                    for i_2 in range(point_names.index(SecS), point_names.index(SecE) + 1):
                        point_names_new.append(point_names[i_2])
                    point_names = point_names_new
                    # 点をブロック単位で分割（"J"で始まる点を区切りとして）
                    blocks = []  # ブロックのリスト
                    current_block = []  # 現在のブロック
                    for p in point_names:
                        # 現在の点をブロックに追加
                        current_block.append(p)
                        # 現在の点が"J"で始まる場合は、現在のブロックを終了
                        if p.startswith("J"):
                            # 現在のブロックのコピーをblocksに保存
                            blocks.append(current_block.copy())
                            # 現在の点から新しいブロックを初期化（"J"の値を繰り返すため）
                            current_block = [p]
                    # 残りのブロックがある場合（"J"で終わらない場合）、追加で保存する
                    if current_block:
                        blocks.append(current_block)
                    sec_panel = blocks[i_1 - BlockS]
                    # -----------------------Type panel--------------------------------------
                    type_panel = {"Girder": Girder, "Block": "B" + str(i_1), "TypePanel": Ws_MainPanel_Line.iat[n, 1]}
                    # ----------------------------------------------------------------------
                    data = {"Name": name_panel, "Line": line_panel, "Sec": sec_panel, "Type": type_panel}
                    MainPanel_Line_Data.append(data)
                    n += 1

    return MainPanel_Line_Data


def Load_Sheet_MainPanel_Rec(Ws_MainPanel_Rec):
    MainPanel_Rec_data = []
    Row_Max = RowMax(Ws_MainPanel_Rec, 1)
    for i in range(1, Row_Max):
        if not pd.isnull(Ws_MainPanel_Rec.iat[i, 0]):
            max_cols = ColMax(Ws_MainPanel_Rec, i)
            for i_1 in range(0, max_cols):
                if i_1 != 1:
                    name_panel = Ws_MainPanel_Rec.iat[i, i_1]
                    material_panel = {
                        "Thick1": Ws_MainPanel_Rec.iat[i + 1, 2],
                        "Thick2": Ws_MainPanel_Rec.iat[i + 1, 3],
                        "Mat": Ws_MainPanel_Rec.iat[i + 1, 4],
                    }
                    extend_panel = {
                        "E1": Ws_MainPanel_Rec.iat[i + 2, 3],
                        "E2": Ws_MainPanel_Rec.iat[i + 3, 3],
                        "E3": Ws_MainPanel_Rec.iat[i + 4, 3],
                        "E4": Ws_MainPanel_Rec.iat[i + 5, 3],
                    }

                    data = {"Name": name_panel, "Material": material_panel, "Expand": extend_panel}
                    MainPanel_Rec_data.append(data)

    return MainPanel_Rec_data


def Load_Sheet_MainPanel_Mark(Ws):
    MainPanel_Mark = []
    Row_Max = RowMax(Ws, 0)
    for i in range(1, Row_Max + 1):
        if not pd.isnull(Ws.iat[i, 0]):
            rs = i
            re = -1
            if i != Row_Max:
                for i_1 in range(i + 1, Row_Max + 1):
                    if not pd.isnull(Ws.iat[i_1, 0]):
                        re = i_1
                        break
            if re == -1:
                re = Ws.shape[0]

            jbut_panels = {}
            break_panel = {}
            corners = []
            lribs = []
            vstiffs = []
            hstiffs = []
            atms = []
            cutouts = []
            studs = []

            if Ws.shape[1] > 1:
                for i_1 in range(rs, re):
                    cell_value = Ws.iat[i_1, 1]
                    if cell_value == "JBUT":
                        jbut_s = []
                        jbut_e = []
                        if not pd.isnull(Ws.iat[i_1, 3]):
                            max_cols = ColMax(Ws, i_1)
                            jbut_s.extend(
                                Ws.iat[i_1, col] for col in range(3, max_cols) if not pd.isnull(Ws.iat[i_1, col])
                            )
                        if not pd.isnull(Ws.iat[i_1 + 1, 3]):
                            max_cols = ColMax(Ws, i_1 + 1)
                            jbut_e.extend(
                                Ws.iat[i_1 + 1, col]
                                for col in range(3, max_cols)
                                if not pd.isnull(Ws.iat[i_1 + 1, col])
                            )
                        jbut_panels = {"S": jbut_s, "E": jbut_e}

                    elif cell_value == "CORNER":
                        corners = [Ws.iat[i_1, 2], Ws.iat[i_1, 3], Ws.iat[i_1, 4], Ws.iat[i_1, 5]]

                    elif cell_value == "LRIB":
                        pitch = [Ws.iat[i_1, 3], Ws.iat[i_1, 4], Ws.iat[i_1, 5]]
                        lribs.append(pitch)
                        for i_2 in range(i_1 + 1, re):
                            if not pd.isnull(Ws.iat[i_2, 1]):
                                break
                            else:
                                if not pd.isnull(Ws.iat[i_2, 2]):
                                    name_point_line = Ws.iat[i_2, 2]
                                    name_point_sec = Ws.iat[i_2, 4]
                                    face = Ws.iat[i_2 + 1, 4]
                                    name_rib = Ws.iat[i_2 + 2, 4]
                                    name_ref = Ws.iat[i_2 + 3, 4]
                                    Lrib = {
                                        "Line": name_point_line,
                                        "Point": name_point_sec,
                                        "Face": face,
                                        "Name": name_rib,
                                        "Ref": name_ref,
                                    }
                                    lribs.append(Lrib)

                    elif cell_value == "VSTIFF":
                        if Ws.iat[i_1, 2] == "PITCH":
                            pitch = [Ws.iat[i_1, 3], Ws.iat[i_1, 4], Ws.iat[i_1, 5], Ws.iat[i_1, 6]]
                        else:
                            pitch = []
                        vstiffs.append(pitch)
                        for i_2 in range(i_1, re):
                            if not pd.isnull(Ws.iat[i_2, 1]) and i_2 != i_1:
                                break
                            else:
                                if not pd.isnull(Ws.iat[i_2, 2]) and Ws.iat[i_2, 2] != "PITCH":
                                    name_point_line = Ws.iat[i_2, 2]
                                    name_point_sec = Ws.iat[i_2, 4]
                                    face = Ws.iat[i_2 + 1, 4]
                                    name_rib = Ws.iat[i_2 + 2, 4]
                                    name_ref = Ws.iat[i_2 + 3, 4]
                                    vstiff = {
                                        "Line": name_point_line,
                                        "Point": name_point_sec,
                                        "Face": face,
                                        "Name": name_rib,
                                        "Ref": name_ref,
                                    }
                                    vstiffs.append(vstiff)

                    elif cell_value == "HSTIFF":
                        pitch = [Ws.iat[i_1, 3], Ws.iat[i_1, 4], Ws.iat[i_1, 5]]
                        hstiffs.append(pitch)
                        for i_2 in range(i_1 + 1, re):
                            if not pd.isnull(Ws.iat[i_2, 1]):
                                break
                            else:
                                if not pd.isnull(Ws.iat[i_2, 2]):
                                    name_point_line = Ws.iat[i_2, 2]
                                    name_point_sec = Ws.iat[i_2, 4]
                                    face = Ws.iat[i_2 + 1, 4]
                                    name_rib = Ws.iat[i_2 + 2, 4]
                                    name_ref = Ws.iat[i_2 + 3, 4]
                                    hstiff = {
                                        "Line": name_point_line,
                                        "Point": name_point_sec,
                                        "Face": face,
                                        "Name": name_rib,
                                        "Ref": name_ref,
                                    }
                                    hstiffs.append(hstiff)

                    elif cell_value == "ATM":
                        pitchlong = [Ws.iat[i_1, 4], Ws.iat[i_1, 5]]
                        pitchtran = [Ws.iat[i_1 + 1, 4], Ws.iat[i_1 + 1, 5]]
                        pitch = [pitchlong, pitchtran]
                        atms.append(pitch)
                        for i_2 in range(i_1 + 2, re):
                            if not pd.isnull(Ws.iat[i_2, 1]):
                                break
                            else:
                                if not pd.isnull(Ws.iat[i_2, 2]):
                                    angle = [Ws.iat[i_2, 4], Ws.iat[i_2, 5]]
                                    face = Ws.iat[i_2 + 1, 4]
                                    name_pie = Ws.iat[i_2 + 2, 4]
                                    name_ref = Ws.iat[i_2 + 3, 4]
                                    atm = {"Angle": angle, "Face": face, "Name": name_pie, "Ref": name_ref}
                                    atms.append(atm)

                    elif cell_value == "CUTOUT":
                        pitchlong = [Ws.iat[i_1, 4], Ws.iat[i_1, 5]]
                        pitchtran = [Ws.iat[i_1 + 1, 4], Ws.iat[i_1 + 1, 5]]
                        pitch = [pitchlong, pitchtran]
                        cutouts.append(pitch)
                        for i_2 in range(i_1 + 2, re):
                            if not pd.isnull(Ws.iat[i_2, 1]):
                                break
                            else:
                                if not pd.isnull(Ws.iat[i_2, 2]):
                                    face = Ws.iat[i_2, 4]
                                    name_ref = Ws.iat[i_2 + 1, 4]
                                    cutout = {"Face": face, "Ref": name_ref}
                                    cutouts.append(cutout)

                    elif cell_value == "STUD":
                        pitchlong = [Ws.iat[i_1, 4], Ws.iat[i_1, 5]]
                        pitchtran = [Ws.iat[i_1 + 1, 4], Ws.iat[i_1 + 1, 5]]
                        pitch = [pitchlong, pitchtran]
                        studs.append(pitch)
                        for i_2 in range(i_1 + 2, re):
                            if not pd.isnull(Ws.iat[i_2, 1]):
                                break
                            else:
                                if not pd.isnull(Ws.iat[i_2, 2]):
                                    face = Ws.iat[i_2, 4]
                                    name_ref = Ws.iat[i_2 + 1, 4]
                                    stud = {"Face": face, "Ref": name_ref}
                                    studs.append(stud)

                    elif cell_value == "BREAK":
                        length = []
                        extend = []
                        thick = []
                        if not pd.isnull(Ws.iat[i_1, 3]):
                            max_cols = ColMax(Ws, i_1)
                            length.extend(
                                Ws.iat[i_1, col] for col in range(3, max_cols) if not pd.isnull(Ws.iat[i_1, col])
                            )
                        if not pd.isnull(Ws.iat[i_1 + 1, 3]):
                            max_cols = ColMax(Ws, i_1 + 1)
                            extend.extend(
                                Ws.iat[i_1 + 1, col]
                                for col in range(3, max_cols)
                                if not pd.isnull(Ws.iat[i_1 + 1, col])
                            )
                        if not pd.isnull(Ws.iat[i_1 + 2, 3]):
                            max_cols = ColMax(Ws, i_1 + 2)
                            thick.extend(
                                Ws.iat[i_1 + 2, col]
                                for col in range(3, max_cols)
                                if not pd.isnull(Ws.iat[i_1 + 2, col])
                            )

                        break_panel = {"Lenght": length, "Extend": extend, "Thick": thick}

            name_panels = Ws.iat[i, 0]
            data = {
                "Name": name_panels,
                "Jbut": jbut_panels,
                "Break": break_panel,
                "Corner": corners,
                "Lrib": lribs,
                "Vstiff": vstiffs,
                "Hstiff": hstiffs,
                "Atm": atms,
                "Cutout": cutouts,
                "Atm": atms,
                "Stud": studs,
            }
            MainPanel_Mark.append(data)

    return MainPanel_Mark


# -------------Sub Panel---------------------------------------------
def Load_Sheet_SubPanel_Line(Ws):
    Row_Max = RowMax(Ws, 1)
    SubPanel_Line_data = []
    for i in range(1, Row_Max):
        if not pd.isnull(Ws.iat[i, 0]):
            rs = i
            re = -1
            if i != Row_Max:
                for i_1 in range(i + 1, Row_Max + 1):
                    if not pd.isnull(Ws.iat[i_1, 0]):
                        re = i_1
                        break
            if re == -1:
                re = Ws.shape[0]

            max_cols = ColMax(Ws, i)
            for i_1 in range(2, max_cols):
                name_subpanel = Ws.iat[i + 1, i_1]
                girder_subpanel = Ws.iat[i, 0]
                sec_subpanel = Ws.iat[i, i_1]
                points = []
                for i_2 in range(rs + 2, re):
                    if not pd.isnull(Ws.iat[i_2, 2]):
                        max_cols_point = ColMax(Ws, i_2)
                        point = []
                        point.extend(
                            str(int(val)) if isinstance(val, float) and val.is_integer() else str(val)
                            for col in range(2, max_cols_point)
                            if not pd.isnull(Ws.iat[i_2, col])
                            for val in [Ws.iat[i_2, col]]
                        )
                        points.append(point)

                data = {"Name": name_subpanel, "Girder": girder_subpanel, "Sec": sec_subpanel, "Point": points}
                SubPanel_Line_data.append(data)

    return SubPanel_Line_data


def Load_Sheet_SubPanel_Rec(Ws):
    SubPanel_Rec_data = []
    Row_Max = RowMax(Ws, 1)
    for i in range(1, Row_Max):
        if not pd.isnull(Ws.iat[i, 0]):
            rs = i
            re = -1
            if i != Row_Max:
                for i_1 in range(i + 1, Row_Max + 1):
                    if not pd.isnull(Ws.iat[i_1, 0]):
                        re = i_1
                        break
            if re == -1:
                re = Ws.shape[0]

            max_cols = ColMax(Ws, i)
            for i_1 in range(0, max_cols):
                if i_1 != 1:
                    name_subpanel = Ws.iat[i, i_1]
                    part_subpanel = []
                    for i_2 in range(rs + 1, re):
                        if not pd.isnull(Ws.iat[i_2, 1]):
                            name_part = Ws.iat[i_2, 1]
                            mat_part = {
                                "Thick1": Ws.iat[i_2, 3],
                                "Thick2": Ws.iat[i_2, 4],
                                "Mat": Ws.iat[i_2, 5],
                            }
                            outL = []
                            n = i_2 + 1
                            max_cols_out = ColMax(Ws, n)
                            outL.extend(
                                str(int(val)) if isinstance(val, float) and val.is_integer() else str(val)
                                for col in range(4, max_cols_out)
                                if not pd.isnull(Ws.iat[n, col])
                                for val in [Ws.iat[n, col]]
                            )
                            outR = []
                            n += 1
                            max_cols_out = ColMax(Ws, n)
                            outR.extend(
                                str(int(val)) if isinstance(val, float) and val.is_integer() else str(val)
                                for col in range(4, max_cols_out)
                                if not pd.isnull(Ws.iat[n, col])
                                for val in [Ws.iat[n, col]]
                            )
                            outT = []
                            n += 1
                            max_cols_out = ColMax(Ws, n)
                            outT.extend(
                                str(int(val)) if isinstance(val, float) and val.is_integer() else str(val)
                                for col in range(4, max_cols_out)
                                if not pd.isnull(Ws.iat[n, col])
                                for val in [Ws.iat[n, col]]
                            )
                            outB = []
                            n += 1
                            max_cols_out = ColMax(Ws, n)
                            outB.extend(
                                str(int(val)) if isinstance(val, float) and val.is_integer() else str(val)
                                for col in range(4, max_cols_out)
                                if not pd.isnull(Ws.iat[n, col])
                                for val in [Ws.iat[n, col]]
                            )
                            outs_part = {"L": outL, "R": outR, "T": outT, "B": outB}

                            extend_part = {
                                "L": Ws.iat[i_2 + 5, 4],
                                "R": Ws.iat[i_2 + 6, 4],
                                "T": Ws.iat[i_2 + 7, 4],
                                "B": Ws.iat[i_2 + 8, 4],
                            }

                            data_part = {
                                "Name": name_part,
                                "Material": mat_part,
                                "Out": outs_part,
                                "Extend": extend_part,
                            }

                            part_subpanel.append(data_part)

                    data = {"Name": name_subpanel, "Part": part_subpanel}
                    SubPanel_Rec_data.append(data)

    return SubPanel_Rec_data


def Load_Sheet_SubPanel_Mark(Ws):
    SubPanel_Mark_data = []
    Row_Max = RowMax(Ws, 1)
    for i in range(1, Row_Max):
        if not pd.isnull(Ws.iat[i, 0]):
            rs = i
            re = -1
            if i != Row_Max:
                for i_1 in range(i + 1, Row_Max + 1):
                    if not pd.isnull(Ws.iat[i_1, 0]):
                        re = i_1
                        break
            if re == -1:
                re = Ws.shape[0]

            max_cols = ColMax(Ws, i)
            for i_1 in range(0, max_cols):
                if i_1 != 1:
                    name_subpanel = Ws.iat[i, i_1]
                    mark_part = []
                    for i_2 in range(rs + 1, re):
                        if not pd.isnull(Ws.iat[i_2, 1]):
                            name_part = Ws.iat[i_2, 1]
                            corner_part = []
                            slot_part = []
                            joint_part = {}
                            cutout_part = []
                            stiff_part = []
                            flg_part = {}
                            re_part = -1
                            for i_3 in range(i_2 + 1, re):
                                if not pd.isnull(Ws.iat[i_3, 1]):
                                    re_part = i_3
                                    break
                            if re_part == -1:
                                re_part = re
                            for i_3 in range(i_2, re_part):
                                cell_value = Ws.iat[i_3, 2]
                                if cell_value == "CORNER":
                                    corner1 = "N"
                                    corner2 = "N"
                                    corner3 = "N"
                                    corner4 = "N"
                                    if not pd.isnull(Ws.iat[i_3, 3]):
                                        corner1 = Ws.iat[i_3, 3]
                                    if not pd.isnull(Ws.iat[i_3, 4]):
                                        corner2 = Ws.iat[i_3, 4]
                                    if not pd.isnull(Ws.iat[i_3, 5]):
                                        corner3 = Ws.iat[i_3, 5]
                                    if not pd.isnull(Ws.iat[i_3, 6]):
                                        corner4 = Ws.iat[i_3, 6]
                                    corner_part = [corner1, corner2, corner3, corner4]

                                elif cell_value == "SLOT":
                                    slot1 = "N"
                                    slot2 = "N"
                                    slot3 = "N"
                                    slot4 = "N"
                                    if not pd.isnull(Ws.iat[i_3, 4]):
                                        slot1 = Ws.iat[i_3, 4]
                                    if not pd.isnull(Ws.iat[i_3 + 1, 4]):
                                        slot2 = Ws.iat[i_3 + 1, 4]
                                    if not pd.isnull(Ws.iat[i_3 + 2, 4]):
                                        slot3 = Ws.iat[i_3 + 2, 4]
                                    if not pd.isnull(Ws.iat[i_3 + 3, 4]):
                                        slot4 = Ws.iat[i_3 + 3, 4]
                                    slot_part = [slot1, slot2, slot3, slot4]

                                elif cell_value == "JOINT":
                                    jbut_s = []
                                    jbut_e = []
                                    if not pd.isnull(Ws.iat[i_3, 4]):
                                        max_cols = ColMax(Ws, i_3)
                                        jbut_s.extend(
                                            Ws.iat[i_3, col]
                                            for col in range(4, max_cols)
                                            if not pd.isnull(Ws.iat[i_3, col])
                                        )

                                    if not pd.isnull(Ws.iat[i_3 + 1, 4]):
                                        max_cols = ColMax(Ws, i_3 + 1)
                                        jbut_e.extend(
                                            Ws.iat[i_3 + 1, col]
                                            for col in range(4, max_cols)
                                            if not pd.isnull(Ws.iat[i_3 + 1, col])
                                        )

                                    joint_part = {"S": jbut_s, "E": jbut_e}
                                elif cell_value == "CUTOUT":
                                    cutout_part = [Ws.iat[i_3, 3], Ws.iat[i_3, 4], Ws.iat[i_3, 5], Ws.iat[i_3, 6]]
                                elif cell_value == "STIFF":
                                    n = i_3
                                    while n <= re_part and not pd.isnull(Ws.iat[n, 3]):
                                        stiff = {
                                            "Point": Ws.iat[n, 3],
                                            "Side": Ws.iat[n, 4],
                                            "Name": Ws.iat[n, 5],
                                            "Ref": Ws.iat[n, 6],
                                        }
                                        stiff_part.append(stiff)
                                        n += 1
                                elif cell_value == "FLG":
                                    uflg_part = []
                                    lflg_part = []
                                    if not pd.isnull(Ws.iat[i_3, 4]):
                                        max_cols = ColMax(Ws, i_3)
                                        uflg_part.extend(
                                            Ws.iat[i_3, col]
                                            for col in range(4, max_cols)
                                            if not pd.isnull(Ws.iat[i_3, col])
                                        )
                                    if not pd.isnull(Ws.iat[i_3 + 1, 4]):
                                        max_cols = ColMax(Ws, i_3 + 1)
                                        lflg_part.extend(
                                            Ws.iat[i_3 + 1, col]
                                            for col in range(4, max_cols)
                                            if not pd.isnull(Ws.iat[i_3 + 1, col])
                                        )
                                    flg_part = {"UFLG": uflg_part, "LFLG": lflg_part}

                            data_part = {
                                "Name": name_part,
                                "Corner": corner_part,
                                "Slot": slot_part,
                                "Joint": joint_part,
                                "Cutout": cutout_part,
                                "Stiff": stiff_part,
                                "FLG": flg_part,
                            }

                            mark_part.append(data_part)

                    data = {"Name": name_subpanel, "MarkPart": mark_part}
                    SubPanel_Mark_data.append(data)

    return SubPanel_Mark_data


# -----------------Data_Taikeikou------------------------------------
def Load_Sheet_Taikeikou(Ws):
    Row_Max = RowMax(Ws, 1)

    Taikeikou_data = []
    for i in range(1, Row_Max):
        if not pd.isnull(Ws.iat[i, 0]):
            rs = i
            re = -1
            if i != Row_Max:
                for i_1 in range(i + 1, Row_Max + 1):
                    if not pd.isnull(Ws.iat[i_1, 0]):
                        re = i_1
                        break
            if re == -1:
                re = Ws.shape[0]

            max_cols = ColMax(Ws, i)
            for i_1 in range(0, max_cols):
                if i_1 != 1:
                    name_taikeikou = Ws.iat[i, i_1]
                    type_taikeikou = ""
                    girder_taikeikou = []
                    point_taikeikou = []
                    distmod_taikeikou = {}
                    hole_taikeikou = {}
                    vstiff_taikeikou = {}
                    shape_taikeikou = {}
                    guss_taikeikou = {}
                    for i_2 in range(rs + 1, re):
                        cell_value = Ws.iat[i_2, 1]
                        if cell_value == "TYPE":
                            type_taikeikou = [Ws.iat[i_2, 2], Ws.iat[i_2, 3], Ws.iat[i_2, 4]]
                        elif cell_value == "GIRDER":
                            girder_taikeikou = [Ws.iat[i_2, 2], Ws.iat[i_2, 3]]
                        elif cell_value == "POINT":
                            point_taikeikou = [Ws.iat[i_2, 2], Ws.iat[i_2, 3], Ws.iat[i_2, 4], Ws.iat[i_2, 5]]
                        elif cell_value == "DISTMOD":
                            tl = [Ws.iat[i_2, 3], Ws.iat[i_2, 4]]
                            tr = [Ws.iat[i_2 + 1, 3], Ws.iat[i_2 + 1, 4]]
                            bl = [Ws.iat[i_2 + 2, 3], Ws.iat[i_2 + 2, 4]]
                            br = [Ws.iat[i_2 + 3, 3], Ws.iat[i_2 + 3, 4]]
                            distmod_taikeikou = {"TL": tl, "TR": tr, "BL": bl, "BR": br}
                        elif cell_value == "HOLE":
                            tl = [Ws.iat[i_2, 3], Ws.iat[i_2, 4], Ws.iat[i_2, 5]]
                            tr = [Ws.iat[i_2 + 1, 3], Ws.iat[i_2 + 1, 4], Ws.iat[i_2 + 1, 5]]
                            bl = [Ws.iat[i_2 + 2, 3], Ws.iat[i_2 + 2, 4], Ws.iat[i_2 + 2, 5]]
                            br = [Ws.iat[i_2 + 3, 3], Ws.iat[i_2 + 3, 4], Ws.iat[i_2 + 3, 5]]
                            hole_taikeikou = {"TL": tl, "TR": tr, "BL": bl, "BR": br}
                        elif cell_value == "VSTIFF":
                            vl = [Ws.iat[i_2, 3], Ws.iat[i_2, 4], Ws.iat[i_2, 5]]
                            vr = [Ws.iat[i_2 + 1, 3], Ws.iat[i_2 + 1, 4], Ws.iat[i_2 + 1, 5]]
                            vstiff_taikeikou = {"L": vl, "R": vr}
                        elif cell_value == "SHAPE":
                            top = [
                                Ws.iat[i_2, 3],
                                Ws.iat[i_2, 4],
                                Ws.iat[i_2, 5],
                                Ws.iat[i_2, 6],
                                Ws.iat[i_2, 7],
                                Ws.iat[i_2, 8],
                            ]
                            bot = [
                                Ws.iat[i_2 + 1, 3],
                                Ws.iat[i_2 + 1, 4],
                                Ws.iat[i_2 + 1, 5],
                                Ws.iat[i_2 + 1, 6],
                                Ws.iat[i_2 + 1, 7],
                                Ws.iat[i_2 + 1, 8],
                            ]
                            left = [
                                Ws.iat[i_2 + 2, 3],
                                Ws.iat[i_2 + 2, 4],
                                Ws.iat[i_2 + 2, 5],
                                Ws.iat[i_2 + 2, 6],
                                Ws.iat[i_2 + 2, 7],
                                Ws.iat[i_2 + 2, 8],
                            ]
                            right = [
                                Ws.iat[i_2 + 3, 3],
                                Ws.iat[i_2 + 3, 4],
                                Ws.iat[i_2 + 3, 5],
                                Ws.iat[i_2 + 3, 6],
                                Ws.iat[i_2 + 3, 7],
                                Ws.iat[i_2 + 3, 8],
                            ]
                            shape_taikeikou = {"T": top, "B": bot, "L": left, "R": right}
                        elif cell_value == "GUSS":
                            tl = [Ws.iat[i_2, 3], Ws.iat[i_2, 4], Ws.iat[i_2, 5], Ws.iat[i_2, 6], Ws.iat[i_2, 7]]
                            tr = [
                                Ws.iat[i_2 + 1, 3],
                                Ws.iat[i_2 + 1, 4],
                                Ws.iat[i_2 + 1, 5],
                                Ws.iat[i_2 + 1, 6],
                                Ws.iat[i_2 + 1, 7],
                            ]
                            bl = [
                                Ws.iat[i_2 + 2, 3],
                                Ws.iat[i_2 + 2, 4],
                                Ws.iat[i_2 + 2, 5],
                                Ws.iat[i_2 + 2, 6],
                                Ws.iat[i_2 + 2, 7],
                            ]
                            br = [
                                Ws.iat[i_2 + 3, 3],
                                Ws.iat[i_2 + 3, 4],
                                Ws.iat[i_2 + 3, 5],
                                Ws.iat[i_2 + 3, 6],
                                Ws.iat[i_2 + 3, 7],
                            ]
                            mid = [
                                Ws.iat[i_2 + 4, 3],
                                Ws.iat[i_2 + 4, 4],
                                Ws.iat[i_2 + 4, 5],
                                Ws.iat[i_2 + 4, 6],
                                Ws.iat[i_2 + 4, 7],
                                Ws.iat[i_2 + 4, 8],
                            ]
                            guss_taikeikou = {"TL": tl, "TR": tr, "BL": bl, "BR": br, "Mid": mid}

                    data = {
                        "Name": name_taikeikou,
                        "Type": type_taikeikou,
                        "Girder": girder_taikeikou,
                        "Point": point_taikeikou,
                        "Distmod": distmod_taikeikou,
                        "Hole": hole_taikeikou,
                        "Vstiff": vstiff_taikeikou,
                        "Shape": shape_taikeikou,
                        "Guss": guss_taikeikou,
                    }
                    Taikeikou_data.append(data)

    return Taikeikou_data


# -----------------Data_Yokokou------------------------------------
def Load_Sheet_Yokokou(Ws):
    Row_Max = Ws.shape[0]
    Yokokou_data = []
    for i in range(0, Row_Max):
        if not pd.isnull(Ws.iat[i, 0]):
            rs, re = Calculate_RowStart_RowEnd(Ws, Row_Max, i, 0)
            name_yk = Ws.iat[i, 0]
            type_yk = []
            girder_yk = []
            point_yk = []
            shape_yk = []
            guss_yk = []
            for i_1 in range(rs, re):
                cell_value = Ws.iat[i_1, 1]
                if cell_value == "TYPE":
                    type_yk = [Ws.iat[i_1, 2], Ws.iat[i_1, 3]]
                elif cell_value == "GIRDER":
                    girder_yk = [Ws.iat[i_1, 2], Ws.iat[i_1, 3]]
                elif cell_value == "POINT":
                    max_cols = ColMax(Ws, i_1)
                    point = []
                    for i_2 in range(2, max_cols):
                        point.append(Ws.iat[i_1, i_2])
                        point.append(Ws.iat[i_1 + 1, i_2])
                        point.append(Ws.iat[i_1 + 2, i_2])
                    point_yk = point
                elif cell_value == "SHAPE":
                    rs_shape, re_shape = Calculate_RowStart_RowEnd(Ws, re, i_1, 1)
                    for i_2 in range(rs_shape, re_shape):
                        if not pd.isnull(Ws.iat[i_2, 2]):
                            name_shape = Ws.iat[i_2, 2]
                            infor_shape = []
                            point_shape = []
                            pitch_shape = []
                            hole_shape = []
                            rs_each_shape, re_each_shape = Calculate_RowStart_RowEnd(Ws, re_shape, i_2, 2)
                            for i_3 in range(rs_each_shape, re_each_shape):
                                if Ws.iat[i_3, 3] == "INFOR":
                                    infor_shape = [Ws.iat[i_3, 4], Ws.iat[i_3, 5], Ws.iat[i_3, 6]]
                                elif Ws.iat[i_3, 3] == "POINT":
                                    point_shape = [Ws.iat[i_3, 4], Ws.iat[i_3, 5], Ws.iat[i_3, 6]]
                                elif Ws.iat[i_3, 3] == "PITCH":
                                    pitch_shape = [Ws.iat[i_3, 4], Ws.iat[i_3, 5], Ws.iat[i_3, 6]]
                                elif Ws.iat[i_3, 3] == "HOLE":
                                    rs_hole_each_shape, re_hole_each_shape = Calculate_RowStart_RowEnd(
                                        Ws, re_each_shape, i_3, 3
                                    )
                                    hole_start_each_shape = []
                                    hole_end_each_shape = []
                                    for i_4 in range(rs_hole_each_shape, re_hole_each_shape):
                                        if Ws.iat[i_4, 4] == "S":
                                            hole_start_each_shape = [Ws.iat[i_4, 5], Ws.iat[i_4, 6], Ws.iat[i_4, 7]]
                                        elif Ws.iat[i_4, 4] == "E":
                                            hole_end_each_shape = [Ws.iat[i_4, 5], Ws.iat[i_4, 6], Ws.iat[i_4, 7]]
                                    hole_shape = {"S": hole_start_each_shape, "E": hole_end_each_shape}

                            shapes = {
                                "Name": name_shape,
                                "Infor": infor_shape,
                                "Point": point_shape,
                                "Pitch": pitch_shape,
                                "Hole": hole_shape,
                            }
                            shape_yk.append(shapes)

                elif cell_value == "GUSS":
                    rs_guss, re_guss = Calculate_RowStart_RowEnd(Ws, re, i_1, 1)
                    for i_2 in range(rs_guss, re_guss):
                        if not pd.isnull(Ws.iat[i_2, 2]):
                            name_guss = Ws.iat[i_2, 2]
                            infor_guss = []
                            point_guss = []
                            face_guss = []
                            edge_guss = []
                            kl_guss = []
                            rs_each_guss, re_each_guss = Calculate_RowStart_RowEnd(Ws, re_guss, i_2, 2)
                            for i_3 in range(rs_each_guss, re_each_guss):
                                if Ws.iat[i_3, 3] == "INFOR":
                                    infor_guss = [Ws.iat[i_3, 4], Ws.iat[i_3, 5]]
                                elif Ws.iat[i_3, 3] == "POINT":
                                    point_guss = Ws.iat[i_3, 4]
                                elif Ws.iat[i_3, 3] == "FACE":
                                    max_cols = ColMax(Ws, i_3)
                                    face_eachguss = []
                                    for i_4 in range(4, max_cols):
                                        if not pd.isnull(Ws.iat[i_3, i_4]):
                                            face_eachguss.append(Ws.iat[i_3, i_4])
                                    face_guss = face_eachguss
                                elif Ws.iat[i_3, 3] == "EDGE":
                                    edge_guss = [Ws.iat[i_3, 4], Ws.iat[i_3, 5]]
                                elif Ws.iat[i_3, 3] == "KL":
                                    if not pd.isnull(Ws.iat[i_3, 4]):
                                        kl_guss = [Ws.iat[i_3, 4], Ws.iat[i_3, 5], Ws.iat[i_3, 6]]
                                elif Ws.iat[i_3, 3] == "SLOT":
                                    if not pd.isnull(Ws.iat[i_3, 4]):
                                        slot = Ws.iat[i_3, 4]
                                    else:
                                        slot = "N"

                            guss = {
                                "Name": name_guss,
                                "Infor": infor_guss,
                                "Point": point_guss,
                                "Face": face_guss,
                                "Edge": edge_guss,
                                "KL": kl_guss,
                                "Slot": slot,
                            }
                            guss_yk.append(guss)

            data = {
                "Name": name_yk,
                "Type": type_yk,
                "Girder": girder_yk,
                "Point": point_yk,
                "Shape": shape_yk,
                "Guss": guss_yk,
            }
            Yokokou_data.append(data)

    return Yokokou_data


def Calculate_RowStart_RowEnd(Ws, RowMax, row, col):
    rs = row
    re = -1
    for i in range(row + 1, RowMax):
        if not pd.isnull(Ws.iat[i, col]):
            re = i
            break
        if re == -1:
            re = RowMax
    return rs, re


# ----------------Data_Shouban--------------------------------------
def Load_Sheet_Shouban(Ws):
    Row_Max = Ws.shape[0]
    Shouban_data = []
    for i in range(0, Row_Max):
        if not pd.isnull(Ws.iat[i, 0]):
            rs, re = Calculate_RowStart_RowEnd(Ws, Row_Max, i, 0)
            name_sb = Ws.iat[i, 0]
            line_sb = []
            sec_sb = []
            for i_1 in range(rs, re):
                cell_value = Ws.iat[i_1, 1]
                if cell_value == "Line":
                    max_cols = ColMax(Ws, i_1)
                    for i_2 in range(2, max_cols):
                        line_sb.append(Ws.iat[i_1, i_2])
                elif cell_value == "Sec":
                    sec_sb = [Ws.iat[i_1, 2], Ws.iat[i_1, 3]]

            data = {"Name": name_sb, "Line": line_sb, "Sec": sec_sb}
            Shouban_data.append(data)

    return Shouban_data


# -----------------Data_Member_SPL------------------------------------
def Load_Sheet_Member_SPL(Ws):
    Member_SPL_data = []
    Row_Max = Ws.shape[0]
    for i in range(0, Row_Max):
        if not pd.isnull(Ws.iat[i, 0]):
            rs, re = Calculate_RowStart_RowEnd(Ws, Row_Max, i, 0)
            name_spl = Ws.iat[i, 0]
            infor = {}
            pitchj = []
            pitchl = []
            pitchr = []
            out = []
            dhole = []
            solid = []
            for i_1 in range(rs, re):
                cell_value = Ws.iat[i_1, 1]
                n = i_1
                if cell_value == "INFOR":
                    infor = {
                        "Thick": Ws.iat[n, 2],
                        "Mat": Ws.iat[n, 3],
                        "Side": Ws.iat[n, 4],
                        "Ang": Ws.iat[n, 5],
                        "GLine": Ws.iat[n, 6],
                    }
                elif cell_value == "PJ":
                    max_cols = ColMax(Ws, n)
                    pitchj.extend(Ws.iat[n, col] for col in range(2, max_cols) if not pd.isnull(Ws.iat[n, col]))
                elif cell_value == "PL":
                    max_cols = ColMax(Ws, n)
                    pitchl.extend(Ws.iat[n, col] for col in range(2, max_cols) if not pd.isnull(Ws.iat[n, col]))
                elif cell_value == "PR":
                    max_cols = ColMax(Ws, n)
                    pitchr.extend(Ws.iat[n, col] for col in range(2, max_cols) if not pd.isnull(Ws.iat[n, col]))
                elif cell_value == "OUT":
                    out = [Ws.iat[n, 2], Ws.iat[n, 3], Ws.iat[n, 4], Ws.iat[n, 5]]
                elif cell_value == "DHOLE":
                    dhole = [Ws.iat[n, 2], Ws.iat[n, 3]]
                elif cell_value == "SOLID":
                    solid = [Ws.iat[n, 2], Ws.iat[n, 3]]
            data = {
                "Name": name_spl,
                "Infor": infor,
                "PJ": pitchj,
                "PL": pitchl,
                "PR": pitchr,
                "Out": out,
                "Dhole": dhole,
                "Solid": solid,
            }
            Member_SPL_data.append(data)

    return Member_SPL_data


# -----------------Data_Member_Rib------------------------------------
def Load_Sheet_Member_Rib(Ws):
    Member_Rib_data = []
    Row_Max = RowMax(Ws, 1)
    for i in range(1, Row_Max):
        if not pd.isnull(Ws.iat[i, 0]):
            rs = i
            re = -1
            if i != Row_Max:
                for i_1 in range(i + 1, Row_Max + 1):
                    if not pd.isnull(Ws.iat[i_1, 0]):
                        re = i_1
                        break
            if re == -1:
                re = Ws.shape[0]

            name_ribs = Ws.iat[i, 0]
            infor = {}
            ang = []
            extend = []
            corner = []
            joints = []
            jointe = []
            for i_1 in range(rs, re):
                cell_value = Ws.iat[i_1, 1]
                if cell_value == "INFOR":
                    infor = {
                        "Thick1": Ws.iat[i_1, 2],
                        "Thick2": Ws.iat[i_1, 3],
                        "Mat": Ws.iat[i_1, 4],
                        "Width": Ws.iat[i_1, 5],
                    }
                elif cell_value == "ANG":
                    ang = [Ws.iat[i_1, 2], Ws.iat[i_1, 3], Ws.iat[i_1, 4]]
                elif cell_value == "EXTEND":
                    extend1 = "N"
                    extend2 = "N"
                    extend3 = "N"
                    extend4 = "N"
                    if not pd.isnull(Ws.iat[i_1, 2]):
                        extend1 = Ws.iat[i_1, 2]
                    if not pd.isnull(Ws.iat[i_1, 3]):
                        extend2 = Ws.iat[i_1, 3]
                    if not pd.isnull(Ws.iat[i_1, 4]):
                        extend3 = Ws.iat[i_1, 4]
                    if not pd.isnull(Ws.iat[i_1, 5]):
                        extend4 = Ws.iat[i_1, 5]
                    extend = [extend1, extend2, extend3, extend4]
                elif cell_value == "CORNER":
                    corner1 = "N"
                    corner2 = "N"
                    corner3 = "N"
                    corner4 = "N"
                    if not pd.isnull(Ws.iat[i_1, 2]):
                        corner1 = Ws.iat[i_1, 2]
                    if not pd.isnull(Ws.iat[i_1, 3]):
                        corner2 = Ws.iat[i_1, 3]
                    if not pd.isnull(Ws.iat[i_1, 4]):
                        corner3 = Ws.iat[i_1, 4]
                    if not pd.isnull(Ws.iat[i_1, 5]):
                        corner4 = Ws.iat[i_1, 5]
                    corner = [corner1, corner2, corner3, corner4]
                elif cell_value == "JOINTS":
                    if not pd.isnull(Ws.iat[i_1, 3]):
                        max_cols = ColMax(Ws, i_1)
                        joints.extend(Ws.iat[i_1, col] for col in range(2, max_cols) if not pd.isnull(Ws.iat[i_1, col]))
                elif cell_value == "JOINTE":
                    if not pd.isnull(Ws.iat[i_1, 3]):
                        max_cols = ColMax(Ws, i_1)
                        jointe.extend(Ws.iat[i_1, col] for col in range(2, max_cols) if not pd.isnull(Ws.iat[i_1, col]))
                else:
                    break

            data = {
                "Name": name_ribs,
                "Infor": infor,
                "Ang": ang,
                "Extend": extend,
                "Corner": corner,
                "JointS": joints,
                "JointE": jointe,
            }
            Member_Rib_data.append(data)

    return Member_Rib_data


# -----------------Data_Member_Data------------------------------------


def Load_Sheet_Member_Data(Ws):
    Member_Data_data = []
    Row_Max = RowMax(Ws, 1)
    for i in range(1, Row_Max):
        if not pd.isnull(Ws.iat[i, 0]):
            cell_value = Ws.iat[i, 2]
            if cell_value == "SLOT":
                data = Load_Infor_Slot(Ws, Ws.iat[i, 0])
                Member_Data_data.append(data)
            elif cell_value == "HOLE":
                data = Load_Infor_Hole(Ws, Ws.iat[i, 0])
                Member_Data_data.append(data)
            elif cell_value == "ASHIBA" or cell_value == "TAICAU":
                data = Load_Infor_ATM(Ws, Ws.iat[i, 0])
                Member_Data_data.append(data)
            elif cell_value == "STUD":
                data = Load_Infor_Stud(Ws, Ws.iat[i, 0])
                Member_Data_data.append(data)

    return Member_Data_data


def Load_Infor_Slot(Ws, Name_Slot):
    data = {}
    Row_Max = RowMax(Ws, 0)
    for i in range(0, Row_Max + 1):
        if not pd.isnull(Ws.iat[i, 1]):
            if Ws.iat[i, 0] == Name_Slot:
                n = i
                Row_Max1 = RowMax(Ws, 1)
                while n <= Row_Max1:
                    cell_value = Ws.iat[n, 1]
                    if cell_value == "INFOR":
                        infor = [Ws.iat[n, 3]]
                    elif cell_value == "WIDE":
                        wides = [Ws.iat[n, 2], Ws.iat[n, 3]]
                    elif cell_value == "RADIUS":
                        radius = [Ws.iat[n, 2]]
                    elif cell_value == "END":
                        break
                    n += 1

                data = {"Name": Name_Slot, "Infor": infor, "Wide": wides, "Radius": radius}
                break

    return data


def Load_Infor_Hole(Ws, Name_Hole):
    data = {}
    Row_Max = RowMax(Ws, 0)
    for i in range(0, Row_Max + 1):
        if not pd.isnull(Ws.iat[i, 1]):
            if Ws.iat[i, 0] == Name_Hole:
                infor = []
                lengths = []
                widths = []
                radius = []
                stiffs = []
                n = i
                Row_Max1 = RowMax(Ws, 1)
                while n <= Row_Max1:
                    cell_value = Ws.iat[n, 1]
                    if cell_value == "INFOR":
                        infor = [Ws.iat[n, 3]]
                    elif cell_value == "LENGTH":
                        lengths = [Ws.iat[n, 2], Ws.iat[n, 3]]
                    elif cell_value == "WIDTH":
                        widths = [Ws.iat[n, 2], Ws.iat[n, 3]]
                    elif cell_value == "RADIUS":
                        radius = [Ws.iat[n, 2], Ws.iat[n, 3], Ws.iat[n, 4], Ws.iat[n, 5]]
                    elif cell_value == "STIFF":
                        distmods = [Ws.iat[n, 2], Ws.iat[n, 3], Ws.iat[n, 4], Ws.iat[n, 5]]
                        n += 1
                        namestiffs = [Ws.iat[n, 2], Ws.iat[n, 3], Ws.iat[n, 4], Ws.iat[n, 5]]
                        stiffs = [distmods, namestiffs]
                    elif cell_value == "END":
                        break
                    n += 1

                data = {
                    "Name": Name_Hole,
                    "Infor": infor,
                    "Length": lengths,
                    "Width": widths,
                    "Radius": radius,
                    "Stiff": stiffs,
                }
                break

    return data


def Load_Infor_ATM(Ws, Name_ATM):
    data = {}
    Row_Max = RowMax(Ws, 0)
    for i in range(0, Row_Max + 1):
        if not pd.isnull(Ws.iat[i, 1]):
            if Ws.iat[i, 0] == Name_ATM:
                infor = []
                points = []
                out = []
                holes = []
                n = i
                Row_Max1 = RowMax(Ws, 1)
                while n <= Row_Max1:
                    cell_value = Ws.iat[n, 1]
                    if cell_value == "INFOR":
                        infor = [Ws.iat[n, 2], Ws.iat[n, 3], Ws.iat[n, 4], Ws.iat[n, 5]]
                    elif cell_value == "POINT":
                        Row_Max2 = RowMax(Ws, 2)
                        m = n
                        while m <= Row_Max2:
                            cell_value1 = Ws.iat[m, 2]
                            if cell_value1 == "END":
                                break
                            else:
                                p = [Ws.iat[m, 2], Ws.iat[m, 3], Ws.iat[m, 4], Ws.iat[m, 5]]
                                points.append(p)
                            m += 1
                    elif cell_value == "OUT":
                        Row_Max2 = RowMax(Ws, 2)
                        m = n
                        while m <= Row_Max2:
                            cell_value1 = Ws.iat[m, 2]
                            array = []
                            if cell_value1 == "END":
                                break
                            else:
                                max_cols = ColMax(Ws, m)
                                array.extend(
                                    str(int(val)) if isinstance(val, float) and val.is_integer() else str(val)
                                    for col in range(2, max_cols)
                                    if not pd.isnull(Ws.iat[m, col])
                                    for val in [Ws.iat[m, col]]
                                )
                            m += 1
                            out.append(array)
                    elif cell_value == "HOLE":
                        Row_Max2 = RowMax(Ws, 2)
                        m = n
                        while m <= Row_Max2:
                            cell_value1 = Ws.iat[m, 2]
                            if cell_value1 == "END":
                                break
                            else:
                                hole = [Ws.iat[m, 2], Ws.iat[m, 3], Ws.iat[m, 4]]
                                holes.append(hole)
                            m += 1
                    elif cell_value == "END":
                        break
                    n += 1

                data = {"Name": Name_ATM, "Infor": infor, "Point": points, "Out": out, "Hole": holes}
                break

    return data


def Load_Infor_Stud(Ws, Name_Stud):
    data = {}
    Row_Max = RowMax(Ws, 0)
    for i in range(0, Row_Max + 1):
        if not pd.isnull(Ws.iat[i, 1]):
            if Ws.iat[i, 0] == Name_Stud:
                infor = []
                nut = []
                n = i
                Row_Max1 = RowMax(Ws, 1)
                while n <= Row_Max1:
                    cell_value = Ws.iat[n, 1]
                    if cell_value == "INFOR":
                        infor = [Ws.iat[n, 2], Ws.iat[n, 3], Ws.iat[n, 4]]
                    elif cell_value == "NUT":
                        nut = [Ws.iat[n, 2]]
                    elif cell_value == "END":
                        break
                    n += 1

                data = {"Name": Name_Stud, "Infor": infor, "Nut": nut}
                break

    return data
