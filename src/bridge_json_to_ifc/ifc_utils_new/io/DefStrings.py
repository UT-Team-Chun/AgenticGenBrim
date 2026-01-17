"""
文字列処理のためのモジュール
ピッチ処理や文字列変換などのユーティリティ関数
"""

import re


def Xu_Ly_Pitch_va_Tim_X(pitch, sum_len):
    """
    ピッチ文字列を処理し、X（未知数）の値を計算する

    ピッチの形式例:
    - "100/200/300" のような固定値
    - "3@100/X" のような未知数を含む形式
    - "100:2" のような比率形式

    Args:
        pitch: ピッチ文字列
        sum_len: 合計長さ

    Returns:
        処理されたピッチ文字列（Xが値に置換された）
    """

    if len(pitch) == 1 and pitch == str(0):
        return pitch
    else:
        try:

            def parse_value(value):
                # Xử lý các định dạng của giá trị
                if "@" in value:
                    count, val = value.split("@")
                    return int(count) * float(val)
                elif ":" in value:
                    num, denom = value.split(":")
                    return float(num) / float(denom)
                else:
                    return float(value)

            if "X" in pitch:
                sum1 = 0
                count_x = 0
                parts = pitch.split("/")

                for part in parts:
                    if part == "X":
                        count_x += 1
                    else:
                        if "@" in part:
                            count, val = part.split("@")
                            count = int(count)
                            if val != "X":
                                sum1 += count * parse_value(val)
                            else:
                                count_x += count
                        elif ":" in part:
                            num, denom = part.split(":")
                            sum1 += float(num) / float(denom)
                        else:
                            sum1 += parse_value(part)
                if count_x == 0:
                    x = 0
                else:
                    x = (sum_len - sum1) / count_x

                pitch_new = ""
                for part in parts:
                    if part != "X":
                        if "@" in part:
                            count, val = part.split("@")
                            count = int(count)

                            for _ in range(count):
                                if pitch_new:
                                    pitch_new += "/" + (str(x) if val == "X" else str(val))
                                else:
                                    pitch_new = str(x) if val == "X" else str(val)

                        elif ":" in part:
                            num, denom = part.split(":")
                            for _ in range(int(denom)):
                                if pitch_new:
                                    pitch_new += "/" + str((float(num) / float(denom)))
                                else:
                                    pitch_new = str(float(num) / float(denom))
                        else:
                            if pitch_new:
                                pitch_new += "/" + str(part)
                            else:
                                pitch_new = str(part)
                    else:
                        if pitch_new:
                            pitch_new += "/" + str(x)
                        else:
                            pitch_new = str(x)
            else:
                parts = pitch.split("/")
                sum1 = 0

                for part in parts:
                    if "@" in part:
                        count, val = part.split("@")
                        sum1 += int(count) * parse_value(val)
                    elif ":" in part:
                        num, denom = part.split(":")
                        sum1 += float(num)
                    else:
                        sum1 += parse_value(part)

                tl = sum_len / sum1
                pitch_new = ""

                for part in parts:
                    if "@" in part:
                        count, val = part.split("@")
                        count = int(count)
                        val = parse_value(val)
                        for _ in range(count):
                            if pitch_new:
                                pitch_new += "/" + str(val * tl)
                            else:
                                pitch_new = str(val * tl)
                    elif ":" in part:
                        num, denom = part.split(":")
                        for _ in range(int(denom)):
                            if pitch_new:
                                pitch_new += "/" + str((float(num) / float(denom)) * tl)
                            else:
                                pitch_new = str((float(num) / float(denom)) * tl)
                    else:
                        if pitch_new:
                            pitch_new += "/" + str(parse_value(part) * tl)
                        else:
                            pitch_new = str(parse_value(part) * tl)

            return pitch_new

        except Exception as ex:
            print(f"Pitch: {pitch} に問題があります\n確認してください！\n{str(ex)}")
            return pitch


