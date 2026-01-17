"""
鋼橋IFCモデル生成 - その他部材生成モジュール
承板、コーナーカット、切り欠き、アンカーボルト、スタッド、穴などの部材生成
"""

import numpy as np
import pandas as pd

from src.bridge_json_to_ifc.ifc_utils_new.core import DefIFC, DefMath
from src.bridge_json_to_ifc.ifc_utils_new.utils import DefBridgeUtils

# グローバル変数: ログファイル出力関数（DefBridge.pyから設定される）
log_print_func = None


def _log_print(*args, **kwargs):
    """ログファイル出力関数（DEBUG_MODE時のみ出力）"""
    if log_print_func:
        log_print_func(*args, **kwargs)


def _calculate_x_break_positions(break_x, x_min, x_max, Senkei_data, sec_shouban):
    """
    X方向（橋軸方向）の分割位置を計算する

    Args:
        break_x: 分割設定（整数または辞書）
            - 整数: 等分割の数
            - {"Type": "equal", "Count": n}: 等分割
            - {"Type": "sections", "Sections": [...]}: セクション位置で分割
            - {"Type": "custom", "Lines": [[x1,y1,x2,y2], ...]}: カスタム線で分割
        x_min, x_max: X座標の範囲
        Senkei_data: 線形データ（セクション位置取得用）
        sec_shouban: 床版のセクションリスト

    Returns:
        分割位置のリスト [x0, x1, x2, ..., xn] （x0=x_min, xn=x_max）
    """
    if isinstance(break_x, int):
        # 従来の等分割
        x_range = x_max - x_min
        return [x_min + (x_range / break_x) * i for i in range(break_x + 1)]

    if isinstance(break_x, dict):
        break_type = break_x.get("Type", "equal")

        if break_type == "equal":
            count = break_x.get("Count", 4)
            x_range = x_max - x_min
            return [x_min + (x_range / count) * i for i in range(count + 1)]

        elif break_type == "sections":
            # セクション位置で分割
            sections = break_x.get("Sections", [])
            positions = [x_min]

            # 各セクションのX座標を取得
            for senkei in Senkei_data:
                for point in senkei.get("Point", []):
                    sec_name = point.get("Sec") or point.get("Name", "")
                    if sec_name in sections:
                        x = point.get("X", 0)
                        if x_min < x < x_max and x not in positions:
                            positions.append(x)

            positions.append(x_max)
            positions = sorted(set(positions))
            _log_print(f"    [Shouban] X方向セクション位置分割: {positions}")
            return positions

        elif break_type == "custom":
            # カスタム線分割（X座標が一定の線のみ使用）
            lines = break_x.get("Lines", [])
            positions = [x_min]

            for line in lines:
                if len(line) >= 4:
                    x1, y1, x2, y2 = line[:4]
                    # X座標が一定の線（垂直線）の場合
                    if abs(x1 - x2) < 1e-6:
                        x = x1
                        if x_min < x < x_max and x not in positions:
                            positions.append(x)

            positions.append(x_max)
            positions = sorted(set(positions))
            _log_print(f"    [Shouban] X方向カスタム線分割: {positions}")
            return positions

    # デフォルト: 4等分割
    x_range = x_max - x_min
    return [x_min + (x_range / 4) * i for i in range(5)]


def _calculate_y_break_positions(break_y, y_min, y_max, Senkei_data, MainPanel_data):
    """
    Y方向（橋軸直角方向）の分割位置を計算する

    Args:
        break_y: 分割設定（整数または辞書）
            - 整数: 等分割の数
            - {"Type": "equal", "Count": n}: 等分割
            - {"Type": "webs", "Girders": [...]}: ウェブ位置で分割
            - {"Type": "custom", "Lines": [[x1,y1,x2,y2], ...]}: カスタム線で分割
        y_min, y_max: Y座標の範囲
        Senkei_data: 線形データ（ウェブ位置取得用）
        MainPanel_data: メインパネルデータ（ウェブ位置取得用）

    Returns:
        分割位置のリスト [y0, y1, y2, ..., yn] （y0=y_min, yn=y_max）
    """
    if isinstance(break_y, int):
        # 従来の等分割
        y_range = y_max - y_min
        return [y_min + (y_range / break_y) * i for i in range(break_y + 1)]

    if isinstance(break_y, dict):
        break_type = break_y.get("Type", "equal")

        if break_type == "equal":
            count = break_y.get("Count", 3)
            y_range = y_max - y_min
            return [y_min + (y_range / count) * i for i in range(count + 1)]

        elif break_type == "webs":
            # ウェブ位置で分割（ウェブ中心線のみ、フランジエッジは除外）
            girders = break_y.get("Girders", [])
            positions = [y_min]

            # 各桁のウェブのY座標を取得
            import re

            for girder in girders:
                # 桁番号を抽出（例: "G1" → "1"）
                match = re.match(r"G(\d+)", girder)
                if match:
                    girder_num = match.group(1)
                    # 対応するウェブ中心線を探す（例: TG1, BG1のみ、TG1L, TG1Rは除外）
                    for senkei in Senkei_data:
                        senkei_name = senkei.get("Name", "")
                        # TG1, BG1など（末尾にLやRがつかないもののみ）
                        if re.match(rf"^[TB]G{girder_num}$", senkei_name):
                            # 最初の点のY座標を取得
                            points = senkei.get("Point", [])
                            if points:
                                y = points[0].get("Y", 0)
                                if y_min < y < y_max and y not in positions:
                                    positions.append(y)

            positions.append(y_max)
            positions = sorted(set(positions))
            _log_print(f"    [Shouban] Y方向ウェブ位置分割: {positions}")
            return positions

        elif break_type == "custom":
            # カスタム線分割（Y座標が一定の線のみ使用）
            lines = break_y.get("Lines", [])
            positions = [y_min]

            for line in lines:
                if len(line) >= 4:
                    x1, y1, x2, y2 = line[:4]
                    # Y座標が一定の線（水平線）の場合
                    if abs(y1 - y2) < 1e-6:
                        y = y1
                        if y_min < y < y_max and y not in positions:
                            positions.append(y)

            positions.append(y_max)
            positions = sorted(set(positions))
            _log_print(f"    [Shouban] Y方向カスタム線分割: {positions}")
            return positions

    # デフォルト: 3等分割
    y_range = y_max - y_min
    return [y_min + (y_range / 3) * i for i in range(4)]


