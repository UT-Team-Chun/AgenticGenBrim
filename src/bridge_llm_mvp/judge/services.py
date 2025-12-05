# src/bridge_llm_mvp/judge/service.py
from __future__ import annotations

from bridge_llm_mvp.judge.models import JudgeInput, JudgeResult, OverallStatus
from bridge_llm_mvp.rag.search import search_text


def build_judge_system_prompt() -> str:
    """Judge 用のシステムプロンプトを組み立てる。

    道路橋示方書・鋼橋・鋼部材編を参照しながら、
    寸法条件をチェックする審査エンジニアという役割を与える。
    """
    # TODO: 本物の Judge 用プロンプト本文を書く。
    return (
        "あなたは道路橋示方書・鋼橋・鋼部材編に基づいて鋼橋断面を審査するエンジニアです。"
        "与えられた断面が主な寸法規定を満足するかどうかを JSON で評価してください。"
    )


def build_judge_user_prompt(judge_input: JudgeInput) -> str:
    """Judge に渡すユーザープロンプト部分を組み立てる。

    Args:
        judge_input: 元の L,B と Designer の設計結果。

    Returns:
        ユーザー部分のプロンプト文字列。
    """
    return (
        "以下の鋼プレートガーダー橋断面について、道路橋示方書の寸法規定を満足しているか"
        "評価してください。\n"
        f"- 支間長 L = {judge_input.span_length_m:.3f} m\n"
        f"- 全幅 B = {judge_input.total_width_m:.3f} m\n"
        "対象は床版厚・腹板厚・フランジ幅厚比・横桁間隔の4点です。"
    )


def judge_design(judge_input: JudgeInput) -> JudgeResult:
    """LLM Judge を呼び出して、設計結果を評価する。

    現時点ではダミー実装であり、すべて OK の固定値を返す。
    後で LLM API を呼び出す処理に差し替える。

    Args:
        judge_input: L,B と設計結果。

    Returns:
        JudgeResult: overall_status と checks のリスト。
    """
    # TODO: RAG で示方書の該当条文を検索し、LLM に判定させる実装に差し替える。
    _ = search_text
    _ = judge_input

    # ひとまず「何もしないけど構造的には正しい」ダミーを返す
    return JudgeResult(overall_status=OverallStatus.OK, checks=[])
