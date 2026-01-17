"""
数学計算のためのモジュール
3D座標計算、ベクトル演算、幾何学的変換などの関数群
"""

import math

import numpy as np


def point_per_line(point1_mod, point1_line, point2_line):
    """
    点を直線上に射影する
    点point1_modを点point1_lineとpoint2_lineで定義される直線上に射影した点を返す

    Args:
        point1_mod: 射影する点
        point1_line: 直線上の点1
        point2_line: 直線上の点2

    Returns:
        直線上に射影された点
    """
    point1_mod = np.array(point1_mod, dtype=float)
    if point1_mod.shape[0] == 2:
        point1_mod = np.append(point1_mod, 0.0)
    point1_line = np.array(point1_line, dtype=float)
    if point1_line.shape[0] == 2:
        point1_line = np.append(point1_line, 0.0)
    point2_line = np.array(point2_line, dtype=float)
    if point2_line.shape[0] == 2:
        point2_line = np.append(point2_line, 0.0)
    # 直線の方向ベクトル
    direction = point2_line - point1_line
    norm_direction = np.linalg.norm(direction)
    # ゼロ除算を防ぐための閾値
    epsilon = 1e-10
    if norm_direction < epsilon:
        # point1_lineとpoint2_lineが同じ点の場合、デフォルトの方向ベクトルを返す
        return point1_mod
    direction_unit = direction / norm_direction  # ベクトルを正規化

    # point1_lineからpoint1_modへのベクトル
    vector_mod_line = point1_mod - point1_line

    # vector_mod_lineのdirectionへの射影の長さ
    projection_length = np.dot(vector_mod_line, direction_unit)

    # 射影点の座標
    projection_point = point1_line + projection_length * direction_unit

    return projection_point


def point_per_plan(point1_mod, point1_plan, point2_plan, point3_plan):
    normal = Normal_vector(point1_mod, point1_plan, point2_plan)

    point1_mod_add = point1_mod + 100 * normal

    intersec = Intersection_line_plane(point1_plan, point2_plan, point3_plan, point1_mod, point1_mod_add)

    return intersec


def Calculate_distance_p2p(point1, point2):
    """
    2点間の距離を計算する

    Args:
        point1: 点1の座標 [x, y, z]
        point2: 点2の座標 [x, y, z]

    Returns:
        2点間の距離
    """
    x1, y1, z1 = point1
    x2, y2, z2 = point2

    # 距離を計算
    distance = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2 + (z2 - z1) ** 2)

    return distance


def Point_on_line(p1, p2, distance):
    """
    直線上で基準点から指定距離の位置にある点の座標を計算する

    Args:
        p1: 直線上の基準点
        p2: 直線上のもう一つの点
        distance: p1からの距離

    Returns:
        直線上でp1からdistance離れた点の座標
    """
    p1 = np.array(p1, dtype=float)
    if p1.shape[0] == 2:
        p1 = np.append(p1, 0.0)
    p2 = np.array(p2, dtype=float)
    if p2.shape[0] == 2:
        p2 = np.append(p2, 0.0)
    # p1からp2へのベクトル
    vector = p2 - p1

    # ベクトルの長さ
    length = np.linalg.norm(vector)

    # ゼロ除算を防ぐための閾値
    epsilon = 1e-10
    if length < epsilon:
        # p1とp2が同じ点の場合、p1を返す
        return p1

    # 比率tを計算
    t = distance / length

    # 点Pの座標を計算
    p = p1 + t * vector

    return p


def Point_on_parallel_line(pbase, p1dir, p2dir, distance):
    """
    基準点から指定距離の位置で、p1dir-p2dirの方向と平行な直線上にある点を計算する

    Args:
        pbase: 基準点
        p1dir: 方向を定義する点1
        p2dir: 方向を定義する点2
        distance: pbaseからの距離

    Returns:
        計算された点の座標
    """
    pbase = np.array(pbase, dtype=float)
    if pbase.shape[0] == 2:
        pbase = np.append(pbase, 0.0)
    p1dir = np.array(p1dir, dtype=float)
    if p1dir.shape[0] == 2:
        p1dir = np.append(p1dir, 0.0)
    p2dir = np.array(p2dir, dtype=float)
    if p2dir.shape[0] == 2:
        p2dir = np.append(p2dir, 0.0)

    # p1dirからp2dirへの方向ベクトル
    direction_vector = p2dir - p1dir

    # 方向ベクトルのノルムを計算
    norm_direction = np.linalg.norm(direction_vector)
    # ゼロ除算を防ぐための閾値
    epsilon = 1e-10
    if norm_direction < epsilon:
        # p1dirとp2dirが同じ点の場合、pbaseを返す
        return pbase

    # 方向ベクトルを正規化（単位ベクトル化）
    direction_vector = direction_vector / norm_direction

    # 点Pの座標を計算
    p = pbase + distance * direction_vector

    return p


def is_number(s):
    """
    文字列が数値かどうかをチェックする

    Args:
        s: チェックする文字列

    Returns:
        数値の場合はTrue、そうでなければFalse
    """
    if s is None:
        return False
    try:
        float(s)  # 実数への変換を試行
        return True
    except ValueError:
        return False


def calculate_plane_equation(p1, p2, p3):
    """
    3点から平面の方程式を計算する
    平面方程式: ax + by + cz + d = 0

    Args:
        p1, p2, p3: 平面上の3点

    Returns:
        (a, b, c, d): 平面方程式の係数
    """
    v1 = p2 - p1
    v2 = p3 - p1
    normal = np.cross(v1, v2)
    a, b, c = normal
    d = -np.dot(normal, p1)
    return a, b, c, d


def is_point_on_plane(point, plane_coefficients, epsilon=0.01):
    """
    点が平面上にあるかどうかをチェックする

    Args:
        point: チェックする点
        plane_coefficients: 平面方程式の係数 (a, b, c, d)
        epsilon: 許容誤差

    Returns:
        平面上にあればTrue、そうでなければFalse
    """
    a, b, c, d = plane_coefficients
    return np.abs(a * point[0] + b * point[1] + c * point[2] + d) < epsilon


def is_point_on_line(point, line_start, line_end, epsilon=0.01):
    """
    点が2D線分上にあるかどうかをチェックする

    Args:
        point: チェックする点
        line_start: 線分の開始点
        line_end: 線分の終了点
        epsilon: 許容誤差

    Returns:
        線分上にあればTrue、そうでなければFalse
    """
    # 点と線分をnumpy配列に変換
    line_vec = np.array(line_end) - np.array(line_start)
    point_vec = np.array(point) - np.array(line_start)

    # 点が同じ直線上にあるかどうかを確認するための外積を計算
    cross_product = np.cross(line_vec, point_vec)

    # 外積がほぼ0の場合（点が同じ直線上にあり、距離もチェック）
    return (
        np.linalg.norm(cross_product) <= epsilon
        and np.dot(line_vec, point_vec) >= 0
        and np.dot(line_vec, point_vec) <= np.dot(line_vec, line_vec)
    )


def is_point_in_polygon_2d(point, polygon, epsilon=0.01):
    """
    点が2D多角形（ポリゴン）の領域内にあるかどうかをチェックする

    Args:
        point: チェックする点
        polygon: 多角形の頂点リスト
        epsilon: 許容誤差

    Returns:
        多角形内にあればTrue、そうでなければFalse
    """
    x, y = point
    n = len(polygon)
    inside = False

    for i in range(n):
        p1 = polygon[i]
        p2 = polygon[(i + 1) % n]

        # 点が辺上にあるかチェック
        if is_point_on_line(point, p1, p2, epsilon):
            return True

        # 点が入力点（p1, p2）の間にあるかチェック
        if (p1[1] > y) != (p2[1] > y):
            x_intercept = (p2[0] - p1[0]) * (y - p1[1]) / (p2[1] - p1[1]) + p1[0]
            if x < x_intercept:
                inside = not inside

    return inside


# Kiểm tra điểm có thuộc miền polygon(đa giác 3D) hay không
def is_point_in_polygon_3d(point, polygon_3d, p1, p2, p3):
    p1 = np.array(p1, dtype=float)
    p2 = np.array(p2, dtype=float)
    p3 = np.array(p3, dtype=float)

    # Tính vector pháp tuyến
    normal = np.cross(p2 - p1, p3 - p1)
    if np.linalg.norm(normal) == 0:
        raise ValueError("p1, p2 và p3 không tạo thành một mặt phẳng hợp lệ.")
    normal /= np.linalg.norm(normal)  # Chuẩn hóa

    # Lấy hai vector trong mặt phẳng
    x_axis = p2 - p1
    x_axis /= np.linalg.norm(x_axis)  # Chuẩn hóa
    y_axis = np.cross(normal, x_axis)
    y_axis /= np.linalg.norm(y_axis)  # Chuẩn hóa

    # Ma trận chuyển đổi
    transform_matrix = np.array([x_axis, y_axis])

    def project_to_plane(point):
        return np.dot(transform_matrix, (np.array(point) - p1))

    # Chiếu toàn bộ điểm
    polygon_2d = [project_to_plane(p) for p in polygon_3d]
    point_2d = project_to_plane(point)

    # Kiểm tra xem điểm có nằm trên bất kỳ cạnh nào không
    for i in range(len(polygon_2d)):
        p1 = polygon_2d[i]
        p2 = polygon_2d[(i + 1) % len(polygon_2d)]
        if is_point_on_line(point_2d, p1, p2):
            return True

    # Kiểm tra xem điểm có nằm trong đa giác 2D không
    return is_point_in_polygon_2d(point_2d, polygon_2d)