# -----------------Shouban（床版）----------------------------------
def Calculate_Shouban(ifc_all, Senkei_data, MainPanel_data, infor_shouban):
    """
    床版（Deck/Shouban）を計算して描画する
    上フランジの上側に接するように配置し、厚みを持たせる
    左右のオーバーハングにも対応
    分割機能：厚さ方向、橋軸方向（X）、橋軸直角方向（Y）に対応
    上フランジ部分だけ厚さ方向分割をしないオプションにも対応

    Args:
        ifc_all: (ifc_file, bridge_span, geom_context)のタプル
        Senkei_data: 線形データ
        MainPanel_data: メインパネルデータ（上フランジの厚みを取得するため）
        infor_shouban: 床版情報（名称、線、断面、左オーバーハング、右オーバーハング、厚さ分割数、X分割数、Y分割数、上フランジ部分は分割しないフラグ、床版厚み、Zオフセット）
    """
    ifc_file, bridge_span, geom_context = ifc_all

    # 新旧両方の形式に対応（後方互換性）
    if len(infor_shouban) >= 11:
        (
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
        ) = infor_shouban
    else:
        # 旧形式（deck_thickness, z_offsetがない場合）
        (
            name_shouban,
            line_shouban,
            sec_shouban,
            overhang_left,
            overhang_right,
            break_thick,
            break_x,
            break_y,
            no_thick_break_for_flange,
        ) = infor_shouban
        deck_thickness = 200.0  # デフォルト値
        z_offset = 0.0  # デフォルト値

    _log_print(f"    [Shouban] 床版厚み: {deck_thickness}mm, Zオフセット: {z_offset}mm")

    secS_shouban = sec_shouban[0]  # 最初の断面（開始点）
    secE_shouban = sec_shouban[
        -1
    ]  # 最後の断面（終了点）- 修正: sec_shouban[1]からsec_shouban[-1]に変更（中間点C1が含まれていても正しく動作）

    idxS = -1
    idxE = -1
    for idx, point in enumerate(Senkei_data[0]["Point"]):
        if point["Name"] == secS_shouban:
            idxS = idx
            break

    for idx, point in enumerate(Senkei_data[0]["Point"]):
        if point["Name"] == secE_shouban:
            idxE = idx
            break

    if idxS == -1 or idxE == -1:
        _log_print(
            f"    [Shouban] 警告: 断面 '{secS_shouban}' または '{secE_shouban}' がSenkeiデータに見つかりません。"
        )
        return

    names_range = [point["Name"] for point in Senkei_data[0]["Point"][idxS : idxE + 1]]

    # 上フランジの実際の厚みとパネル情報を取得（MainPanelデータから）
    flange_thickness = 12.0  # デフォルト値
    thick1 = 12.0  # デフォルト値（中心線から上面までの距離）
    split_thickness = False  # デフォルト値
    uf_panel = None
    for panel in MainPanel_data:
        if panel.get("Type", {}).get("TypePanel") == "UF":
            # 上フランジパネルを発見
            uf_panel = panel
            mat_panel = panel.get("Material", {})
            split_thickness = mat_panel.get("SplitThickness", False)

            # Break.Thickから実際の厚さを取得（"上半分/下半分"形式）
            break_data = panel.get("Break", {})
            break_thick_list = break_data.get("Thick", [])
            if break_thick_list and len(break_thick_list) > 0:
                # 最初のBreak.Thick値から厚さを取得
                thick_str = break_thick_list[0]  # 例: "20.0/20.0"
                if "/" in str(thick_str):
                    parts = str(thick_str).split("/")
                    thick1 = float(parts[0])  # 上半分の厚さ
                    thick2 = float(parts[1]) if len(parts) > 1 else thick1  # 下半分の厚さ
                else:
                    thick1 = float(thick_str)
                    thick2 = thick1
            else:
                # Break.Thickがない場合はMaterialから取得
                thick1 = mat_panel.get("Thick1", 12.0)
                thick2 = mat_panel.get("Thick2", thick1)

            flange_thickness = thick1 + thick2
            break

    _log_print("    [Shouban DEBUG] 上フランジパネル情報:")
    if uf_panel:
        uf_name = uf_panel.get("Name", "")
        uf_line = uf_panel.get("Line", [])
        uf_expand = uf_panel.get("Expand", {})
        _log_print(f"    [Shouban DEBUG]   パネル名: {uf_name}")
        _log_print(f"    [Shouban DEBUG]   線形: {uf_line}")
        _log_print(f"    [Shouban DEBUG]   Thick1={thick1}mm, Thick2={thick2}mm, SplitThickness={split_thickness}")
        _log_print(f"    [Shouban DEBUG]   計算された上フランジ厚み: {flange_thickness}mm")
        _log_print(
            f"    [Shouban DEBUG]   拡張情報: E1={uf_expand.get('E1', 0)}, E2={uf_expand.get('E2', 0)}, E3={uf_expand.get('E3', 0)}, E4={uf_expand.get('E4', 0)}"
        )
    else:
        _log_print("    [Shouban DEBUG]   警告: 上フランジパネルが見つかりませんでした")

    # 床版の座標を取得（上フランジのラインから）
    _log_print("    [Shouban DEBUG] 床版座標取得:")
    _log_print(f"    [Shouban DEBUG]   床版の線形: {line_shouban}")
    _log_print(f"    [Shouban DEBUG]   断面範囲: {names_range}")
    Coord_Shouban_bottom = DefBridgeUtils.Load_Coordinate_Panel(Senkei_data, line_shouban, names_range)

    if Coord_Shouban_bottom and len(Coord_Shouban_bottom) > 0:
        _log_print(f"    [Shouban DEBUG]   拡張前の座標線数: {len(Coord_Shouban_bottom)}")
        if len(Coord_Shouban_bottom[0]) > 0:
            first_point = Coord_Shouban_bottom[0][0]
            last_point = Coord_Shouban_bottom[0][-1]
            _log_print(
                f"    [Shouban DEBUG]   拡張前の最初の点: [{first_point[0]:.2f}, {first_point[1]:.2f}, {first_point[2]:.2f}]"
            )
            _log_print(
                f"    [Shouban DEBUG]   拡張前の最後の点: [{last_point[0]:.2f}, {last_point[1]:.2f}, {last_point[2]:.2f}]"
            )

    # 上フランジと同じ拡張処理を適用
    if uf_panel:
        uf_name = uf_panel.get("Name", "")
        uf_expand = uf_panel.get("Expand", {})
        ExtendL = uf_expand.get("E1", 0)
        ExtendR = uf_expand.get("E2", 0)
        ExtendT = uf_expand.get("E3", 0)
        ExtendB = uf_expand.get("E4", 0)
        _log_print(
            f"    [Shouban DEBUG]   拡張処理を適用: ExtendL={ExtendL}, ExtendR={ExtendR}, ExtendT={ExtendT}, ExtendB={ExtendB}"
        )
        Coord_Shouban_bottom = DefBridgeUtils.Calculate_Extend(
            MainPanel_data, Senkei_data, uf_name, Coord_Shouban_bottom, ExtendL, ExtendR, ExtendT, ExtendB
        )

        if Coord_Shouban_bottom and len(Coord_Shouban_bottom) > 0:
            _log_print(f"    [Shouban DEBUG]   拡張後の座標線数: {len(Coord_Shouban_bottom)}")
            if len(Coord_Shouban_bottom[0]) > 0:
                first_point = Coord_Shouban_bottom[0][0]
                last_point = Coord_Shouban_bottom[0][-1]
                _log_print(
                    f"    [Shouban DEBUG]   拡張後の最初の点: [{first_point[0]:.2f}, {first_point[1]:.2f}, {first_point[2]:.2f}]"
                )
                _log_print(
                    f"    [Shouban DEBUG]   拡張後の最後の点: [{last_point[0]:.2f}, {last_point[1]:.2f}, {last_point[2]:.2f}]"
                )
                _log_print(f"    [Shouban DEBUG]   上フランジ中心線Z座標: {first_point[2]:.2f}mm")

                # 上フランジの実際の上面位置を計算（Offset_Faceを使用）
                # 上フランジのラインは中心線を表しているため、上面までの距離はthick1のみ
                # SplitThickness=true: 中心線から上面まではthick1（上半分の厚さ）
                # SplitThickness=false: 中心線から上面までは全厚の半分
                flange_top_offset = thick1 if split_thickness else flange_thickness / 2
                Coord_Shouban_top = DefMath.Offset_Face(Coord_Shouban_bottom, flange_top_offset)
                if Coord_Shouban_top and len(Coord_Shouban_top) > 0 and len(Coord_Shouban_top[0]) > 0:
                    top_point = Coord_Shouban_top[0][0]
                    _log_print(f"    [Shouban DEBUG]   Offset_Faceで計算した上フランジ上面Z座標: {top_point[2]:.2f}mm")
                    _log_print(f"    [Shouban DEBUG]   中心線から上面までの距離: {top_point[2] - first_point[2]:.2f}mm")
                    # 上フランジの上面位置を使用する
                    Coord_Shouban_bottom = Coord_Shouban_top
                else:
                    # Offset_Faceが失敗した場合、従来の方法を使用
                    _log_print(
                        f"    [Shouban DEBUG]   Offset_Faceが失敗したため、従来の方法を使用: {first_point[2] + flange_thickness:.2f}mm"
                    )

    # deck_thicknessはinfor_shoubanから取得済み（デフォルト200mm）

    if not Coord_Shouban_bottom or len(Coord_Shouban_bottom) < 4:
        _log_print("    [Shouban] 警告: 床版の座標データが取得できませんでした。")
        return

    # オーバーハングを適用した座標を計算
    # 各ポリラインの点を順番に並べて、閉じた形状の座標を取得
    base_points = []  # オーバーハング適用後の基本座標（Zは上フランジ上面）

    # 最初のポリライン（左端、例：TG1L）の点を順番に取得
    first_polyline = Coord_Shouban_bottom[0]
    _log_print("    [Shouban DEBUG] base_points計算開始:")
    _log_print(f"    [Shouban DEBUG]   最初のポリラインの点の数: {len(first_polyline)}")
    _log_print("    [Shouban DEBUG]   Coord_Shouban_bottomは既に上フランジ上面位置を表しています")
    for point in first_polyline:
        z_original = point[2]
        # Coord_Shouban_bottomは既に上フランジ上面位置を表しているため、flange_thicknessを追加しない
        base_points.append([point[0], point[1] - overhang_left, z_original])
        _log_print(f"    [Shouban DEBUG]   点追加: Z座標={z_original:.2f}mm (上フランジ上面位置)")

    # 2番目のポリライン（例：TG1R）の最後の点を取得
    if len(Coord_Shouban_bottom) > 1:
        second_polyline = Coord_Shouban_bottom[1]
        if len(second_polyline) > 1:
            point = second_polyline[-1]
            z_original = point[2]
            base_points.append([point[0], point[1], z_original])
            _log_print(f"    [Shouban DEBUG]   2番目ポリライン最後の点: Z座標={z_original:.2f}mm")

    # 3番目のポリライン（右端、例：TG3R）の点を逆順で取得
    if len(Coord_Shouban_bottom) > 2:
        third_polyline = Coord_Shouban_bottom[2]
        for i in range(len(third_polyline) - 1, -1, -1):
            point = third_polyline[i]
            z_original = point[2]
            base_points.append([point[0], point[1] + overhang_right, z_original])

    # 4番目のポリライン（例：TG3L）の最初の点を取得
    if len(Coord_Shouban_bottom) > 3:
        fourth_polyline = Coord_Shouban_bottom[3]
        if len(fourth_polyline) > 1:
            point = fourth_polyline[0]
            z_original = point[2]
            base_points.append([point[0], point[1], z_original])

    if len(base_points) < 4:
        _log_print("    [Shouban] 警告: 床版の基本座標が不足しています。")
        return

    # base_pointsのZ座標範囲を確認
    z_min = min(p[2] for p in base_points)
    z_max = max(p[2] for p in base_points)
    _log_print("    [Shouban DEBUG] base_points計算完了:")
    _log_print(f"    [Shouban DEBUG]   base_points数: {len(base_points)}")
    _log_print(f"    [Shouban DEBUG]   Z座標範囲: {z_min:.2f}mm ～ {z_max:.2f}mm")
    _log_print(f"    [Shouban DEBUG]   床版の下面Z座標（期待値）: {z_min:.2f}mm")

    # 分割処理
    # X方向（橋軸方向）の範囲を計算
    x_min = min(p[0] for p in base_points)
    x_max = max(p[0] for p in base_points)

    # Y方向（橋軸直角方向）の範囲を計算
    y_min = min(p[1] for p in base_points)
    y_max = max(p[1] for p in base_points)

    # Z座標（上フランジ上面）を取得
    # base_pointsは上フランジの上面位置を表している
    z_base = base_points[0][2] if base_points else 0.0

    # X方向とY方向の分割位置を計算（高度な分割設定に対応）
    x_positions = _calculate_x_break_positions(break_x, x_min, x_max, Senkei_data, sec_shouban)
    y_positions = _calculate_y_break_positions(break_y, y_min, y_max, Senkei_data, MainPanel_data)

    _log_print("    [Shouban DEBUG] 分割位置:")
    _log_print(f"    [Shouban DEBUG]   X方向: {len(x_positions) - 1}分割 = {x_positions}")
    _log_print(f"    [Shouban DEBUG]   Y方向: {len(y_positions) - 1}分割 = {y_positions}")

    # 各分割セグメントを生成
    segment_count = 0

    if no_thick_break_for_flange:
        # NoThickBreakForFlangeがtrueの場合、上フランジ部分は生成せず、床版部分だけを分割する
        # z_baseは上フランジの上面位置を表しているため、床版はその上に配置する
        # 上フランジの厚み分だけ上に移動させ、さらにz_offsetを追加
        z_deck_bottom = z_base + flange_thickness + z_offset
        z_deck_top = z_base + flange_thickness + z_offset + deck_thickness

        _log_print("    [Shouban DEBUG] 床版位置計算:")
        _log_print(f"    [Shouban DEBUG]   z_base (上フランジ上面): {z_base:.2f}mm")
        _log_print(f"    [Shouban DEBUG]   flange_thickness: {flange_thickness}mm")
        _log_print(f"    [Shouban DEBUG]   z_offset: {z_offset}mm")
        _log_print(f"    [Shouban DEBUG]   deck_thickness: {deck_thickness}mm")
        _log_print(
            f"    [Shouban DEBUG]   計算される床版下面Z座標: {z_deck_bottom:.2f}mm (上フランジ上面 + {flange_thickness}mm + {z_offset}mm)"
        )
        _log_print(f"    [Shouban DEBUG]   計算される床版上面Z座標: {z_deck_top:.2f}mm")

        # 床版部分の厚さ方向の分割（床版の厚み全体を分割）
        segment_thickness = deck_thickness / break_thick
        _log_print(f"    [Shouban DEBUG]   厚さ方向分割数: {break_thick}, セグメント厚み: {segment_thickness:.2f}mm")

        for thick_idx in range(break_thick):
            z_bottom = z_deck_bottom + (thick_idx * segment_thickness)
            z_top = z_deck_bottom + ((thick_idx + 1) * segment_thickness)

            for x_idx in range(len(x_positions) - 1):
                x_start = x_positions[x_idx]
                x_end = x_positions[x_idx + 1]

                for y_idx in range(len(y_positions) - 1):
                    y_start = y_positions[y_idx]
                    y_end = y_positions[y_idx + 1]

                    seg_bottom = _create_segment_polygon_with_straight_lines(
                        base_points, x_start, x_end, y_start, y_end, z_bottom
                    )
                    seg_top = _create_segment_polygon_with_straight_lines(
                        base_points, x_start, x_end, y_start, y_end, z_top
                    )

                    if seg_bottom and seg_top and len(seg_bottom) >= 4 and len(seg_top) >= 4:
                        try:
                            solid_segment = DefIFC.Create_brep_from_prism(ifc_file, seg_top, seg_bottom)
                            segment_name = f"{name_shouban}_T{thick_idx}_X{x_idx}_Y{y_idx}"

                            color_style = DefIFC.create_color(ifc_file, 176.0, 176.0, 176.0)
                            styled_item = ifc_file.createIfcStyledItem(Item=solid_segment, Styles=[color_style])
                            shape_representation = ifc_file.createIfcShapeRepresentation(
                                ContextOfItems=geom_context,
                                RepresentationIdentifier="Body",
                                RepresentationType="Brep",
                                Items=[solid_segment],
                            )
                            DefIFC.Add_shape_representation_in_Beam(
                                ifc_file, bridge_span, shape_representation, segment_name
                            )
                            segment_count += 1
                        except Exception as e:
                            _log_print(
                                f"    [Shouban] 床版セグメント生成エラー (T={thick_idx}, X={x_idx}, Y={y_idx}): {str(e)}"
                            )
    else:
        # 通常の分割（全体を厚さ方向に分割）
        # z_baseは上フランジの上面位置を表しているため、床版はその上に配置する
        # 上フランジの厚み分だけ上に移動させ、さらにz_offsetを追加
        z_deck_bottom = z_base + flange_thickness + z_offset
        segment_thickness = deck_thickness / break_thick

        _log_print("    [Shouban DEBUG] 床版位置計算（通常分割）:")
        _log_print(f"    [Shouban DEBUG]   z_base (上フランジ上面): {z_base:.2f}mm")
        _log_print(f"    [Shouban DEBUG]   flange_thickness: {flange_thickness}mm")
        _log_print(f"    [Shouban DEBUG]   z_offset: {z_offset}mm")
        _log_print(f"    [Shouban DEBUG]   deck_thickness: {deck_thickness}mm")
        _log_print(
            f"    [Shouban DEBUG]   計算される床版下面Z座標: {z_deck_bottom:.2f}mm (上フランジ上面 + {flange_thickness}mm + {z_offset}mm)"
        )
        _log_print(f"    [Shouban DEBUG]   厚さ方向分割数: {break_thick}, セグメント厚み: {segment_thickness:.2f}mm")

        for thick_idx in range(break_thick):
            z_bottom = z_deck_bottom + (thick_idx * segment_thickness)
            z_top = z_deck_bottom + ((thick_idx + 1) * segment_thickness)

            for x_idx in range(len(x_positions) - 1):
                x_start = x_positions[x_idx]
                x_end = x_positions[x_idx + 1]

                for y_idx in range(len(y_positions) - 1):
                    y_start = y_positions[y_idx]
                    y_end = y_positions[y_idx + 1]

                    # セグメントの境界を正確に計算（直線分割）
                    seg_bottom = _create_segment_polygon_with_straight_lines(
                        base_points, x_start, x_end, y_start, y_end, z_bottom
                    )
                    seg_top = _create_segment_polygon_with_straight_lines(
                        base_points, x_start, x_end, y_start, y_end, z_top
                    )

                    # デバッグログ
                    if not seg_bottom or not seg_top:
                        _log_print(
                            f"    [Shouban] セグメントポリゴン生成失敗 (T={thick_idx}, X={x_idx}, Y={y_idx}): seg_bottom={seg_bottom is not None}, seg_top={seg_top is not None}"
                        )
                    elif len(seg_bottom) < 4 or len(seg_top) < 4:
                        _log_print(
                            f"    [Shouban] セグメントポリゴン点数不足 (T={thick_idx}, X={x_idx}, Y={y_idx}): bottom={len(seg_bottom)}, top={len(seg_top)}"
                        )

                    if seg_bottom and seg_top and len(seg_bottom) >= 4 and len(seg_top) >= 4:
                        try:
                            solid_segment = DefIFC.Create_brep_from_prism(ifc_file, seg_top, seg_bottom)
                            segment_name = f"{name_shouban}_T{thick_idx}_X{x_idx}_Y{y_idx}"

                            color_style = DefIFC.create_color(ifc_file, 176.0, 176.0, 176.0)
                            styled_item = ifc_file.createIfcStyledItem(Item=solid_segment, Styles=[color_style])
                            shape_representation = ifc_file.createIfcShapeRepresentation(
                                ContextOfItems=geom_context,
                                RepresentationIdentifier="Body",
                                RepresentationType="Brep",
                                Items=[solid_segment],
                            )
                            DefIFC.Add_shape_representation_in_Beam(
                                ifc_file, bridge_span, shape_representation, segment_name
                            )
                            segment_count += 1
                        except Exception as e:
                            _log_print(
                                f"    [Shouban] セグメント生成エラー (T={thick_idx}, X={x_idx}, Y={y_idx}): {str(e)}"
                            )

    _log_print(f"    [Shouban] {segment_count}個の分割セグメントを生成しました。")


