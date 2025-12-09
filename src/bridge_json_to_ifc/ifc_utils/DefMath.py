"""IFC 生成で用いる基本的な幾何ユーティリティ。"""

from __future__ import annotations

from typing import Sequence

import numpy as np

DEFAULT_Z_VALUE = 0.0
LENGTH_EPS = 1e-9

type PointLike = Sequence[float]
type Vector3D = np.ndarray


def _ensure_3d(point: PointLike) -> Vector3D:
    """2次元/3次元座標を必ず3次元ベクトルに変換する。

    Args:
        point: 2要素または3要素の座標

    Returns:
        3次元の numpy 配列
    """
    array = np.array(point, dtype=float)
    if array.shape[0] == 2:
        array = np.append(array, DEFAULT_Z_VALUE)
    return array


def Calculate_distance_p2p(point1: PointLike, point2: PointLike) -> float:
    """2点間距離を計算する。

    Args:
        point1: 始点座標
        point2: 終点座標

    Returns:
        2点間のユークリッド距離
    """
    p1 = _ensure_3d(point1)
    p2 = _ensure_3d(point2)
    return float(np.linalg.norm(p2 - p1))


def Point_on_line(p1: PointLike, p2: PointLike, distance: float) -> Vector3D:
    """始点から指定距離だけ直線上に進んだ座標を返す。

    Args:
        p1: 直線上の始点
        p2: 直線上の終点（方向を与える）
        distance: 始点からの距離

    Returns:
        3次元座標

    Raises:
        ValueError: 2点が同一で方向が定義できない場合
    """
    start = _ensure_3d(p1)
    end = _ensure_3d(p2)
    direction = end - start
    length = np.linalg.norm(direction)
    if length < LENGTH_EPS:
        raise ValueError("始点と終点が同一点のため、方向ベクトルを計算できません。")
    unit_direction = direction / length
    return start + distance * unit_direction


def Point_on_parallel_line(pbase: PointLike, p1dir: PointLike, p2dir: PointLike, distance: float) -> Vector3D:
    """基準点から指定距離だけ方向ベクトルに沿って平行移動した座標を返す。

    Args:
        pbase: 平行移動の基準点
        p1dir: 方向ベクトルの始点
        p2dir: 方向ベクトルの終点
        distance: 平行移動量

    Returns:
        3次元座標

    Raises:
        ValueError: 方向ベクトルの長さが0の場合
    """
    base = _ensure_3d(pbase)
    dir_start = _ensure_3d(p1dir)
    dir_end = _ensure_3d(p2dir)
    direction = dir_end - dir_start
    length = np.linalg.norm(direction)
    if length < LENGTH_EPS:
        raise ValueError("方向ベクトルの長さが0のため、平行移動方向を決定できません。")
    unit_direction = direction / length
    return base + distance * unit_direction