# Hàm để xây dựng hệ tọa độ cơ sở cho mặt phẳng từ ba điểm
def Build_coordinate_system(base, align, surface):
    base = np.array(base, dtype=float)
    align = np.array(align, dtype=float)
    surface = np.array(surface, dtype=float)

    v1 = align - base
    v1 /= np.linalg.norm(v1)
    temp = surface - base
    v2 = temp - np.dot(temp, v1) * v1
    v2 /= np.linalg.norm(v2)
    v3 = np.cross(v1, v2)
    return np.vstack((v1, v2, v3))


# Hàm để chuyển đổi điểm từ hệ tọa độ này sang hệ tọa độ khác (Align)
def Transform_point_face2face(P, p1, p2, p3, m1, m2, m3):
    P = np.array(P, dtype=float)
    if P.shape[0] == 2:
        P = np.append(P, 0.0)
    p1 = np.array(p1, dtype=float)
    if p1.shape[0] == 2:
        p1 = np.append(p1, 0.0)
    p2 = np.array(p2, dtype=float)
    if p2.shape[0] == 2:
        p2 = np.append(p2, 0.0)
    p3 = np.array(p3, dtype=float)
    if p3.shape[0] == 2:
        p3 = np.append(p3, 0.0)
    m1 = np.array(m1, dtype=float)
    if m1.shape[0] == 2:
        m1 = np.append(m1, 0.0)
    m2 = np.array(m2, dtype=float)
    if m2.shape[0] == 2:
        m2 = np.append(m2, 0.0)
    m3 = np.array(m3, dtype=float)
    if m3.shape[0] == 2:
        m3 = np.append(m3, 0.0)

    # Xây dựng hệ tọa độ cơ sở cho mặt phẳng đầu tiên
    T1 = Build_coordinate_system(p1, p2, p3)

    # Xây dựng hệ tọa độ cơ sở cho mặt phẳng thứ hai
    T2 = Build_coordinate_system(m1, m2, m3)

    # Tính toán ma trận chuyển đổi
    transformation_matrix = np.dot(np.linalg.inv(T2), T1)

    # Chuyển đổi điểm
    P_relative = P - p1
    P_transformed = np.dot(transformation_matrix, P_relative) + m1
    if abs(P_transformed[2] < 0.001):
        P_transformed[2] = 0
    return P_transformed


# Hàm duỗi tọa độ ( khai triển tọa độ từ 3D xuống 2D)
def Expand_Coord_2Line(CoordT, CoordB):
    CoordT_New = CoordT.copy()
    CoordB_New = CoordB.copy()

    pb1 = CoordB[0]
    pb2 = CoordT[0]
    pb3 = CoordB[1]

    pa1 = (0, 0, 0)
    pa2 = (0, 100, 0)
    pa3 = (100, 0, 0)

    for i in range(0, len(CoordT) - 1):
        pb1 = np.array(CoordB[i], dtype=float)
        pb2 = np.array(CoordT[i], dtype=float)
        pb3 = np.array(CoordB[i + 1], dtype=float)

        if i == 0:
            CoordT_New[i] = Transform_point_face2face(CoordT[i], pb1, pb2, pb3, pa1, pa2, pa3)
            CoordB_New[i] = Transform_point_face2face(CoordB[i], pb1, pb2, pb3, pa1, pa2, pa3)

            CoordT_New[i + 1] = Transform_point_face2face(CoordT[i + 1], pb1, pb2, pb3, pa1, pa2, pa3)
            CoordB_New[i + 1] = Transform_point_face2face(CoordB[i + 1], pb1, pb2, pb3, pa1, pa2, pa3)

            pa1 = CoordB_New[i + 1]
            pa2 = CoordT_New[i + 1]
            pa3 = (pa1[0] + 100, pa1[1], pa1[2])
        else:
            CoordT_New[i + 1] = Transform_point_face2face(CoordT[i + 1], pb1, pb2, pb3, pa1, pa2, pa3)
            CoordB_New[i + 1] = Transform_point_face2face(CoordB[i + 1], pb1, pb2, pb3, pa1, pa2, pa3)

            pa1 = CoordB_New[i + 1]
            pa2 = CoordT_New[i + 1]
            pa3 = (pa1[0] + 100, pa1[1], pa1[2])

    return CoordT_New, CoordB_New


# Chuẩn hóa vector
def Normalize_vector(vector):
    """
    ベクトルを正規化（単位ベクトル化）する

    Args:
        vector: 正規化するベクトル

    Returns:
        正規化されたベクトル（単位ベクトル）
    """
    norm = np.linalg.norm(vector)
    # ゼロ除算を防ぐための閾値
    epsilon = 1e-10
    if norm < epsilon:
        # ベクトルがゼロの場合、ゼロベクトルを返す
        return np.zeros_like(vector)
    return vector / norm


# Tính vector pháp tuyến của mặt phẳng p1,p2,p3
def Normal_vector(p1, p2, p3):
    # Chuyển đổi tọa độ điểm thành mảng NumPy
    p1 = np.array(p1, dtype=float)
    p2 = np.array(p2, dtype=float)
    p3 = np.array(p3, dtype=float)

    # Tạo hai vector từ ba điểm
    v1 = p2 - p1
    v2 = p3 - p1
    # Tính tích chéo của hai vector để tìm vector pháp tuyến
    normal_vector = np.cross(v1, v2)
    # Chuẩn hóa vector pháp tuyến
    normal_vector = Normalize_vector(normal_vector)
    # Trả về vector pháp tuyến
    return normal_vector


def Offset_point(p1, p2, p3, distance):
    p1 = np.array(p1, dtype=float)
    p2 = np.array(p2, dtype=float)
    p3 = np.array(p3, dtype=float)
    normal_vector = Normal_vector(p1, p2, p3)

    # Tính tọa độ của điểm P11
    p11 = p1 + distance * normal_vector

    return p11


def Angle_between_planes(p1, p2, p3, pp1, pp2, pp3):
    """
    2つの平面間の角度を計算する

    Args:
        p1, p2, p3: 平面1を定義する3点
        pp1, pp2, pp3: 平面2を定義する3点

    Returns:
        平面間の角度（ラジアン）
    """
    p1 = np.array(p1, dtype=float)
    p2 = np.array(p2, dtype=float)
    p3 = np.array(p3, dtype=float)

    pp1 = np.array(pp1, dtype=float)
    pp2 = np.array(pp2, dtype=float)
    pp3 = np.array(pp3, dtype=float)

    # Tính vector pháp tuyến của từng mặt phẳng
    n1 = Normal_vector(p1, p2, p3)
    n2 = Normal_vector(pp1, pp2, pp3)

    # Tính tích vô hướng của hai vector pháp tuyến
    dot_product = np.dot(n1, n2)

    # Tính độ dài (norm) của từng vector pháp tuyến
    norm_n1 = np.linalg.norm(n1)
    norm_n2 = np.linalg.norm(n2)

    # ゼロ除算を防ぐための閾値
    epsilon = 1e-10
    if norm_n1 < epsilon or norm_n2 < epsilon:
        # 法線ベクトルがゼロの場合、平行または無効な平面として0を返す
        return 0.0

    # 法線ベクトル間の角度の余弦を計算
    cos_theta = dot_product / (norm_n1 * norm_n2)

    # cos_thetaを[-1, 1]の範囲にクリップして数値誤差を防ぐ
    cos_theta = np.clip(cos_theta, -1.0, 1.0)

    # 角度を計算（ラジアン）
    theta = np.arccos(cos_theta)
    # angle_in_degrees = np.degrees(theta)
    return theta


def Angle_between_vectors(p1, p2, p3):
    """
    3点から2つのベクトルを作成し、それらの間の角度を計算する

    Args:
        p1: 基準点
        p2: ベクトル1の終点
        p3: ベクトル2の終点

    Returns:
        ベクトル間の角度（ラジアン）
    """
    p1 = np.array(p1, dtype=float)
    p2 = np.array(p2, dtype=float)
    p3 = np.array(p3, dtype=float)

    # 3点から2つのベクトルを作成
    u = p2 - p1
    v = p3 - p1

    # 内積を計算
    dot_product = np.dot(u, v)

    # 各ベクトルのノルムを計算
    norm_u = np.linalg.norm(u)
    norm_v = np.linalg.norm(v)

    # ゼロ除算を防ぐための閾値
    epsilon = 1e-10
    if norm_u < epsilon or norm_v < epsilon:
        # ベクトルがゼロの場合、角度を0として返す
        return 0.0

    # 角度の余弦を計算
    cos_theta = dot_product / (norm_u * norm_v)

    # cos_thetaを[-1, 1]の範囲にクリップして数値誤差を防ぐ
    cos_theta = np.clip(cos_theta, -1.0, 1.0)

    # 角度を計算（ラジアン）
    angle_rad = np.arccos(cos_theta)

    return angle_rad