def _create_segment_polygon_with_straight_lines(base_points, x_start, x_end, y_start, y_end, z):
    """
    直線の分割線（X=一定、Y=一定）を使用してセグメントのポリゴンを計算する
    元の床版の形状を保持しながら、直線で分割する

    Args:
        base_points: 基本座標点のリスト（元の床版の形状）
        x_start, x_end: X方向の範囲（X=一定の直線で分割）
        y_start, y_end: Y方向の範囲（Y=一定の直線で分割）
        z: Z座標

    Returns:
        セグメントのポリゴン点のリスト
    """
    segment_points = []
    n = len(base_points)

    # 1. 元のポリゴンの点でセグメント内にあるものを追加
    for p in base_points:
        if x_start <= p[0] <= x_end and y_start <= p[1] <= y_end:
            segment_points.append([p[0], p[1], z])

    # 2. 元のポリゴンの各辺と直線の分割線（X=一定、Y=一定）の交点を計算
    for i in range(n):
        p1 = base_points[i]
        p2 = base_points[(i + 1) % n]

        # X方向の分割線（X=一定の直線）との交点
        # 左境界 (x = x_start)
        if p1[0] != p2[0]:  # 垂直でない辺
            if min(p1[0], p2[0]) <= x_start <= max(p1[0], p2[0]):
                t = (x_start - p1[0]) / (p2[0] - p1[0])
                if 0 <= t <= 1:
                    y_inter = p1[1] + t * (p2[1] - p1[1])
                    if y_start <= y_inter <= y_end:
                        point = [x_start, y_inter, z]
                        if not any(abs(p[0] - point[0]) < 1e-6 and abs(p[1] - point[1]) < 1e-6 for p in segment_points):
                            segment_points.append(point)

        # 右境界 (x = x_end)
        if p1[0] != p2[0]:  # 垂直でない辺
            if min(p1[0], p2[0]) <= x_end <= max(p1[0], p2[0]):
                t = (x_end - p1[0]) / (p2[0] - p1[0])
                if 0 <= t <= 1:
                    y_inter = p1[1] + t * (p2[1] - p1[1])
                    if y_start <= y_inter <= y_end:
                        point = [x_end, y_inter, z]
                        if not any(abs(p[0] - point[0]) < 1e-6 and abs(p[1] - point[1]) < 1e-6 for p in segment_points):
                            segment_points.append(point)

        # Y方向の分割線（Y=一定の直線）との交点
        # 下境界 (y = y_start)
        if p1[1] != p2[1]:  # 水平でない辺
            if min(p1[1], p2[1]) <= y_start <= max(p1[1], p2[1]):
                t = (y_start - p1[1]) / (p2[1] - p1[1])
                if 0 <= t <= 1:
                    x_inter = p1[0] + t * (p2[0] - p1[0])
                    if x_start <= x_inter <= x_end:
                        point = [x_inter, y_start, z]
                        if not any(abs(p[0] - point[0]) < 1e-6 and abs(p[1] - point[1]) < 1e-6 for p in segment_points):
                            segment_points.append(point)

        # 上境界 (y = y_end)
        if p1[1] != p2[1]:  # 水平でない辺
            if min(p1[1], p2[1]) <= y_end <= max(p1[1], p2[1]):
                t = (y_end - p1[1]) / (p2[1] - p1[1])
                if 0 <= t <= 1:
                    x_inter = p1[0] + t * (p2[0] - p1[0])
                    if x_start <= x_inter <= x_end:
                        point = [x_inter, y_end, z]
                        if not any(abs(p[0] - point[0]) < 1e-6 and abs(p[1] - point[1]) < 1e-6 for p in segment_points):
                            segment_points.append(point)

    # 3. セグメント矩形の角が元のポリゴン内にある場合に追加
    seg_corners = [[x_start, y_start, z], [x_end, y_start, z], [x_end, y_end, z], [x_start, y_end, z]]

    for corner in seg_corners:
        if _point_in_polygon_2d(corner[:2], [p[:2] for p in base_points]):
            if not any(abs(p[0] - corner[0]) < 1e-6 and abs(p[1] - corner[1]) < 1e-6 for p in segment_points):
                segment_points.append(corner)

    # 4. 点を時計回りまたは反時計回りにソート
    if len(segment_points) >= 3:
        # 重心を計算
        cx = sum(p[0] for p in segment_points) / len(segment_points)
        cy = sum(p[1] for p in segment_points) / len(segment_points)

        # 角度でソート
        def angle_key(p):
            import math

            return math.atan2(p[1] - cy, p[0] - cx)

        segment_points.sort(key=angle_key)

    return segment_points if len(segment_points) >= 4 else None


