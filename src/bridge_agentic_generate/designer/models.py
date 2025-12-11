from __future__ import annotations

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