# Giao  măt và mặt
def intersec_face_with_face(arFace1_line, arFace2_plan, pos):
    for i in range(0, len(arFace1_line[0])):
        if pos == "S":
            pl1 = arFace1_line[0][i]
            pl2 = arFace1_line[1][i]
        else:
            pl1 = arFace1_line[-1][i]
            pl2 = arFace1_line[-2][i]

        if i == 0:
            for i_1 in range(0, len(arFace2_plan) - 1):
                pp1 = arFace2_plan[i_1][i]
                pp2 = arFace2_plan[i_1][i + 1]
                pp3 = arFace2_plan[i_1 + 1][i]
                pp4 = arFace2_plan[i_1 + 1][i + 1]

                intersec = Intersection_line_plane(pp1, pp2, pp3, pl1, pl2)
                polygon3d = [pp1, pp2, pp3, pp4]
                polygon3d = sort_points_clockwise(polygon3d)
                if is_point_in_polygon_3d(intersec, polygon3d, pp1, pp2, pp3) == True:
                    if pos == "S":
                        arFace1_line[0][i] = intersec
                    else:
                        arFace1_line[-1][i] = intersec
                    break
        elif i == len(arFace1_line[0]) - 1:
            for i_1 in range(0, len(arFace2_plan) - 1):
                pp1 = arFace2_plan[i_1][i]
                pp2 = arFace2_plan[i_1][i - 1]
                pp3 = arFace2_plan[i_1 + 1][i]
                pp4 = arFace2_plan[i_1 + 1][i - 1]

                intersec = Intersection_line_plane(pp1, pp2, pp3, pl1, pl2)
                polygon3d = [pp1, pp2, pp3, pp4]
                polygon3d = sort_points_clockwise(polygon3d)
                if is_point_in_polygon_3d(intersec, polygon3d, pp1, pp2, pp3) == True:
                    if pos == "S":
                        arFace1_line[0][i] = intersec
                    else:
                        arFace1_line[-1][i] = intersec
                    break
        else:
            for i_1 in range(0, len(arFace2_plan) - 1):
                pp1 = arFace2_plan[i_1][i]
                pp2 = arFace2_plan[i_1][i + 1]
                pp3 = arFace2_plan[i_1 + 1][i]
                pp4 = arFace2_plan[i_1 + 1][i + 1]

                intersec1 = Intersection_line_plane(pp1, pp2, pp3, pl1, pl2)
                polygon3d = [pp1, pp2, pp3, pp4]
                polygon3d = sort_points_clockwise(polygon3d)
                if is_point_in_polygon_3d(intersec1, polygon3d, pp1, pp2, pp3) == True:
                    break

            for i_1 in range(0, len(arFace2_plan) - 1):
                pp1 = arFace2_plan[i_1][i]
                pp2 = arFace2_plan[i_1][i - 1]
                pp3 = arFace2_plan[i_1 + 1][i]
                pp4 = arFace2_plan[i_1 + 1][i - 1]

                intersec2 = Intersection_line_plane(pp1, pp2, pp3, pl1, pl2)
                polygon3d = [pp1, pp2, pp3, pp4]
                polygon3d = sort_points_clockwise(polygon3d)
                if is_point_in_polygon_3d(intersec2, polygon3d, pp1, pp2, pp3) == True:
                    break

            intersec = (intersec1 + intersec2) / 2
            if pos == "S":
                arFace1_line[0][i] = intersec
            else:
                arFace1_line[-1][i] = intersec

    return arFace1_line


def Intersection_line_plane(p1, p2, p3, d1, d2):
    p1 = np.array(p1, dtype=float)
    p2 = np.array(p2, dtype=float)
    p3 = np.array(p3, dtype=float)
    d1 = np.array(d1, dtype=float)
    d2 = np.array(d2, dtype=float)

    # Lấy phương trình mặt phẳng
    normal_vector = Normal_vector(p1, p2, p3)
    A, B, C = normal_vector
    D = np.dot(normal_vector, p1)
    # Vector chỉ phương của đường thẳng
    line_dir = np.subtract(d2, d1)
    # Tham số hóa đường thẳng: d(t) = d1 + t * (d2 - d1)
    t_numerator = D - (A * d1[0] + B * d1[1] + C * d1[2])
    t_denominator = A * line_dir[0] + B * line_dir[1] + C * line_dir[2]

    if t_denominator == 0:
        return None  # Đường thẳng song song với mặt phẳng
    t = t_numerator / t_denominator
    # Tọa độ giao điểm
    intersection = d1 + t * line_dir
    return intersection


# Giao điểm của mặt phẳng và đoạn thẳng
def Intersection_plane_segment(p1, p2, p3, d1, d2):
    # Chuyển đổi các điểm thành numpy array để xử lý dễ dàng hơn
    p1 = np.array(p1, dtype=float)
    p2 = np.array(p2, dtype=float)
    p3 = np.array(p3, dtype=float)
    d1 = np.array(d1, dtype=float)
    d2 = np.array(d2, dtype=float)

    # Lấy phương trình mặt phẳng từ 3 điểm p1, p2, p3
    normal_vector = np.cross(p2 - p1, p3 - p1)  # Vector pháp tuyến của mặt phẳng
    A, B, C = normal_vector
    D = np.dot(normal_vector, p1)  # Hệ số D trong phương trình mặt phẳng

    # Vector chỉ phương của đoạn thẳng
    line_dir = np.subtract(d2, d1)

    # Tính tham số hóa của đoạn thẳng: d(t) = d1 + t * (d2 - d1)
    t_numerator = D - (A * d1[0] + B * d1[1] + C * d1[2])
    t_denominator = A * line_dir[0] + B * line_dir[1] + C * line_dir[2]

    if t_denominator == 0:
        return None  # Đoạn thẳng song song với mặt phẳng (không có giao điểm hoặc nằm trên mặt phẳng)

    t = t_numerator / t_denominator

    # Kiểm tra xem t có nằm trong khoảng [0, 1] không, tức là giao điểm có nằm trên đoạn thẳng hay không
    if t < 0 or t > 1:
        return None  # Giao điểm nằm ngoài đoạn thẳng d1d2

    # Tính tọa độ giao điểm
    intersection = d1 + t * line_dir
    return intersection


def Intersec_line_line(p1, p2, p3, p4, eps=1e-4, as_segments=False):
    # ép về 2D float
    p1 = np.asarray(p1, float)[:2]
    p2 = np.asarray(p2, float)[:2]
    p3 = np.asarray(p3, float)[:2]
    p4 = np.asarray(p4, float)[:2]

    v1 = p2 - p1
    v2 = p4 - p3

    # suy biến: độ dài gần 0
    if np.linalg.norm(v1) < eps or np.linalg.norm(v2) < eps:
        return None

    # det = cross(v1, v2)
    det = v1[0] * v2[1] - v1[1] * v2[0]
    # ゼロ除算を防ぐための閾値（epsより小さくすることで、警告を防ぐ）
    epsilon_zero = max(eps, 1e-10)
    if abs(det) < epsilon_zero:
        # 平行またはほぼ平行（同一直線を含む）
        return None

    # パラメータ解: p1 + t*v1 = p3 + u*v2
    r = p3 - p1
    t = (r[0] * v2[1] - r[1] * v2[0]) / det
    u = (r[0] * v1[1] - r[1] * v1[0]) / det

    if as_segments and not (0 - eps <= t <= 1 + eps and 0 - eps <= u <= 1 + eps):
        return None

    inter = p1 + t * v1
    return inter  # np.array([x, y])


# Hàm tìm giao điểm giữa hai đường thẳng trong không gian 3D
def intersection_2Line_3D(p1, p2, d1, d2):
    v1 = np.array(p2) - np.array(p1)
    v2 = np.array(d2) - np.array(d1)
    A = np.vstack([v1, -v2]).T
    b = np.array(d1) - np.array(p1)

    if np.linalg.matrix_rank(A) < 2:
        return None

    t, s = np.linalg.lstsq(A, b, rcond=None)[0]
    point_on_line1 = np.array(p1) + t * v1
    point_on_line2 = np.array(d1) + s * v2

    if np.allclose(point_on_line1, point_on_line2):
        return point_on_line1
    else:
        return None


