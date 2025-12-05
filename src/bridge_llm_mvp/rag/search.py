# src/bridge_llm_mvp/rag/search.py
from __future__ import annotations

from typing import Sequence


def search_text(query: str, top_k: int = 5) -> list[str]:
    """RAG 用のテキスト検索関数 (MVP 用のシンプルなインターフェース)。

    現時点ではダミー実装で、空のリストを返す。
    後でベクターストアや自前の検索ロジックに差し替える。

    Args:
        query: 検索クエリ（日本語で OK）。
        top_k: 上位何件まで取得するか。

    Returns:
        検索でヒットしたテキストチャンクのリスト。
    """
    # TODO: PDF から抽出したチャンクを検索する実装に差し替える。
    _ = top_k  # 未使用変数警告を避けるため
    return []


def search_multiple(queries: Sequence[str], top_k: int = 5) -> list[list[str]]:
    """複数クエリをまとめて検索するためのヘルパー関数。

    Args:
        queries: クエリのリスト。
        top_k: 各クエリごとに取得する件数。

    Returns:
        各クエリごとのテキストチャンクリスト。
    """
    return [search_text(q, top_k=top_k) for q in queries]
