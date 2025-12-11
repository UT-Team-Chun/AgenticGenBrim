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
   - - 条文や図中に「d = 30L + 110」などの明確な設計式がある場合は、
        必ず condition_expression および formula_latex にその式を含めてください。
   - - 単なる「代表例の数値」（例：床版厚 210 mm の断面例）は、
        原則として notes に書き、condition_expression では式を優先してください。

   - 抽出したルールは `DesignRule` オブジェクトとしてリスト化してください。
   - 各ルールには、根拠となった参考文献の番号 (Reference N) を `source_hit_ranks` に記録してください。
   - **重要**: 参考文献に見当たらないが実務上必要な仮定を行う場合、`source_hit_ranks` は空にし、
     必ず `summary` または `notes` に「仮定」「実務的目安」等の文言を含めて区別してください。

3. **断面諸元の決定 (bridge_design)**
   - 抽出した `rules` の条件式を **数値的に満たす** ように寸法を決定してください。
   - 条文や教科書から抽出されたルール（source_hit_ranks が空でないもの）は、
    可能な限りすべて満足することを第一優先としてください。
   - それらのルール同士がどうしても両立しない場合のみ、
    どのルールを緩和したかを notes に明示したうえで妥協してください。

   - **幾何学的整合性**: 桁本数・桁間隔と全幅の関係が矛盾しないようにしてください。
     - 全幅 B = (主桁本数 - 1) × 主桁間隔 + 2 × 張出し長 (overhang)
     - 張出し長は通常 0.5m ～ 1.5m 程度確保してください。
     - 主桁の中心線は、床版端より overhang だけ内側に位置するものとし、
        主桁中心が床版の外側に出るような配置はとってはならない。

   - **工学的妥当性**: 参考文献に記載がない項目については、一般的な工学的知見に基づいて妥当な値を仮定し、
     極端な値（薄すぎる板厚など）は避けてください。
   - RC床版厚さを算定するときの支間 L_support には、主桁の中心間隔
  (= girder_spacing [mm] を m に換算したもの) を用いてよい。
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