def Offset_Face_2Line(Coord1_Base, Coord2_Base, Distance):
    if Distance == 0:
        Coord1_off = Coord1_Base.copy()
        Coord2_off = Coord2_Base.copy()
    else:
        Coord1_off = Coord1_Base.copy()
        Coord2_off = Coord2_Base.copy()
        for i in range(0, len(Coord1_Base)):
            if i == 0:
                Point_Off = Offset_point(Coord1_Base[i], Coord2_Base[i], Coord1_Base[i + 1], Distance)
                Coord1_off[i] = Point_Off

                Point_Off = Offset_point(Coord2_Base[i], Coord1_Base[i], Coord2_Base[i + 1], -Distance)
                Coord2_off[i] = Point_Off

            elif i == len(Coord1_Base) - 1:
                Point_Off = Offset_point(Coord1_Base[i], Coord2_Base[i], Coord1_Base[i - 1], -Distance)
                Coord1_off[i] = Point_Off

                Point_Off = Offset_point(Coord2_Base[i], Coord1_Base[i], Coord2_Base[i - 1], Distance)
                Coord2_off[i] = Point_Off

            else:
                Ang1 = Angle_between_planes(
                    Coord1_Base[i],
                    Coord2_Base[i],
                    Coord1_Base[i - 1],
                    Coord1_Base[i],
                    Coord2_Base[i],
                    Coord1_Base[i + 1],
                )

                atc = Offset_point(Coord1_Base[i], Coord2_Base[i], Coord1_Base[i + 1], Distance)
                atc1 = Offset_point(Coord1_Base[i], Coord2_Base[i], Coord1_Base[i - 1], -Distance)
                atc2 = Offset_point(Coord2_Base[i], Coord1_Base[i], Coord2_Base[i + 1], -Distance)
                atc3 = Offset_point(Coord2_Base[i], Coord1_Base[i], Coord2_Base[i - 1], Distance)
                atc5 = Offset_point(Coord1_Base[i + 1], Coord2_Base[i + 1], Coord1_Base[i], -Distance)
                atc6 = Offset_point(Coord1_Base[i - 1], Coord2_Base[i - 1], Coord1_Base[i], Distance)

                if abs(Ang1 - math.pi) < 0.000001 or math.isnan(Ang1):
                    Coord1_off[i] = atc
                else:
                    atc7 = Intersection_line_plane(atc1, atc3, atc6, atc, atc5)
                    atc8 = Intersection_line_plane(atc, atc2, atc5, atc1, atc6)
                    # atc7またはatc8がNoneの場合の処理
                    if atc7 is None and atc8 is None:
                        Coord1_off[i] = atc  # デフォルトとしてatcを使用
                    elif atc7 is None:
                        Coord1_off[i] = atc8
                    elif atc8 is None:
                        Coord1_off[i] = atc7
                    else:
                        Coord1_off[i] = (atc7 + atc8) / 2

                atc = Offset_point(Coord2_Base[i], Coord1_Base[i], Coord2_Base[i + 1], -Distance)
                atc1 = Offset_point(Coord2_Base[i], Coord1_Base[i], Coord2_Base[i - 1], Distance)
                atc2 = Offset_point(Coord1_Base[i], Coord2_Base[i], Coord1_Base[i + 1], Distance)
                atc3 = Offset_point(Coord1_Base[i], Coord2_Base[i], Coord1_Base[i - 1], -Distance)
                atc5 = Offset_point(Coord2_Base[i + 1], Coord1_Base[i + 1], Coord2_Base[i], Distance)
                atc6 = Offset_point(Coord2_Base[i - 1], Coord1_Base[i - 1], Coord2_Base[i], -Distance)
                if abs(Ang1 - math.pi) < 0.000001 or math.isnan(Ang1):
                    Coord2_off[i] = atc
                else:
                    atc7 = Intersection_line_plane(atc1, atc3, atc6, atc, atc5)
                    atc8 = Intersection_line_plane(atc, atc2, atc5, atc1, atc6)
                    # atc7またはatc8がNoneの場合の処理
                    if atc7 is None and atc8 is None:
                        Coord2_off[i] = atc  # デフォルトとしてatcを使用
                    elif atc7 is None:
                        Coord2_off[i] = atc8
                    elif atc8 is None:
                        Coord2_off[i] = atc7
                    else:
                        Coord2_off[i] = (atc7 + atc8) / 2

    return Coord1_off, Coord2_off


def Offset_Face(CoordLines_Base, Distance):
    if Distance == 0:
        CoordLines_Off = CoordLines_Base.copy()
    else:
        CoordLines_Off = CoordLines_Base.copy()
        for i in range(0, len(CoordLines_Off)):
            if i == 0:
                CoordLines_Off[i], CoordLines_Off[i + 1] = Offset_Face_2Line(
                    CoordLines_Base[i], CoordLines_Base[i + 1], Distance
                )
            elif i == len(CoordLines_Off) - 1:
                CoordLines_Off[i], CoordLines_Off[i - 1] = Offset_Face_2Line(
                    CoordLines_Base[i], CoordLines_Base[i - 1], -Distance
                )
            else:
                arCoord1, arCoord2 = Offset_Face_2Line(CoordLines_Base[i], CoordLines_Base[i + 1], Distance)
                arCoord3, arCoord4 = Offset_Face_2Line(CoordLines_Base[i], CoordLines_Base[i - 1], -Distance)
                arCoord_Off = []
                for i_1 in range(0, len(arCoord1)):
                    if i_1 == len(arCoord1) - 1:
                        angle = Angle_between_planes(
                            arCoord3[i_1],
                            arCoord4[i_1],
                            arCoord3[i_1 - 1],
                            arCoord1[i_1],
                            arCoord2[i_1],
                            arCoord1[i_1 - 1],
                        )
                    else:
                        angle = Angle_between_planes(
                            arCoord3[i_1],
                            arCoord4[i_1],
                            arCoord3[i_1 + 1],
                            arCoord1[i_1],
                            arCoord2[i_1],
                            arCoord1[i_1 + 1],
                        )

                    if abs(angle - math.pi) < 0.000001 or math.isnan(angle):
                        arCoord_Off.append(arCoord1[i_1])
                    else:
                        if i_1 == 0:
                            atc1 = Intersection_line_plane(
                                arCoord1[i_1], arCoord2[i_1], arCoord1[i_1 + 1], arCoord3[i_1], arCoord4[i_1]
                            )
                            atc2 = Intersection_line_plane(
                                arCoord3[i_1], arCoord4[i_1], arCoord3[i_1 + 1], arCoord1[i_1], arCoord2[i_1]
                            )
                            # atc1またはatc2がNoneの場合の処理
                            if atc1 is None and atc2 is None:
                                atc = arCoord1[i_1]  # デフォルトとしてarCoord1を使用
                            elif atc1 is None:
                                atc = atc2
                            elif atc2 is None:
                                atc = atc1
                            else:
                                atc = (atc1 + atc2) / 2
                            arCoord_Off.append(atc)
                        elif i_1 == len(arCoord1) - 1:
                            atc1 = Intersection_line_plane(
                                arCoord1[i_1], arCoord2[i_1], arCoord1[i_1 - 1], arCoord3[i_1], arCoord4[i_1]
                            )
                            atc2 = Intersection_line_plane(
                                arCoord3[i_1], arCoord4[i_1], arCoord3[i_1 - 1], arCoord1[i_1], arCoord2[i_1]
                            )
                            # atc1またはatc2がNoneの場合の処理
                            if atc1 is None and atc2 is None:
                                atc = arCoord1[i_1]  # デフォルトとしてarCoord1を使用
                            elif atc1 is None:
                                atc = atc2
                            elif atc2 is None:
                                atc = atc1
                            else:
                                atc = (atc1 + atc2) / 2
                            arCoord_Off.append(atc)
                        else:
                            atc1 = Intersection_line_plane(
                                arCoord1[i_1], arCoord2[i_1], arCoord1[i_1 + 1], arCoord3[i_1], arCoord4[i_1]
                            )
                            atc2 = Intersection_line_plane(
                                arCoord3[i_1], arCoord4[i_1], arCoord3[i_1 + 1], arCoord1[i_1], arCoord2[i_1]
                            )
                            # atc1またはatc2がNoneの場合の処理
                            if atc1 is None and atc2 is None:
                                atc_1 = arCoord1[i_1]  # デフォルトとしてarCoord1を使用
                            elif atc1 is None:
                                atc_1 = atc2
                            elif atc2 is None:
                                atc_1 = atc1
                            else:
                                atc_1 = (atc1 + atc2) / 2

                            atc1 = Intersection_line_plane(
                                arCoord1[i_1], arCoord2[i_1], arCoord1[i_1 - 1], arCoord3[i_1], arCoord4[i_1]
                            )
                            atc2 = Intersection_line_plane(
                                arCoord3[i_1], arCoord4[i_1], arCoord3[i_1 - 1], arCoord1[i_1], arCoord2[i_1]
                            )
                            # atc1またはatc2がNoneの場合の処理
                            if atc1 is None and atc2 is None:
                                atc_2 = arCoord1[i_1]  # デフォルトとしてarCoord1を使用
                            elif atc1 is None:
                                atc_2 = atc2
                            elif atc2 is None:
                                atc_2 = atc1
                            else:
                                atc_2 = (atc1 + atc2) / 2

                            atc = (atc_1 + atc_2) / 2
                            arCoord_Off.append(atc)

                CoordLines_Off[i] = arCoord_Off

    return CoordLines_Off