def _create_segment_polygon(base_points, x_start, x_end, y_start, y_end, z):
    """
    セグメントの境界に基づいてポリゴンの点を計算する

    Args:
        base_points: 基本座標点のリスト
        x_start, x_end: X方向の範囲
        y_start, y_end: Y方向の範囲
        z: Z座標

    Returns:
        セグメントのポリゴン点のリスト
    """
    segment_points = []
    n = len(base_points)

    # セグメント矩形の4つの角
    seg_corners = [[x_start, y_start, z], [x_end, y_start, z], [x_end, y_end, z], [x_start, y_end, z]]

    # 1. 元のポリゴンの点でセグメント内にあるものを追加
    for p in base_points:
        if x_start <= p[0] <= x_end and y_start <= p[1] <= y_end:
            segment_points.append([p[0], p[1], z])

    # 2. 元のポリゴンの各辺とセグメント境界の交点を計算
    for i in range(n):
        p1 = base_points[i]
        p2 = base_points[(i + 1) % n]

        # セグメントの4つの境界線との交点を計算
        # 左境界 (x = x_start)
        inter = _line_line_intersection_2d(p1, p2, [x_start, y_start], [x_start, y_end])
        if inter and x_start <= inter[0] <= x_end and y_start <= inter[1] <= y_end:
            point = [x_start, inter[1], z]
            if not any(abs(p[0] - point[0]) < 1e-6 and abs(p[1] - point[1]) < 1e-6 for p in segment_points):
                segment_points.append(point)

        # 右境界 (x = x_end)
        inter = _line_line_intersection_2d(p1, p2, [x_end, y_start], [x_end, y_end])
        if inter and x_start <= inter[0] <= x_end and y_start <= inter[1] <= y_end:
            point = [x_end, inter[1], z]
            if not any(abs(p[0] - point[0]) < 1e-6 and abs(p[1] - point[1]) < 1e-6 for p in segment_points):
                segment_points.append(point)

        # 下境界 (y = y_start)
        inter = _line_line_intersection_2d(p1, p2, [x_start, y_start], [x_end, y_start])
        if inter and x_start <= inter[0] <= x_end and y_start <= inter[1] <= y_end:
            point = [inter[0], y_start, z]
            if not any(abs(p[0] - point[0]) < 1e-6 and abs(p[1] - point[1]) < 1e-6 for p in segment_points):
                segment_points.append(point)

        # 上境界 (y = y_end)
        inter = _line_line_intersection_2d(p1, p2, [x_start, y_end], [x_end, y_end])
        if inter and x_start <= inter[0] <= x_end and y_start <= inter[1] <= y_end:
            point = [inter[0], y_end, z]
            if not any(abs(p[0] - point[0]) < 1e-6 and abs(p[1] - point[1]) < 1e-6 for p in segment_points):
                segment_points.append(point)

    # 3. セグメントの角が元のポリゴン内にある場合、またはセグメント矩形とポリゴンが交差する場合に角を追加
    for corner in seg_corners:
        # 角がポリゴン内にあるか、またはセグメント矩形がポリゴンと交差している場合
        if _point_in_polygon_2d(corner[:2], [p[:2] for p in base_points]):
            if not any(abs(p[0] - corner[0]) < 1e-6 and abs(p[1] - corner[1]) < 1e-6 for p in segment_points):
                segment_points.append(corner)

    # 4. セグメント矩形とポリゴンが交差しているが、角がポリゴン内にない場合でも、
    # セグメント矩形の角を追加（セグメント矩形がポリゴンと交差している場合）
    if len(segment_points) < 4:
        # セグメント矩形とポリゴンが交差しているかチェック
        # セグメント矩形の各辺がポリゴンと交差しているか、またはセグメント矩形内にポリゴンの点があるか
        has_intersection = False
        for corner in seg_corners:
            if _point_in_polygon_2d(corner[:2], [p[:2] for p in base_points]):
                has_intersection = True
                break

        # セグメント矩形の辺とポリゴンの辺が交差しているかチェック
        if not has_intersection:
            for i in range(4):
                seg_p1 = seg_corners[i]
                seg_p2 = seg_corners[(i + 1) % 4]
                for j in range(n):
                    poly_p1 = base_points[j]
                    poly_p2 = base_points[(j + 1) % n]
                    if _line_intersects_segment(seg_p1, seg_p2, poly_p1, poly_p2):
                        has_intersection = True
                        break
                if has_intersection:
                    break

        # 交差している場合、セグメント矩形の角を追加
        if has_intersection:
            for corner in seg_corners:
                if not any(abs(p[0] - corner[0]) < 1e-6 and abs(p[1] - corner[1]) < 1e-6 for p in segment_points):
                    segment_points.append(corner)

    # 5. 点を時計回りまたは反時計回りにソート
    if len(segment_points) >= 3:
        # 重心を計算
        cx = sum(p[0] for p in segment_points) / len(segment_points)
        cy = sum(p[1] for p in segment_points) / len(segment_points)

        # 角度でソート
        def angle_key(p):
            import math

            return math.atan2(p[1] - cy, p[0] - cx)

        segment_points.sort(key=angle_key)

    return segment_points if len(segment_points) >= 4 else None


def _line_intersects_segment(p1, p2, s1, s2):
    """線分p1-p2と線分s1-s2が交差するかチェック（2D）"""

    def ccw(A, B, C):
        return (C[1] - A[1]) * (B[0] - A[0]) > (B[1] - A[1]) * (C[0] - A[0])

    return ccw(p1[:2], s1[:2], s2[:2]) != ccw(p2[:2], s1[:2], s2[:2]) and ccw(p1[:2], p2[:2], s1[:2]) != ccw(
        p1[:2], p2[:2], s2[:2]
    )


def _line_line_intersection_2d(p1, p2, q1, q2):
    """2つの2D線分の交点を計算"""
    x1, y1 = p1[0], p1[1]
    x2, y2 = p2[0], p2[1]
    x3, y3 = q1[0], q1[1]
    x4, y4 = q2[0], q2[1]

    denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    if abs(denom) < 1e-10:
        return None

    t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom
    u = -((x1 - x2) * (y1 - y3) - (y1 - y2) * (x1 - x3)) / denom

    if 0 <= t <= 1 and 0 <= u <= 1:
        x = x1 + t * (x2 - x1)
        y = y1 + t * (y2 - y1)
        return [x, y]
    return None


def _point_in_polygon_2d(point, polygon):
    """点がポリゴン内にあるかチェック（2D）"""
    x, y = point[0], point[1]
    n = len(polygon)
    inside = False

    p1x, p1y = polygon[0][0], polygon[0][1]
    for i in range(1, n + 1):
        p2x, p2y = polygon[i % n][0], polygon[i % n][1]
        if y > min(p1y, p2y):
            if y <= max(p1y, p2y):
                if x <= max(p1x, p2x):
                    if p1y != p2y:
                        xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or x <= xinters:
                        inside = not inside
        p1x, p1y = p2x, p2y

    return inside


# ----------------------------Corner------------------------------------------------------
def Draw_Corner(ifc_file, corner, pcorner, pdirX, pdirY):
    """
    コーナーカットを描画する

    Args:
        ifc_file: IFCファイルオブジェクト
        corner: コーナー指定（"R数値"=丸み、"C数値"または"C数値x数値"=角カット）
        pcorner: コーナー点
        pdirX: X方向の点
        pdirY: Y方向の点

    Returns:
        IfcExtrudedAreaSolidまたはIfcBooleanResultエンティティ
    """
    solid_corner = None

    if corner[:1] == "R":
        pal1 = pcorner.copy()
        normalvector = DefMath.Normal_vector(pcorner, pdirX, pdirY)
        pal2 = pal1 + 100 * normalvector
        pal3 = pdirX.copy()
        p = [0, 0, 0]
        solid_corner = DefIFC.Draw_Solid_Circle(ifc_file, p, corner[1:], pal1, pal2, pal3)

    elif corner[:1] == "C":
        """
        コーナーカットを描画する（C形式: 角を切り取る）
        C15x10 または C15 のような形式を処理
        """
        val = corner[1:]
        if "x" in val or "X" in val:
            # C15x10 または C15X10 形式の場合
            parts = val.lower().split("x")
            if len(parts) == 2:
                x_offset = float(parts[0])
                y_offset = float(parts[1])
            else:
                raise ValueError(f"無効な形式: {corner}")
        else:
            # 数値が1つのみの場合、XとYの両方に同じ値を適用
            x_offset = y_offset = float(val)

        p1 = DefMath.Point_on_line(pcorner, pdirX, x_offset)
        p2 = DefMath.Point_on_line(pcorner, pdirY, y_offset)
        arPoint = [pcorner, p1, p2]

        normalvector = DefMath.Normal_vector(pcorner, p1, p2)
        normalvector = normalvector.tolist()

        # プロファイルの点を調整（法線ベクトル方向にオフセット）
        translated_points = []
        for point in arPoint:
            translated_point = [point[i] + (-0.5 * normalvector[i] * 100) for i in range(3)]
            translated_points.append(translated_point)

        # 移動した点からpolylineとprofileを作成
        trans_polyline = ifc_file.createIfcPolyline(
            [DefIFC.create_cartesian_point(ifc_file, pt) for pt in translated_points]
        )
        trans_profile = ifc_file.createIfcArbitraryClosedProfileDef("AREA", None, trans_polyline)

        # 移動したプロファイルでsolid extrusionを作成
        extrusion_dir = ifc_file.createIfcDirection(normalvector)
        solid_corner = ifc_file.createIfcExtrudedAreaSolid(trans_profile, None, extrusion_dir, 100)

    return solid_corner


def Coord_Outline_ATM(arNamePoint, arCoordPoint, out):
    """
    ATM（アンカーボルト・台座）の外形座標を計算する

    Args:
        arNamePoint: 点名称の配列
        arCoordPoint: 座標点の配列
        out: 外形定義（LINEまたはARC）

    Returns:
        外形座標の配列
    """
    arCoord_Outline_ATM = []
    for i in range(0, len(out)):
        atc = out[i]
        if atc[0] == "LINE":
            for i_1 in range(1, len(atc)):
                index = arNamePoint.index(atc[i_1])
                arCoord_Outline_ATM.append(arCoordPoint[index])
        if atc[0] == "ARC":
            for i_1 in range(1, len(atc), 3):
                index = arNamePoint.index(atc[i_1])
                pl = arCoordPoint[index]

                index = arNamePoint.index(atc[i_1 + 1])
                pc = arCoordPoint[index]

                index = arNamePoint.index(atc[i_1 + 2])
                pr = arCoordPoint[index]

                points_arc = DefMath.devide_arc_to_points_polyline(pr, pl, pc, 20)
                points_arc.reverse()

                for i_2 in range(0, len(points_arc)):
                    p = [points_arc[i_2][0], points_arc[i_2][1], 0]
                    arCoord_Outline_ATM.append(p)

    arCoord_Outline_ATM_final = []
    seen = set()

    for i in range(0, len(arCoord_Outline_ATM)):
        coord = arCoord_Outline_ATM[i]
        coord_tuple = tuple(arCoord_Outline_ATM[i])
        if coord_tuple not in seen:
            arCoord_Outline_ATM_final.append(coord)
            seen.add(coord_tuple)
        else:
            if i == len(arCoord_Outline_ATM) - 1:
                arCoord_Outline_ATM_final.append(coord)

    return arCoord_Outline_ATM_final


