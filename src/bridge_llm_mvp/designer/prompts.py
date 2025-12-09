from typing import Sequence

from src.bridge_llm_mvp.designer.models import DesignerInput
from src.bridge_llm_mvp.rag.embedding_config import IndexChunk


def build_designer_prompt(
    inputs: DesignerInput,
    chunks: Sequence[IndexChunk],
) -> str:
    """Designer 用のプロンプト文を組み立てる。

    Args:
        inputs: 設計条件（橋長 L, 幅員 B）。
        chunks: 参考文献チャンク（教科書・示方書から RAG で取得）。

    Returns:
        str: LLM に渡すプロンプト文。
    """
    header = f"""あなたは鋼橋の設計担当エンジニアです。
橋長 L と幅員 B が与えられたとき、鋼プレートガーダー橋（RC床版）の断面モデルを提案してください。

## 設計条件
- 橋長 L = {inputs.bridge_length_m:.1f} m
- 幅員 B = {inputs.total_width_m:.1f} m
## 参考文献
次に示すのは、教科書および道路橋示方書からの参考抜粋です。
これらを根拠として、工学的に妥当な寸法のモデルを提案してください。
"""

    refs_parts: list[str] = []
    for i, chunk in enumerate(chunks, start=1):
        refs_parts.append(
            f"\n--- 参考テキスト {i} ---\n[source={chunk.source}, page={chunk.page}]\n{chunk.text}\n",
        )

    refs_block = "\n".join(refs_parts)

    tail = """
## 注意事項
- 出力は与えられた JSON スキーマ（BridgeDesign）に従ってください。
- 値が不明な場合でも、工学的に妥当だと思う値を仮定して埋めてください。
"""

    return header + refs_block + tail
