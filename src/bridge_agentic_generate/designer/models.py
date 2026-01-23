from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class DesignerInput(BaseModel):
    """LLM Designer に渡す入力（MVP版）。

    橋長 L [m] と 全幅 B [m] だけ。
    """

    bridge_length_m: float = Field(..., description="橋長 L [m]")
    total_width_m: float = Field(..., description="幅員 B [m]")


class Dimensions(BaseModel):
    bridge_length: float = Field(..., description="橋長 [mm]。")
    total_width: float = Field(..., description="橋全幅 [mm]。")
    num_girders: int = Field(..., description="主桁本数。")
    girder_spacing: float = Field(..., description="主桁間隔 [mm]。")
    panel_length: float = Field(..., description="パネル長 [mm]。")
    num_panels: int | None = Field(default=None, description="指定がない場合は bridge_length / panel_length から算出。")


class GirderSection(BaseModel):
    """主桁の標準断面（I 形）。単位 mm。"""

    web_height: float = Field(..., description="腹板高さ（フランジ間距離）[mm]")
    web_thickness: float = Field(..., description="腹板板厚 [mm]")
    top_flange_width: float = Field(..., description="上フランジ幅 [mm]")
    top_flange_thickness: float = Field(..., description="上フランジ厚 [mm]")
    bottom_flange_width: float = Field(..., description="下フランジ幅 [mm]")
    bottom_flange_thickness: float = Field(..., description="下フランジ厚 [mm]")


class CrossbeamSection(BaseModel):
    """横桁の標準断面（I 形）。単位 mm。"""

    total_height: float = Field(..., description="桁高 [mm]")
    web_thickness: float = Field(..., description="腹板板厚 [mm]")
    flange_width: float = Field(..., description="フランジ幅 [mm]")
    flange_thickness: float = Field(..., description="フランジ厚 [mm]")


class Deck(BaseModel):
    """床版（MVPでは厚さだけ）。"""

    thickness: float = Field(..., description="床版厚 [mm]")


class Sections(BaseModel):
    """断面情報のコンテナ。"""

    girder_standard: GirderSection = Field(..., description="主桁標準断面。")
    crossbeam_standard: CrossbeamSection = Field(..., description="横桁標準断面。")


class Components(BaseModel):
    """構成要素。MVPでは床版だけ。"""

    deck: Deck = Field(..., description="RC床版。")


class BridgeDesign(BaseModel):
    """Designer が返す設計結果のトップレベルモデル。"""

    dimensions: Dimensions = Field(..., description="橋全体の寸法情報。")
    sections: Sections = Field(..., description="主桁・横桁の断面情報。")
    components: Components = Field(..., description="床版などの構成要素。")


class RagHit(BaseModel):
    """RAG で取得した 1 件分のヒット。"""

    rank: int = Field(..., description="ランキング（1始まり）")
    score: float = Field(..., description="コサイン類似度スコア")
    source: str = Field(..., description="元ファイル名（PDF 名）")
    page: int = Field(..., description="PDF ページ番号（0始まり）")
    text: str = Field(..., description="チャンク本文")


class DesignerRagLog(BaseModel):
    """Designer 実行時の RAG コンテキストログ。"""

    query: str = Field(..., description="RAG 用に投げたクエリ文字列")
    top_k: int = Field(..., description="取得した件数")
    hits: list[RagHit] = Field(..., description="ヒット一覧（スコア順）")
    reasoning: str = Field(
        default="",
        description="設計プロセス全体の思考・判断根拠。",
    )
    rules: list[DesignRule] = Field(
        default_factory=list,
        description="適用した設計ルール一覧。",
    )
    dependency_rules: list[DependencyRule] = Field(
        default_factory=list,
        description="部材間の依存関係ルール。",
    )


class DesignResult(BaseModel):
    """設計結果とRAGログを含むレスポンスモデル。"""

    design: BridgeDesign = Field(..., description="生成された設計結果")
    rag_log: DesignerRagLog = Field(..., description="RAGの実行ログ")
    rules: list[DesignRule] | None = Field(
        default=None,
        description="今回の設計で使用したルール一覧（あれば）。",
    )
    dependency_rules: list[DependencyRule] = Field(
        default_factory=list,
        description="部材間の依存関係ルール。PatchPlan 適用後の連動更新に使用。",
    )