def Calculate_ATM(ifc_all, Member_data, name_atm, ref_atm, pal1, pal2, pal3):
    """
    ATM（アンカーボルト・台座）を計算して描画する

    Args:
        ifc_all: (ifc_file, bridge_span, geom_context)のタプル
        Member_data: メンバーデータ
        name_atm: ATM名称
        ref_atm: 参照ATM名称
        pal1, pal2, pal3: 座標系を定義する3点
    """
    ifc_file, bridge_span, geom_context = ifc_all

    for Atm in Member_data:
        if Atm["Name"] == ref_atm:
            infor = Atm["Infor"]
            points = Atm["Point"]
            out = Atm["Out"]
            holes = Atm["Hole"]
            break
    result = infor, points, out, holes
    Type_ATM, Thick1_ATM, Thick2_ATM, Mat_ATM = infor
    arNamePoint = []
    arCoordPoint = []
    for point in points:
        arNamePoint.append(point[0])
        p = [point[1], point[2], point[3]]
        arCoordPoint.append(p)

    arCoord_Outline_ATM = Coord_Outline_ATM(arNamePoint, arCoordPoint, out)

    Solid1_ATM = DefIFC.extrude_profile_and_align(ifc_file, arCoord_Outline_ATM, Thick1_ATM, pal1, pal2, pal3)
    Solid2_ATM = DefIFC.extrude_profile_and_align(ifc_file, arCoord_Outline_ATM, -Thick2_ATM, pal1, pal2, pal3)
    Solid_ATM = ifc_file.createIfcBooleanResult("UNION", Solid1_ATM, Solid2_ATM)

    if holes:
        for hole in holes:
            namepoint_hole, type_hole, d_hole = hole
            index = arNamePoint.index(namepoint_hole)
            pbase_hole = arCoordPoint[index]
            solid_hole = Draw_Solid_Hole(ifc_file, pbase_hole, type_hole, d_hole, pal1, pal2, pal3)
            Solid_ATM = ifc_file.createIfcBooleanResult("DIFFERENCE", Solid_ATM, solid_hole)

    color_style = DefIFC.create_color(ifc_file, 80.0, 217.0, 236.0)
    styled_item = ifc_file.createIfcStyledItem(Item=Solid_ATM, Styles=[color_style])
    shape_representation = ifc_file.createIfcShapeRepresentation(
        ContextOfItems=geom_context, RepresentationIdentifier="Body", RepresentationType="Brep", Items=[Solid_ATM]
    )
    DefIFC.Add_shape_representation_in_Beam(ifc_file, bridge_span, shape_representation, name_atm)


def Calculate_Stud(ifc_all, Member_data, name_stud, pal1, pal2, pal3):
    """
    スタッドを計算して描画する

    Args:
        ifc_all: (ifc_file, bridge_span, geom_context)のタプル
        Member_data: メンバーデータ
        name_stud: スタッド名称
        pal1, pal2, pal3: 座標系を定義する3点
    """
    ifc_file, bridge_span, geom_context = ifc_all

    for Stud in Member_data:
        if Stud["Name"] == name_stud:
            infor = Stud["Infor"]
            nut = Stud["Nut"]
            break
    result = infor, nut
    type_stud, size_stud, mat_stud = infor
    atc = size_stud.split("x")
    d_stud, h_stud = atc
    p = [0, 0, 0]
    solid_stud = DefIFC.Draw_Solid_Circle(ifc_file, p, d_stud, pal1, pal2, pal3, float(h_stud))

    if nut:
        size_nut = nut[0]
        atc_nut = size_nut.split("x")
        p = [0, 0, float(h_stud)]
        d_nut, h_nut = atc_nut

        pal1_nut = DefMath.Point_on_line(pal1, pal2, float(h_stud))
        pal2_nut = DefMath.Point_on_line(pal1, pal2, 2 * float(h_stud))
        p1 = np.array(pal1_nut, dtype=float)
        p2 = np.array(pal2_nut, dtype=float)
        v1 = p2 - p1
        normal_vector = DefMath.Normalize_vector(v1)
        pal3_nut = pal3 + float(h_stud) * normal_vector

        solid_nut = DefIFC.Draw_Solid_Circle(ifc_file, p, d_nut, pal1_nut, pal2_nut, pal3_nut, float(h_nut))
        solid_stud = ifc_file.createIfcBooleanResult("UNION", solid_stud, solid_nut)

    color_style = DefIFC.create_color(ifc_file, 80.0, 217.0, 236.0)
    styled_item = ifc_file.createIfcStyledItem(Item=solid_stud, Styles=[color_style])
    shape_representation = ifc_file.createIfcShapeRepresentation(
        ContextOfItems=geom_context, RepresentationIdentifier="Body", RepresentationType="Brep", Items=[solid_stud]
    )
    DefIFC.Add_shape_representation_in_Beam(ifc_file, bridge_span, shape_representation, name_stud)


def Draw_Solid_Hole(ifc_file, pbase_hole, type_hole, d_hole, pal1, pal2, pal3):
    """
    穴を描画する

    Args:
        ifc_file: IFCファイルオブジェクト
        pbase_hole: 穴の基準点
        type_hole: 穴タイプ（"C"=円形、"HV"=長穴）
        d_hole: 穴の直径またはサイズ
        pal1, pal2, pal3: 座標系を定義する3点

    Returns:
        IfcExtrudedAreaSolidまたはIfcBooleanResultエンティティ
    """
    solid_hole = None
    if type_hole == "C":
        solid_hole = DefIFC.Draw_Solid_Circle(ifc_file, pbase_hole, d_hole, pal1, pal2, pal3)
    elif type_hole == "HV":
        solid_hole = Draw_Solid_LongHole(ifc_file, pbase_hole, type_hole, d_hole, pal1, pal2, pal3)

    return solid_hole


def Draw_Solid_LongHole(ifc_file, pbase_hole, type_hole, d_hole, pal1, pal2, pal3):
    """
    長穴を描画する

    Args:
        ifc_file: IFCファイルオブジェクト
        pbase_hole: 穴の基準点
        type_hole: 穴タイプ（"HV"）
        d_hole: 穴のサイズ（"幅x長さ"形式）
        pal1, pal2, pal3: 座標系を定義する3点

    Returns:
        IfcBooleanResultエンティティ（UNION演算後のソリッド）
    """
    atc = d_hole.split("x")
    width_hole = float(atc[0]) / 2
    len_hole = float(atc[1]) / 2

    if type_hole == "HV":
        ps_arc = [pbase_hole[0] + width_hole, pbase_hole[1] + len_hole - width_hole]
        pe_arc = [pbase_hole[0] - width_hole, pbase_hole[1] + len_hole - width_hole]
        pc_arc = [pbase_hole[0], pbase_hole[1] + len_hole - width_hole]
        points_arc1 = DefMath.devide_arc_to_points_polyline(ps_arc, pe_arc, pc_arc, 10)
        points_arc1.reverse()

        ps_arc = [pbase_hole[0] - width_hole, pbase_hole[1] - (len_hole - width_hole)]
        pe_arc = [pbase_hole[0] + width_hole, pbase_hole[1] - (len_hole - width_hole)]
        pc_arc = [pbase_hole[0], pbase_hole[1] - (len_hole - width_hole)]
        points_arc2 = DefMath.devide_arc_to_points_polyline(ps_arc, pe_arc, pc_arc, 10)
        points_arc2.reverse()

        points = points_arc1 + points_arc2

        solid_hole1 = DefIFC.extrude_profile_and_align(ifc_file, points, 100, pal1, pal2, pal3)
        solid_hole2 = DefIFC.extrude_profile_and_align(ifc_file, points, -100, pal1, pal2, pal3)

        solid_hole = ifc_file.createIfcBooleanResult("UNION", solid_hole1, solid_hole2)

    return solid_hole