def Offset_Line(p1, p2, offset_distance):
    p1 = np.array(p1, dtype=float)
    if p1.shape[0] == 3:
        p1 = p1[:2]
    p2 = np.array(p2, dtype=float)
    if p2.shape[0] == 3:
        p2 = p2[:2]

    # Tính vector từ P1 đến P2
    line_vector = np.array(p2) - np.array(p1)

    # ベクトルの長さを計算
    length = np.linalg.norm(line_vector)

    # ゼロ除算を防ぐための閾値
    epsilon = 1e-10
    if length < epsilon:
        # p1とp2が同じ点の場合、p1とp2をそのまま返す
        return p1.copy(), p2.copy()

    # 単位ベクトルを計算
    unit_vector = line_vector / length

    # Tính vector pháp tuyến đơn vị (vuông góc với unit_vector)
    normal_vector = np.array([-unit_vector[1], unit_vector[0]])

    # Tính các điểm offset
    offset_p1 = np.array(p1) + offset_distance * normal_vector
    offset_p2 = np.array(p2) + offset_distance * normal_vector

    return offset_p1, offset_p2


def Offset_Polyline(points, offset_distance):
    n = len(points)
    if n < 2:
        return np.array(points)
    is_3d = len(points[0]) == 3
    # Offset từng đoạn
    offset_segments = []
    for i in range(n - 1):
        op1, op2 = Offset_Line(points[i], points[i + 1], offset_distance)
        offset_segments.append((op1, op2))
    # Tính các đỉnh mới
    offset_points = []
    if is_3d:
        offset_points.append([offset_segments[0][0][0], offset_segments[0][0][1], points[0][2]])  # Đầu tiên giữ nguyên
    else:
        offset_points.append(offset_segments[0][0])  # Đầu tiên giữ nguyên

    for i in range(1, n - 1):
        # Giao điểm 2 đoạn offset liên tiếp
        prev = offset_segments[i - 1]
        curr = offset_segments[i]
        inter = Intersec_line_line(prev[0], prev[1], curr[0], curr[1])

        if inter is not None:
            # Nếu là 3D thì giữ nguyên z của điểm gốc
            if is_3d:
                inter = np.array([inter[0], inter[1], points[i][2]])
            offset_points.append(inter)
        else:
            if is_3d:
                offset_points.append([curr[0][0], curr[0][1], points[i][2]])  # fallback
            else:
                offset_points.append([curr[0][0], curr[0][1]])  # fallback

    if is_3d:
        offset_points.append(
            [offset_segments[-1][1][0], offset_segments[-1][1][1], points[-1][2]]
        )  # Cuối cùng giữ nguyên
    else:
        offset_points.append(offset_segments[-1][1])  # Đầu tiên giữ nguyên

    return np.array(offset_points)


# Xoay điểm D quanh trục p1 p2
def rotate_point_around_axis(P1, P2, D, angle_degrees):
    # Chuyển đổi độ sang radian
    angle_radians = np.radians(angle_degrees)

    # 回転軸P1P2の単位ベクトルを計算
    axis = np.array(P2) - np.array(P1)
    norm_axis = np.linalg.norm(axis)
    # ゼロ除算を防ぐための閾値
    epsilon = 1e-10
    if norm_axis < epsilon:
        # P1とP2が同じ点の場合、デフォルトの軸ベクトルを返す
        raise ValueError("回転軸の両端点が同じ点です。")
    axis = axis / norm_axis

    # Tạo các ma trận cần thiết cho việc xoay
    cos_theta = np.cos(angle_radians)
    sin_theta = np.sin(angle_radians)
    ux, uy, uz = axis

    # Ma trận xoay quanh một trục bất kỳ
    rotation_matrix = np.array(
        [
            [
                cos_theta + ux**2 * (1 - cos_theta),
                ux * uy * (1 - cos_theta) - uz * sin_theta,
                ux * uz * (1 - cos_theta) + uy * sin_theta,
            ],
            [
                uy * ux * (1 - cos_theta) + uz * sin_theta,
                cos_theta + uy**2 * (1 - cos_theta),
                uy * uz * (1 - cos_theta) - ux * sin_theta,
            ],
            [
                uz * ux * (1 - cos_theta) - uy * sin_theta,
                uz * uy * (1 - cos_theta) + ux * sin_theta,
                cos_theta + uz**2 * (1 - cos_theta),
            ],
        ]
    )

    # Dịch điểm D về gốc tọa độ
    D_translated = np.array(D) - np.array(P1)

    # Xoay điểm D quanh trục P1P2
    D_rotated = np.dot(rotation_matrix, D_translated)

    # Dịch ngược lại điểm D về vị trí ban đầu
    D_final = D_rotated + np.array(P1)

    return D_final


# Tính toán góc đọ arc
def calculate_angle_arc(origin, point):
    dx = point[0] - origin[0]
    dy = point[1] - origin[1]
    return math.atan2(dy, dx)


# Tạo arc với điểm đầu điểm cuối và tâm
def devide_arc_to_points_polyline(start_point, end_point, center_point, num_segments=30):
    radius = math.sqrt((start_point[0] - center_point[0]) ** 2 + (start_point[1] - center_point[1]) ** 2)
    start_angle = calculate_angle_arc(center_point, start_point)
    end_angle = calculate_angle_arc(center_point, end_point)

    if end_angle < start_angle:
        end_angle += 2 * math.pi

    # ゼロ除算を防ぐためのチェック
    if num_segments <= 0:
        num_segments = 30  # デフォルト値を使用

    angle_step = (end_angle - start_angle) / num_segments

    outer_points = []

    for i in range(num_segments + 1):
        angle = start_angle + i * angle_step
        x = center_point[0] + radius * math.cos(angle)
        y = center_point[1] + radius * math.sin(angle)
        outer_points.append([x, y])

    points = outer_points

    return points


# Hàm kiểm tra xem một điểm có nằm trong mặt phẳng không
def point_in_plane_limits(point, plane_points):
    min_x, max_x = min(plane_points[:, 0]), max(plane_points[:, 0])
    min_y, max_y = min(plane_points[:, 1]), max(plane_points[:, 1])
    min_z, max_z = min(plane_points[:, 2]), max(plane_points[:, 2])
    return (min_x <= point[0] <= max_x) and (min_y <= point[1] <= max_y) and (min_z <= point[2] <= max_z)


# Hàm tính phương trình mặt phẳng từ vector pháp tuyến và một điểm trên mặt phẳng
def plane_equation(normal, point):
    d = -np.dot(normal, point)
    return np.append(normal, d)


# Hàm tìm giao tuyến của hai mặt phẳng
def plane_intersection(plane1, plane2):
    direction = np.cross(plane1[:3], plane2[:3])
    if np.linalg.norm(direction) < 1e-6:
        return None, None  # Hai mặt phẳng song song hoặc trùng nhau
    A = np.array([plane1[:3], plane2[:3], direction])
    b = np.array([-plane1[3], -plane2[3], 0])
    point_on_line = np.linalg.solve(A, b)
    return point_on_line, direction


