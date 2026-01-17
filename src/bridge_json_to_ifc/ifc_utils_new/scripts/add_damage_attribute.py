# -*- coding: utf-8 -*-
"""
JSONファイルに「損傷度」属性を追加するスクリプト
"""

import json
import os


def add_damage_attribute(input_file, output_file):
    """JSONファイルに損傷度属性を追加"""

    # JSONファイルを読み込む
    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    # MainPanelに損傷度を追加
    if "MainPanel" in data:
        for panel in data["MainPanel"]:
            # パネル全体のデフォルト損傷度
            panel["Damage"] = "None"  # デフォルト値

            # 分割セグメントごとの損傷度（Break.Lenghtと同じ長さ）
            if "Break" in panel and "Lenght" in panel["Break"]:
                length_count = len(panel["Break"]["Lenght"])
                # 各セグメントのデフォルト損傷度を設定
                panel["Break"]["Damage"] = ["None"] * length_count
                # 例として、最初のセグメントに損傷を設定（テスト用）
                # panel["Break"]["Damage"][0] = "D"  # 最初のセグメントを重度損傷に

    # Shoubanに損傷度を追加
    if "Shouban" in data:
        for shouban in data["Shouban"]:
            # 床版全体のデフォルト損傷度
            shouban["Damage"] = "None"

            # 分割セグメントごとの損傷度（オプション）
            # 床版の分割は複雑（X×Y×Thick）なので、まずは全体のDamageのみ
            # 必要に応じて、Break.Damageを追加可能

    # Taikeikouに損傷度を追加
    if "Taikeikou" in data:
        for taikeikou in data["Taikeikou"]:
            taikeikou["Damage"] = "None"

    # Yokokouに損傷度を追加
    if "Yokokou" in data:
        for yokokou in data["Yokokou"]:
            yokokou["Damage"] = "None"

    # Yokokou_LateralBracingに損傷度を追加
    if "Yokokou_LateralBracing" in data:
        for lb in data["Yokokou_LateralBracing"]:
            lb["Damage"] = "None"

    # Bearingに損傷度を追加
    if "Bearing" in data:
        for bearing in data["Bearing"]:
            bearing["Damage"] = "None"

    # Guardrailに損傷度を追加
    if "Shouban" in data:
        for shouban in data["Shouban"]:
            if "Guardrail" in shouban:
                if "Left" in shouban["Guardrail"]:
                    shouban["Guardrail"]["Left"]["Damage"] = "None"
                if "Right" in shouban["Guardrail"]:
                    shouban["Guardrail"]["Right"]["Damage"] = "None"

    # 新しいファイルに保存
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    print(f"損傷度属性を追加しました: {output_file}")


if __name__ == "__main__":
    # スクリプトのディレクトリを取得
    script_dir = os.path.dirname(os.path.abspath(__file__))
    input_file = os.path.join(script_dir, "sample_skew_bridge.json")
    output_file = os.path.join(script_dir, "skew_bridge1.json")

    if os.path.exists(input_file):
        add_damage_attribute(input_file, output_file)
    else:
        print(f"エラー: {input_file} が見つかりません")