def Draw_Solid_CutOut(
    ifc_all, Member_data, Mem_Rib_data, ref_cutout, face_cutout, ThickA_PA, ThickF_PA, pbase, pdir, p1_3d, p2_3d, p3_3d
):
    """
    切り欠きを描画する

    Args:
        ifc_all: (ifc_file, bridge_span, geom_context)のタプル
        Member_data: メンバーデータ
        Mem_Rib_data: リブメンバーデータ
        ref_cutout: 参照切り欠き名称
        face_cutout: 切り欠き面（"L", "R", "T", "B"）
        ThickA_PA: A側の厚さ
        ThickF_PA: F側の厚さ
        pbase: 基準点
        pdir: 方向点
        p1_3d, p2_3d, p3_3d: 座標系を定義する3点

    Returns:
        IfcBooleanResultエンティティ（切り欠きソリッド）
    """
    ifc_file, bridge_span, geom_context = ifc_all
    for cutout in Member_data:
        if cutout["Name"] == ref_cutout:
            infor = cutout["Infor"]
            lengths = cutout["Length"]
            widths = cutout["Width"]
            radius = cutout["Radius"]
            stiffs = cutout["Stiff"]
            break

    result_hole = infor, lengths, widths, radius, stiffs

    if infor[0] == "Type1":
        pal1_hole = pbase.copy()
        normal_p1p2p3 = DefMath.Normal_vector(p1_3d, p2_3d, p3_3d)
        pal2_hole = pal1_hole + 100 * normal_p1p2p3
        pal3_hole = DefMath.rotate_point_around_axis(pal1_hole, pal2_hole, pdir, 90)

        p0 = [0, 0]
        pt = [0, lengths[0]]
        pb = [0, -lengths[1]]
        ptl = [-widths[0], lengths[0]]
        ptr = [widths[1], lengths[0]]
        pbl = [-widths[0], -lengths[1]]
        pbr = [widths[1], -lengths[1]]

        ps_arc = [-(widths[0] - radius[0]), lengths[0]]
        pe_arc = [-widths[0], lengths[0] - radius[0]]
        pc_arc = [-(widths[0] - radius[0]), lengths[0] - radius[0]]
        points_arc1 = DefMath.devide_arc_to_points_polyline(ps_arc, pe_arc, pc_arc, 20)
        points_arc1.reverse()

        ps_arc = [-widths[0], -(lengths[0] - radius[1])]
        pe_arc = [-(widths[0] - radius[1]), -lengths[0]]
        pc_arc = [-(widths[0] - radius[1]), -(lengths[0] - radius[1])]
        points_arc2 = DefMath.devide_arc_to_points_polyline(ps_arc, pe_arc, pc_arc, 20)
        points_arc2.reverse()

        ps_arc = [(widths[0] - radius[2]), -lengths[0]]
        pe_arc = [widths[0], -(lengths[0] - radius[2])]
        pc_arc = [(widths[0] - radius[2]), -(lengths[0] - radius[2])]
        points_arc3 = DefMath.devide_arc_to_points_polyline(ps_arc, pe_arc, pc_arc, 20)
        points_arc3.reverse()

        ps_arc = [widths[0], lengths[0] - radius[3]]
        pe_arc = [(widths[0] - radius[3]), lengths[0]]
        pc_arc = [(widths[0] - radius[3]), lengths[0] - radius[3]]
        points_arc4 = DefMath.devide_arc_to_points_polyline(ps_arc, pe_arc, pc_arc, 20)
        points_arc4.reverse()

        points = points_arc1 + points_arc4 + points_arc3 + points_arc2

        solid_hole1 = DefIFC.extrude_profile_and_align(ifc_file, points, 100, pal1_hole, pal2_hole, pal3_hole)
        solid_hole2 = DefIFC.extrude_profile_and_align(ifc_file, points, -100, pal1_hole, pal2_hole, pal3_hole)

        solid_hole = ifc_file.createIfcBooleanResult("UNION", solid_hole1, solid_hole2)

        if stiffs:
            p1b = [0, 0, 0]
            p2b = [0, -1, 0]
            p3b = [1, 0, 0]
            p1a = pbase
            p2a = pdir
            p3a = p2_3d

            distmods, namestiffs = stiffs
            distmodT, distmodB, distmodL, distmodR = distmods
            namestiffT, namestiffB, namestiffL, namestiffR = namestiffs

            if not pd.isnull(namestiffT) and namestiffT != "N":
                p1mod_2d, p2mod_2d = DefMath.Offset_Line(ptl, ptr, distmodT)
                p1mod = [p1mod_2d[0], p1mod_2d[1], 0]
                p2mod = [p2mod_2d[0], p2mod_2d[1], 0]

                p1mod = DefMath.Transform_point_face2face(p1mod, p1b, p2b, p3b, p1a, p2a, p3a)
                p2mod = DefMath.Transform_point_face2face(p2mod, p1b, p2b, p3b, p1a, p2a, p3a)

                Draw_Stiff_CutOut(
                    ifc_all,
                    Mem_Rib_data,
                    namestiffT,
                    face_cutout,
                    p1mod,
                    p2mod,
                    ThickA_PA,
                    ThickF_PA,
                    p1_3d,
                    p2_3d,
                    p3_3d,
                )

            if not pd.isnull(namestiffB) and namestiffB != "N":
                p1mod_2d, p2mod_2d = DefMath.Offset_Line(pbr, pbl, distmodB)
                p1mod = [p2mod_2d[0], p2mod_2d[1], 0]
                p2mod = [p1mod_2d[0], p1mod_2d[1], 0]

                p1mod = DefMath.Transform_point_face2face(p1mod, p1b, p2b, p3b, p1a, p2a, p3a)
                p2mod = DefMath.Transform_point_face2face(p2mod, p1b, p2b, p3b, p1a, p2a, p3a)

                Draw_Stiff_CutOut(
                    ifc_all,
                    Mem_Rib_data,
                    namestiffB,
                    face_cutout,
                    p1mod,
                    p2mod,
                    ThickA_PA,
                    ThickF_PA,
                    p1_3d,
                    p2_3d,
                    p3_3d,
                )

            if not pd.isnull(namestiffL) and namestiffL != "N":
                p1mod_2d, p2mod_2d = DefMath.Offset_Line(pbl, ptl, distmodL)
                p1mod = [p2mod_2d[0], p2mod_2d[1], 0]
                p2mod = [p1mod_2d[0], p1mod_2d[1], 0]

                p1mod = DefMath.Transform_point_face2face(p1mod, p1b, p2b, p3b, p1a, p2a, p3a)
                p2mod = DefMath.Transform_point_face2face(p2mod, p1b, p2b, p3b, p1a, p2a, p3a)

                Draw_Stiff_CutOut(
                    ifc_all,
                    Mem_Rib_data,
                    namestiffL,
                    face_cutout,
                    p1mod,
                    p2mod,
                    ThickA_PA,
                    ThickF_PA,
                    p1_3d,
                    p2_3d,
                    p3_3d,
                )

            if not pd.isnull(namestiffR) and namestiffR != "N":
                p1mod_2d, p2mod_2d = DefMath.Offset_Line(ptr, pbr, distmodR)
                p1mod = [p1mod_2d[0], p1mod_2d[1], 0]
                p2mod = [p2mod_2d[0], p2mod_2d[1], 0]

                p1mod = DefMath.Transform_point_face2face(p1mod, p1b, p2b, p3b, p1a, p2a, p3a)
                p2mod = DefMath.Transform_point_face2face(p2mod, p1b, p2b, p3b, p1a, p2a, p3a)

                Draw_Stiff_CutOut(
                    ifc_all,
                    Mem_Rib_data,
                    namestiffR,
                    face_cutout,
                    p1mod,
                    p2mod,
                    ThickA_PA,
                    ThickF_PA,
                    p1_3d,
                    p2_3d,
                    p3_3d,
                )

    return solid_hole