# Hàm tìm giao tuyến của hai mặt phẳng giới hạn miền
def intersection_2plan_limit(plane1_points, plane2_points, Compare=0):
    plane1_points = sort_points_clockwise(plane1_points)
    plane2_points = sort_points_clockwise(plane2_points)
    # Tính vector pháp tuyến của mỗi mặt phẳng
    normal1 = Normal_vector(plane1_points[0], plane1_points[1], plane1_points[2])
    normal2 = Normal_vector(plane2_points[0], plane2_points[1], plane2_points[2])

    # Tính phương trình mặt phẳng
    plane1_eq = plane_equation(normal1, plane1_points[0])
    plane2_eq = plane_equation(normal2, plane2_points[0])

    # Tìm giao tuyến của hai mặt phẳng
    line_point, line_dir = plane_intersection(plane1_eq, plane2_eq)

    if line_point is not None and line_dir is not None:
        edges_plane1 = []
        for i in range(len(plane1_points)):
            for i_1 in range(i + 1, len(plane1_points)):
                edges_plane1.append((plane1_points[i], plane1_points[i_1]))

        intersection1_points = []
        for edge in edges_plane1:
            intersection = intersection_2Line_3D(edge[0], edge[1], line_point, line_point + line_dir)
            if intersection is not None:
                intersection1_points.append(intersection)
        # Lọc các điểm giao thuộc miền mặt phẳng 1
        # filtered_intersection1 = [pt for pt in intersection1_points if point_in_plane_limits(pt, plane1_points) and point_in_plane_limits(pt, plane2_points)]
        filtered_intersection1 = [
            pt
            for pt in intersection1_points
            if is_point_in_polygon_3d(pt, plane1_points, plane1_points[0], plane1_points[1], plane1_points[-1])
            and is_point_in_polygon_3d(pt, plane2_points, plane2_points[0], plane2_points[1], plane2_points[-1])
        ]
        edges_plane2 = []
        for i in range(len(plane2_points)):
            for i_1 in range(i + 1, len(plane2_points)):
                edges_plane2.append((plane2_points[i], plane2_points[i_1]))

        intersection2_points = []
        for edge in edges_plane2:
            intersection = intersection_2Line_3D(edge[0], edge[1], line_point, line_point + line_dir)
            if intersection is not None:
                intersection2_points.append(intersection)
        # Lọc các điểm giao thuộc miền mặt phẳng 2
        # filtered_intersection2 = [pt for pt in intersection2_points if point_in_plane_limits(pt, plane1_points) and point_in_plane_limits(pt, plane2_points)]
        filtered_intersection2 = [
            pt
            for pt in intersection2_points
            if is_point_in_polygon_3d(pt, plane1_points, plane1_points[0], plane1_points[1], plane1_points[-1])
            and is_point_in_polygon_3d(pt, plane2_points, plane2_points[0], plane2_points[1], plane2_points[-1])
        ]
        # Gộp hai mảng điểm giao
        combined_intersections = np.concatenate((filtered_intersection1, filtered_intersection2), axis=0)

        if combined_intersections:
            # Tìm điểm min và max trong tập hợp mới
            min_index = np.argmin(combined_intersections[:, Compare])
            min_point = combined_intersections[min_index]

            max_index = np.argmax(combined_intersections[:, Compare])
            max_point = combined_intersections[max_index]

            # In ra điểm min và max
            return min_point, max_point
        else:
            return None, None
    else:
        return None, None


# Sắp xếp các điểm 3D theo chiều kim đồng hồ quanh một điểm trung tâm.
def sort_points_clockwise(points):
    # Chuyển đổi danh sách thành mảng numpy
    points = np.array(points)

    # Chọn 3 điểm đầu tiên để xác định mặt phẳng
    p1, p2, p3 = points[:3]

    # 平面の法線ベクトルを計算
    v1 = p2 - p1
    v2 = p3 - p1
    normal = np.cross(v1[:3], v2[:3])
    norm_normal = np.linalg.norm(normal)
    # ゼロ除算を防ぐための閾値
    epsilon = 1e-10
    if norm_normal < epsilon:
        # 3点が一直線上にある場合、デフォルトの法線ベクトルを返す
        raise ValueError("3点が一直線上にあり、平面を定義できません。")
    normal = normal / norm_normal

    # 平面上の2つの基底ベクトルを作成
    norm_v1 = np.linalg.norm(v1)
    if norm_v1 < epsilon:
        raise ValueError("ベクトルv1がゼロです。")
    u = v1 / norm_v1
    v = np.cross(normal, u)

    # Chiếu các điểm lên mặt phẳng 2D
    points_2d = []
    for p in points:
        # Tính tọa độ 2D cho mỗi điểm
        x = np.dot(p - p1, u)
        y = np.dot(p - p1, v)
        points_2d.append([x, y])

    points_2d = np.array(points_2d)

    # Tính điểm trung tâm của các điểm 2D
    center = np.mean(points_2d, axis=0)

    # Tính góc của mỗi điểm so với điểm trung tâm
    angles = np.arctan2(points_2d[:, 1] - center[1], points_2d[:, 0] - center[0])

    # Sắp xếp các điểm theo góc
    sorted_indices = np.argsort(angles)

    # Trả về các điểm 3D theo thứ tự đã sắp xếp
    return points[sorted_indices]


# Sắp xếp các điểm 2D theo chiều kim đồng hồ quanh một điểm trung tâm
def sort_points_clockwise_2D(points):
    # Tạo danh sách mới để lưu các điểm đã được chuyển đổi
    converted_points = []

    # Kiểm tra từng phần tử trong danh sách points
    for point in points:
        # Nếu point có ba phần tử, chỉ lấy hai phần tử đầu tiên
        if len(point) == 3:
            point = point[:2]
        # Thêm điểm vào danh sách mới
        converted_points.append(point)

    # Chuyển đổi danh sách mới thành mảng numpy
    points = np.array(converted_points, dtype=float)

    # Chuyển đổi danh sách thành mảng numpy
    # points = np.array(points)

    # Tính điểm trung tâm của các điểm 2D
    center = np.mean(points, axis=0)

    # Tính góc của mỗi điểm so với điểm trung tâm
    angles = np.arctan2(points[:, 1] - center[1], points[:, 0] - center[0])

    # Sắp xếp các điểm theo góc (theo chiều kim đồng hồ)
    sorted_indices = np.argsort(angles)

    # Trả về các điểm 2D theo thứ tự đã sắp xếp
    return points[sorted_indices]


