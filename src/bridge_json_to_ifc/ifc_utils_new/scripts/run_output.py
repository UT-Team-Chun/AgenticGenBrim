"""
鋼橋IFCモデル生成スクリプト

使用方法:
    python run_output.py [オプション]

オプション:
    -j, --json FILE    入力JSONファイル（省略時はデフォルトファイルを使用）
    -h, --help         ヘルプを表示

出力先:
    output/ifc/{入力JSON名}_{タイムスタンプ}.ifc
    output/txt/{入力JSON名}_{タイムスタンプ}.txt

例:
    python run_output.py                    # デフォルト設定で実行
    python run_output.py -j my_bridge.json  # JSONファイルを指定
    python run_output.py my_bridge.json     # 位置引数でもJSONファイル指定可能
"""

import os
import argparse
from datetime import datetime

from src.bridge_json_to_ifc.ifc_utils_new.core import DefBridge, DefIFC

# デフォルト値
DEFAULT_JSON_FILE = "output_0109.json"

# 出力ディレクトリ
OUTPUT_DIR = "output"
IFC_DIR = os.path.join(OUTPUT_DIR, "ifc")
TXT_DIR = os.path.join(OUTPUT_DIR, "txt")


def parse_args():
    """コマンドライン引数を解析"""
    parser = argparse.ArgumentParser(
        description="鋼橋IFCモデル生成スクリプト",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
例:
    python run_output.py                    # デフォルト設定で実行
    python run_output.py -j my_bridge.json  # JSONファイルを指定
    python run_output.py my_bridge.json     # 位置引数でもJSONファイル指定可能

出力先:
    output/ifc/{入力JSON名}_{タイムスタンプ}.ifc
    output/txt/{入力JSON名}_{タイムスタンプ}.txt
""",
    )

    parser.add_argument(
        "json_file_pos",
        nargs="?",
        default=None,
        metavar="JSON_FILE",
        help="入力JSONファイル（位置引数、-jオプションより優先度低）",
    )

    parser.add_argument(
        "-j",
        "--json",
        dest="json_file",
        default=None,
        metavar="FILE",
        help=f"入力JSONファイル（省略時: {DEFAULT_JSON_FILE}）",
    )

    return parser.parse_args()


def get_output_paths(json_filename, base_dir):
    """入力JSON名とタイムスタンプから出力パスを生成"""
    # ベース名（拡張子除去）
    base_name = os.path.splitext(json_filename)[0]

    # タイムスタンプ
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 絶対パスでディレクトリを作成
    ifc_dir = os.path.join(base_dir, IFC_DIR)
    txt_dir = os.path.join(base_dir, TXT_DIR)

    os.makedirs(ifc_dir, exist_ok=True)
    os.makedirs(txt_dir, exist_ok=True)

    # 出力パス（絶対パス）
    ifc_path = os.path.join(ifc_dir, f"{base_name}_{timestamp}.ifc")
    txt_path = os.path.join(txt_dir, f"{base_name}_{timestamp}.txt")

    return ifc_path, txt_path


def resolve_path(file_path, base_dir):
    """ファイルパスを解決し、locationとファイル名に分割"""
    if file_path is None:
        return None, None

    if os.path.dirname(file_path):
        # パスが含まれている場合
        if os.path.isabs(file_path):
            # 絶対パス
            location = os.path.dirname(file_path) + os.sep
            name = os.path.basename(file_path)
        else:
            # 相対パス
            full_path = os.path.join(base_dir, file_path)
            location = os.path.dirname(full_path) + os.sep
            name = os.path.basename(full_path)
    else:
        # ファイル名のみ
        location = base_dir + os.sep
        name = file_path

    return location, name


def main():
    args = parse_args()

    # カレントワーキングディレクトリを取得（実行時のディレクトリ）
    current_dir = os.getcwd()

    # JSONファイルの決定（-jオプション > 位置引数 > デフォルト）
    if args.json_file:
        json_input = args.json_file
    elif args.json_file_pos:
        json_input = args.json_file_pos
    else:
        json_input = DEFAULT_JSON_FILE

    # JSONファイルのパス解決
    location, name_file = resolve_path(json_input, current_dir)

    # 出力パスを生成（カレントディレクトリ基準の絶対パス）
    ifc_path, txt_path = get_output_paths(name_file, current_dir)

    # 入出力ファイル情報を表示
    print(f"入力: {location}{name_file}")
    print(f"出力: {ifc_path}")
    print(f"要素一覧: {txt_path}")

    # 要素名リストをクリア（前回の実行結果をリセット）
    DefIFC.clear_generated_element_names()

    try:
        DefBridge.RunBridge(location, name_file, ifc_path)

        # 生成された要素名を取得
        element_names = DefIFC.get_generated_element_names()

        # 要素名をファイルに出力
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write("生成されたIFC要素名一覧\n")
            f.write("=" * 60 + "\n")
            f.write(f"総要素数: {len(element_names)}\n")
            f.write("=" * 60 + "\n\n")

            for i, name in enumerate(element_names, 1):
                f.write(f"{i:4d}. {name}\n")

        print(f"完了: {len(element_names)}個の要素を生成")
    except Exception as e:
        import traceback

        print(f"エラー: {e}")
        print(traceback.format_exc())


if __name__ == "__main__":
    main()