def Draw_Stiff_CutOut(
    ifc_all, Mem_Rib_data, ref_stiff, face_stiff, p1_stiff, p2_stiff, ThickA_PA, ThickF_PA, p1_3d, p2_3d, p3_3d
):
    """
    補剛材の切り欠きを描画する

    Args:
        ifc_all: (ifc_file, bridge_span, geom_context)のタプル
        Mem_Rib_data: リブメンバーデータ
        ref_stiff: 参照補剛材名称
        face_stiff: 補剛材面（"L", "R"）
        p1_stiff, p2_stiff: 補剛材の2点
        ThickA_PA: A側の厚さ
        ThickF_PA: F側の厚さ
        p1_3d, p2_3d, p3_3d: 座標系を定義する3点

    Returns:
        IfcBooleanResultエンティティ（切り欠きソリッド）
    """
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
    extendL_rib, extendR_rib, extendT_rib, extendB_rib = extend
    corner1, corner2, corner3, corner4 = corner
    # ------------------------------------------------------------
    arface_stiff = []
    if face_stiff == "ALL":
        arface_stiff = ["L", "R"]
    else:
        arface_stiff = [face_stiff]

    for side in arface_stiff:
        if side == "A" or side == "R" or side == "T":
            P1Mod = p1_stiff + ThickA_PA * normal_p1p2p3
            P2Mod = p2_stiff + ThickA_PA * normal_p1p2p3
            if side == "R":
                P1Mod = p1_stiff + ThickF_PA * normal_p1p2p3
                P2Mod = p2_stiff + ThickF_PA * normal_p1p2p3
        elif side == "F" or side == "L" or side == "B":
            P1Mod = p1_stiff - ThickF_PA * normal_p1p2p3
            P2Mod = p2_stiff - ThickF_PA * normal_p1p2p3
            if side == "L":
                P1Mod = p1_stiff - ThickA_PA * normal_p1p2p3
                P2Mod = p2_stiff - ThickA_PA * normal_p1p2p3

        if DefMath.is_number(extendL_rib) == True:
            p = DefMath.Point_on_line(P1Mod, P2Mod, -extendL_rib)
            P1Mod = p

        if DefMath.is_number(extendR_rib) == True:
            p = DefMath.Point_on_line(P2Mod, P1Mod, -extendR_rib)
            P2Mod = p

        p1al = P2Mod.copy()
        if side == "A" or side == "R" or side == "T":
            p3al = p1al + 100 * normal_p1p2p3
            p2al = DefMath.Offset_point(P2Mod, P1Mod, p3al, -100)

            P3Mod = P1Mod + height_rib * normal_p1p2p3
            P4Mod = P2Mod + height_rib * normal_p1p2p3
        elif side == "F" or side == "L" or side == "B":
            p3al = p1al - 100 * normal_p1p2p3
            p2al = DefMath.Offset_point(P2Mod, P1Mod, p3al, -100)

            P3Mod = P1Mod - height_rib * normal_p1p2p3
            P4Mod = P2Mod - height_rib * normal_p1p2p3
        # Draw_3DSolid_VstiffはDefStiffener.pyに移動予定（一時的にDefBridgeからインポート）
        # TODO: DefStiffener.py作成後に修正
        # 循環参照を避けるため、関数内でインポート
        from src.bridge_json_to_ifc.ifc_utils_new.core import DefBridge

        Solid_Vstiff = DefBridge.Draw_3DSolid_Vstiff(
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
        DefIFC.Add_shape_representation_in_Beam(ifc_file, bridge_span, shape_representation, ref_stiff)

    return None


# -----------------Bearing（支承）----------------------------------
def Calculate_Bearing(ifc_all, Senkei_data, MainPanel_data, infor_bearing):
    """
    下フランジ下面に直方体の支承ブロックを配置する

    Args:
        ifc_all: (ifc_file, bridge_span, geom_context)
        Senkei_data: 線形データ
        MainPanel_data: 主桁パネルデータ
        infor_bearing: (
            name_bearing, girder_bearing, section_bearing, type_bearing,
            shape_bearing, line_bearing, offset_z, offset_y,
            local_offset_x, local_offset_y
        )
    """
    ifc_file, bridge_span, geom_context = ifc_all
    (
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
    ) = infor_bearing

    _log_print(f"  [Bearing] ========== 処理開始: {name_bearing} ==========")
    _log_print(
        f"  [Bearing] Type={type_bearing}, Girder={girder_bearing}, Section={section_bearing}, Line={line_bearing}"
    )
    _log_print(
        f"  [Bearing] OffsetZ={offset_z}mm, OffsetY={offset_y}mm, LocalOffset=({local_offset_x},{local_offset_y})mm"
    )

    # 1. 下フランジの線形と断面から位置を取得
    _log_print(f"  [Bearing] Load_Coordinate_Point呼び出し: Line={line_bearing}, Section={section_bearing}")
    bearing_point = DefBridgeUtils.Load_Coordinate_Point(Senkei_data, line_bearing, section_bearing)
    if bearing_point is None:
        _log_print(f"  [Bearing] エラー: 支承位置の取得に失敗: Line={line_bearing}, Section={section_bearing}")
        raise ValueError(f"支承位置の取得に失敗: Line={line_bearing}, Section={section_bearing}")

    _log_print(f"  [Bearing] Load_Coordinate_Point結果: bearing_point={bearing_point}")
    _log_print(f"  [Bearing] bearing_point型: {type(bearing_point)}")
    if isinstance(bearing_point, (list, tuple)) and len(bearing_point) >= 3:
        _log_print(
            f"  [Bearing] bearing_point[0]={bearing_point[0]:.2f}, [1]={bearing_point[1]:.2f}, [2]={bearing_point[2]:.2f}"
        )

    # 2. 下フランジの厚みを取得して、下面位置を計算
    # 下フランジパネルを検索（例: G1B1LF）
    panel_data = None
    for panel in MainPanel_data:
        panel_name = panel.get("Name", "")
        panel_type = panel.get("Type", {})
        if panel_name.startswith(girder_bearing) and panel_type.get("TypePanel") == "LF":
            panel_data = panel
            break

    if panel_data is None:
        raise ValueError(f"下フランジパネルが見つかりません: Girder={girder_bearing}")

    material = panel_data.get("Material", {})
    thick1 = float(material.get("Thick1", 0))
    thick2 = float(material.get("Thick2", 0))
    split_thickness = material.get("SplitThickness", False)

    # 下フランジのeffective_Thick2を計算（DefBridge.pyと同じロジック）
    effective_Thick1 = thick1
    effective_Thick2 = thick2
    if not split_thickness:
        # SplitThicknessがfalseの場合、LFはThick2のみ使用（Thick1は無視）
        effective_Thick1 = 0

    _log_print(
        f"  [Bearing] 下フランジパネル: {panel_data.get('Name', 'Unknown')}, Thick1={thick1}mm, Thick2={thick2}mm, SplitThickness={split_thickness}"
    )
    _log_print(f"  [Bearing] effective_Thick1={effective_Thick1}mm, effective_Thick2={effective_Thick2}mm")

    # 下フランジの下面位置を計算
    # DefBridge.pyでは、arCoordLines_Out_off1 = Offset_Face(arCoordLines_Out, -effective_Thick2) が下面
    # 下フランジは水平なので、中心線から-effective_Thick2だけ下がった位置が下面
    # bearing_pointは中心線上の点なので、bearing_point[2] - effective_Thick2 が下面のZ座標
    bearing_bottom_z = bearing_point[2] - effective_Thick2 + offset_z
    bearing_x = bearing_point[0] + float(local_offset_x)
    bearing_y = bearing_point[1] + offset_y + float(local_offset_y)

    _log_print(f"  [Bearing] 下フランジ中心線Z座標: {bearing_point[2]:.2f}mm")
    _log_print(f"  [Bearing] 下フランジ下面Z座標: {bearing_bottom_z:.2f}mm (中心線から{effective_Thick2}mm下)")

    length = float(shape_bearing.get("Length", 0))
    width = float(shape_bearing.get("Width", 0))
    height = float(shape_bearing.get("Height", 0))
    if length <= 0 or width <= 0 or height <= 0:
        raise ValueError(f"支承形状の寸法が不正です: Length={length}, Width={width}, Height={height}")

    block_top_z = bearing_bottom_z
    block_bottom_z = block_top_z - height
    half_l = length / 2.0
    half_w = width / 2.0

    p1t = [bearing_x - half_l, bearing_y - half_w, block_top_z]
    p2t = [bearing_x + half_l, bearing_y - half_w, block_top_z]
    p3t = [bearing_x + half_l, bearing_y + half_w, block_top_z]
    p4t = [bearing_x - half_l, bearing_y + half_w, block_top_z]

    p1b = [bearing_x - half_l, bearing_y - half_w, block_bottom_z]
    p2b = [bearing_x + half_l, bearing_y - half_w, block_bottom_z]
    p3b = [bearing_x + half_l, bearing_y + half_w, block_bottom_z]
    p4b = [bearing_x - half_l, bearing_y + half_w, block_bottom_z]

    _log_print(f"  [Bearing] 直方体寸法: L={length}mm, W={width}mm, H={height}mm")
    _log_print(f"  [Bearing] ブロック上面Z={block_top_z:.2f}mm, 下面Z={block_bottom_z:.2f}mm")

    solid_bearing = DefIFC.Create_brep_from_box_8points(ifc_file, p1t, p2t, p3t, p4t, p1b, p2b, p3b, p4b)

    color_map = {"Rubber": (120.0, 120.0, 120.0), "Movable": (90.0, 140.0, 210.0), "Fixed": (190.0, 130.0, 80.0)}
    color_rgb = color_map.get(type_bearing, (150.0, 150.0, 150.0))
    color_style = DefIFC.create_color(ifc_file, *color_rgb)
    styled_item = ifc_file.createIfcStyledItem(Item=solid_bearing, Styles=[color_style])
    shape_representation = ifc_file.createIfcShapeRepresentation(
        ContextOfItems=geom_context, RepresentationIdentifier="Body", RepresentationType="Brep", Items=[solid_bearing]
    )
    metadata = {
        "ObjectType": f"{type_bearing} Bearing",
        "PredefinedType": "USERDEFINED",
        "Tag": f"{girder_bearing}-{section_bearing}",
        "PropertySetName": "Pset_BearingCommon",
        "Properties": {
            "BearingType": type_bearing,
            "Girder": girder_bearing,
            "Section": section_bearing,
            "Length": length,
            "Width": width,
            "Height": height,
        },
    }
    DefIFC.Add_shape_representation_in_Beam(ifc_file, bridge_span, shape_representation, (name_bearing, metadata))

    _log_print(f"  [Bearing] ========== {name_bearing} 生成完了 ==========")

    return None


# -----------------Guardrail（高欄）----------------------------------
def Calculate_Guardrail(ifc_all, Senkei_data, MainPanel_data, infor_guardrail):
    """
    高欄（Guardrail）を計算して描画する
    床版の左右の端に沿って配置する

    Args:
        ifc_all: (ifc_file, bridge_span, geom_context)のタプル
        Senkei_data: 線形データ
        MainPanel_data: メインパネルデータ（上フランジの厚みを取得するため）
        infor_guardrail: 高欄情報（名称、床版の線、断面、左オーバーハング、右オーバーハング、左高欄の幅・高さ、右高欄の幅・高さ、左高欄の分割情報、右高欄の分割情報）
    """
    ifc_file, bridge_span, geom_context = ifc_all
    (
        name_guardrail,
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
    ) = infor_guardrail

    secS_shouban = sec_shouban[0]  # 最初の断面（開始点）
    secE_shouban = sec_shouban[
        -1
    ]  # 最後の断面（終了点）- 修正: sec_shouban[1]からsec_shouban[-1]に変更（中間点C1が含まれていても正しく動作）

    idxS = -1
    idxE = -1
    for idx, point in enumerate(Senkei_data[0]["Point"]):
        if point["Name"] == secS_shouban:
            idxS = idx
            break

    for idx, point in enumerate(Senkei_data[0]["Point"]):
        if point["Name"] == secE_shouban:
            idxE = idx
            break

    if idxS == -1 or idxE == -1:
        _log_print(
            f"    [Guardrail] 警告: 断面 '{secS_shouban}' または '{secE_shouban}' がSenkeiデータに見つかりません。"
        )
        return

    names_range = [point["Name"] for point in Senkei_data[0]["Point"][idxS : idxE + 1]]

    # 上フランジの実際の厚みを取得（床版の位置計算に使用）
    flange_thickness = 12.0  # デフォルト値
    uf_panel = None
    for panel in MainPanel_data:
        if panel.get("Type", {}).get("TypePanel") == "UF":
            uf_panel = panel
            mat_panel = panel.get("Material", {})
            thick1 = mat_panel.get("Thick1", 0)
            thick2 = mat_panel.get("Thick2", 0)
            split_thickness = mat_panel.get("SplitThickness", False)

            if not split_thickness:
                flange_thickness = thick1
            else:
                flange_thickness = thick1 + thick2
            break

    # 床版の座標を取得（上フランジのラインから）
    Coord_Shouban_bottom = DefBridgeUtils.Load_Coordinate_Panel(Senkei_data, line_shouban, names_range)

    if uf_panel:
        uf_name = uf_panel.get("Name", "")
        ExtendL = uf_panel.get("Expand", {}).get("E1", 0)
        ExtendR = uf_panel.get("Expand", {}).get("E2", 0)
        ExtendT = uf_panel.get("Expand", {}).get("E3", 0)
        ExtendB = uf_panel.get("Expand", {}).get("E4", 0)
        Coord_Shouban_bottom = DefBridgeUtils.Calculate_Extend(
            MainPanel_data, Senkei_data, uf_name, Coord_Shouban_bottom, ExtendL, ExtendR, ExtendT, ExtendB
        )

        # 上フランジの上面位置を計算
        if Coord_Shouban_bottom and len(Coord_Shouban_bottom) > 0:
            Coord_Shouban_top = DefMath.Offset_Face(Coord_Shouban_bottom, flange_thickness)
            if Coord_Shouban_top and len(Coord_Shouban_top) > 0:
                Coord_Shouban_bottom = Coord_Shouban_top

    if not Coord_Shouban_bottom or len(Coord_Shouban_bottom) < 4:
        _log_print("    [Guardrail] 警告: 床版の座標データが取得できませんでした。")
        return

    deck_thickness = 200.0  # 床版の厚み（mm）
    z_deck_top = Coord_Shouban_bottom[0][0][2] + flange_thickness + deck_thickness  # 床版の上面Z座標

    _log_print(f"    [Guardrail] 高欄生成開始: {name_guardrail}")
    _log_print(f"    [Guardrail] 床版上面Z座標: {z_deck_top:.2f}mm")

    # 左端の高欄を生成（オーバーハングの端に配置）
    if left_width > 0 and left_height > 0:
        _log_print(f"    [Guardrail] 左高欄: 幅={left_width}mm, 高さ={left_height}mm, 分割={left_break}")
        first_polyline = Coord_Shouban_bottom[0]  # 左端のポリライン（例：TG1L）
        # オーバーハングを考慮：左端はY座標からoverhang_leftを引く
        # 高欄のエッジを床版のエッジに合わせるため、高欄の幅の半分だけ内側に移動
        half_width_left = left_width / 2.0
        y_offset_left = -overhang_left + half_width_left
        _create_guardrail_along_polyline(
            ifc_file,
            bridge_span,
            geom_context,
            first_polyline,
            left_width,
            left_height,
            z_deck_top,
            y_offset_left,
            f"{name_guardrail}_Left",
            left_break,
        )

    # 右端の高欄を生成（オーバーハングの端に配置）
    if right_width > 0 and right_height > 0:
        _log_print(f"    [Guardrail] 右高欄: 幅={right_width}mm, 高さ={right_height}mm, 分割={right_break}")
        if len(Coord_Shouban_bottom) > 2:
            third_polyline = Coord_Shouban_bottom[2]  # 右端のポリライン（例：TG3R）
            # オーバーハングを考慮：右端はY座標にoverhang_rightを足す
            # 高欄のエッジを床版のエッジに合わせるため、高欄の幅の半分だけ内側に移動
            half_width_right = right_width / 2.0
            y_offset_right = overhang_right - half_width_right
            _create_guardrail_along_polyline(
                ifc_file,
                bridge_span,
                geom_context,
                third_polyline,
                right_width,
                right_height,
                z_deck_top,
                y_offset_right,
                f"{name_guardrail}_Right",
                right_break,
            )

    _log_print(f"    [Guardrail] 高欄生成完了: {name_guardrail}")


def _create_guardrail_along_polyline(
    ifc_file, bridge_span, geom_context, polyline, width, height, z_deck_top, y_offset, name_guardrail, break_info=False
):
    """
    ポリラインに沿って高欄を生成する

    Args:
        ifc_file: IFCファイルオブジェクト
        bridge_span: 橋梁スパン
        geom_context: 幾何コンテキスト
        polyline: ポリラインの点リスト
        width: 高欄の幅（mm）
        height: 高欄の高さ（mm）
        z_deck_top: 床版の上面Z座標（mm）
        y_offset: Y方向のオフセット（mm、左端は負、右端は正）
        name_guardrail: 高欄の名前
        break_info: 分割情報（False=分割しない、数値=等分割数、配列=分割長さの配列）
    """
    if not polyline or len(polyline) < 2:
        _log_print("    [Guardrail] 警告: ポリラインの点が不足しています。")
        return

    # 分割しない場合（break_infoがFalseまたはNone）
    if not break_info or break_info is False:
        # ポリライン全体を1つのソリッドとして生成
        _create_single_guardrail_solid(
            ifc_file, bridge_span, geom_context, polyline, width, height, z_deck_top, y_offset, name_guardrail
        )
        return

    # 分割する場合
    # break_infoが数値の場合は等分割、配列の場合は指定された長さで分割
    if isinstance(break_info, (int, float)):
        # 等分割
        num_segments = int(break_info)
        if num_segments <= 0:
            num_segments = 1

        # ポリラインの全長を計算（3D距離）
        total_length = 0.0
        segment_lengths = []
        cumulative_lengths = [0.0]  # 累積距離（最初の点は0）

        for i in range(len(polyline) - 1):
            p1 = polyline[i]
            p2 = polyline[i + 1]
            dx = p2[0] - p1[0]
            dy = p2[1] - p1[1]
            dz = p2[2] - p1[2]
            seg_len = np.sqrt(dx**2 + dy**2 + dz**2)
            segment_lengths.append(seg_len)
            total_length += seg_len
            cumulative_lengths.append(total_length)

        segment_length = total_length / num_segments
        _log_print(
            f"    [Guardrail] 等分割: {num_segments}セグメント, 全長={total_length:.2f}mm, セグメント長={segment_length:.2f}mm"
        )

        # 等分割でセグメントを生成
        for seg_idx in range(num_segments):
            target_start = seg_idx * segment_length
            target_end = (seg_idx + 1) * segment_length
            if seg_idx == num_segments - 1:
                target_end = total_length  # 最後のセグメントは端まで

            # 開始点と終了点を見つける
            start_point = _find_point_on_polyline(polyline, cumulative_lengths, target_start)
            end_point = _find_point_on_polyline(polyline, cumulative_lengths, target_end)

            if start_point and end_point:
                _create_guardrail_segment(
                    ifc_file,
                    bridge_span,
                    geom_context,
                    start_point,
                    end_point,
                    width,
                    height,
                    z_deck_top,
                    y_offset,
                    f"{name_guardrail}_Seg{seg_idx + 1}",
                )

    elif isinstance(break_info, list):
        # 指定された長さで分割
        _log_print(f"    [Guardrail] 指定長さで分割: {break_info}")

        # ポリラインの全長を計算（3D距離）
        total_length = 0.0
        segment_lengths = []
        cumulative_lengths = [0.0]

        for i in range(len(polyline) - 1):
            p1 = polyline[i]
            p2 = polyline[i + 1]
            dx = p2[0] - p1[0]
            dy = p2[1] - p1[1]
            dz = p2[2] - p1[2]
            seg_len = np.sqrt(dx**2 + dy**2 + dz**2)
            segment_lengths.append(seg_len)
            total_length += seg_len
            cumulative_lengths.append(total_length)

        # 指定された長さで分割
        current_length = 0.0
        seg_idx = 0
        for break_len in break_info:
            target_start = current_length
            target_end = current_length + float(break_len)
            if target_end > total_length:
                target_end = total_length

            start_point = _find_point_on_polyline(polyline, cumulative_lengths, target_start)
            end_point = _find_point_on_polyline(polyline, cumulative_lengths, target_end)

            if start_point and end_point:
                _create_guardrail_segment(
                    ifc_file,
                    bridge_span,
                    geom_context,
                    start_point,
                    end_point,
                    width,
                    height,
                    z_deck_top,
                    y_offset,
                    f"{name_guardrail}_Seg{seg_idx + 1}",
                )

            current_length = target_end
            seg_idx += 1
            if current_length >= total_length:
                break

    elif isinstance(break_info, list):
        # 指定された長さで分割
        _log_print(f"    [Guardrail] 指定長さで分割: {break_info}")
        # 簡略化：各点間でセグメントを作成（既存のロジックを使用）
        for i in range(len(polyline) - 1):
            _create_guardrail_segment(
                ifc_file,
                bridge_span,
                geom_context,
                polyline[i],
                polyline[i + 1],
                width,
                height,
                z_deck_top,
                y_offset,
                f"{name_guardrail}_Seg{i + 1}",
            )

    else:
        # その他の場合は、各点間でセグメントを作成（既存のロジック）
        for i in range(len(polyline) - 1):
            _create_guardrail_segment(
                ifc_file,
                bridge_span,
                geom_context,
                polyline[i],
                polyline[i + 1],
                width,
                height,
                z_deck_top,
                y_offset,
                f"{name_guardrail}_Seg{i + 1}",
            )


def _find_point_on_polyline(polyline, cumulative_lengths, target_length):
    """
    ポリライン上で指定された累積距離に対応する点を見つける

    Args:
        polyline: ポリラインの点リスト
        cumulative_lengths: 各点までの累積距離のリスト
        target_length: 目標の累積距離

    Returns:
        点の座標 [x, y, z]、見つからない場合はNone
    """
    if target_length <= 0:
        return polyline[0] if len(polyline) > 0 else None

    if target_length >= cumulative_lengths[-1]:
        return polyline[-1] if len(polyline) > 0 else None

    # どのセグメントに含まれるかを見つける
    for i in range(len(cumulative_lengths) - 1):
        if cumulative_lengths[i] <= target_length < cumulative_lengths[i + 1]:
            # このセグメント内で線形補間
            p1 = polyline[i]
            p2 = polyline[i + 1]
            seg_start_len = cumulative_lengths[i]
            seg_end_len = cumulative_lengths[i + 1]
            seg_len = seg_end_len - seg_start_len

            if seg_len < 0.001:
                return p1

            ratio = (target_length - seg_start_len) / seg_len
            x = p1[0] + (p2[0] - p1[0]) * ratio
            y = p1[1] + (p2[1] - p1[1]) * ratio
            z = p1[2] + (p2[2] - p1[2]) * ratio
            return [x, y, z]

    return None


def _create_single_guardrail_solid(
    ifc_file, bridge_span, geom_context, polyline, width, height, z_deck_top, y_offset, name_guardrail
):
    """
    ポリライン全体を1つのソリッドとして高欄を生成する（分割しない）
    """
    if len(polyline) < 2:
        return

    # ポリラインの最初と最後の点を使用
    p_start = polyline[0]
    p_end = polyline[-1]

    _create_guardrail_segment(
        ifc_file, bridge_span, geom_context, p_start, p_end, width, height, z_deck_top, y_offset, name_guardrail
    )


def _create_guardrail_segment(
    ifc_file, bridge_span, geom_context, p1, p2, width, height, z_deck_top, y_offset, segment_name
):
    """
    2点間で高欄のセグメントを生成する

    Args:
        ifc_file: IFCファイルオブジェクト
        bridge_span: 橋梁スパン
        geom_context: 幾何コンテキスト
        p1: 開始点 [x, y, z]
        p2: 終了点 [x, y, z]
        width: 高欄の幅（mm）
        height: 高欄の高さ（mm）
        z_deck_top: 床版の上面Z座標（mm）
        y_offset: Y方向のオフセット（mm）
        segment_name: セグメントの名前
    """
    # 高欄の中心線の座標（床版の端に沿う）
    x1 = p1[0]
    y1 = p1[1] + y_offset
    z1 = z_deck_top

    x2 = p2[0]
    y2 = p2[1] + y_offset
    z2 = z_deck_top

    # 高欄の方向ベクトルを計算
    dx = x2 - x1
    dy = y2 - y1
    dz = z2 - z1
    length = np.sqrt(dx**2 + dy**2 + dz**2)

    if length < 0.001:  # 点が重なっている場合はスキップ
        return

    # 高欄の幅方向（Y方向）と高さ方向（Z方向）を定義
    # 高欄は床版の端に沿って配置され、幅はY方向、高さはZ方向
    half_width = width / 2.0

    # セグメントの方向ベクトルを正規化
    dir_x = dx / length
    dir_y = dy / length
    dir_z = dz / length

    # Y方向の単位ベクトル（高欄の幅方向）
    # 床版の端に垂直な方向を計算（X-Y平面での法線）
    if abs(dir_x) < 0.001:  # X方向が小さい場合（ほぼY方向）
        perp_y = 1.0
        perp_x = 0.0
    else:
        # X-Y平面での法線ベクトル
        perp_x = -dir_y
        perp_y = dir_x
        perp_len = np.sqrt(perp_x**2 + perp_y**2)
        if perp_len > 0.001:
            perp_x /= perp_len
            perp_y /= perp_len

    # 高欄の8点を計算
    # 下面の4点
    p1b = [x1 + perp_x * half_width, y1 + perp_y * half_width, z1]
    p2b = [x1 - perp_x * half_width, y1 - perp_y * half_width, z1]
    p3b = [x2 - perp_x * half_width, y2 - perp_y * half_width, z2]
    p4b = [x2 + perp_x * half_width, y2 + perp_y * half_width, z2]

    # 上面の4点
    p1t = [x1 + perp_x * half_width, y1 + perp_y * half_width, z1 + height]
    p2t = [x1 - perp_x * half_width, y1 - perp_y * half_width, z1 + height]
    p3t = [x2 - perp_x * half_width, y2 - perp_y * half_width, z2 + height]
    p4t = [x2 + perp_x * half_width, y2 + perp_y * half_width, z2 + height]

    # 直方体ソリッドを生成
    solid_guardrail = DefIFC.Create_brep_from_box_8points(ifc_file, p1t, p2t, p3t, p4t, p1b, p2b, p3b, p4b)

    # 色を設定（高欄は通常、明るい色）
    color_style = DefIFC.create_color(ifc_file, 200.0, 200.0, 200.0)  # ライトグレー
    styled_item = ifc_file.createIfcStyledItem(Item=solid_guardrail, Styles=[color_style])

    # 形状表現を作成
    shape_representation = ifc_file.createIfcShapeRepresentation(
        ContextOfItems=geom_context, RepresentationIdentifier="Body", RepresentationType="Brep", Items=[solid_guardrail]
    )

    # IFCエンティティとして追加
    DefIFC.Add_shape_representation_in_Beam(ifc_file, bridge_span, shape_representation, segment_name)

    _log_print(f"    [Guardrail] セグメント生成: {segment_name}, 長さ={length:.2f}mm")
