#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
対話型JSON生成ツール
鋼橋IFCモデル生成用のJSONファイルを対話的に作成・編集するツール

使用方法:
    python interactive_json_builder.py
"""

import json


class JSONBuilder:
    """対話的にJSONファイルを構築するクラス"""

    def __init__(self):
        self.data = {
            "Infor": {},
            "Senkei": [],
            "Calculate": [],
            "MainPanel": [],
            "SubPanel": [],
            "Taikeikou": [],
            "Yokokou": [],
            "Yokokou_LateralBracing": [],
            "Shouban": [],
            "Bearing": [],
            "Guardrail": {},
            "MemberSPL": [],
            "MemberRib": [],
            "MemberData": [],
        }

    def print_section(self, title: str):
        """セクションタイトルを表示"""
        print("\n" + "=" * 60)
        print(f"  {title}")
        print("=" * 60)

    def input_str(self, prompt: str, default: str = "") -> str:
        """文字列入力を取得"""
        if default:
            response = input(f"{prompt} [{default}]: ").strip()
            return response if response else default
        else:
            return input(f"{prompt}: ").strip()

    def input_int(self, prompt: str, default: int | None = None) -> int:
        """整数入力を取得"""
        while True:
            if default is not None:
                response = input(f"{prompt} [{default}]: ").strip()
                if not response:
                    return default
            else:
                response = input(f"{prompt}: ").strip()

            try:
                return int(response)
            except ValueError:
                print("  エラー: 整数を入力してください")

    def input_float(self, prompt: str, default: float | None = None) -> float:
        """浮動小数点入力を取得"""
        while True:
            if default is not None:
                response = input(f"{prompt} [{default}]: ").strip()
                if not response:
                    return default
            else:
                response = input(f"{prompt}: ").strip()

            try:
                return float(response)
            except ValueError:
                print("  エラー: 数値を入力してください")

    def input_yes_no(self, prompt: str, default: bool = True) -> bool:
        """Yes/No入力を取得"""
        default_str = "Y/n" if default else "y/N"
        while True:
            response = input(f"{prompt} [{default_str}]: ").strip().lower()
            if not response:
                return default
            if response in ["y", "yes", "はい"]:
                return True
            elif response in ["n", "no", "いいえ"]:
                return False
            else:
                print("  エラー: Y または N を入力してください")

    def check_existing_data(self, section_key: str, section_name: str) -> bool:
        """
        既存データの有無をチェックし、クリアするかどうかを確認

        Args:
            section_key: データのキー（例: "Shouban", "Taikeikou"）
            section_name: 表示名（例: "床版", "対傾構"）

        Returns:
            True: 処理を続行, False: 戻る（キャンセル）
        """
        existing_data = self.data.get(section_key, [])
        existing_count = len(existing_data) if isinstance(existing_data, list) else (1 if existing_data else 0)

        if existing_count == 0:
            return True  # データがない場合はそのまま続行

        print("\n【既存データの確認】")
        print(f"既存の{section_name}データが {existing_count} 件あります。")
        print("  1. 追加モード（既存データに追加）")
        print("  2. クリア＆新規作成（既存データを削除して最初から）")
        print("  3. 戻る")

        while True:
            choice = input("選択してください [1/2/3, デフォルト: 1]: ").strip()
            if not choice or choice == "1":
                print("  → 追加モードで続行します")
                return True
            elif choice == "2":
                if isinstance(self.data.get(section_key), list):
                    self.data[section_key] = []
                else:
                    self.data[section_key] = {}
                print(f"  → {section_name}データをクリアしました")
                return True
            elif choice == "3":
                print("  → 戻ります")
                return False
            else:
                print("  エラー: 1, 2, または 3 を入力してください")

    def _get_default_deck_lines(self) -> str:
        """
        床版用のデフォルト線形名を既存データから生成

        Returns:
            デフォルト線形名（カンマ区切り文字列）
        """
        senkei_data = self.data.get("Senkei", [])
        if not senkei_data:
            return "TG1L, TG1R, TG3R, TG3L"

        # 上フランジ線形（TGで始まる）を抽出
        tg_lines = []
        for senkei in senkei_data:
            name = senkei.get("Name", "")
            if name.startswith("TG"):
                tg_lines.append(name)

        if not tg_lines:
            return "TG1L, TG1R, TG3R, TG3L"

        # 桁番号ごとに分類
        girder_lines = {}  # {桁番号: {L: 名前, R: 名前, 中央: 名前}}
        import re

        for line in tg_lines:
            # TG1L, TG1R, TG1 などのパターン
            match = re.match(r"TG(\d+)(L|R)?", line)
            if match:
                girder_num = int(match.group(1))
                side = match.group(2) if match.group(2) else "C"  # L, R, または中央(C)
                if girder_num not in girder_lines:
                    girder_lines[girder_num] = {}
                girder_lines[girder_num][side] = line

        if not girder_lines:
            return ", ".join(tg_lines)

        # 最小と最大の桁番号を取得
        min_girder = min(girder_lines.keys())
        max_girder = max(girder_lines.keys())

        # 床版の外周線形を構築（左端のL → 右端のR → 右端のL → 左端のR の順序）
        result_lines = []

        # 左端の桁のL側
        if min_girder in girder_lines:
            if "L" in girder_lines[min_girder]:
                result_lines.append(girder_lines[min_girder]["L"])
            elif "C" in girder_lines[min_girder]:
                result_lines.append(girder_lines[min_girder]["C"])

        # 左端の桁のR側（存在する場合）
        if min_girder in girder_lines and "R" in girder_lines[min_girder]:
            result_lines.append(girder_lines[min_girder]["R"])

        # 右端の桁のR側
        if max_girder != min_girder and max_girder in girder_lines:
            if "R" in girder_lines[max_girder]:
                result_lines.append(girder_lines[max_girder]["R"])
            elif "C" in girder_lines[max_girder]:
                result_lines.append(girder_lines[max_girder]["C"])

        # 右端の桁のL側（存在する場合）
        if max_girder != min_girder and max_girder in girder_lines and "L" in girder_lines[max_girder]:
            result_lines.append(girder_lines[max_girder]["L"])

        if len(result_lines) >= 2:
            return ", ".join(result_lines)
        else:
            return ", ".join(tg_lines)

    def _get_all_sections(self) -> str:
        """
        既存データから全セクション名を取得してデフォルト値を生成
        X座標順にソートして返す

        Returns:
            セクション名（カンマ区切り文字列、X座標順）
        """
        # セクション名とX座標のマッピングを作成
        section_x_coords = {}

        # Senkeiからセクション名とX座標を取得
        senkei_data = self.data.get("Senkei", [])
        for senkei in senkei_data:
            points = senkei.get("Point", [])
            for point in points:
                sec_name = point.get("Sec") or point.get("Name", "")
                if sec_name and sec_name not in section_x_coords:
                    x_coord = point.get("X", 0)
                    section_x_coords[sec_name] = x_coord

        # MainPanelからセクション名を取得（X座標がなければSenkeiから補完）
        mainpanel_data = self.data.get("MainPanel", [])
        for panel in mainpanel_data:
            sec_list = panel.get("Sec", [])
            for sec in sec_list:
                if sec and sec not in section_x_coords:
                    # Senkeiから対応するX座標を探す
                    for senkei in senkei_data:
                        for point in senkei.get("Point", []):
                            point_name = point.get("Sec") or point.get("Name", "")
                            if point_name == sec:
                                section_x_coords[sec] = point.get("X", 0)
                                break
                        if sec in section_x_coords:
                            break
                    # 見つからなければ0を設定
                    if sec not in section_x_coords:
                        section_x_coords[sec] = 0

        if not section_x_coords:
            return "S1, E1"

        # X座標順にソート
        sorted_sections = sorted(section_x_coords.keys(), key=lambda s: section_x_coords[s])
        return ", ".join(sorted_sections)

    def _get_available_girders(self) -> list:
        """
        既存データから利用可能な桁名を取得

        Returns:
            桁名のリスト（例: ["G1", "G2", "G3"]）
        """
        girders = set()

        # Senkeiから桁番号を推測
        senkei_data = self.data.get("Senkei", [])
        import re

        for senkei in senkei_data:
            name = senkei.get("Name", "")
            # TG1L, BG2R などから桁番号を抽出
            match = re.search(r"[TB]G(\d+)", name)
            if match:
                girders.add(f"G{match.group(1)}")

        # MainPanelから桁名を推測
        mainpanel_data = self.data.get("MainPanel", [])
        for panel in mainpanel_data:
            name = panel.get("Name", "")
            # G1_P01_UF などから桁名を抽出
            match = re.match(r"(G\d+)", name)
            if match:
                girders.add(match.group(1))

        if not girders:
            return ["G1", "G2", "G3"]

        return sorted(girders, key=lambda x: int(x[1:]) if x[1:].isdigit() else 0)

    def _get_end_sections(self) -> str:
        """
        端点セクション（S1, E1など）のデフォルト値を取得

        Returns:
            端点セクション名（カンマ区切り文字列）
        """
        sections = set()

        # Senkeiからセクション名を取得
        senkei_data = self.data.get("Senkei", [])
        for senkei in senkei_data:
            points = senkei.get("Point", [])
            for point in points:
                sec = point.get("Sec", "")
                # S または E で始まるセクションを抽出
                if sec.startswith("S") or sec.startswith("E"):
                    sections.add(sec)

        if not sections:
            return "S1, E1"

        # ソート（S1, S2, ..., E2, E1）
        def sort_key(s):
            prefix = s[0] if s else "Z"
            try:
                num = int(s[1:]) if len(s) > 1 else 0
            except ValueError:
                num = 0
            prefix_order = {"S": 0, "E": 2}.get(prefix, 1)
            if prefix == "E":
                return (prefix_order, -num)
            return (prefix_order, num)

        return ", ".join(sorted(sections, key=sort_key))

    def _get_middle_sections(self) -> str:
        """
        中間セクション（C1, C2など）のデフォルト値を取得

        Returns:
            中間セクション名（カンマ区切り文字列）
        """
        sections = set()

        # Senkeiからセクション名を取得
        senkei_data = self.data.get("Senkei", [])
        for senkei in senkei_data:
            points = senkei.get("Point", [])
            for point in points:
                sec = point.get("Sec", "")
                # C で始まるセクションを抽出
                if sec.startswith("C"):
                    sections.add(sec)

        if not sections:
            return "C1"

        # ソート（C1, C2, C3...）
        def sort_key(s):
            try:
                return int(s[1:]) if len(s) > 1 else 0
            except ValueError:
                return 0

        return ", ".join(sorted(sections, key=sort_key))

    def _input_deck_break_settings(self, layer_name: str = "") -> dict:
        """
        床版の分割設定を入力（高度なオプション付き）

        Args:
            layer_name: レイヤー名（表示用）

        Returns:
            Break設定辞書
        """
        prefix = f"【{layer_name}の分割設定】" if layer_name else "【分割設定】"
        print(f"\n{prefix}")

        # Y方向（橋軸直角方向）分割設定
        print("\n【Y方向（橋軸直角方向）分割】")
        print("  1. 等分割: 指定した数で均等に分割")
        print("  2. ウェブ位置分割: 各桁のウェブ上端位置で分割")
        y_mode = self.input_str("Y方向分割モード (1:等分割, 2:ウェブ位置)", "1")

        y_break = {}
        if y_mode == "2":
            # ウェブ位置分割
            default_girders = self._get_available_girders()
            default_girder_str = ", ".join(default_girders)
            print(f"  ※ 利用可能な桁: {default_girder_str}")
            print("  ウェブ位置で分割する桁を指定（カンマ区切り）")
            girder_input = self.input_str("桁名", default_girder_str)
            girders = [g.strip() for g in girder_input.split(",") if g.strip()]
            y_break = {"Type": "webs", "Girders": girders}
            print(f"  → ウェブ位置分割: {girders}")
        else:
            # 等分割
            y_count = self.input_int("Y方向分割数", 3)
            y_break = {"Type": "equal", "Count": y_count}

        # X方向（橋軸方向）分割設定
        print("\n【X方向（橋軸方向）分割】")
        print("  1. 等分割: 指定した数で均等に分割")
        print("  2. セクション位置分割: セクション名の位置で分割")
        print("  3. カスタム線分割: 任意の直線で分割（X1,Y1,X2,Y2形式）")
        x_mode = self.input_str("X方向分割モード (1:等分割, 2:セクション位置, 3:カスタム線)", "1")

        x_break = {}
        if x_mode == "2":
            # セクション位置分割
            default_sections = self._get_all_sections()
            print(f"  ※ 利用可能なセクション: {default_sections}")
            print("  分割位置とするセクションを指定（カンマ区切り）")
            section_input = self.input_str("セクション名", default_sections)
            sections = [s.strip() for s in section_input.split(",") if s.strip()]
            x_break = {"Type": "sections", "Sections": sections}
            print(f"  → セクション位置分割: {sections}")
        elif x_mode == "3":
            # カスタム線分割
            print("  分割線を指定します（X1,Y1,X2,Y2形式）")
            print("  例: 0,0,0,5000 → X=0の位置でY方向に伸びる線")
            print("  複数の線を追加できます")
            lines = []
            while True:
                line_input = self.input_str("分割線 (X1,Y1,X2,Y2, Enterで終了)", "")
                if not line_input:
                    break
                try:
                    coords = [float(c.strip()) for c in line_input.split(",")]
                    if len(coords) == 4:
                        lines.append(coords)
                        print(f"    ✓ 分割線追加: ({coords[0]}, {coords[1]}) → ({coords[2]}, {coords[3]})")
                    else:
                        print("    エラー: 4つの数値をカンマ区切りで入力してください")
                except ValueError:
                    print("    エラー: 数値を入力してください")

            if lines:
                x_break = {"Type": "custom", "Lines": lines}
                print(f"  → カスタム線分割: {len(lines)}本の分割線")
            else:
                # 線が指定されなかった場合は等分割にフォールバック
                x_count = self.input_int("X方向分割数", 4)
                x_break = {"Type": "equal", "Count": x_count}
        else:
            # 等分割
            x_count = self.input_int("X方向分割数", 4)
            x_break = {"Type": "equal", "Count": x_count}

        # 従来形式との互換性のため、等分割の場合は数値のみを返す
        break_data = {}

        if x_break.get("Type") == "equal":
            break_data["X"] = x_break.get("Count", 4)
        else:
            break_data["X"] = x_break

        if y_break.get("Type") == "equal":
            break_data["Y"] = y_break.get("Count", 3)
        else:
            break_data["Y"] = y_break

        return break_data

    def handle_existing_name_for_bearing(self, name: str, girder: str, section: str, data_list: list) -> str | None:
        """
        支承専用の既存名前処理
        同じ桁・同じセクション（G3, E1）に対して末尾に番号を追加する

        Args:
            name: チェックする名前（例: "Bearing_G3_E1"）
            girder: 桁（例: "G3"）
            section: セクション（例: "E1"）
            data_list: 支承のデータリスト

        Returns:
            使用する名前（上書きの場合は元の名前、新規作成の場合は新しい名前、スキップの場合はNone）
        """
        existing = [item for item in data_list if item.get("Name") == name]
        if not existing:
            return name

        print(f"\n支承 '{name}' は既に存在します。")
        print("  1. 上書きする")
        print("  2. 新規作成する（同じ桁・セクションで末尾に番号を追加）")
        print("  3. スキップする")

        while True:
            choice = input("選択してください [1/2/3, デフォルト: 2]: ").strip()
            if not choice:
                choice = "2"

            if choice == "1":
                # 上書き: 既存のアイテムを削除
                data_list[:] = [item for item in data_list if item.get("Name") != name]
                print(f"  → '{name}' を上書きします")
                return name
            elif choice == "2":
                # 新規作成: 同じ桁・セクションの組み合わせに対して末尾に番号を追加
                import re

                # 同じ桁・セクションの組み合わせを持つ既存の支承を探す
                existing_names = [item.get("Name") for item in data_list]
                numbers = []

                # パターン: Bearing_{桁}_{セクション} または Bearing_{桁}_{セクション}_{番号}
                base_pattern = rf"^Bearing_{re.escape(girder)}_{re.escape(section)}$"
                numbered_pattern = rf"^Bearing_{re.escape(girder)}_{re.escape(section)}_(\d+)$"

                for existing_name in existing_names:
                    # 完全一致（番号なし）
                    if re.match(base_pattern, existing_name):
                        numbers.append(1)  # 番号なしは1として扱う
                    # 番号付き
                    match = re.match(numbered_pattern, existing_name)
                    if match:
                        numbers.append(int(match.group(1)))

                if numbers:
                    next_num = max(numbers) + 1
                else:
                    next_num = 2

                new_name = f"Bearing_{girder}_{section}_{next_num}"

                # 新しい名前も既に存在する場合はさらに次の番号を探す
                while any(item.get("Name") == new_name for item in data_list):
                    next_num += 1
                    new_name = f"Bearing_{girder}_{section}_{next_num}"

                print(f"  → 新規作成: '{new_name}' を使用します")
                return new_name
            elif choice == "3":
                # スキップ
                print(f"  → '{name}' をスキップします")
                return None
            else:
                print("  エラー: 1, 2, または 3 を入力してください")

    def handle_existing_name_for_lateral_bracing(
        self, name: str, girder1: str, girder2: str, data_list: list
    ) -> str | None:
        """
        横構専用の既存名前処理
        同じ桁の組み合わせ（G1-G2）に対して番号をインクリメントする

        Args:
            name: チェックする名前（例: "LB1_G1_G2"）
            girder1: 1つ目の桁（例: "G1"）
            girder2: 2つ目の桁（例: "G2"）
            data_list: 横構のデータリスト

        Returns:
            使用する名前（上書きの場合は元の名前、新規作成の場合は新しい名前、スキップの場合はNone）
        """
        existing = [item for item in data_list if item.get("Name") == name]
        if not existing:
            return name

        print(f"\n横構 '{name}' は既に存在します。")
        print("  1. 上書きする")
        print("  2. 新規作成する（同じ桁組み合わせで次の番号を自動生成）")
        print("  3. スキップする")

        while True:
            choice = input("選択してください [1/2/3, デフォルト: 2]: ").strip()
            if not choice:
                choice = "2"

            if choice == "1":
                # 上書き: 既存のアイテムを削除
                data_list[:] = [item for item in data_list if item.get("Name") != name]
                print(f"  → '{name}' を上書きします")
                return name
            elif choice == "2":
                # 新規作成: 同じ桁の組み合わせに対して番号をインクリメント
                import re

                # 同じ桁の組み合わせを持つ既存の横構を探す
                # 桁の組み合わせを正規化（G1-G2とG2-G1は同じ）
                girder_pair = tuple(sorted([girder1, girder2]))

                existing_names = [item.get("Name") for item in data_list]
                numbers = []

                # パターン: LB{番号}_G{桁1}_G{桁2}
                pattern = r"^LB(\d+)_G(\d+)_G(\d+)$"
                for existing_name in existing_names:
                    match = re.match(pattern, existing_name)
                    if match:
                        num = int(match.group(1))
                        g1 = match.group(2)
                        g2 = match.group(3)
                        existing_pair = tuple(sorted([f"G{g1}", f"G{g2}"]))
                        if existing_pair == girder_pair:
                            numbers.append(num)

                if numbers:
                    next_num = max(numbers) + 1
                else:
                    # 同じ桁の組み合わせがない場合、元の名前から番号を抽出
                    match = re.match(pattern, name)
                    if match:
                        next_num = int(match.group(1)) + 1
                    else:
                        next_num = 2

                new_name = f"LB{next_num}_{girder1}_{girder2}"

                # 新しい名前も既に存在する場合はさらに次の番号を探す
                while any(item.get("Name") == new_name for item in data_list):
                    next_num += 1
                    new_name = f"LB{next_num}_{girder1}_{girder2}"

                print(f"  → 新規作成: '{new_name}' を使用します")
                return new_name
            elif choice == "3":
                # スキップ
                print(f"  → '{name}' をスキップします")
                return None
            else:
                print("  エラー: 1, 2, または 3 を入力してください")

    def handle_existing_name(
        self, name: str, item_type: str, data_list: list, name_pattern: str | None = None
    ) -> str | None:
        """
        既存の名前が存在する場合の処理

        Args:
            name: チェックする名前
            item_type: アイテムタイプ（例: "対傾構", "横構"）
            data_list: データリスト
            name_pattern: 名前パターン（例: "T{num}" で T1, T2, T3... を検索）

        Returns:
            使用する名前（上書きの場合は元の名前、新規作成の場合は新しい名前、スキップの場合はNone）
        """
        existing = [item for item in data_list if item.get("Name") == name]
        if not existing:
            return name

        print(f"\n{item_type} '{name}' は既に存在します。")
        print("  1. 上書きする")
        print("  2. 新規作成する（次の番号を自動生成）")
        print("  3. スキップする")

        while True:
            choice = input("選択してください [1/2/3, デフォルト: 2]: ").strip()
            if not choice:
                choice = "2"

            if choice == "1":
                # 上書き: 既存のアイテムを削除
                data_list[:] = [item for item in data_list if item.get("Name") != name]
                print(f"  → '{name}' を上書きします")
                return name
            elif choice == "2":
                # 新規作成: 次の番号を自動生成
                if name_pattern:
                    # パターンに基づいて次の番号を生成
                    import re

                    # 既存の名前から番号を抽出
                    existing_names = [item.get("Name") for item in data_list]
                    numbers = []
                    pattern = name_pattern.replace("{num}", r"(\d+)")
                    for existing_name in existing_names:
                        match = re.match(pattern, existing_name)
                        if match:
                            numbers.append(int(match.group(1)))

                    if numbers:
                        next_num = max(numbers) + 1
                    else:
                        # パターンに一致する名前がない場合、元の名前から番号を抽出
                        match = re.search(r"(\d+)", name)
                        if match:
                            next_num = int(match.group(1)) + 1
                        else:
                            next_num = 1

                    new_name = name_pattern.replace("{num}", str(next_num))
                else:
                    # パターンがない場合、元の名前に番号を追加
                    import re

                    # 既存の名前から、同じベース名を持つものを探す
                    existing_names = [item.get("Name") for item in data_list]
                    base_name = name
                    numbers = []

                    # 末尾の数字を探す
                    match = re.search(r"(\d+)$", name)
                    if match:
                        base_name = name[: match.start()]
                        numbers.append(int(match.group(1)))

                    # 既存の名前から同じベース名を持つものを探す
                    for existing_name in existing_names:
                        if existing_name.startswith(base_name):
                            match = re.search(r"(\d+)$", existing_name)
                            if match:
                                try:
                                    numbers.append(int(match.group(1)))
                                except:
                                    pass

                    if numbers:
                        next_num = max(numbers) + 1
                    else:
                        next_num = 2

                    new_name = f"{base_name}{next_num}"

                # 新しい名前も既に存在する場合はさらに次の番号を探す
                while any(item.get("Name") == new_name for item in data_list):
                    if name_pattern:
                        next_num += 1
                        new_name = name_pattern.replace("{num}", str(next_num))
                    else:
                        import re

                        match = re.search(r"(\d+)$", new_name)
                        if match:
                            next_num = int(match.group(1)) + 1
                            new_name = re.sub(r"\d+$", str(next_num), new_name)
                        else:
                            new_name = f"{new_name}_2"

                print(f"  → 新規作成: '{new_name}' を使用します")
                return new_name
            elif choice == "3":
                # スキップ
                print(f"  → '{name}' をスキップします")
                return None
            else:
                print("  エラー: 1, 2, または 3 を入力してください")

    def create_infor(self):
        """Inforセクションを作成"""
        self.print_section("基本情報 (Infor)")

        print("橋梁の基本情報を設定します。")
        print("\n【橋梁名】")
        print("  - 任意の文字列で橋梁の名前を指定します")
        print('  - 例: "Sample Bridge", "斜橋テスト", "Bridge No.1"')
        name = self.input_str("橋梁名", "Sample Bridge")

        print("\n【エクスポート側】")
        print("  - 2: 両側をエクスポート（上フランジと下フランジの両方）")
        print("  - 1: 上側のみエクスポート（上フランジのみ）")
        print("  - -1: 下側のみエクスポート（下フランジのみ）")
        print("  - 通常は 2（両側）を選択します")
        side_export = self.input_int("エクスポート側 (2=両側, 1=上側のみ, -1=下側のみ)", 2)

        self.data["Infor"] = {"NameBridge": name, "SideExport": side_export}

        print(f"\n✓ 基本情報を設定しました: {name} (エクスポート側: {side_export})")

    def create_senkei(self):
        """Senkeiセクションを作成"""
        self.print_section("線形データ (Senkei)")

        # 既存データの確認
        if not self.check_existing_data("Senkei", "線形"):
            return

        print("線形データを追加します。")
        print("\n【線形名の形式】")
        print("  - TG1L, TG1, TG1R: 上フランジ (Top Girder)")
        print("    * TG1L: 桁1の上フランジ左側")
        print("    * TG1: 桁1の上フランジ中央")
        print("    * TG1R: 桁1の上フランジ右側")
        print("  - BG1L, BG1, BG1R: 下フランジ (Bottom Girder)")
        print("    * BG1L: 桁1の下フランジ左側")
        print("    * BG1: 桁1の下フランジ中央")
        print("    * BG1R: 桁1の下フランジ右側")
        print("\n【例】")
        print("  3桁橋の場合: TG1L, TG1, TG1R, TG2L, TG2, TG2R, TG3L, TG3, TG3R")
        print("              BG1L, BG1, BG1R, BG2L, BG2, BG2R, BG3L, BG3, BG3R")
        print("\n【便利機能: 自動生成】")
        print("  - 「3Girder」と入力すると、3桁橋の全線形を自動生成します")
        print("  - 形式: {桁数}Girder (例: 2Girder, 3Girder, 4Girder)")
        print("  - 自動生成される線形:")
        print("    * 各桁について: TG*L, TG*, TG*R (上フランジ)")
        print("    * 各桁について: BG*L, BG*, BG*R (下フランジ)")
        print("  - 例: 3Girder → 18本の線形を自動生成（3桁×6線形/桁）")
        print("  - 座標点はテンプレートとして一度入力し、各桁のY座標を自動調整します")
        print("  - 直橋の場合: 各桁のY座標のみが異なり、X/Z座標は同じ")
        print("  - 斜橋の場合: 後で個別に座標を調整可能")

        while True:
            print("\n--- 新しい線形を追加 ---")
            line_input = self.input_str("線形名または桁数指定 (例: TG1 または 3Girder, Enterで終了)")
            if not line_input:
                break

            # 桁数指定の自動生成機能
            if line_input.lower().endswith("girder"):
                try:
                    num_girders = int(line_input.lower().replace("girder", "").strip())
                    if num_girders < 1 or num_girders > 30:
                        print("  警告: 桁数は1-30の範囲で指定してください")
                        continue

                    print(f"\n  {num_girders}桁橋の線形を自動生成します...")

                    # 座標点のデフォルト値を取得
                    print("\n【座標系の説明】")
                    print("  - X軸: 橋軸方向（長さ方向、橋の進行方向）")
                    print("  - Y軸: 橋軸直角方向（横方向、桁の配置方向）")
                    print("  - Z軸: 重力方向（高さ方向、上下）")
                    print("  ※ 注意: Z=0は地面ではなく、相対的な高さです")
                    print("\n【点名の意味】")
                    print("  点名（S1, C1, E1など）は橋軸方向（X方向）の位置を表します。")
                    print("  これは「上フランジの上端」や「下フランジの下端」ではなく、")
                    print("  橋の長さ方向のどの位置かを示す名前です。")
                    print("  - S1: スタート点（通常X=0付近、橋の始端）")
                    print("  - S2: スタート付近の中間点（通常X=4000付近）")
                    print("  - C1: 中央点（通常X=15000付近、橋の中央）")
                    print("  - E2: エンド付近の中間点（通常X=26000付近）")
                    print("  - E1: エンド点（通常X=30000付近、橋の終端）")
                    print("  ※ 点名は任意の文字列でも構いませんが、上記の規則に従うと分かりやすいです")
                    print("\n【座標点テンプレートの設定】")
                    print("  すべての線形（TG1L, TG1, TG1R, BG1L, BG1, BG1Rなど）で使用する")
                    print("  座標点のテンプレートを設定します。")
                    print("  - X座標: 全線形で共通（橋軸方向の位置は同じ）")
                    print("  - Z座標: 上フランジ用は10000、下フランジ用は9000（後で自動調整）")
                    print("  - Y座標: 基準値として0を入力（各桁のY座標中央位置は後で設定）")
                    print("\n【Z座標について】")
                    print("  - 上フランジ（TG*）: Z=10000（上フランジの中心線の高さ、例）")
                    print("  - 下フランジ（BG*）: Z=上フランジのZ座標 - 桁の高さ（ウェブの高さ）")
                    print("  ※ 例: 上フランジZ=10000、桁の高さ=1000mmの場合、下フランジZ=9000")
                    print("  ※ 桁の高さは設計によって異なります（500mm, 1000mm, 1500mmなど）")
                    print("  ※ Z=0は地面ではなく、相対的な高さです（実際の地面はもっと下）")
                    print("\n【Y座標について】")
                    print("  テンプレートでは基準値として0を入力してください。")
                    print("  後で各桁のY座標中央位置を設定すると、自動的に調整されます。")
                    print("  例: 桁1の中央がY=-2500、桁2の中央がY=0、桁3の中央がY=2500の場合、")
                    print("      テンプレートでY基準=0を入力すると、各桁で自動的に調整されます。")
                    print("\n【例】")
                    print("  最小構成（2点のみ）:")
                    print("    S1: X=0, Y基準=0, Z=10000")
                    print("      → 橋の始端（X=0）の位置、上フランジの中心線高さ（Z=10000）")
                    print("    E1: X=30000, Y基準=0, Z=10000")
                    print("      → 橋の終端（X=30000）の位置、上フランジの中心線高さ（Z=10000）")
                    print("  中間点あり（3点以上）:")
                    print("    S1: X=0, Y基準=0, Z=10000")
                    print("    C1: X=15000, Y基準=0, Z=10000  （橋の中央）")
                    print("    E1: X=30000, Y基準=0, Z=10000")
                    print("  ※ 下フランジ用の線形（BG*）は自動的にZ=9000に調整されます")

                    points_template = []
                    print("\n  座標点を追加します（Enterで次の点へ、空で終了）")
                    print("  ※ 同じ点名を入力すると、既存の点を上書きします")
                    while True:
                        point_name = self.input_str("  点名 (例: S1)", "")
                        if not point_name:
                            break

                        # 同じ点名が既に存在するかチェック
                        existing_point_index = None
                        for i, pt in enumerate(points_template):
                            if pt["name"] == point_name:
                                existing_point_index = i
                                break

                        x = self.input_float("  X座標 (mm, 橋軸方向の位置, 例: 0)", 0.0)
                        y_base = self.input_float("  Y座標の基準値 (mm, 0でOK, 各桁で自動調整されます)", 0.0)
                        z = self.input_float("  Z座標 (mm, 上フランジ用の例: 10000)", 10000.0)
                        print(f"    ※ この点は橋軸方向X={x}の位置、高さZ={z}を表します")
                        print("    ※ Y座標は後で各桁の位置に応じて自動調整されます")
                        print("    ※ 下フランジ用のZ座標は、後で桁の高さを設定して自動調整されます")

                        point_data = {"name": point_name, "x": x, "y_base": y_base, "z": z}

                        if existing_point_index is not None:
                            # 既存の点を上書き
                            points_template[existing_point_index] = point_data
                            print(f"    ✓ 点 {point_name} を上書き: X={x}, Y基準={y_base}, Z={z}")
                        else:
                            # 新しい点を追加
                            points_template.append(point_data)
                            print(f"    ✓ 点 {point_name} を追加: X={x}, Y基準={y_base}, Z={z}")

                    if not points_template:
                        print("  警告: 座標点が設定されていません。スキップします")
                        continue

                    # 各桁のY座標オフセットを計算
                    print("\n【各桁のY座標中央位置】")
                    print("  各桁の中央位置のY座標を設定します")
                    print("  【例】")
                    print("    3桁橋で桁間2500mmの場合:")
                    print("      桁1: -2500mm (または 0mm)")
                    print("      桁2: 0mm (または 2500mm)")
                    print("      桁3: 2500mm (または 5000mm)")
                    girder_y_offsets = []
                    for i in range(1, num_girders + 1):
                        default_y = (i - 1) * 2500.0 - (num_girders - 1) * 1250.0  # 中央揃え
                        y_offset = self.input_float(f"  桁{i}のY座標中央 (mm)", default_y)
                        girder_y_offsets.append(y_offset)

                    # 各桁の幅を設定（上フランジと下フランジで別々）
                    print("\n【各桁の幅】")
                    print("  各桁の左端から右端までの幅（mm）")
                    print("  【例】")
                    print("    上フランジ: 通常500mm")
                    print("    下フランジ: 通常500mm（上フランジと同じ場合が多い）")
                    print("    幅が異なる場合は後で個別調整可能")
                    girder_width_uf = self.input_float("  上フランジの幅 (mm, 全桁共通)", 500.0)
                    girder_width_lf = self.input_float("  下フランジの幅 (mm, 全桁共通)", 500.0)

                    # 桁の高さを設定
                    print("\n【桁の高さ（ウェブの高さ）】")
                    print("  上フランジと下フランジの間の高さ（mm）")
                    print("  【例】")
                    print("    通常: 1000mm（上フランジZ=10000の場合、下フランジZ=9000）")
                    print("    桁の高さが異なる場合は後で個別調整可能")
                    print("  ※ 下フランジ用の線形（BG*）のZ座標は、上フランジのZ座標からこの値を引いた値になります")
                    girder_height = self.input_float("  桁の高さ (mm, 全桁共通)", 1000.0)

                    # 線形を自動生成
                    generated_count = 0
                    for girder_num in range(1, num_girders + 1):
                        y_center = girder_y_offsets[girder_num - 1]

                        # 上フランジのY座標を計算
                        y_left_uf = y_center - girder_width_uf / 2
                        y_right_uf = y_center + girder_width_uf / 2

                        # 下フランジのY座標を計算
                        y_left_lf = y_center - girder_width_lf / 2
                        y_right_lf = y_center + girder_width_lf / 2

                        # 上フランジ: TG*L, TG*, TG*R
                        for suffix, y_offset in [("L", y_left_uf), ("", y_center), ("R", y_right_uf)]:
                            line_name = f"TG{girder_num}{suffix}"
                            points = []
                            for pt in points_template:
                                # Y座標を調整（斜橋の場合は後で個別調整が必要）
                                points.append(
                                    {"Name": pt["name"], "X": pt["x"], "Y": pt["y_base"] + y_offset, "Z": pt["z"]}
                                )

                            self.data["Senkei"].append({"Name": line_name, "Point": points})
                            generated_count += 1

                        # 下フランジ: BG*L, BG*, BG*R
                        for suffix, y_offset in [("L", y_left_lf), ("", y_center), ("R", y_right_lf)]:
                            line_name = f"BG{girder_num}{suffix}"
                            points = []
                            for pt in points_template:
                                # Z座標は下フランジなので桁の高さ分下げる
                                z_offset = -girder_height
                                points.append(
                                    {
                                        "Name": pt["name"],
                                        "X": pt["x"],
                                        "Y": pt["y_base"] + y_offset,
                                        "Z": pt["z"] + z_offset,
                                    }
                                )

                            self.data["Senkei"].append({"Name": line_name, "Point": points})
                            generated_count += 1

                    print(f"\n✓ {num_girders}桁橋の線形を{generated_count}本自動生成しました")
                    print("  生成された線形: TG*L, TG*, TG*R, BG*L, BG*, BG*R (各桁)")

                    if not self.input_yes_no("さらに線形を追加しますか？", False):
                        break
                    continue

                except ValueError:
                    print(f"  警告: '{line_input}' は無効な形式です。通常の線形名として処理します")
                    line_name = line_input
            else:
                line_name = line_input

            points = []
            print("\n【座標系の説明】")
            print("  - X軸: 橋軸方向（長さ方向、橋の進行方向）")
            print("  - Y軸: 橋軸直角方向（横方向、桁の配置方向）")
            print("  - Z軸: 重力方向（高さ方向、上下）")
            print("\n【座標点の追加】")
            print("点名は橋軸方向（X方向）の位置を表します：")
            print("  - S1: スタート点（通常X=0付近、橋の始端）")
            print("  - S2: スタート付近の中間点（通常X=4000付近）")
            print("  - C1: 中央点（通常X=15000付近、橋の中央）")
            print("  - E2: エンド付近の中間点（通常X=26000付近）")
            print("  - E1: エンド点（通常X=30000付近、橋の終端）")
            print("  ※ 点名は任意の文字列でも構いませんが、上記の規則に従うと分かりやすいです")
            print("\n【例】")
            print("  直橋の場合（Y座標は各桁で異なります）:")
            print("    S1: X=0, Y=-2500（桁1の場合）, Z=10000")
            print("    E1: X=30000, Y=-1500（桁1の場合）, Z=10000")
            print("  斜橋の場合（Y座標がX方向で変化）:")
            print("    S1: X=0, Y=-2500, Z=10000")
            print("    C1: X=15000, Y=-2000, Z=10000  （Y座標が変化）")
            print("    E1: X=30000, Y=-1500, Z=10000  （Y座標が変化）")

            print("  ※ 同じ点名を入力すると、既存の点を上書きします")
            while True:
                point_name = self.input_str("点名 (例: S1, Enterで終了)")
                if not point_name:
                    break

                # 同じ点名が既に存在するかチェック
                existing_point_index = None
                for i, pt in enumerate(points):
                    if pt.get("Name") == point_name:
                        existing_point_index = i
                        break

                print(f"\n  点 {point_name} の座標を入力してください（mm単位）")
                x = self.input_float("  X座標 (mm)", 0.0)
                y = self.input_float("  Y座標 (mm)", 0.0)
                z = self.input_float("  Z座標 (mm)", 10000.0)

                point_data = {"Name": point_name, "X": x, "Y": y, "Z": z}

                if existing_point_index is not None:
                    # 既存の点を上書き
                    points[existing_point_index] = point_data
                    print(f"  ✓ 点 {point_name} を上書きしました: ({x}, {y}, {z})")
                else:
                    # 新しい点を追加
                    points.append(point_data)
                    print(f"  ✓ 点 {point_name} を追加しました: ({x}, {y}, {z})")

            if points:
                # 同じ名前の線形が既に存在するかチェック
                existing_index = None
                for i, existing_line in enumerate(self.data["Senkei"]):
                    if existing_line.get("Name") == line_name:
                        existing_index = i
                        break

                if existing_index is not None:
                    # 既存の線形がある場合: 既存のPoint配列に新しい点を追加または上書き
                    existing_points = self.data["Senkei"][existing_index].get("Point", [])

                    # 新しい点を既存のPoint配列に追加または上書き
                    for new_point in points:
                        new_point_name = new_point.get("Name")
                        # 既存のPoint配列内で同じ点名があるかチェック
                        point_found = False
                        for i, existing_point in enumerate(existing_points):
                            if existing_point.get("Name") == new_point_name:
                                # 同じ点名があれば上書き
                                existing_points[i] = new_point
                                point_found = True
                                print(
                                    f"  ✓ 点 {new_point_name} を上書きしました: ({new_point.get('X')}, {new_point.get('Y')}, {new_point.get('Z')})"
                                )
                                break

                        if not point_found:
                            # 同じ点名がなければ追加
                            existing_points.append(new_point)
                            print(
                                f"  ✓ 点 {new_point_name} を追加しました: ({new_point.get('X')}, {new_point.get('Y')}, {new_point.get('Z')})"
                            )

                    # 既存の線形データを更新
                    self.data["Senkei"][existing_index]["Point"] = existing_points
                    print(f"\n✓ 線形 {line_name} を更新しました (合計{len(existing_points)}点)")
                else:
                    # 新しい線形を追加
                    line_data = {"Name": line_name, "Point": points}
                    self.data["Senkei"].append(line_data)
                    print(f"\n✓ 線形 {line_name} を追加しました ({len(points)}点)")
            else:
                print("  警告: 点が追加されていません")

            if not self.input_yes_no("さらに線形を追加しますか？", True):
                break

        print(f"\n✓ 線形データ: {len(self.data['Senkei'])}個の線形を追加しました")

    def create_mainpanel(self):
        """MainPanelセクションを作成"""
        self.print_section("主桁パネル (MainPanel)")

        # 既存データの確認
        if not self.check_existing_data("MainPanel", "主桁パネル"):
            return

        print("主桁パネルを追加します。")
        print("\n【パネルとは】")
        print("  パネルは、橋の主桁（メインガーダー）を構成する部材の1つです。")
        print("  主桁は以下の3種類のパネルで構成されます：")
        print("  - 上フランジ（UF）: 主桁の上側の水平部材")
        print("  - ウェブ（W）: 主桁の垂直部材（上フランジと下フランジを繋ぐ）")
        print("  - 下フランジ（LF）: 主桁の下側の水平部材")
        print("  例: 3桁橋の場合、各桁にUF、W、LFの3パネルが必要 → 合計9パネル")
        print("\n【パネル名の形式】")
        print("  G{桁番号}B{ブロック番号}{タイプ}")
        print("  - 桁番号: G1（1番目の桁）, G2（2番目の桁）, G3（3番目の桁）など")
        print("  - ブロック番号: B1（通常はB1のみ使用）")
        print("  - タイプ: UF（上フランジ）, W（ウェブ）, LF（下フランジ）")
        print("\n【例】")
        print("  - G1B1UF: 桁1の上フランジ")
        print("  - G1B1W: 桁1のウェブ")
        print("  - G1B1LF: 桁1の下フランジ")
        print("  - G2B1UF: 桁2の上フランジ")
        print("\n【便利機能: 自動生成】")
        print("  - 「3Girder」と入力すると、3桁橋の全パネルを自動生成します")
        print("  - 形式: {桁数}Girder (例: 2Girder, 3Girder, 4Girder)")
        print("  - 自動生成されるパネル: 各桁について UF, W, LF（合計{桁数}×3パネル）")
        print("  - 例: 3Girder → 9個のパネルを自動生成（G1B1UF, G1B1W, G1B1LF, G2B1UF, ...）")

        while True:
            print("\n--- 新しいパネルを追加 ---")
            panel_input = self.input_str("パネル名または桁数指定 (例: G1B1UF または 3Girder, Enterで終了)")
            if not panel_input:
                break

            # 桁数指定の自動生成機能
            if panel_input.lower().endswith("girder"):
                try:
                    num_girders = int(panel_input.lower().replace("girder", "").strip())
                    if num_girders < 1 or num_girders > 30:
                        print("  警告: 桁数は1-30の範囲で指定してください")
                        continue

                    print(f"\n  {num_girders}桁橋のパネルを自動生成します...")

                    # 共通設定を取得
                    print("\n【共通設定】")
                    print("  全パネルに共通する設定を入力します")

                    # セクション
                    print("\n【セクション（橋軸方向の位置）】")
                    print("  - コンマ区切りで一度に複数入力できます")

                    # デフォルト値を既存データから生成
                    default_sections = self._get_all_sections()
                    print(f"  ※ 既存データから推奨: {default_sections}")
                    section_input = self.input_str("  セクション名", default_sections)
                    if not section_input:
                        sections = [s.strip() for s in default_sections.split(",")]
                        print(f"  デフォルトセクションを使用: {sections}")
                    else:
                        # コンマ区切りで分割
                        sections = [section.strip() for section in section_input.split(",") if section.strip()]
                        # 重複チェック
                        unique_sections = []
                        for section in sections:
                            if section not in unique_sections:
                                unique_sections.append(section)
                                print(f"    ✓ セクション {section} を追加")
                            else:
                                print(f"    ※ セクション {section} は既に追加されています（スキップ）")
                        sections = unique_sections

                        if not sections:
                            sections = ["S1", "E1"]  # デフォルト
                            print(f"  デフォルトセクションを使用: {sections}")

                    # 材料情報（タイプ別）
                    print("\n【材料情報（タイプ別）】")
                    materials = {}
                    for panel_type, type_name, default_thick1, default_thick2, default_split in [
                        ("UF", "上フランジ", 12.0, 12.0, False),
                        ("W", "ウェブ", 6.0, 6.0, True),
                        ("LF", "下フランジ", 16.0, 16.0, True),
                    ]:
                        print(f"\n  {type_name} ({panel_type}) の材料情報:")
                        thick1 = self.input_float("    Thick1 (mm)", default_thick1)
                        thick2 = self.input_float("    Thick2 (mm)", default_thick2)
                        mat = self.input_str("    材料 (例: SM400A)", "SM400A")
                        split_thickness = self.input_yes_no("    厚さ方向分割 (SplitThickness)", default_split)
                        materials[panel_type] = {
                            "Thick1": thick1,
                            "Thick2": thick2,
                            "Mat": mat,
                            "SplitThickness": split_thickness,
                        }

                    # 分割設定
                    print("\n【分割設定 (Break)】")
                    print("  パネルを長さ方向に分割する設定です")
                    print("  【例】")
                    print("    4等分割: 分割数4を入力 → 全長を4等分")
                    print("    カスタム分割: 7500,7500,7500,7500 のように各セグメントの長さを指定")
                    has_break = self.input_yes_no("  分割設定を追加しますか？", True)
                    break_data = {}
                    if has_break:
                        length_input = self.input_str("  長さ方向分割 (例: 4 または 7500,7500,7500,7500)", "4")
                        num_segments = 0
                        if length_input.isdigit():
                            # 分割数を指定
                            num_divisions = int(length_input)
                            # 全長を取得（セクションから推定、または入力）
                            total_length = self.input_float("  全長 (mm, 例: 30000)", 30000.0)
                            segment_length = total_length / num_divisions
                            break_data["Lenght"] = [segment_length] * num_divisions
                            num_segments = num_divisions
                            print(f"    ✓ {num_divisions}等分割: 各{segment_length:.0f}mm")
                        else:
                            # カスタム分割
                            try:
                                lengths = [float(x.strip()) for x in length_input.split(",")]
                                break_data["Lenght"] = lengths
                                num_segments = len(lengths)
                                print(f"    ✓ カスタム分割: {num_segments}セグメント")
                            except:
                                print("    警告: 無効な形式です。分割設定をスキップします")
                                break_data = {}

                        # ExtendとThickを追加（Lenghtの数に合わせる）
                        if num_segments > 0:
                            break_data["Extend"] = [0] * num_segments
                            # Thickは後でパネルタイプに応じて設定される

                    # 線形の自動決定
                    print("\n【線形の自動決定】")
                    print("  各パネルタイプに応じた線形を自動設定します")
                    print("  - 上フランジ(UF): TG*L, TG*, TG*R")
                    print("  - ウェブ(W): TG*, BG*")
                    print("  - 下フランジ(LF): BG*L, BG*, BG*R")

                    # パネルを自動生成
                    generated_count = 0
                    for girder_num in range(1, num_girders + 1):
                        for panel_type, type_name in [("UF", "上フランジ"), ("W", "ウェブ"), ("LF", "下フランジ")]:
                            panel_name = f"G{girder_num}B1{panel_type}"

                            # 線形を決定
                            if panel_type == "UF":
                                lines = [f"TG{girder_num}L", f"TG{girder_num}", f"TG{girder_num}R"]
                            elif panel_type == "W":
                                lines = [f"TG{girder_num}", f"BG{girder_num}"]
                            else:  # LF
                                lines = [f"BG{girder_num}L", f"BG{girder_num}", f"BG{girder_num}R"]

                            # Breakデータをコピーして、Thickをパネルタイプに応じて設定
                            panel_break = break_data.copy() if break_data else {}
                            if panel_break and "Lenght" in panel_break:
                                num_segments = len(panel_break["Lenght"])
                                # Thickをパネルタイプに応じて設定
                                thick1 = materials[panel_type]["Thick1"]
                                thick2 = materials[panel_type]["Thick2"]
                                panel_break["Thick"] = [f"{thick1}/{thick2}"] * num_segments
                                # Extendが設定されていない場合は追加
                                if "Extend" not in panel_break:
                                    panel_break["Extend"] = [0] * num_segments

                            # パネルデータを作成
                            panel = {
                                "Name": panel_name,
                                "Line": lines,
                                "Sec": sections,
                                "Type": {"Girder": f"G{girder_num}", "Block": "B1", "TypePanel": panel_type},
                                "Material": materials[panel_type].copy(),
                                "Expand": {"E1": 0, "E2": 0, "E3": 0, "E4": 0},
                                "Jbut": {"S": [], "E": []},
                                "Break": panel_break,
                                "Corner": [],
                                "Lrib": [],
                                "Vstiff": [],
                                "Hstiff": [],
                                "Atm": [],
                                "Cutout": [],
                                "Stud": [],
                            }

                            # 既存のパネルをチェックして上書きまたは追加
                            existing_index = None
                            for i, existing_panel in enumerate(self.data["MainPanel"]):
                                if existing_panel.get("Name") == panel_name:
                                    existing_index = i
                                    break

                            if existing_index is not None:
                                self.data["MainPanel"][existing_index] = panel
                                print(f"  ✓ パネル {panel_name} を上書き")
                            else:
                                self.data["MainPanel"].append(panel)
                                print(f"  ✓ パネル {panel_name} を追加")
                            generated_count += 1

                    print(f"\n✓ {num_girders}桁橋のパネルを{generated_count}個自動生成しました")
                    print("  生成されたパネル: 各桁について UF, W, LF")

                    if not self.input_yes_no("さらにパネルを追加しますか？", False):
                        break
                    continue

                except ValueError:
                    print(f"  警告: '{panel_input}' は無効な形式です。通常のパネル名として処理します")
                    panel_name = panel_input
            else:
                panel_name = panel_input

            # 線形の入力
            print("\n【線形の指定】")
            print("このパネルが使用する線形（Senkeiで定義した線形）を指定します")
            print("  線形は、パネルの形状を決める座標線のことです")
            print("  - 上フランジ(UF): TG*L, TG*, TG*R（左、中央、右の3本）")
            print("  - ウェブ(W): TG*, BG*（上と下の2本）")
            print("  - 下フランジ(LF): BG*L, BG*, BG*R（左、中央、右の3本）")
            print("\n【例】")
            print("  G1B1UF（桁1の上フランジ）の場合: TG1L, TG1, TG1R")
            print("  G1B1W（桁1のウェブ）の場合: TG1, BG1")
            print("  G1B1LF（桁1の下フランジ）の場合: BG1L, BG1, BG1R")
            lines = []
            while True:
                line = self.input_str("線形名 (Enterで終了)")
                if not line:
                    break
                if line not in lines:
                    lines.append(line)
                    print(f"  ✓ 線形 {line} を追加")
                else:
                    print(f"  ※ 線形 {line} は既に追加されています")

            if not lines:
                print("  警告: 線形が指定されていません")
                continue

            # セクションの入力
            print("\n【セクションの指定】")
            print("このパネルが使用するセクション（橋軸方向の位置）を指定します")
            print("  セクションは、線形（Senkei）で定義した点名（S1, C1, E1など）のことです")
            print("  - 通常: S1, E1（スタートとエンド）")
            print("  - 中間点がある場合: S1, S2, C1, E2, E1")
            print("\n【例】")
            print("  最小構成: S1, E1")
            print("  中間点あり: S1, S2, C1, E2, E1")
            print("  - コンマ区切りで一度に複数入力できます（例: S1, C1, E1）")
            section_input = self.input_str("セクション名 (例: S1, E1 または Enterでデフォルト)", "")
            if not section_input:
                sections = ["S1", "E1"]  # デフォルト
                print(f"  デフォルトセクションを使用: {sections}")
            else:
                # コンマ区切りで分割
                sections = [section.strip() for section in section_input.split(",") if section.strip()]
                # 重複チェック
                unique_sections = []
                for section in sections:
                    if section not in unique_sections:
                        unique_sections.append(section)
                        print(f"  ✓ セクション {section} を追加")
                    else:
                        print(f"  ※ セクション {section} は既に追加されています（スキップ）")
                sections = unique_sections

                if not sections:
                    sections = ["S1", "E1"]  # デフォルト
                    print(f"  デフォルトセクションを使用: {sections}")

            # Type
            print("\n【パネルタイプ情報】")
            girder = self.input_str("桁番号 (例: G1)", "G1")
            block = self.input_str("ブロック番号 (例: B1)", "B1")
            type_panel = self.input_str("パネルタイプ (UF/W/LF)", "W")

            # Material
            print("\n【材料情報】")
            print("  - Thick1, Thick2: パネルの厚み（mm）")
            print("    * 上フランジ(UF): 通常12mm程度")
            print("    * ウェブ(W): 通常6mm程度")
            print("    * 下フランジ(LF): 通常16mm程度")
            print("  - SplitThickness: 厚さ方向に分割するか")
            print("    * false: 分割しない（UFで推奨）")
            print("    * true: 分割する（LFで推奨）")
            thick1 = self.input_float("Thick1 (mm)", 12.0)
            thick2 = self.input_float("Thick2 (mm)", 12.0)
            mat = self.input_str("材料 (例: SM400A)", "SM400A")
            split_thickness = self.input_yes_no("厚さ方向分割 (SplitThickness)", False)

            # Expand
            e1 = self.input_int("Extend E1 (mm)", 0)
            e2 = self.input_int("Extend E2 (mm)", 0)
            e3 = self.input_int("Extend E3 (mm)", 0)
            e4 = self.input_int("Extend E4 (mm)", 0)

            # Break
            print("\n【分割設定 (Break)】")
            print("パネルを長さ方向や厚さ方向に分割する設定です")
            print("  - Lenght: 長さ方向の分割（各セグメントの長さの配列）")
            print("  - Thick: 厚さ方向の分割（各セグメントの厚みの配列）")
            print("  - Extend: 拡張量（通常は[0,0,0,0]）")
            has_break = self.input_yes_no("分割設定 (Break) を追加しますか？", False)
            break_data = {}
            num_segments = 0
            if has_break:
                print("\n【長さ方向分割】")
                print("  入力方法1: 分割数を指定（例: 4 → 等分割）")
                print("  入力方法2: 各セグメントの長さを指定（例: 7500,7500,7500,7500）")
                print("  【例】")
                print("    4分割で各7500mm: 7500,7500,7500,7500")
                print("    4等分割（全長30000mm）: 4 を入力 → 各7500mmに自動計算")
                length_str = self.input_str("長さ方向分割 (例: 7500,7500,7500,7500 または 4)", "")
                if length_str:
                    if length_str.isdigit():
                        # 等分割
                        num = int(length_str)
                        total_length = self.input_float("全長 (mm)", 30000.0)
                        segment_length = total_length / num
                        break_data["Lenght"] = [segment_length] * num
                        num_segments = num
                        print(f"  → {num}等分割、各セグメント {segment_length}mm")
                    else:
                        # カンマ区切り
                        try:
                            lengths = [float(x.strip()) for x in length_str.split(",")]
                            break_data["Lenght"] = lengths
                            num_segments = len(lengths)
                            print(f"  → {num_segments}分割: {lengths}")
                        except:
                            print("  警告: 無効な形式です。スキップします")

                # ExtendとThickを自動生成（Lenghtの数に合わせる）
                if num_segments > 0:
                    # Extendを自動生成（デフォルトは0）
                    break_data["Extend"] = [0] * num_segments

                    # Thickを自動生成（MaterialのThick1/Thick2から）
                    thick_val = f"{int(thick1)}/{int(thick2)}"
                    break_data["Thick"] = [thick_val] * num_segments
                    print(f"  → Extend: {break_data['Extend']} (自動生成)")
                    print(f"  → Thick: {break_data['Thick']} (自動生成、Materialから)")

                    # 必要に応じて上書き可能にする
                    if self.input_yes_no("  Extend/Thickを手動で変更しますか？", False):
                        print("\n【厚さ方向分割（上書き）】")
                        thick_str = self.input_str(
                            f"厚さ方向分割 (例: {thick_val},{thick_val} または Enterでスキップ)", ""
                        )
                        if thick_str:
                            if thick_str.isdigit():
                                num = int(thick_str)
                                thick_val_custom = self.input_str("厚さ値 (例: 12/12)", thick_val)
                                break_data["Thick"] = [thick_val_custom] * num
                            else:
                                try:
                                    thick_vals = [x.strip().strip('"') for x in thick_str.split(",")]
                                    if len(thick_vals) == num_segments:
                                        break_data["Thick"] = thick_vals
                                    else:
                                        print(f"  警告: {num_segments}個の値を入力してください")
                                except:
                                    print("  警告: 無効な形式です。スキップします")

                        print("\n【拡張設定（上書き）】")
                        extend_str = self.input_str("拡張 (例: 0,0,0 または Enterでスキップ)", "")
                        if extend_str:
                            try:
                                extends = [int(x.strip()) for x in extend_str.split(",")]
                                if len(extends) == num_segments:
                                    break_data["Extend"] = extends
                                else:
                                    print(f"  警告: {num_segments}個の値を入力してください")
                            except:
                                print("  警告: 無効な形式です。スキップします")

            panel = {
                "Name": panel_name,
                "Line": lines,
                "Sec": sections,
                "Type": {"Girder": girder, "Block": block, "TypePanel": type_panel},
                "Material": {"Thick1": thick1, "Thick2": thick2, "Mat": mat, "SplitThickness": split_thickness},
                "Expand": {"E1": e1, "E2": e2, "E3": e3, "E4": e4},
                "Jbut": {"S": [], "E": []},
                "Break": break_data if break_data else {},
                "Corner": [],
                "Lrib": [],
                "Vstiff": [],
                "Hstiff": [],
                "Atm": [],
                "Cutout": [],
                "Stud": [],
            }

            self.data["MainPanel"].append(panel)
            print(f"\n✓ パネル {panel_name} を追加しました")

            if not self.input_yes_no("さらにパネルを追加しますか？", True):
                break

    def create_shouban(self):
        """Shoubanセクションを作成"""
        self.print_section("床版 (Shouban)")

        # 既存データの確認
        if not self.check_existing_data("Shouban", "床版"):
            return

        print("床版（Shouban）を追加します。")
        print("床版は主桁の上に配置されるコンクリートスラブです。")

        # レイヤー分割オプション
        print("\n【床版レイヤー分割オプション】")
        print("床版を上下のレイヤーに分けて作成できます。")
        print("  - 1つの床版: 従来通り1つの床版として作成")
        print("  - 複数レイヤー: 上面と下面を別々の床版として作成（異なる分割パターン可能）")
        print("\n【複数レイヤーのメリット】")
        print("  - 上面と下面で異なる分割パターンを設定可能")
        print("  - 接する面で分割線が一致する必要がない")
        print("  - 損傷評価時に上面/下面を区別可能")

        use_layers = self.input_yes_no("複数レイヤーに分けて作成しますか？", False)

        if use_layers:
            self._create_shouban_layers()
            return

        # 従来の1つの床版作成
        name = self.input_str("床版名 (例: Deck_Main)", "Deck_Main")

        # 線形
        print("\n【線形の指定】")
        print("床版の形状を定義する線形を指定します（通常4本）")
        print("  床版は、複数の線形で囲まれた閉じた多角形として定義されます")
        print("\n【重要な理解】")
        print("  - 各線形（TG1L, TG1R, TG3R, TG3Lなど）は橋軸方向（X方向）に伸びる線です")
        print("  - これらの線形は互いに平行です（全て橋軸方向に伸びるため）")
        print("  - 床版は、これらの平行な線形を橋軸直角方向（Y方向）に結んで多角形を形成します")
        print("\n【線形の本数について】")
        print("  Q: TG1LとTG3Rだけでも四角形はできるのでは？")
        print("  A: はい、TG1LとTG3Rだけでも長方形（四角形）はできます。")
        print("     しかし、4本の線形（TG1L, TG1R, TG3R, TG3L）を指定することで、")
        print("     より複雑な形状（台形や平行四辺形）を表現できます。")
        print("\n【2本の線形の場合（例：TG1L, TG3R）】")
        print("  - 単純な長方形（四角形）を形成")
        print("  - 左端と右端の2本の線で囲まれた形状")
        print("  - 直橋の場合に適している")
        print("\n【4本の線形の場合（例：TG1L, TG1R, TG3R, TG3L）】")
        print("  - より複雑な形状（台形や平行四辺形）を表現可能")
        print("  - 左端、左内側、右端、右内側の4本の線で囲まれた形状")
        print("  - 斜橋や可変橋の場合、各線形のY座標がX座標に応じて変化するため、")
        print("    4本の線形が必要になることがあります")
        print("  - 各桁の上フランジの幅を正確に反映できる")
        print("\n【3桁橋の例（4本の線形）】")
        print("  図解（上から見た図、X軸は画面奥行き方向、Y軸は左右方向）:")
        print("    Y軸（左右）")
        print("    ←──────────────→")
        print("    TG1L │  ← 桁1の左端")
        print("    TG1R │  ← 桁1の右端")
        print("    TG2L │  ← 桁2の左端（省略可能）")
        print("    TG2R │  ← 桁2の右端（省略可能）")
        print("    TG3L │  ← 桁3の左端")
        print("    TG3R │  ← 桁3の右端")
        print("  各線形は全てX軸方向（橋軸方向）に伸びる平行線です")
        print("  床版は、これらの線形をY軸方向（橋軸直角方向）に結んで多角形を形成します")
        print("\n【線形の指定方法】")
        print("  左から右へ（または右から左へ）順番に線形を指定します")
        print("  例（2本）: TG1L, TG3R  → 長方形")
        print("  例（4本）: TG1L, TG1R, TG3R, TG3L  → 台形や平行四辺形")
        print("  （最後の線形から最初の線形に自動的に戻って閉じた多角形になります）")
        print("\n【線形の順序について】")
        print("  3桁橋の場合、以下の2つの順序が考えられます：")
        print("  1. TG1L → TG1R → TG3R → TG3L（標準・推奨）")
        print("     左端 → 左内側 → 右端 → 右内側")
        print("     この順序は、左から右へ、外側から内側へという自然な流れです")
        print("     実際のJSONファイル（sample_simple6.json, sample_skew_bridge.json）でも")
        print("     この順序が使用されています")
        print("  2. TG1L → TG1R → TG3L → TG3R")
        print("     左端 → 左内側 → 右内側 → 右端")
        print("     この順序も技術的には可能ですが、外側の線形（TG3R）が途中で")
        print("     挟まれるため、一般的ではありません")
        print("\n【実際の使用例】")
        print("  sample_simple6.json, sample_skew_bridge.json:")
        print('    "Line": ["TG1L", "TG1R", "TG3R", "TG3L"]')
        print("  → この順序（TG1L, TG1R, TG3R, TG3L）が標準として使用されています")
        print("\n【順序の覚え方】")
        print("  左から右へ、外側から内側へ：")
        print("    TG1L（左外） → TG1R（左内） → TG3R（右外） → TG3L（右内）")
        print("\n【線形の意味】")
        print("  - TG1L: 桁1の上フランジ左端の線形（左側の外側、X軸方向に伸びる）")
        print("  - TG1R: 桁1の上フランジ右端の線形（左側の内側、X軸方向に伸びる）")
        print("  - TG3R: 桁3の上フランジ右端の線形（右側の外側、X軸方向に伸びる）")
        print("  - TG3L: 桁3の上フランジ左端の線形（右側の内側、X軸方向に伸びる）")
        print("  ※ これらの線形は、Senkeiで定義した線形名を使用します")
        print("  ※ 全ての線形は橋軸方向（X方向）に伸びる平行線です")
        print("\n【注意】")
        print("  - 線形は2本以上であれば構いません（2本で長方形、4本で台形など）")
        print("  - 線形の順序は重要です（Y軸方向の並び順）")
        print("  - 最後の線形から最初の線形に自動的に戻って閉じます")
        print("  - 同じ線形を2回入力する必要はありません（自動的に閉じます）")
        print("  - コンマ区切りで一度に複数入力できます（例: TG1L, TG1R, TG3R, TG3L）")

        # デフォルト値を既存データから生成
        default_lines = self._get_default_deck_lines()
        print(f"\n  ※ 既存データから推奨: {default_lines}")
        line_input = self.input_str("線形名", default_lines)
        if not line_input:
            return

        # コンマ区切りで分割
        lines = [line.strip() for line in line_input.split(",") if line.strip()]

        # 重複チェック
        unique_lines = []
        for line in lines:
            if line not in unique_lines:
                unique_lines.append(line)
                print(f"  ✓ 線形 {line} を追加（現在{len(unique_lines)}本）")
            else:
                print(f"  ※ 線形 {line} は既に追加されています（スキップ）")
        lines = unique_lines

        if len(lines) < 3:
            print("  警告: 線形が3本未満です。床版を形成できません")
            if not self.input_yes_no("続行しますか？", False):
                return

        # セクション
        print("\n【セクションの指定】")
        print("床版が使用するセクションを指定します")
        print("  - コンマ区切りで一度に複数入力できます")

        # デフォルト値を既存データから生成
        default_sections = self._get_all_sections()
        print(f"\n  ※ 既存データから推奨: {default_sections}")
        section_input = self.input_str("セクション名", default_sections)
        if not section_input:
            return

        # コンマ区切りで分割
        sections = [section.strip() for section in section_input.split(",") if section.strip()]

        if not sections:
            print("  警告: セクションが指定されていません")
            if not self.input_yes_no("続行しますか？", False):
                return

        # オーバーハング
        print("\n【オーバーハング】")
        print("床版が主桁からはみ出す部分の幅（mm）")
        print("  - OverhangLeft: 左側のはみ出し")
        print("  - OverhangRight: 右側のはみ出し")
        print("\n【例】")
        print("  通常: 500mm程度")
        overhang_left = self.input_float("左オーバーハング (mm)", 500.0)
        overhang_right = self.input_float("右オーバーハング (mm)", 500.0)

        # 厚み
        print("\n【床版厚み】")
        print("床版の厚さ（mm）")
        print("  - 通常: 200mm程度")
        thick = self.input_float("床版厚み (mm)", 200.0)

        # Break
        print("\n【分割設定 (Break)】")
        print("床版を3次元的に分割する設定です")
        has_break = self.input_yes_no("分割設定 (Break) を追加しますか？", True)
        break_data = {}
        if has_break:
            # 厚さ方向分割
            break_thick = self.input_int("厚さ方向分割数 (例: 2)", 2)
            no_thick_break_for_flange = self.input_yes_no(
                "上フランジ部分を厚さ分割しない (NoThickBreakForFlange)", True
            )

            # 高度な分割オプション
            use_advanced = self.input_yes_no(
                "高度な分割設定を使用しますか？（ウェブ位置分割、セクション位置分割など）", False
            )

            if use_advanced:
                xy_break = self._input_deck_break_settings("床版")
                break_data = {
                    "Thick": break_thick,
                    "X": xy_break.get("X", 4),
                    "Y": xy_break.get("Y", 3),
                    "NoThickBreakForFlange": no_thick_break_for_flange,
                }
            else:
                # 従来の等分割
                break_x = self.input_int("X方向（橋軸方向）分割数", 4)
                break_y = self.input_int("Y方向（橋軸直角方向）分割数", 3)
                break_data = {
                    "Thick": break_thick,
                    "X": break_x,
                    "Y": break_y,
                    "NoThickBreakForFlange": no_thick_break_for_flange,
                }

            # 設定表示
            x_info = (
                break_data["X"]
                if isinstance(break_data["X"], int)
                else f"高度設定({break_data['X'].get('Type', 'unknown')})"
            )
            y_info = (
                break_data["Y"]
                if isinstance(break_data["Y"], int)
                else f"高度設定({break_data['Y'].get('Type', 'unknown')})"
            )
            print(f"  → 分割設定: 厚さ{break_thick}、X方向={x_info}、Y方向={y_info}")

        # Guardrail
        print("\n【高欄 (Guardrail)】")
        print("床版の左右の端に配置される高欄（ガードレール）の設定")
        print("  - Width: 高欄の幅（mm、床版の端に垂直な方向）")
        print("  - Height: 高欄の高さ（mm、床版の上面から上方向）")
        print("  - Break: 分割設定")
        print("    * false: 分割しない（1つのソリッド）")
        print("    * 数値: その数で等分割")
        print("    * 配列: 指定された長さで分割")
        print("\n【例】")
        print("  幅200mm、高さ1000mm、分割なし: Width=200, Height=1000, Break=false")
        has_guardrail = self.input_yes_no("高欄 (Guardrail) を追加しますか？", False)
        guardrail_data = {}
        if has_guardrail:
            print("\n【左高欄の設定】")
            left_width = self.input_float("左高欄の幅 (mm, 例: 200)", 200.0)
            left_height = self.input_float("左高欄の高さ (mm, 例: 1000)", 1000.0)
            print("  分割設定: false=分割なし, 数値=等分割, 配列=指定長さで分割")
            left_break_input = self.input_str("左高欄の分割 (false/数値/配列, 例: false)", "false")
            if left_break_input.lower() == "false":
                left_break = False
            elif left_break_input.isdigit():
                left_break = int(left_break_input)
            else:
                try:
                    left_break = [float(x.strip()) for x in left_break_input.strip("[]").split(",")]
                except:
                    left_break = False

            print("\n【右高欄の設定】")
            right_width = self.input_float("右高欄の幅 (mm, 例: 200)", 200.0)
            right_height = self.input_float("右高欄の高さ (mm, 例: 1000)", 1000.0)
            print("  分割設定: false=分割なし, 数値=等分割, 配列=指定長さで分割")
            right_break_input = self.input_str("右高欄の分割 (false/数値/配列, 例: false)", "false")
            if right_break_input.lower() == "false":
                right_break = False
            elif right_break_input.isdigit():
                right_break = int(right_break_input)
            else:
                try:
                    right_break = [float(x.strip()) for x in right_break_input.strip("[]").split(",")]
                except:
                    right_break = False

            guardrail_data = {
                "Left": {"Width": left_width, "Height": left_height, "Break": left_break},
                "Right": {"Width": right_width, "Height": right_height, "Break": right_break},
            }

        shouban = {
            "Name": name,
            "Line": lines,
            "Sec": sections,
            "OverhangLeft": overhang_left,
            "OverhangRight": overhang_right,
            "Thickness": thick,  # 床版厚み（mm）
            "ZOffset": 0.0,  # Z方向オフセット（上フランジ上面からの距離、デフォルト0）
            "Break": break_data if break_data else {},
            "Guardrail": guardrail_data if guardrail_data else {},
        }

        self.data["Shouban"].append(shouban)
        print(f"\n✓ 床版 {name} を追加しました")

    def _create_shouban_layers(self):
        """複数レイヤーの床版を作成"""
        print("\n【床版レイヤー設定】")
        print("床版を複数のレイヤー（上面、下面など）に分けて作成します。")
        print("各レイヤーは独立した床版として生成され、異なる分割パターンを設定できます。")

        # 共通設定
        print("\n【共通設定】")
        base_name = self.input_str("床版ベース名 (例: Deck_Main)", "Deck_Main")

        # デフォルト値を既存データから生成
        default_lines = self._get_default_deck_lines()
        default_sections = self._get_all_sections()

        # 線形
        print("\n【線形の指定（全レイヤー共通）】")
        print("床版の形状を定義する線形を指定します（コンマ区切り）")
        print(f"  ※ 既存データから推奨: {default_lines}")
        line_input = self.input_str("線形名", default_lines)
        lines = [line.strip() for line in line_input.split(",") if line.strip()]

        # セクション
        print("\n【セクション（全レイヤー共通）】")
        print(f"  ※ 既存データから推奨: {default_sections}")
        section_input = self.input_str("セクション名", default_sections)
        sections = [section.strip() for section in section_input.split(",") if section.strip()]

        # オーバーハング
        print("\n【オーバーハング（全レイヤー共通）】")
        overhang_left = self.input_float("左オーバーハング (mm)", 500.0)
        overhang_right = self.input_float("右オーバーハング (mm)", 500.0)

        # レイヤー数
        print("\n【レイヤー数】")
        print("通常は2（上面と下面）です。")
        num_layers = self.input_int("レイヤー数", 2)

        # 全体の床版厚み
        total_thickness = self.input_float("床版全体の厚み (mm)", 200.0)

        # 各レイヤーの設定
        print("\n【各レイヤーの設定】")
        print("下から順番に設定します（レイヤー0が最下層）。")

        layer_thicknesses = []
        layer_breaks = []

        for i in range(num_layers):
            print(
                f"\n--- レイヤー {i} ({['下面', '上面', '中間'][min(i, 2)] if num_layers <= 3 else f'レイヤー{i}'}) ---"
            )

            # 厚み
            default_thickness = total_thickness / num_layers
            thickness = self.input_float(f"レイヤー{i}の厚み (mm)", default_thickness)
            layer_thicknesses.append(thickness)

            # 分割設定（高度なオプション）
            use_advanced = self.input_yes_no(f"レイヤー{i}の高度な分割設定を使用しますか？", False)
            if use_advanced:
                break_data = self._input_deck_break_settings(f"レイヤー{i}")
                layer_breaks.append(break_data)
            else:
                # 従来の等分割
                print(f"\n【レイヤー{i}の分割設定（等分割）】")
                break_x = self.input_int("X方向分割数", 4)
                break_y = self.input_int("Y方向分割数", 3)
                layer_breaks.append({"X": break_x, "Y": break_y})

        # 各レイヤーのZ方向オフセットを計算
        z_offsets = [0.0]  # 最下層は0
        for i in range(1, num_layers):
            z_offsets.append(z_offsets[-1] + layer_thicknesses[i - 1])

        # 高欄（地覆）設定 - 最上層のみ
        print("\n【高欄・地覆設定】")
        print("高欄（地覆）は最上層（上面）に追加されます。")
        has_guardrail = self.input_yes_no("高欄・地覆を追加しますか？", False)
        guardrail_data = {}
        if has_guardrail:
            print("\n【左高欄の設定】")
            left_width = self.input_float("左高欄の幅 (mm, 例: 200)", 200.0)
            left_height = self.input_float("左高欄の高さ (mm, 例: 1000)", 1000.0)
            print("  分割設定: false=分割なし, 数値=等分割, 配列=指定長さで分割")
            left_break_input = self.input_str("左高欄の分割 (false/数値/配列, 例: false)", "false")
            if left_break_input.lower() == "false":
                left_break = False
            elif left_break_input.isdigit():
                left_break = int(left_break_input)
            else:
                try:
                    left_break = [float(x.strip()) for x in left_break_input.strip("[]").split(",")]
                except:
                    left_break = False

            print("\n【右高欄の設定】")
            right_width = self.input_float("右高欄の幅 (mm, 例: 200)", 200.0)
            right_height = self.input_float("右高欄の高さ (mm, 例: 1000)", 1000.0)
            print("  分割設定: false=分割なし, 数値=等分割, 配列=指定長さで分割")
            right_break_input = self.input_str("右高欄の分割 (false/数値/配列, 例: false)", "false")
            if right_break_input.lower() == "false":
                right_break = False
            elif right_break_input.isdigit():
                right_break = int(right_break_input)
            else:
                try:
                    right_break = [float(x.strip()) for x in right_break_input.strip("[]").split(",")]
                except:
                    right_break = False

            guardrail_data = {
                "Left": {"Width": left_width, "Height": left_height, "Break": left_break},
                "Right": {"Width": right_width, "Height": right_height, "Break": right_break},
            }

        # レイヤーを生成
        print("\n【生成される床版レイヤー】")
        for i in range(num_layers):
            layer_name = f"{base_name}_L{i}"
            z_offset = z_offsets[i]
            thickness = layer_thicknesses[i]

            # Break設定を構築
            x_break = layer_breaks[i].get("X", 4)
            y_break = layer_breaks[i].get("Y", 3)

            break_data = {
                "Thick": 1,  # 各レイヤーは厚さ方向に分割しない（既に分割済み）
                "X": x_break,
                "Y": y_break,
                "NoThickBreakForFlange": True,
            }

            # 高欄は最上層のみに設定
            is_top_layer = i == num_layers - 1
            layer_guardrail = guardrail_data if is_top_layer else {}

            shouban = {
                "Name": layer_name,
                "Line": lines,
                "Sec": sections,
                "OverhangLeft": overhang_left,
                "OverhangRight": overhang_right,
                "Thickness": thickness,
                "ZOffset": z_offset,
                "Break": break_data,
                "Guardrail": layer_guardrail,
            }

            self.data["Shouban"].append(shouban)

            # 表示用の分割情報を生成
            x_info = x_break if isinstance(x_break, int) else f"{x_break.get('Type', 'custom')}"
            y_info = y_break if isinstance(y_break, int) else f"{y_break.get('Type', 'custom')}"
            guardrail_info = " (高欄あり)" if is_top_layer and guardrail_data else ""
            print(f"  ✓ {layer_name}: 厚み={thickness}mm, ZOffset={z_offset}mm, X={x_info}, Y={y_info}{guardrail_info}")

        print(f"\n✓ 合計 {num_layers} 個の床版レイヤーを追加しました")

    def create_bearing(self):
        """Bearingセクションを作成"""
        self.print_section("支承 (Bearing)")

        # 既存データの確認
        if not self.check_existing_data("Bearing", "支承"):
            return

        print("支承（Bearing）を追加します。")
        print("支承は下フランジの下に配置され、橋梁を支える部材です。")
        print("\n【支承タイプ】")
        print("  - Rubber: ゴム支承（通常は固定端）")
        print("  - Movable: 可動支承（通常は可動端）")
        print("  - Fixed: 固定支承")

        # 一括生成オプション
        print("\n【一括生成オプション】")
        print("複数の桁に対して一度に支承を生成できます。")
        print("  例: 3Girder → G1, G2, G3の両端（S1, E1）に支承を自動生成")
        print("  例: 2Girder → G1, G2の両端（S1, E1）に支承を自動生成")
        use_auto = self.input_yes_no("一括生成を使用しますか？", False)

        if use_auto:
            # 一括生成モード
            print("\n【一括生成設定】")

            # デフォルト桁リストを既存データから生成
            default_girders = self._get_available_girders()
            default_girder_str = ", ".join(default_girders) if default_girders else "G1, G2, G3"
            print(f"  ※ 既存データから推奨: {default_girder_str}")
            girder_input = self.input_str("桁 (例: G1,G2,G3)", default_girder_str)

            # 桁リストを取得
            if girder_input.lower().endswith("girder"):
                try:
                    num_girders = int(girder_input.lower().replace("girder", "").strip())
                    girders = [f"G{i + 1}" for i in range(num_girders)]
                except:
                    print("  警告: 無効な形式です。個別入力に切り替えます。")
                    girders = []
            else:
                # コンマ区切りで桁を指定
                girders = [g.strip() for g in girder_input.split(",") if g.strip()]

            if not girders:
                print("  警告: 桁が指定されていません。個別入力に切り替えます。")
                use_auto = False
            else:
                print(f"  対象桁: {', '.join(girders)}")

                # セクション設定
                print("\n【セクション設定】")
                print("支承を配置するセクションを指定します")
                print("  通常: S1（開始端）とE1（終端）の両方に配置")
                section_input = self.input_str("セクション名 (例: S1,E1 または EnterでS1,E1)", "S1,E1")
                if not section_input:
                    sections = ["S1", "E1"]
                else:
                    sections = [s.strip() for s in section_input.split(",") if s.strip()]

                if not sections:
                    sections = ["S1", "E1"]

                print(f"  対象セクション: {', '.join(sections)}")

                # タイプ設定（セクションごと）
                print("\n【支承タイプ設定】")
                print("各セクションに配置する支承タイプを指定します")
                print("  例: S1=Rubber, E1=Movable")
                type_map = {}
                for section in sections:
                    default_type = "Rubber" if section == "S1" else "Movable"
                    bearing_type = self.input_str(
                        f"{section}側の支承タイプ (Rubber/Movable/Fixed, 例: {default_type})", default_type
                    )
                    type_map[section] = bearing_type

                # 形状設定（タイプごと）
                print("\n【支承形状設定】")
                print("各タイプの支承の形状を設定します")
                shape_map = {}
                for bearing_type in set(type_map.values()):
                    print(f"\n【{bearing_type}支承の形状】")
                    if bearing_type == "Rubber":
                        default_length, default_width, default_height = 450.0, 450.0, 60.0
                    elif bearing_type == "Movable":
                        default_length, default_width, default_height = 550.0, 450.0, 70.0
                    else:  # Fixed
                        default_length, default_width, default_height = 500.0, 400.0, 50.0

                    length = self.input_float(f"{bearing_type}支承の長さ (mm)", default_length)
                    width = self.input_float(f"{bearing_type}支承の幅 (mm)", default_width)
                    height = self.input_float(f"{bearing_type}支承の高さ (mm)", default_height)
                    shape_map[bearing_type] = {"Length": length, "Width": width, "Height": height}

                # 位置設定
                print("\n【位置設定】")
                print("支承の位置オフセットを設定します")
                print("  Z方向オフセット: デフォルト0mm（下フランジ下面に配置）")
                offset_z = self.input_float("Z方向オフセット (mm, デフォルト0)", 0.0)

                offset_y = self.input_float("Y方向オフセット (mm, 通常0)", 0.0)
                local_offset_y = self.input_float("ローカルY方向オフセット (mm, 通常0)", 0.0)

                # 一括生成
                count = 0
                for girder in girders:
                    # G1 → BG1, G2 → BG2, G3 → BG3
                    girder_num = girder[1:] if girder.startswith("G") else girder
                    line = f"BG{girder_num}"
                    for section in sections:
                        bearing_type = type_map[section]
                        name = f"Bearing_{girder}_{section}"

                        # 既存の支承をチェック（支承専用の処理を使用）
                        name = self.handle_existing_name_for_bearing(
                            name, girder, section, self.data.get("Bearing", [])
                        )
                        if name is None:
                            continue

                        # LocalOffsetXのデフォルト値計算（セクションに応じて）
                        bearing_length = shape_map[bearing_type]["Length"]
                        if section == "S1":
                            default_local_offset_x = bearing_length / 2.0  # 支承の長さの半分
                        elif section == "E1":
                            default_local_offset_x = -bearing_length / 2.0  # 支承の長さの半分に-1をかけたもの
                        else:
                            default_local_offset_x = 0.0  # その他のセクションは0

                        bearing = {
                            "Name": name,
                            "Girder": girder,
                            "Section": section,
                            "Type": bearing_type,
                            "Shape": shape_map[bearing_type].copy(),
                            "Position": {
                                "Line": line,
                                "OffsetZ": offset_z,
                                "OffsetY": offset_y,
                                "LocalOffsetX": default_local_offset_x,
                                "LocalOffsetY": local_offset_y,
                            },
                        }

                        self.data["Bearing"].append(bearing)
                        count += 1
                        print(f"  ✓ 支承 {name} を追加しました")

                print(f"\n✓ 合計 {count} 個の支承を一括生成しました")
                return

        # 個別入力モード
        while True:
            print("\n--- 新しい支承を追加 ---")
            name = self.input_str("支承名 (例: Bearing_G1_S1, Enterで終了)")
            if not name:
                break

            # 既存の支承をチェック（支承専用の処理を使用）
            # 名前から桁・セクション情報を抽出
            import re

            match = re.match(r"^Bearing_(G\d+)_(\w+)$", name)
            if match:
                girder_from_name = match.group(1)
                section_from_name = match.group(2)
                name = self.handle_existing_name_for_bearing(
                    name, girder_from_name, section_from_name, self.data.get("Bearing", [])
                )
            else:
                # 名前の形式が想定外の場合は通常の処理を使用
                name = self.handle_existing_name(name, "支承", self.data.get("Bearing", []))
            if name is None:
                continue

            print("\n【支承の基本情報】")
            bearing_type = self.input_str("支承タイプ (Rubber/Movable/Fixed, 例: Rubber)", "Rubber")
            girder = self.input_str("桁番号 (例: G1)", "G1")
            section = self.input_str("セクション名 (例: S1)", "S1")
            line = self.input_str("線形名 (例: BG1, 下フランジの線形)", "BG1")

            # Shape
            print("\n【支承の形状（直方体ブロック）】")
            print("  - Length: 長さ（mm、X軸方向）")
            print("  - Width: 幅（mm、Y軸方向）")
            print("  - Height: 高さ（mm、Z軸方向）")
            print("\n【例】")
            print("  ゴム支承: 450×450×60mm")
            print("  可動支承: 550×450×70mm")
            length = self.input_float("長さ (mm, 例: 450)", 450.0)
            width = self.input_float("幅 (mm, 例: 450)", 450.0)
            height = self.input_float("高さ (mm, 例: 60)", 60.0)

            # Position
            print("\n【支承の位置】")
            print("  - OffsetZ: Z方向オフセット（mm、下フランジ下面からの距離、デフォルト0mm）")
            print("  - OffsetY: Y方向オフセット（mm、通常0）")
            print("  - LocalOffsetX: ローカルX方向オフセット（mm、セクションに応じて自動設定）")
            print("    * S1の場合: 支承の長さの半分（支承が内側に収まるように）")
            print("    * E1の場合: 支承の長さの半分に-1をかけたもの（支承が内側に収まるように）")
            print("  - LocalOffsetY: ローカルY方向オフセット（mm、微調整用、通常0）")
            offset_z = self.input_float("Z方向オフセット (mm, デフォルト0)", 0.0)
            offset_y = self.input_float("Y方向オフセット (mm, 例: 0)", 0.0)

            # LocalOffsetXのデフォルト値計算（セクションに応じて）
            if section == "S1":
                default_local_offset_x = length / 2.0  # 支承の長さの半分
            elif section == "E1":
                default_local_offset_x = -length / 2.0  # 支承の長さの半分に-1をかけたもの
            else:
                default_local_offset_x = 0.0  # その他のセクションは0

            local_offset_x = self.input_float(
                f"ローカルX方向オフセット (mm, デフォルト: {default_local_offset_x:.1f})", default_local_offset_x
            )
            local_offset_y = self.input_float("ローカルY方向オフセット (mm, 例: 0)", 0.0)

            bearing = {
                "Name": name,
                "Girder": girder,
                "Section": section,
                "Type": bearing_type,
                "Shape": {"Length": length, "Width": width, "Height": height},
                "Position": {
                    "Line": line,
                    "OffsetZ": offset_z,
                    "OffsetY": offset_y,
                    "LocalOffsetX": local_offset_x,
                    "LocalOffsetY": local_offset_y,
                },
            }

            self.data["Bearing"].append(bearing)
            print(f"\n✓ 支承 {name} を追加しました")

            if not self.input_yes_no("さらに支承を追加しますか？", True):
                break

    def create_taikeikou(self):
        """対傾構（Taikeikou）セクションを作成"""
        self.print_section("対傾構 (Taikeikou)")

        # 既存データの確認
        if not self.check_existing_data("Taikeikou", "対傾構"):
            return

        print("対傾構（Taikeikou）を追加します。")
        print("対傾構は2つの桁を接続する斜めの部材です。")

        # 一括生成オプション
        print("\n【一括生成オプション】")
        print("複数の桁間に対して一度に対傾構を生成できます。")
        print("  例: 3Girder → G1-G2, G2-G3の対傾構を自動生成")
        use_auto = self.input_yes_no("一括生成を使用しますか？", False)

        if use_auto:
            # 一括生成モード
            print("\n【一括生成設定】")

            # デフォルト桁リストを既存データから生成
            default_girders = self._get_available_girders()
            default_girder_str = ", ".join(default_girders) if default_girders else "G1, G2, G3"
            print(f"  ※ 既存データから推奨: {default_girder_str}")
            girder_input = self.input_str("桁 (例: G1,G2,G3)", default_girder_str)

            # 桁リストを取得
            if girder_input.lower().endswith("girder"):
                try:
                    num_girders = int(girder_input.lower().replace("girder", "").strip())
                    girders = [f"G{i + 1}" for i in range(num_girders)]
                except:
                    print("  警告: 無効な形式です。個別入力に切り替えます。")
                    girders = []
            else:
                # コンマ区切りで桁を指定
                girders = [g.strip() for g in girder_input.split(",") if g.strip()]

            if not girders or len(girders) < 2:
                print("  警告: 桁が2つ以上指定されていません。個別入力に切り替えます。")
                use_auto = False
            else:
                print(f"  対象桁: {', '.join(girders)}")

                # セクション設定
                print("\n【セクション設定】")
                print("対傾構を配置する位置を指定します。")
                print("  - 複数のセクションを指定: コンマ区切りで入力（例: C1,C3,C5）")
                print("  - 各セクションごとに対傾構が生成されます")

                # デフォルト値を既存データから生成（中間セクション）
                default_sections = self._get_middle_sections()
                print(f"  ※ 既存データから推奨: {default_sections}")
                section_input = self.input_str("セクション名", default_sections)
                if not section_input:
                    section_input = default_sections

                # コンマ区切りで分割
                sections = [s.strip() for s in section_input.split(",") if s.strip()]
                if not sections:
                    sections = ["C1"]

                print(f"  セクション名ベース: {', '.join(sections)} を使用します（{len(sections)}個のセクション）")

                # 形状設定
                print("\n【対傾構の形状設定】")
                print("各方向の部材の形状を設定します")
                print("  形式: [型鋼タイプ, サイズ, 材質, 向き, オフセット, ピッチ]")
                print("\n【ピッチ（Pitch）の詳細説明】")
                print("  ピッチは、対傾構の部材（水平材や斜材）に沿って何かを配置する")
                print('  際の間隔を表します。形式: "開始位置/中間間隔/終了位置"')
                print("\n【重要な理解】")
                print("  - セクション（C1）は対傾構の配置位置を決めます（線形上の点）")
                print("  - ピッチは、その位置で生成される部材の長さに沿って適用されます")
                print("  - 例えば、水平材（T, B）は2つの桁間の距離（例: 2500mm）に")
                print("    沿って生成され、その距離に対してピッチが適用されます")
                print("\n【0/X/0 の意味】")
                print("  - 開始位置: 0 = 部材の開始端から0mm（つまり開始端に配置）")
                print("  - 中間間隔: X = 部材の長さに応じて自動計算される間隔")
                print("  - 終了位置: 0 = 部材の終了端から0mm（つまり終了端に配置）")
                print("  → つまり、部材の両端に配置し、中間は部材長さに応じて自動調整")
                print("\n【具体例】")
                print("  水平材が2つの桁間（2500mm）に配置される場合:")
                print('    "0/X/0" → 開始端(0mm)と終了端(2500mm)に配置、Xは自動計算')
                print('    "100/X/100" → 開始端から100mm、終了端から100mm、中間はX')
                print('    "100/200/300" → 開始端から100mm、200mm間隔、終了端から300mm')
                print("\n【その他のピッチ形式】")
                print('  - "100/200/300": 固定ピッチ（100mm, 200mm, 300mm）')
                print('  - "3@100/X": 100mmを3回繰り返し、残りはX（自動計算）')
                print('  - "100:2": 100mmを2等分（50mm間隔）')
                print("\n【対傾構での使用】")
                print('  通常の対傾構では "0/X/0" を使用します。')
                print("  これは、部材の両端から配置し、中間部分を部材長さに応じて")
                print("  自動調整することを意味します。")
                print("\n【入力例】")
                print("  CT, 95x152x8x8, SM400A, U, 0, 0/X/0")

                shape_t = self.input_str(
                    "上側水平材 (T) (例: CT,95x152x8x8,SM400A,U,0,0/X/0)", "CT,95x152x8x8,SM400A,U,0,0/X/0"
                )
                shape_b = self.input_str(
                    "下側水平材 (B) (例: CT,95x152x8x8,SM400A,D,0,0/X/0)", "CT,95x152x8x8,SM400A,D,0,0/X/0"
                )
                shape_l = self.input_str(
                    "左側斜材 (L) (例: CT,95x152x8x8,SM400A,U,0,0/X/0)", "CT,95x152x8x8,SM400A,U,0,0/X/0"
                )
                shape_r = self.input_str(
                    "右側斜材 (R) (例: CT,95x152x8x8,SM400A,U,0,0/X/0)", "CT,95x152x8x8,SM400A,U,0,0/X/0"
                )

                # 形状をパース
                def parse_shape(shape_str):
                    parts = [s.strip() for s in shape_str.split(",")]
                    if len(parts) >= 6:
                        return [
                            parts[0],
                            parts[1],
                            parts[2],
                            parts[3],
                            int(parts[4]) if parts[4].isdigit() else 0,
                            parts[5],
                        ]
                    return ["CT", "95x152x8x8", "SM400A", "U", 0, "0/X/0"]

                shape_t_parsed = parse_shape(shape_t)
                shape_b_parsed = parse_shape(shape_b)
                shape_l_parsed = parse_shape(shape_l)
                shape_r_parsed = parse_shape(shape_r)

                # 一括生成
                count = 0
                for i in range(len(girders) - 1):
                    girder1 = girders[i]
                    girder2 = girders[i + 1]

                    # 各セクションごとに対傾構を生成
                    for section_idx, section in enumerate(sections):
                        # 対傾構名を生成（セクション名を含める）
                        if len(sections) == 1:
                            name = f"T{i + 1}"
                        else:
                            name = f"T{i + 1}_{section}"

                        # 既存の対傾構をチェック
                        name = self.handle_existing_name(name, "対傾構", self.data.get("Taikeikou", []), "T{num}")
                        if name is None:
                            continue

                        # 線形名を自動決定
                        tg1 = f"TG{girder1[1:]}"  # G1 → TG1
                        tg2 = f"TG{girder2[1:]}"  # G2 → TG2
                        bg1 = f"BG{girder1[1:]}"  # G1 → BG1
                        bg2 = f"BG{girder2[1:]}"  # G2 → BG2

                        taikeikou = {
                            "Name": name,
                            "Type": ["Type1U", "F", "F"],
                            "Girder": [girder1, girder2],
                            "Point": [tg1, tg2, bg2, bg1],
                            "Distmod": {"TL": [0, 0], "TR": [0, 0], "BL": [0, 0], "BR": [0, 0]},
                            "Hole": {"TL": [0, "0", 0], "TR": [0, "0", 0], "BL": [0, "0", 0], "BR": [0, "0", 0]},
                            "Vstiff": {"L": [], "R": []},
                            "Shape": {
                                "T": shape_t_parsed,
                                "B": shape_b_parsed,
                                "L": shape_l_parsed,
                                "R": shape_r_parsed,
                            },
                            "Guss": {"TL": [], "TR": [], "BL": [], "BR": [], "Mid": []},
                        }

                        # セクション指定を追加
                        taikeikou["Section"] = section

                        self.data["Taikeikou"].append(taikeikou)
                        count += 1
                        print(f"  ✓ 対傾構 {name} ({girder1}-{girder2}, セクション: {section}) を追加しました")

                print(f"\n✓ 合計 {count} 個の対傾構を一括生成しました")
                return

        # 個別入力モード
        while True:
            print("\n--- 新しい対傾構を追加 ---")
            name = self.input_str("対傾構名 (例: T1, Enterで終了)")
            if not name:
                break

            # 既存の対傾構をチェック
            name = self.handle_existing_name(name, "対傾構", self.data.get("Taikeikou", []), "T{num}")
            if name is None:
                continue

            print("\n【対傾構の基本情報】")
            girder1 = self.input_str("1つ目の桁 (例: G1)", "G1")
            girder2 = self.input_str("2つ目の桁 (例: G2)", "G2")

            # 線形名を自動決定
            tg1 = f"TG{girder1[1:]}" if girder1.startswith("G") else f"TG{girder1}"
            tg2 = f"TG{girder2[1:]}" if girder2.startswith("G") else f"TG{girder2}"
            bg1 = f"BG{girder1[1:]}" if girder1.startswith("G") else f"BG{girder1}"
            bg2 = f"BG{girder2[1:]}" if girder2.startswith("G") else f"BG{girder2}"

            print(f"  自動決定された線形: {tg1}, {tg2}, {bg2}, {bg1}")
            use_auto_lines = self.input_yes_no("この線形を使用しますか？", True)

            if use_auto_lines:
                point_lines = [tg1, tg2, bg2, bg1]
            else:
                point_input = self.input_str("線形名 (例: TG1,TG2,BG2,BG1)", f"{tg1},{tg2},{bg2},{bg1}")
                point_lines = [p.strip() for p in point_input.split(",") if p.strip()]

            # セクション設定
            print("\n【セクション設定】")
            print("対傾構を配置するセクションを指定します。")
            print("  - セクションは線形（TG*, BG*）上の点を指定します")
            print("  - 例: S1（開始端）, S2, C1（中間点）, E2, E1（終端）")
            print("  - 複数のセクションを指定する場合: コンマ区切りで入力（例: C1,C3,C5）")
            print("  - 複数指定すると、各セクションごとに対傾構が生成されます")
            print("  - デフォルト: C1（中間点）")
            section_input = self.input_str("セクション名 (例: C1 または C1,C3,C5, EnterでC1)", "C1")
            if not section_input:
                section_input = "C1"

            # コンマ区切りで分割
            sections = [s.strip() for s in section_input.split(",") if s.strip()]
            if not sections:
                sections = ["C1"]

            print(f"  セクション名ベース: {', '.join(sections)} を使用します（{len(sections)}個のセクション）")

            # 形状設定
            print("\n【対傾構の形状設定】")
            print("各方向の部材の形状を設定します")
            print("  形式: [型鋼タイプ, サイズ, 材質, 向き, オフセット, ピッチ]")
            print("\n【ピッチ（Pitch）の詳細説明】")
            print("  ピッチは、部材に沿って何かを配置する際の間隔を表します。")
            print('  形式: "開始位置/中間間隔/終了位置"')
            print("\n【0/X/0 の意味】")
            print("  - 開始位置: 0 = 部材の開始端から0mm（つまり開始端に配置）")
            print("  - 中間間隔: X = 部材の長さに応じて自動計算される間隔")
            print("  - 終了位置: 0 = 部材の終了端から0mm（つまり終了端に配置）")
            print("  → つまり、部材の両端に配置し、中間は部材長さに応じて自動調整")
            print("\n【具体例】")
            print("  部材長さが2500mmの場合:")
            print('    "0/X/0" → 開始端(0mm)と終了端(2500mm)に配置、Xは自動計算')
            print('    "100/X/100" → 開始端から100mm、終了端から100mm、中間はX')
            print('    "100/200/300" → 開始端から100mm、200mm間隔、終了端から300mm')
            print("\n【その他のピッチ形式】")
            print('  - "100/200/300": 固定ピッチ（100mm, 200mm, 300mm）')
            print('  - "3@100/X": 100mmを3回繰り返し、残りはX（自動計算）')
            print('  - "100:2": 100mmを2等分（50mm間隔）')
            print("\n【対傾構での使用】")
            print('  通常の対傾構では "0/X/0" を使用します。')
            print("  これは、部材の両端から配置し、中間部分を部材長さに応じて")
            print("  自動調整することを意味します。")
            print("\n【入力例】")
            print("  CT, 95x152x8x8, SM400A, U, 0, 0/X/0")

            shape_t = self.input_str("上側水平材 (T)", "CT,95x152x8x8,SM400A,U,0,0/X/0")
            shape_b = self.input_str("下側水平材 (B)", "CT,95x152x8x8,SM400A,D,0,0/X/0")
            shape_l = self.input_str("左側斜材 (L)", "CT,95x152x8x8,SM400A,U,0,0/X/0")
            shape_r = self.input_str("右側斜材 (R)", "CT,95x152x8x8,SM400A,U,0,0/X/0")

            # 形状をパース
            def parse_shape(shape_str):
                parts = [s.strip() for s in shape_str.split(",")]
                if len(parts) >= 6:
                    return [
                        parts[0],
                        parts[1],
                        parts[2],
                        parts[3],
                        int(parts[4]) if parts[4].isdigit() else 0,
                        parts[5],
                    ]
                return ["CT", "95x152x8x8", "SM400A", "U", 0, "0/X/0"]

            # 各セクションごとに対傾構を生成
            count = 0
            for section_idx, section in enumerate(sections):
                # 対傾構名を生成（複数セクションの場合はセクション名を含める）
                if len(sections) == 1:
                    taikeikou_name = name
                else:
                    taikeikou_name = f"{name}_{section}"

                # 既存の対傾構をチェック（セクション名を含めた名前で）
                taikeikou_name = self.handle_existing_name(
                    taikeikou_name, "対傾構", self.data.get("Taikeikou", []), "T{num}"
                )
                if taikeikou_name is None:
                    continue

                taikeikou = {
                    "Name": taikeikou_name,
                    "Type": ["Type1U", "F", "F"],
                    "Girder": [girder1, girder2],
                    "Point": point_lines,
                    "Distmod": {"TL": [0, 0], "TR": [0, 0], "BL": [0, 0], "BR": [0, 0]},
                    "Hole": {"TL": [0, "0", 0], "TR": [0, "0", 0], "BL": [0, "0", 0], "BR": [0, "0", 0]},
                    "Vstiff": {"L": [], "R": []},
                    "Shape": {
                        "T": parse_shape(shape_t),
                        "B": parse_shape(shape_b),
                        "L": parse_shape(shape_l),
                        "R": parse_shape(shape_r),
                    },
                    "Guss": {"TL": [], "TR": [], "BL": [], "BR": [], "Mid": []},
                }

                # セクション指定を追加
                taikeikou["Section"] = section

                self.data["Taikeikou"].append(taikeikou)
                count += 1
                print(f"  ✓ 対傾構 {taikeikou_name} (セクション: {section}) を追加しました")

            if count > 0:
                print(f"\n✓ 合計 {count} 個の対傾構を追加しました")

            if not self.input_yes_no("さらに対傾構を追加しますか？", True):
                break

    def create_yokokou(self):
        """横桁（Yokogeta）セクションを作成"""
        self.print_section("横桁 (Yokogeta)")

        # 既存データの確認
        if not self.check_existing_data("Yokogeta", "横桁"):
            return

        print("横桁（Yokogeta）を追加します。")
        print("横桁は2つの桁を接続する水平の部材です。")

        # 一括生成オプション
        print("\n【一括生成オプション】")
        print("複数の桁間に対して一度に横桁を生成できます。")
        print("  例: 3Girder → G1-G2, G2-G3の横桁を自動生成")
        use_auto = self.input_yes_no("一括生成を使用しますか？", False)

        if use_auto:
            # 一括生成モード
            print("\n【一括生成設定】")

            # デフォルト桁リストを既存データから生成
            default_girders = self._get_available_girders()
            default_girder_str = ", ".join(default_girders) if default_girders else "G1, G2, G3"
            print(f"  ※ 既存データから推奨: {default_girder_str}")
            girder_input = self.input_str("桁 (例: G1,G2,G3)", default_girder_str)

            # 桁リストを取得
            if girder_input.lower().endswith("girder"):
                try:
                    num_girders = int(girder_input.lower().replace("girder", "").strip())
                    girders = [f"G{i + 1}" for i in range(num_girders)]
                except:
                    print("  警告: 無効な形式です。個別入力に切り替えます。")
                    girders = []
            else:
                # コンマ区切りで桁を指定
                girders = [g.strip() for g in girder_input.split(",") if g.strip()]

            if not girders or len(girders) < 2:
                print("  警告: 桁が2つ以上指定されていません。個別入力に切り替えます。")
                use_auto = False
            else:
                print(f"  対象桁: {', '.join(girders)}")

                # セクション設定
                print("\n【セクション設定】")
                print("横桁を配置するセクションを指定します")

                # デフォルト値を既存データから生成（端点セクション）
                default_end_sections = self._get_end_sections()
                # 横桁は通常S1のみなので、最初の端点を使用
                first_end_section = default_end_sections.split(",")[0].strip() if default_end_sections else "S1"
                print(f"  ※ 利用可能な端点セクション: {default_end_sections}")
                section_input = self.input_str("セクション名", first_end_section)
                section = section_input if section_input else first_end_section

                # 形状設定
                print("\n【横桁の形状設定】")
                print("横桁の形状を設定します")
                print("  形式: [型鋼タイプ, サイズ, 材質]")
                print("  例: CT, 95x152x8x8, SM400A")
                shape_info = self.input_str("形状情報 (例: CT,95x152x8x8,SM400A)", "CT,95x152x8x8,SM400A")

                # 形状をパース
                shape_parts = [s.strip() for s in shape_info.split(",")]
                if len(shape_parts) >= 3:
                    shape_infor = [shape_parts[0], shape_parts[1], shape_parts[2]]
                else:
                    shape_infor = ["CT", "95x152x8x8", "SM400A"]

                # 一括生成
                count = 0
                for i in range(len(girders) - 1):
                    girder1 = girders[i]
                    girder2 = girders[i + 1]
                    name = f"Crossbeam_{girder1}_{girder2}_Span"

                    # 既存の横桁をチェック
                    name = self.handle_existing_name(name, "横桁", self.data.get("Yokokou", []))
                    if name is None:
                        continue

                    yokokou = {
                        "Name": name,
                        "Type": ["L", "Bottom"],
                        "Girder": [f"{girder1}/W", f"{girder2}/W"],
                        "Point": [section, 0, 0, section, 0, 0],
                        "Shape": [
                            {
                                "Name": f"CB{i + 1}",
                                "Infor": shape_infor,
                                "Point": [section, section],
                                "Pitch": [0, "X", 0],
                                "Hole": {"S": [0, "0", "0"], "E": [0, "0", "0"]},
                            }
                        ],
                        "Guss": [],
                    }

                    self.data["Yokokou"].append(yokokou)
                    count += 1
                    print(f"  ✓ 横桁 {name} ({girder1}-{girder2}) を追加しました")

                print(f"\n✓ 合計 {count} 個の横桁を一括生成しました")
                return

        # 個別入力モード
        while True:
            print("\n--- 新しい横桁を追加 ---")
            name = self.input_str("横桁名 (例: Crossbeam_G1_G2_Span, Enterで終了)")
            if not name:
                break

            # 既存の横桁をチェック
            name = self.handle_existing_name(name, "横桁", self.data.get("Yokokou", []))
            if name is None:
                continue

            print("\n【横桁の基本情報】")
            girder1 = self.input_str("1つ目の桁 (例: G1)", "G1")
            girder2 = self.input_str("2つ目の桁 (例: G2)", "G2")

            print("\n【セクション設定】")
            print("  注意: 両端で同じセクション名を使用してください（例: S1とS1）")
            section = self.input_str("セクション名 (例: S1)", "S1")

            # 形状設定
            print("\n【横桁の形状設定】")
            print("  形式: [型鋼タイプ, サイズ, 材質]")
            print("  例: CT, 95x152x8x8, SM400A")
            shape_info = self.input_str("形状情報", "CT,95x152x8x8,SM400A")

            # 形状をパース
            shape_parts = [s.strip() for s in shape_info.split(",")]
            if len(shape_parts) >= 3:
                shape_infor = [shape_parts[0], shape_parts[1], shape_parts[2]]
            else:
                shape_infor = ["CT", "95x152x8x8", "SM400A"]

            yokokou = {
                "Name": name,
                "Type": ["L", "Bottom"],
                "Girder": [f"{girder1}/W", f"{girder2}/W"],
                "Point": [section, 0, 0, section, 0, 0],
                "Shape": [
                    {
                        "Name": "CB1",
                        "Infor": shape_infor,
                        "Point": [section, section],
                        "Pitch": [0, "X", 0],
                        "Hole": {"S": [0, "0", "0"], "E": [0, "0", "0"]},
                    }
                ],
                "Guss": [],
            }

            self.data["Yokokou"].append(yokokou)
            print(f"\n✓ 横桁 {name} を追加しました")

            if not self.input_yes_no("さらに横桁を追加しますか？", True):
                break

    def create_yokokou_lateral_bracing(self):
        """横構（Yokokou_LateralBracing）セクションを作成"""
        self.print_section("横構 (Yokokou_LateralBracing)")

        # 既存データの確認
        if not self.check_existing_data("Yokokou_LateralBracing", "横構"):
            return

        print("横構（Yokokou_LateralBracing）を追加します。")
        print("横構は2つの桁を斜めに接続する部材です。")

        # 一括生成オプション
        print("\n【一括生成オプション】")
        print("複数の桁間に対して一度に横構を生成できます。")
        print("  例: 3Girder → G1-G2, G2-G3の横構を自動生成")
        use_auto = self.input_yes_no("一括生成を使用しますか？", False)

        if use_auto:
            # 一括生成モード
            print("\n【一括生成設定】")

            # デフォルト桁リストを既存データから生成
            default_girders = self._get_available_girders()
            default_girder_str = ", ".join(default_girders) if default_girders else "G1, G2, G3"
            print(f"  ※ 既存データから推奨: {default_girder_str}")
            girder_input = self.input_str("桁 (例: G1,G2,G3)", default_girder_str)

            # 桁リストを取得
            if girder_input.lower().endswith("girder"):
                try:
                    num_girders = int(girder_input.lower().replace("girder", "").strip())
                    girders = [f"G{i + 1}" for i in range(num_girders)]
                except:
                    print("  警告: 無効な形式です。個別入力に切り替えます。")
                    girders = []
            else:
                # コンマ区切りで桁を指定
                girders = [g.strip() for g in girder_input.split(",") if g.strip()]

            if not girders or len(girders) < 2:
                print("  警告: 桁が2つ以上指定されていません。個別入力に切り替えます。")
                use_auto = False
            else:
                print(f"  対象桁: {', '.join(girders)}")

                # 生成モード選択
                print("\n【生成モード選択】")
                print("  1本生成: 各桁間に1本の横構を生成（例: G1S1-G2C1）")
                print("  2本生成（クロス）: 各桁間に2本の横構をクロスして生成（例: G1S1-G2S2 と G1S2-G2S1）")
                generate_mode = self.input_str("生成モード (1本/2本, デフォルト: 1本)", "1本")
                is_cross = generate_mode.strip() in ["2本", "2", "クロス", "cross"]

                # セクション設定
                print("\n【セクション設定】")

                # デフォルト値を既存データから生成
                all_sections = self._get_all_sections()
                print(f"  ※ 利用可能なセクション: {all_sections}")

                if is_cross:
                    print("横構の開始・終了セクションを指定します（2本クロス生成）")
                    start_section = self.input_str("開始セクション", "S1")
                    end_section = self.input_str("終了セクション", "S2")
                else:
                    print("横構の開始・終了セクションを指定します（1本生成）")
                    start_section = self.input_str("開始セクション", "S1")
                    end_section = self.input_str("終了セクション", "C1")

                # 形状設定
                print("\n【横構の形状設定】")
                print("  形式: [型鋼タイプ, サイズ, 材質]")
                print("  例: CT, 118x176x8x8, SM400A")
                shape_info = self.input_str("形状情報", "CT,118x176x8x8,SM400A")

                # 形状をパース
                shape_parts = [s.strip() for s in shape_info.split(",")]
                if len(shape_parts) >= 3:
                    shape = [shape_parts[0], shape_parts[1], shape_parts[2]]
                else:
                    shape = ["CT", "118x176x8x8", "SM400A"]

                # ZOffset設定
                z_offset = self.input_float("Z方向オフセット (mm, 下フランジ内側へ, 例: 400)", 400.0)
                y_offset = self.input_float("Y方向オフセット (mm, 通常0)", 0.0)

                # 一括生成
                count = 0
                for i in range(len(girders) - 1):
                    girder1 = girders[i]
                    girder2 = girders[i + 1]

                    if is_cross:
                        # 2本生成（クロス）
                        for j, (sec1, sec2) in enumerate([(start_section, end_section), (end_section, start_section)]):
                            name = f"LB{i * 2 + j + 1}_{girder1}_{girder2}"

                            # 既存の横構をチェック（横構専用の処理を使用）
                            name = self.handle_existing_name_for_lateral_bracing(
                                name, girder1, girder2, self.data.get("Yokokou_LateralBracing", [])
                            )
                            if name is None:
                                continue

                            # 線形名を自動決定
                            bg1 = f"BG{girder1[1:]}" if girder1.startswith("G") else f"BG{girder1}"
                            bg2 = f"BG{girder2[1:]}" if girder2.startswith("G") else f"BG{girder2}"

                            yokokou_lb = {
                                "Name": name,
                                "Level": "Bottom",
                                "Member": {
                                    "Start": {"Girder": girder1, "Line": bg1, "Section": sec1},
                                    "End": {"Girder": girder2, "Line": bg2, "Section": sec2},
                                },
                                "Shape": shape,
                                "Pitch": [0, "X", 0],
                                "ZOffset": z_offset,
                                "YOffset": y_offset,
                                "Hole": {},
                                "Guss": [],
                            }

                            self.data["Yokokou_LateralBracing"].append(yokokou_lb)
                            count += 1
                            print(f"  ✓ 横構 {name} ({girder1}-{girder2}, {sec1}-{sec2}) を追加しました")
                    else:
                        # 1本生成
                        name = f"LB{i + 1}_{girder1}_{girder2}"

                        # 既存の横構をチェック（横構専用の処理を使用）
                        name = self.handle_existing_name_for_lateral_bracing(
                            name, girder1, girder2, self.data.get("Yokokou_LateralBracing", [])
                        )
                        if name is None:
                            continue

                        # 線形名を自動決定
                        bg1 = f"BG{girder1[1:]}" if girder1.startswith("G") else f"BG{girder1}"
                        bg2 = f"BG{girder2[1:]}" if girder2.startswith("G") else f"BG{girder2}"

                        yokokou_lb = {
                            "Name": name,
                            "Level": "Bottom",
                            "Member": {
                                "Start": {"Girder": girder1, "Line": bg1, "Section": start_section},
                                "End": {"Girder": girder2, "Line": bg2, "Section": end_section},
                            },
                            "Shape": shape,
                            "Pitch": [0, "X", 0],
                            "ZOffset": z_offset,
                            "YOffset": y_offset,
                            "Hole": {},
                            "Guss": [],
                        }

                        self.data["Yokokou_LateralBracing"].append(yokokou_lb)
                        count += 1
                        print(f"  ✓ 横構 {name} ({girder1}-{girder2}, {start_section}-{end_section}) を追加しました")

                print(f"\n✓ 合計 {count} 個の横構を一括生成しました")
                return

        # 個別入力モード
        while True:
            print("\n--- 新しい横構を追加 ---")
            print("  横構名の形式: LB{番号}_{開始桁}_{開始セクション}_{終了桁}_{終了セクション}")
            print("  例: LB5_G3_C4_G4_C3 → 開始桁G3, 開始セクションC4, 終了桁G4, 終了セクションC3")
            name = self.input_str("横構名 (例: LB5_G3_C4_G4_C3, Enterで終了)")
            if not name:
                break

            # 既存の横構をチェック（横構専用の処理を使用）
            # 名前から情報を抽出
            import re

            # 形式1: LB{番号}_{開始桁}_{開始セクション}_{終了桁}_{終了セクション} (例: LB5_G3_C4_G4_C3)
            match_full = re.match(r"^LB\d+_(G\d+)_([CS]\d+|E\d+)_(G\d+)_([CS]\d+|E\d+)$", name)
            # 形式2: LB{番号}_{開始桁}_{終了桁} (例: LB1_G1_G2) - 後方互換性のため
            match_simple = re.match(r"^LB\d+_(G\d+)_(G\d+)$", name)

            # デフォルト値の初期化
            default_start_girder = "G1"
            default_start_line = "BG1"
            default_start_section = "S1"
            default_end_girder = "G2"
            default_end_line = "BG2"
            default_end_section = "S2"

            if match_full:
                # 完全な形式から情報を抽出
                girder1_from_name = match_full.group(1)
                section1_from_name = match_full.group(2)
                girder2_from_name = match_full.group(3)
                section2_from_name = match_full.group(4)

                # デフォルト値を設定
                default_start_girder = girder1_from_name
                default_start_line = (
                    f"BG{girder1_from_name[1:]}" if girder1_from_name.startswith("G") else f"BG{girder1_from_name}"
                )
                default_start_section = section1_from_name
                default_end_girder = girder2_from_name
                default_end_line = (
                    f"BG{girder2_from_name[1:]}" if girder2_from_name.startswith("G") else f"BG{girder2_from_name}"
                )
                default_end_section = section2_from_name

                print(
                    f"  ✓ 横構名から情報を抽出: 開始={girder1_from_name}({section1_from_name}), 終了={girder2_from_name}({section2_from_name})"
                )

                name = self.handle_existing_name_for_lateral_bracing(
                    name, girder1_from_name, girder2_from_name, self.data.get("Yokokou_LateralBracing", [])
                )
            elif match_simple:
                # シンプルな形式から情報を抽出（後方互換性）
                girder1_from_name = match_simple.group(1)
                girder2_from_name = match_simple.group(2)

                # デフォルト値を設定（セクションはデフォルト値のまま）
                default_start_girder = girder1_from_name
                default_start_line = (
                    f"BG{girder1_from_name[1:]}" if girder1_from_name.startswith("G") else f"BG{girder1_from_name}"
                )
                default_end_girder = girder2_from_name
                default_end_line = (
                    f"BG{girder2_from_name[1:]}" if girder2_from_name.startswith("G") else f"BG{girder2_from_name}"
                )

                print(f"  ✓ 横構名から情報を抽出: 開始={girder1_from_name}, 終了={girder2_from_name}")

                name = self.handle_existing_name_for_lateral_bracing(
                    name, girder1_from_name, girder2_from_name, self.data.get("Yokokou_LateralBracing", [])
                )
            else:
                # 名前の形式が想定外の場合は通常の処理を使用
                name = self.handle_existing_name(name, "横構", self.data.get("Yokokou_LateralBracing", []))

            if name is None:
                continue

            print("\n【横構の基本情報】")
            start_girder = self.input_str(f"開始桁 (例: G1, Enterで{default_start_girder})", default_start_girder)
            if not start_girder:
                start_girder = default_start_girder
            start_line = self.input_str(f"開始線形 (例: BG1, Enterで{default_start_line})", default_start_line)
            if not start_line:
                start_line = default_start_line
            start_section = self.input_str(
                f"開始セクション (例: S1, Enterで{default_start_section})", default_start_section
            )
            if not start_section:
                start_section = default_start_section

            end_girder = self.input_str(f"終了桁 (例: G2, Enterで{default_end_girder})", default_end_girder)
            if not end_girder:
                end_girder = default_end_girder
            end_line = self.input_str(f"終了線形 (例: BG2, Enterで{default_end_line})", default_end_line)
            if not end_line:
                end_line = default_end_line
            end_section = self.input_str(f"終了セクション (例: S2, Enterで{default_end_section})", default_end_section)
            if not end_section:
                end_section = default_end_section

            # 形状設定
            print("\n【横構の形状設定】")
            print("  形式: [型鋼タイプ, サイズ, 材質]")
            print("  例: CT, 118x176x8x8, SM400A")
            shape_info = self.input_str("形状情報", "CT,118x176x8x8,SM400A")

            # 形状をパース
            shape_parts = [s.strip() for s in shape_info.split(",")]
            if len(shape_parts) >= 3:
                shape = [shape_parts[0], shape_parts[1], shape_parts[2]]
            else:
                shape = ["CT", "118x176x8x8", "SM400A"]

            z_offset = self.input_float("Z方向オフセット (mm, 下フランジ内側へ, 例: 400)", 400.0)
            y_offset = self.input_float("Y方向オフセット (mm, 通常0)", 0.0)

            yokokou_lb = {
                "Name": name,
                "Level": "Bottom",
                "Member": {
                    "Start": {"Girder": start_girder, "Line": start_line, "Section": start_section},
                    "End": {"Girder": end_girder, "Line": end_line, "Section": end_section},
                },
                "Shape": shape,
                "Pitch": [0, "X", 0],
                "ZOffset": z_offset,
                "YOffset": y_offset,
                "Hole": {},
                "Guss": [],
            }

            self.data["Yokokou_LateralBracing"].append(yokokou_lb)
            print(f"\n✓ 横構 {name} を追加しました")

            if not self.input_yes_no("さらに横構を追加しますか？", True):
                break

    def load_existing(self, filepath: str):
        """既存のJSONファイルを読み込む"""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                self.data = json.load(f)
            print(f"\n✓ ファイルを読み込みました: {filepath}")
            return True
        except FileNotFoundError:
            print(f"\n✗ ファイルが見つかりません: {filepath}")
            return False
        except json.JSONDecodeError as e:
            print(f"\n✗ JSONの解析エラー: {e}")
            return False
        except Exception as e:
            print(f"\n✗ エラー: {e}")
            return False

    def save_json(self, filepath: str):
        """JSONファイルを保存"""
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=4)
            print(f"\n✓ JSONファイルを保存しました: {filepath}")
            return True
        except Exception as e:
            print(f"\n✗ 保存エラー: {e}")
            return False

    def show_summary(self):
        """現在のデータの概要を表示"""
        self.print_section("現在のデータ概要")
        print(f"基本情報: {self.data.get('Infor', {}).get('NameBridge', '未設定')}")
        print(f"線形数: {len(self.data.get('Senkei', []))}")
        print(f"主桁パネル数: {len(self.data.get('MainPanel', []))}")
        print(f"床版数: {len(self.data.get('Shouban', []))}")
        print(f"支承数: {len(self.data.get('Bearing', []))}")
        print(f"対傾構数: {len(self.data.get('Taikeikou', []))}")
        print(f"横桁数: {len(self.data.get('Yokokou', []))}")
        print(f"横構数: {len(self.data.get('Yokokou_LateralBracing', []))}")

    def main_menu(self):
        """メインメニュー"""
        while True:
            self.print_section("メインメニュー")
            print("1. 基本情報 (Infor) を設定")
            print("2. 線形データ (Senkei) を追加・編集")
            print("3. 主桁パネル (MainPanel) を追加・編集")
            print("4. 床版 (Shouban) を追加・編集")
            print("5. 支承 (Bearing) を追加・編集")
            print("6. 対傾構 (Taikeikou) を追加・編集")
            print("7. 横桁 (Yokogeta) を追加・編集")
            print("8. 横構 (Yokokou_LateralBracing) を追加・編集")
            print("9. データ概要を表示")
            print("10. JSONファイルを保存")
            print("11. 既存JSONファイルを読み込む")
            print("0. 終了")

            choice = input("\n選択してください [0-11]: ").strip()

            if choice == "1":
                self.create_infor()
            elif choice == "2":
                self.create_senkei()
            elif choice == "3":
                self.create_mainpanel()
            elif choice == "4":
                self.create_shouban()
            elif choice == "5":
                self.create_bearing()
            elif choice == "6":
                self.create_taikeikou()
            elif choice == "7":
                self.create_yokokou()
            elif choice == "8":
                self.create_yokokou_lateral_bracing()
            elif choice == "9":
                self.show_summary()
            elif choice == "10":
                filepath = self.input_str("保存先ファイル名", "output.json")
                self.save_json(filepath)
            elif choice == "11":
                filepath = self.input_str("読み込むファイル名")
                if filepath:
                    self.load_existing(filepath)
            elif choice == "0":
                if self.input_yes_no("保存せずに終了しますか？", False):
                    break
                else:
                    filepath = self.input_str("保存先ファイル名", "output.json")
                    self.save_json(filepath)
                    break
            else:
                print("無効な選択です")


def main():
    """メイン関数"""
    print("=" * 60)
    print("  鋼橋IFCモデル生成用 JSON対話型生成ツール")
    print("=" * 60)

    builder = JSONBuilder()

    # 既存ファイルの読み込み確認
    load_existing = input("\n既存のJSONファイルを読み込みますか？ [y/N]: ").strip().lower()
    if load_existing in ["y", "yes", "はい"]:
        filepath = input("ファイル名: ").strip()
        if filepath:
            if not builder.load_existing(filepath):
                print("新規作成を開始します")

    # メインメニューを開始
    builder.main_menu()

    print("\n終了しました。ありがとうございました！")


if __name__ == "__main__":
    main()