def Xu_Ly_Pitch(pitch):
    """
    ピッチ文字列を処理する（Xの計算なし）

    Args:
        pitch: ピッチ文字列

    Returns:
        処理されたピッチ文字列
    """
    try:
        if len(pitch) == 1 and pitch == str(0):
            return pitch

        pitch_new = ""
        parts = pitch.split("/")

        for part in parts:
            if "@" in part:
                count, val = part.split("@")
                count = int(count)
                for _ in range(count):
                    if pitch_new:
                        pitch_new += "/" + val
                    else:
                        pitch_new = val
            elif ":" in part:
                num, denom = part.split(":")
                repeat = int(denom)
                val = float(num) / float(denom)
                for _ in range(repeat):
                    if pitch_new:
                        pitch_new += "/" + str(val)
                    else:
                        pitch_new = str(val)
            else:
                if pitch_new:
                    pitch_new += "/" + part
                else:
                    pitch_new = part

        return pitch_new

    except Exception as ex:
        print(f"Pitch: {pitch} に問題があります\n確認してください！\n{str(ex)}")
        return pitch


def process_array(input_array):
    """
    配列を処理し、文字列を数値に変換する

    Args:
        input_array: 処理する配列（数値、文字列、'N@M'形式など）

    Returns:
        処理された配列（数値のリスト）
    """
    result = []
    for item in input_array:
        if item == 0 or item == "0":  # Xử lý cả số 0 và chuỗi '0'
            result.append(0)
        elif isinstance(item, (int, float)):  # Nếu là số nguyên hoặc số thực, giữ nguyên
            result.append(item)
        elif isinstance(item, str):  # Nếu là chuỗi
            try:
                # Thử chuyển chuỗi thành số nguyên
                result.append(int(item))
            except ValueError:
                # Nếu không phải số nguyên, kiểm tra định dạng 'N@M'
                match = re.match(r"(\d+)@(\d+)", item)
                if match:
                    count, value = map(int, match.groups())
                    result.extend([value] * count)
                else:
                    raise ValueError(f"要素を処理できません: {item}")
        else:
            raise TypeError(f"無効な要素: {item}")
    return result


def Xu_Ly_Chuoi_From_To(Strings_Input):
    """
    "From-To"形式の文字列を処理し、範囲内のすべての値のリストを生成する
    例: "A1-A5" -> ["A1", "A2", "A3", "A4", "A5"]

    Args:
        Strings_Input: "From-To"形式の文字列（例: "A1-A5"）

    Returns:
        範囲内のすべての値のリスト
    """
    result = []

    try:
        start, end = Strings_Input.split("-")

        # 文字部分（あれば）と数値部分を取得
        start_match = re.match(r"([a-zA-Z]*)([0-9]+)", start)
        end_match = re.match(r"([a-zA-Z]*)([0-9]+)", end)

        if start_match and end_match:
            start_prefix = start_match.group(1)  # 文字部分を取得（空の場合もある）
            start_num = int(start_match.group(2))  # 数値部分を取得して整数に変換
            end_num = int(end_match.group(2))  # 同様にend文字列から取得

            # start_numからend_numまでの結果リストを生成
            result = [f"{start_prefix}{i}" for i in range(start_num, end_num + 1)]

    except ValueError:
        print("入力文字列が無効であるか、'-'で分割できません")

    return result


def Chuyen_Name_LRib_thanh_Array(Name_LRib):
    """
    リブ名を配列に変換する
    "From-To"形式の場合は範囲展開、カンマ区切りの場合は分割

    Args:
        Name_LRib: リブ名（"A1-A5"または"A1,A2,A3"形式）

    Returns:
        リブ名のリスト
    """
    if "-" in Name_LRib:
        Name_LRib_New = Xu_Ly_Chuoi_From_To(Name_LRib)
    else:
        Name_LRib_New = Name_LRib.split(",")

    return Name_LRib_New