class DesignRuleCategory(StrEnum):
    DIMENSIONS = "dimensions"
    GIRDER_SECTION = "girder_section"
    DECK = "deck"
    CROSSBEAM_SECTION = "crossbeam_section"
    OTHER = "other"


class DependencyRule(BaseModel):
    """部材間の依存関係を表す演算可能なルール。

    主に「横桁高さは主桁高さの〇倍」といった連動関係を表現する。
    PatchPlan 適用後に自動で連動させるために使用する。
    """

    rule_id: str = Field(
        ...,
        description='ルールID (例: "D1", "D2" などの連番)。',
    )
    target_field: str = Field(
        ...,
        description='更新対象のフィールドパス (例: "crossbeam.total_height")。',
    )
    source_field: str = Field(
        ...,
        description='参照元のフィールドパス (例: "girder.web_height")。',
    )
    factor: float = Field(
        ...,
        description="係数 (例: 0.8)。target = source × factor で計算される。",
    )
    source_hit_ranks: list[int] = Field(
        default_factory=list,
        description="該当する RAG ヒットの rank (1 始まり) の一覧。",
    )
    notes: str | None = Field(
        default=None,
        description='補足 (例: "示方書より横桁高さは主桁の80%程度")。省略可。',
    )


class DesignRule(BaseModel):
    """今回の設計で使用したルール 1 件分（簡易 Extractor 用）。

    - 今は Designer の中で都度生成するが、
      将来的には独立した Extractor コンポーネントでも再利用できる形を目指す。
    """

    rule_id: str = Field(
        ...,
        description='ルールID (例: "R1", "R2" などの連番)。',
    )
    category: DesignRuleCategory = Field(
        ...,
        description=(
            "ルールのカテゴリ。"
            "dimensions: 橋長・幅員・桁本数・桁間隔・パネル長など全体寸法, "
            "girder_section: 主桁断面, "
            "deck: RC床版, "
            "crossbeam_section: 横桁, "
            "other: その他。"
        ),
    )
    summary: str = Field(
        ...,
        description="ルール内容の日本語要約（1〜3文程度）。",
    )
    condition_expression: str | None = Field(
        default=None,
        description='不等式や比などの条件式 (例: "web_height ≒ L/20〜L/25")。省略可。',
    )
    formula_latex: str | None = Field(
        default=None,
        description=('数式がある場合の LaTeX 風表現 (例: "h_g \\approx L/20 \\sim L/25")。省略可。'),
    )
    applies_to_fields: list[str] = Field(
        default_factory=list,
        description=(
            "このルールが影響する BridgeDesign のフィールド名一覧。"
            '例: ["dimensions.num_girders", '
            '"sections.girder_standard.web_height"] など。'
        ),
    )
    source_hit_ranks: list[int] = Field(
        default_factory=list,
        description=(
            "該当する RAG ヒットの rank (1 始まり) の一覧。DesignerRagLog.hits[*].rank への参照として用いる。"
        ),
    )
    notes: str | None = Field(
        default=None,
        description="解釈上の注意や適用範囲などの補足。省略可。",
    )


class DesignerOutput(BaseModel):
    """LLM (Designer) からの Structured Output。

    - reasoning: 設計プロセス全体の思考・判断根拠
    - rules: 今回の設計で使用したルール一覧（簡易 Extractor 的）
    - dependency_rules: 部材間の依存関係ルール（PatchPlan 連動用）
    - bridge_design: 既存の BridgeDesign モデル
    """

    reasoning: str = Field(
        ...,
        description="設計プロセス全体の思考・判断根拠。なぜその寸法を選んだか、どの条文を重視したかなど。",
    )
    rules: list[DesignRule] = Field(
        default_factory=list,
        description="今回の設計で利用した設計ルール一覧。",
    )
    dependency_rules: list[DependencyRule] = Field(
        default_factory=list,
        description="部材間の依存関係ルール。PatchPlan 適用後の連動更新に使用。",
    )
    bridge_design: BridgeDesign = Field(
        ...,
        description="生成された橋梁断面 (BridgeDesign)。",
    )
