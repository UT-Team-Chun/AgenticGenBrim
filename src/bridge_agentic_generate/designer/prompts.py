from src.bridge_agentic_generate.designer.models import DesignerInput

DESIGNER_PROMPT = """
あなたは鋼橋設計の専門家です。
提供された参考文献（RAGコンテキスト）に基づき、鋼プレートガーダー橋（RC床版）の概略断面設計を行ってください。

# 入力条件
- 橋長 L: {bridge_length_m} m
- 幅員 B: {total_width_m} m
- 橋種: 鋼プレートガーダー橋（RC床版合成桁）

# 参考文献 (RAG Context)

## [1] 桁配置・支間割・全体諸元 (dimensions_context)
{dimensions_context}

## [2] 主桁断面 (girder_section_context)
{girder_section_context}

## [3] RC床版 (deck_context)
{deck_context}

## [4] その他 (other_context)
{other_context}

これらのテキストは、設計の根拠となる条文・解説の一部抜粋です。
引用されていない条文を勝手に想像せず、基本的には上記の範囲で考えてください。

# 設計手順と注意事項

1. **思考プロセスの記述 (reasoning)**
   - まず、参考文献のどの部分を重視するか、設計の全体方針を検討し、日本語で記述してください。
   - 競合する条件がある場合、どのように判断したかも記述してください。

2. **設計ルールの抽出 (rules)**
   - 参考文献から、今回の設計に適用すべき具体的な数値基準や数式を抽出してください。
   - 抽出したルールは `DesignRule` オブジェクトとしてリスト化してください。
   - 各ルールには、根拠となった参考文献の番号 (Reference N) を `source_hit_ranks` に記録してください。
   - 参考文献にないが実務上必要な仮定を行った場合は、その旨を `notes` に記述してください。

3. **断面諸元の決定 (bridge_design)**
   - 抽出したルールと入力条件に基づき、具体的な寸法を決定してください。
   - **幾何学的整合性**: 桁本数・桁間隔と全幅の関係が矛盾しないようにしてください。
   - **工学的妥当性**: 参考文献に記載がない項目については、一般的な工学的知見に基づいて妥当な値を仮定し、
     極端な値（薄すぎる板厚など）は避けてください。
   - すべての長さ・厚さは **mm 単位** で出力すること。

出力は定義されたスキーマ (DesignerOutput) に従ってください。
"""


def build_designer_prompt(
    inputs: DesignerInput,
    dimensions_context: str,
    girder_section_context: str,
    deck_context: str,
    other_context: str = "",
) -> str:
    """Designer 用のプロンプト文を組み立てる。

    Args:
        inputs: 設計条件（橋長 L, 幅員 B）。
        dimensions_context: 桁配置・全体諸元のコンテキスト文字列。
        girder_section_context: 主桁断面のコンテキスト文字列。
        deck_context: 床版のコンテキスト文字列。
        other_context: その他のコンテキスト文字列。

    Returns:
        str: LLM に渡すプロンプト文。
    """
    return DESIGNER_PROMPT.format(
        bridge_length_m=inputs.bridge_length_m,
        total_width_m=inputs.total_width_m,
        dimensions_context=dimensions_context,
        girder_section_context=girder_section_context,
        deck_context=deck_context,
        other_context=other_context,
    )