def profile2D_shapL(NameShapeL, pbase=[0, 0]):
    arShapeL = [
        {"name": "25x25x3", "a": 25, "b": 25, "t": 3, "r1": 2, "r2": 2},
        {"name": "30x30x3", "a": 30, "b": 30, "t": 3, "r1": 2, "r2": 2},
        {"name": "30x30x5", "a": 30, "b": 30, "t": 5, "r1": 4.5, "r2": 2},
        {"name": "40x40x3", "a": 40, "b": 40, "t": 3, "r1": 4.5, "r2": 2},
        {"name": "40x40x5", "a": 40, "b": 40, "t": 5, "r1": 4.5, "r2": 3},
        {"name": "45x45x4", "a": 45, "b": 45, "t": 4, "r1": 6.5, "r2": 3},
        {"name": "50x50x4", "a": 50, "b": 50, "t": 4, "r1": 6.5, "r2": 3},
        {"name": "50x50x6", "a": 50, "b": 50, "t": 6, "r1": 6.5, "r2": 4.5},
        {"name": "60x60x4", "a": 60, "b": 60, "t": 4, "r1": 6.5, "r2": 3},
        {"name": "60x60x5", "a": 60, "b": 60, "t": 5, "r1": 6.5, "r2": 3},
        {"name": "65x65x6", "a": 65, "b": 65, "t": 6, "r1": 8.5, "r2": 4},
        {"name": "65x65x8", "a": 65, "b": 65, "t": 8, "r1": 8.5, "r2": 6},
        {"name": "70x70x6", "a": 70, "b": 70, "t": 6, "r1": 8.5, "r2": 4},
        {"name": "75x75x6", "a": 75, "b": 75, "t": 6, "r1": 8.5, "r2": 4},
        {"name": "75x75x9", "a": 75, "b": 75, "t": 9, "r1": 8.5, "r2": 6},
        {"name": "75x75x12", "a": 75, "b": 75, "t": 12, "r1": 8.5, "r2": 6},
        {"name": "80x80x6", "a": 80, "b": 80, "t": 6, "r1": 8.5, "r2": 4},
        {"name": "90x90x6", "a": 90, "b": 90, "t": 6, "r1": 10, "r2": 5},
        {"name": "90x90x7", "a": 90, "b": 90, "t": 7, "r1": 10, "r2": 5},
        {"name": "90x90x10", "a": 90, "b": 90, "t": 10, "r1": 10, "r2": 7},
        {"name": "90x90x13", "a": 90, "b": 90, "t": 13, "r1": 10, "r2": 7},
        {"name": "100x100x7", "a": 100, "b": 100, "t": 7, "r1": 10, "r2": 5},
        {"name": "100x100x10", "a": 100, "b": 100, "t": 10, "r1": 10, "r2": 7},
        {"name": "100x100x13", "a": 100, "b": 100, "t": 13, "r1": 10, "r2": 7},
        {"name": "120x120x8", "a": 120, "b": 120, "t": 8, "r1": 12, "r2": 5},
        {"name": "130x130x9", "a": 130, "b": 130, "t": 9, "r1": 12, "r2": 6},
        {"name": "130x130x12", "a": 130, "b": 130, "t": 12, "r1": 12, "r2": 8.5},
        {"name": "130x130x15", "a": 130, "b": 130, "t": 15, "r1": 12, "r2": 8.5},
        {"name": "150x150x12", "a": 150, "b": 150, "t": 12, "r1": 14, "r2": 7},
        {"name": "150x150x15", "a": 150, "b": 150, "t": 15, "r1": 14, "r2": 10},
        {"name": "150x150x19", "a": 150, "b": 150, "t": 19, "r1": 14, "r2": 10},
        {"name": "175x175x12", "a": 175, "b": 175, "t": 12, "r1": 15, "r2": 11},
        {"name": "175x175x15", "a": 175, "b": 175, "t": 15, "r1": 15, "r2": 11},
        {"name": "200x200x15", "a": 200, "b": 200, "t": 15, "r1": 17, "r2": 12},
        {"name": "200x200x20", "a": 200, "b": 200, "t": 20, "r1": 17, "r2": 12},
        {"name": "200x200x25", "a": 200, "b": 200, "t": 25, "r1": 17, "r2": 12},
        {"name": "250x250x25", "a": 250, "b": 250, "t": 25, "r1": 24, "r2": 12},
        {"name": "250x250x35", "a": 250, "b": 250, "t": 35, "r1": 24, "r2": 18},
    ]

    arcoord_profile = []
    status = False
    for profile in arShapeL:
        if NameShapeL == profile["name"]:
            a = profile["a"]
            b = profile["b"]
            t = profile["t"]
            r1 = profile["r1"]
            r2 = profile["r2"]
            status = True
            break

    x = pbase[0]
    y = pbase[1]
    if status == True:
        arcoord_profile.append(pbase)
        arcoord_profile.append([x + b, y + 0])
        points_arc = devide_arc_to_points_polyline(
            [x + b, y + t - r2], [x + b - r2, y + t], [x + b - r2, y + t - r2], int(r2 // 1)
        )
        for point in points_arc:
            arcoord_profile.append(point)
        points_arc = devide_arc_to_points_polyline(
            [x + t, y + t + r1], [x + t + r1, y + t], [x + t + r1, y + t + r1], int(r1 // 1)
        )
        points_arc.reverse()
        for point in points_arc:
            arcoord_profile.append(point)
        points_arc = devide_arc_to_points_polyline(
            [x + t, y + a - r2], [x + t - r2, y + a], [x + t - r2, y + a - r2], int(r2 // 1)
        )
        for point in points_arc:
            arcoord_profile.append(point)
        arcoord_profile.append([x + 0, y + a])

    else:
        return None

    return arcoord_profile


def profile2D_shapCT(NameShapeCT, pbase=[0, 0]):
    arShapeCT = [
        {"name": "95x152x8x8", "h": 95, "b": 152, "t1": 8, "t2": 8, "r": 8},
        {"name": "118x176x8x8", "h": 118, "b": 176, "t1": 8, "t2": 8, "r": 13},
        {"name": "119x177x9x9", "h": 119, "b": 177, "t1": 9, "t2": 9, "r": 13},
        {"name": "118x178x10x8", "h": 118, "b": 178, "t1": 10, "t2": 8, "r": 13},
        {"name": "142x200x8x8", "h": 142, "b": 200, "t1": 8, "t2": 8, "r": 13},
        {"name": "144x204x12x10", "h": 144, "b": 204, "t1": 12, "t2": 10, "r": 13},
        {"name": "165x251x10x10", "h": 165, "b": 251, "t1": 10, "t2": 10, "r": 13},
    ]

    arcoord_profile = []
    status = False
    for profile in arShapeCT:
        if NameShapeCT == profile["name"]:
            h = profile["h"]
            b = profile["b"]
            t1 = profile["t1"]
            t2 = profile["t2"]
            r = profile["r"]
            status = True
            break

    if status == True:
        x = pbase[0]
        y = pbase[1]
        arcoord_profile.append([x + t1 / 2, y + 0])
        points_arc = devide_arc_to_points_polyline(
            [x + t1 / 2 + r, y + h - t2], [x + t1 / 2, y + h - t2 - r], [x + t1 / 2 + r, y + h - t2 - r], int(r // 1)
        )
        points_arc.reverse()
        for point in points_arc:
            arcoord_profile.append(point)
        arcoord_profile.append([x + b / 2, y + h - t2])
        arcoord_profile.append([x + b / 2, y + h])
        arcoord_profile.append([x - b / 2, y + h])
        arcoord_profile.append([x - b / 2, y + h - t2])
        points_arc = devide_arc_to_points_polyline(
            [x - t1 / 2, y + h - t2 - r], [x - t1 / 2 - r, y + h - t2], [x - t1 / 2 - r, y + h - t2 - r], int(r // 1)
        )
        points_arc.reverse()
        for point in points_arc:
            arcoord_profile.append(point)
        arcoord_profile.append([x - t1 / 2, y + 0])
    else:
        return None

    return arcoord_profile


def profile2D_shapC(NameShapeCT, pbase=[0, 0]):
    arShapeC = [
        {"name": "75x40x5", "h": 75, "b": 40, "t1": 5.0, "t2": 7.0, "r1": 8, "r2": 4},
        {"name": "100x50x5", "h": 100, "b": 50, "t1": 5.0, "t2": 7.5, "r1": 8, "r2": 4},
        {"name": "125x65x6", "h": 125, "b": 65, "t1": 6.0, "t2": 8.0, "r1": 8, "r2": 4},
        {"name": "150x75x6.5", "h": 150, "b": 75, "t1": 6.5, "t2": 10.0, "r1": 10, "r2": 5},
        {"name": "150x75x9", "h": 150, "b": 75, "t1": 9.0, "t2": 12.5, "r1": 15, "r2": 7.5},
        {"name": "180x75x7", "h": 180, "b": 75, "t1": 7.0, "t2": 10.5, "r1": 11, "r2": 5.5},
        {"name": "200x80x7.5", "h": 200, "b": 80, "t1": 7.5, "t2": 11.0, "r1": 12, "r2": 6},
        {"name": "200x90x8", "h": 200, "b": 90, "t1": 8.0, "t2": 13.5, "r1": 14, "r2": 7},
        {"name": "250x90x9", "h": 250, "b": 90, "t1": 9.0, "t2": 13.0, "r1": 14, "r2": 7},
        {"name": "250x90x11", "h": 250, "b": 90, "t1": 11.0, "t2": 14.5, "r1": 17, "r2": 8.5},
        {"name": "300x90x9", "h": 300, "b": 90, "t1": 9.0, "t2": 13.0, "r1": 14, "r2": 7},
        {"name": "300x90x10", "h": 300, "b": 90, "t1": 10.0, "t2": 15.5, "r1": 19, "r2": 9.5},
        {"name": "300x90x12", "h": 300, "b": 90, "t1": 12.0, "t2": 16.0, "r1": 19, "r2": 9.5},
        {"name": "380x100x10.5", "h": 380, "b": 100, "t1": 10.5, "t2": 16.0, "r1": 18, "r2": 9},
        {"name": "380x100x13", "h": 380, "b": 100, "t1": 13.0, "t2": 16.5, "r1": 18, "r2": 9},
    ]

    arcoord_profile = []
    status = False
    for profile in arShapeC:
        if NameShapeCT == profile["name"]:
            h = profile["h"]
            b = profile["b"]
            t1 = profile["t1"]
            t2 = profile["t2"]
            r1 = profile["r1"]
            r2 = profile["r2"]
            status = True
            break

    if status == True:
        x = pbase[0]
        y = pbase[1]
        arcoord_profile.append(pbase)
        arcoord_profile.append([x + b, y + 0])
        points_arc = devide_arc_to_points_polyline(
            [x + b, y + t2 - r2], [x + b - r2, y + t2], [x + b - r2, y + t2 - r2], int(r2 // 1)
        )
        for point in points_arc:
            arcoord_profile.append(point)
        points_arc = devide_arc_to_points_polyline(
            [x + t1, y + t2 + r1], [x + t1 + r1, y + t2], [x + t1 + r1, y + t2 + r1], int(r1 // 1)
        )
        points_arc.reverse()
        for point in points_arc:
            arcoord_profile.append(point)
        points_arc = devide_arc_to_points_polyline(
            [x + t1 + r1, y + h - t2], [x + t1, y + h - t2 - r1], [x + t1 + r1, y + h - t2 - r1], int(r2 // 1)
        )
        points_arc.reverse()
        for point in points_arc:
            arcoord_profile.append(point)
        points_arc = devide_arc_to_points_polyline(
            [x + b - r2, y + h - t2], [x + b, y + h - t2 + r2], [x + b - r2, y + h - t2 + r2], int(r2 // 1)
        )
        for point in points_arc:
            arcoord_profile.append(point)
        arcoord_profile.append([x + b, y + h])
        arcoord_profile.append([x, y + h])
    else:
        return None

    return arcoord_profile


def fillet_on_two_lines(V, u1, u2, r, side="inside"):
    """
    Fillet tiếp xúc 2 line đi ra từ điểm V theo hướng u1, u2.
    - V: (x,y)
    - u1, u2: vector hướng (không cần đơn vị; hàm sẽ chuẩn hóa)
    - r: bán kính
    - side: "inside" (cung nằm trong góc nhỏ) hoặc "outside" (lật ra ngoài)
    Trả về: (S, E, C) = (điểm tiếp xúc trên line1, điểm tiếp xúc trên line2, tâm cung)
    """
    V = np.array(V, float)
    u1 = np.array(u1, float)
    u1 /= np.linalg.norm(u1)
    u2 = np.array(u2, float)
    u2 /= np.linalg.norm(u2)

    # góc trong giữa 2 line: 0..pi
    dot = np.clip(np.dot(u1, u2), -1.0, 1.0)
    theta = math.acos(dot)  # rad

    if not (0 < theta < math.pi):
        raise ValueError("Hai line trùng hoặc đối hướng; không fillet được.")

    # khoảng cách từ V đến tiếp điểm & tâm
    if side.lower() == "inside":
        p = r / math.tan(theta / 2.0)  # r*cot(theta/2)
        b = u1 + u2  # phân giác trong
    elif side.lower() == "outside":
        p = r * math.tan(theta / 2.0)  # r*tan(theta/2)
        b = u1 - u2  # phân giác ngoài
    else:
        raise ValueError("side phải là 'inside' hoặc 'outside'.")

    d = r / math.sin(theta / 2.0)  # như nhau cho cả 2 trường hợp
    b /= np.linalg.norm(b)

    # tiếp điểm trên từng line (theo quy ước: S trên line1, E trên line2)
    S = V + p * u1
    E = V + p * u2
    C = V + d * b
    return tuple(S), tuple(E), tuple(C)


def rotate_point(x, y, cx, cy, angle_deg):
    """Xoay 1 điểm (x, y) quanh tâm (cx, cy) theo góc angle_deg (độ)."""
    angle_rad = math.radians(angle_deg)
    x_new = cx + (x - cx) * math.cos(angle_rad) - (y - cy) * math.sin(angle_rad)
    y_new = cy + (x - cx) * math.sin(angle_rad) + (y - cy) * math.cos(angle_rad)
    return x_new, y_new


def rotate_points(points, center, angle_deg):
    """Xoay danh sách điểm quanh 1 tâm."""
    cx, cy = center
    return [rotate_point(x, y, cx, cy, angle_deg) for x, y in points]


def profile2D_Urib(NameShapeCT, pbase=[0, 0]):
    arShapeURib = [
        {"name": "320x240x6", "A": 320, "B": 213.3, "H": 240, "t": 6, "R": 40},
        {"name": "320x260x6", "A": 320, "B": 204.4, "H": 260, "t": 6, "R": 40},
        {"name": "320x240x8", "A": 324.1, "B": 216.5, "H": 242, "t": 8, "R": 40},
        {"name": "320x260x8", "A": 324.1, "B": 207.7, "H": 262, "t": 8, "R": 40},
        {"name": "440x330x8", "A": 440, "B": 293.3, "H": 330, "t": 8, "R": 40},
        {"name": "450x330x9", "A": 450, "B": 303.3, "H": 330, "t": 9, "R": 45},
    ]
    arcoord_profile = []
    status = False
    for profile in arShapeURib:
        if NameShapeCT == profile["name"]:
            A = profile["A"]
            B = profile["B"]
            H = profile["H"]
            t = profile["t"]
            R = profile["R"]
            status = True
            break

    if status == True:
        x = pbase[0]
        y = pbase[1]
        angUR = math.degrees(math.pi - math.atan(4.5))
        arcoord_profile.append([x - A / 2, 0])

        V = (x - B / 2, y - H)
        u1 = (1, 0)
        u2 = (math.cos(math.radians(angUR)), math.sin(math.radians(angUR)))
        St, En, Ce = fillet_on_two_lines(V, u1, u2, R, side="inside")
        points_arc = devide_arc_to_points_polyline(En, St, Ce, int(R // 1))
        # points_arc.reverse()
        for point in points_arc:
            arcoord_profile.append(point)

        V = (x + B / 2, y - H)
        u1 = (-1, 0)
        u2 = (-math.cos(math.radians(angUR)), math.sin(math.radians(angUR)))
        St, En, Ce = fillet_on_two_lines(V, u1, u2, R, side="inside")
        points_arc = devide_arc_to_points_polyline(St, En, Ce, int(R // 1))
        # points_arc.reverse()
        for point in points_arc:
            arcoord_profile.append(point)
        arcoord_profile.append([x + A / 2, 0])

        # ---------------------------------------
        p1, p2 = Offset_Line((x + A / 2, 0), (x + B / 2, y - H), -t)
        p3, p4 = Offset_Line((x - B / 2, y - H), (x + B / 2, y - H), t)
        p1234 = Intersec_line_line(p1, p2, p3, p4)
        arcoord_profile.append(p1)
        V = p1234
        u1 = (-1, 0)
        u2 = (-math.cos(math.radians(angUR)), math.sin(math.radians(angUR)))
        St, En, Ce = fillet_on_two_lines(V, u1, u2, R, side="inside")
        points_arc = devide_arc_to_points_polyline(St, En, Ce, int(R // 1))
        points_arc.reverse()
        for point in points_arc:
            arcoord_profile.append(point)

        p1, p2 = Offset_Line((x - A / 2, 0), (x - B / 2, y - H), t)
        p3, p4 = Offset_Line((x - B / 2, y - H), (x + B / 2, y - H), t)
        p1234 = Intersec_line_line(p1, p2, p3, p4)
        V = p1234
        u1 = (1, 0)
        u2 = (math.cos(math.radians(angUR)), math.sin(math.radians(angUR)))
        St, En, Ce = fillet_on_two_lines(V, u1, u2, R, side="inside")
        points_arc = devide_arc_to_points_polyline(En, St, Ce, int(R // 1))
        points_arc.reverse()
        for point in points_arc:
            arcoord_profile.append(point)
        arcoord_profile.append(p1)

        # arcoord_profile = rotate_points(arcoord_profile, (0, 0), -90)
    else:
        return None

    return arcoord_profile


def find_line_coefficients(P1, P2):
    """
    Tính các hệ số a, b, c của phương trình đường thẳng ax + by + c = 0
    từ hai điểm P1 và P2.

    Args:
        P1: Tọa độ điểm thứ nhất (x1, y1).
        P2: Tọa độ điểm thứ hai (x2, y2).

    Returns:
        a, b, c: Hệ số của phương trình đường thẳng.
    """

    P1 = np.array(P1, dtype=float)
    if P1.shape[0] == 3:
        P1 = P1[:2]
    P2 = np.array(P2, dtype=float)
    if P2.shape[0] == 3:
        P2 = P2[:2]
    x1, y1 = P1
    x2, y2 = P2
    a = y2 - y1
    b = -(x2 - x1)
    c = -(a * x1 + b * y1)
    return a, b, c


def find_points_perpendicular_to_line(PsLine, PeLine, PonLine, distance):
    """
    Tìm tọa độ hai điểm cách đường thẳng một khoảng k và nằm trên đường vuông góc
    đi qua điểm A.

    Args:
        P1, P2: Hai điểm xác định đường thẳng.
        A: Tọa độ điểm A (nằm trên đường thẳng).
        k: Khoảng cách cần tìm.

    Returns:
        Hai điểm tọa độ (x1, y1) và (x2, y2).
    """
    PsLine = np.array(PsLine, dtype=float)
    if PsLine.shape[0] == 3:
        PsLine = PsLine[:2]
    PeLine = np.array(PeLine, dtype=float)
    if PeLine.shape[0] == 3:
        PeLine = PeLine[:2]
    PonLine = np.array(PonLine, dtype=float)
    if PonLine.shape[0] == 3:
        PonLine = PonLine[:2]
    # Tính hệ số đường thẳng
    a, b, c = find_line_coefficients(PsLine, PeLine)

    # Tọa độ điểm PonLine
    x0, y0 = PonLine

    # 法線ベクトルの長さ
    norm = math.sqrt(a**2 + b**2)

    # ゼロ除算を防ぐための閾値
    epsilon = 1e-10
    if norm < epsilon:
        # 直線が無効な場合、元の点を返す
        return (x0, y0)

    # Aから距離kにある2点の座標を計算
    x1 = x0 + distance * a / norm
    y1 = y0 + distance * b / norm

    return (x1, y1)


def Calculate_Coord_Mid(arCoordLines_1, arCoordLines_2):
    CoordLines_mid = arCoordLines_1.copy()

    for i in range(0, len(CoordLines_mid)):
        CoordLines_mid[i] = [(a + b) / 2 for a, b in zip(arCoordLines_1[i], arCoordLines_2[i])]

    return CoordLines_mid


def is_real_number(value):
    try:
        float(value)
        return True
    except ValueError:
        return False


def calculate_unit_vector_bridge(start_point, end_point):
    """
    橋梁の開始点から終了点への単位ベクトルを計算する

    Args:
        start_point: 開始点
        end_point: 終了点

    Returns:
        単位ベクトル
    """
    start_point = np.array(start_point, dtype=float)
    end_point = np.array(end_point, dtype=float)
    dir_vector = end_point - start_point
    norm_dir = np.linalg.norm(dir_vector)
    # ゼロ除算を防ぐための閾値
    epsilon = 1e-10
    if norm_dir < epsilon:
        # 開始点と終了点が同じ場合、デフォルトの単位ベクトルを返す
        return np.array([1.0, 0.0, 0.0])
    unit_vector = dir_vector / norm_dir

    return unit_vector
