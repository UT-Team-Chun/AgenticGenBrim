# src/bridge_llm_mvp/designer/service.py
from __future__ import annotations

from bridge_llm_mvp.designer.models import BridgeDesign, DesignerInput
from bridge_llm_mvp.rag.search import search_text


def build_designer_system_prompt() -> str:
    """Designer 用のシステムプロンプトを組み立てる。

    実装としては、卒論で決めた「役割・前提条件・出力 JSON スキーマ」の説明を
    ここにまとめるイメージ。
    """
    # TODO: 本物のプロンプト本文を書く。
    return (
        "あなたは鋼プレートガーダー橋の設計エンジニアです。"
        "橋長 L [m] と幅員 B [m] から、主桁・横桁・床版厚の断面モデルを JSON で出力します。"
    )


def build_designer_user_prompt(designer_input: DesignerInput) -> str:
    """Designer に渡すユーザープロンプト部分を組み立てる。

    Args:
        designer_input: 橋長 L, 幅員 B を含む入力。

    Returns:
        ユーザー部分のプロンプト文字列。
    """
    return (
        "以下の条件で鋼プレートガーダー橋の断面モデルを設計してください。\n"
        f"- 支間長 L = {designer_input.span_length_m:.3f} m\n"
        f"- 全幅 B = {designer_input.total_width_m:.3f} m\n"
        "出力は指定された JSON スキーマに従ってください。"
    )


def generate_design(designer_input: DesignerInput) -> BridgeDesign:
    """LLM Designer を呼び出して橋梁断面モデルを生成する。

    現時点ではダミー実装であり、NotImplementedError を送出する。
    後で OpenAI などの LLM API を呼び出す処理に差し替える。

    Args:
        designer_input: 橋長 L, 幅員 B。

    Returns:
        LLM が生成した BridgeDesign モデル。
    """
    # ここで将来的には:
    # 1. RAG で必要な条文や設計例を検索 (e.g., 床版, 腹板, フランジ など)
    # 2. system_prompt / user_prompt を組み立てる
    # 3. structured output (BridgeDesign モデルに対応するスキーマ) を指定して LLM を呼ぶ
    # という流れになる想定。
    _ = search_text  # 一旦未使用回避。実装時に削る。

    system_prompt = build_designer_system_prompt()
    user_prompt = build_designer_user_prompt(designer_input)
    _ = (system_prompt, user_prompt)  # こちらも未使用回避

    msg = "generate_design() はまだ実装されていません。LLM クライアントを用意したら、この関数内で呼び出してください。"
    raise NotImplementedError(msg)
