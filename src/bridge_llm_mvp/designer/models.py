from __future__ import annotations

from pydantic import BaseModel, Field


class DesignerInput(BaseModel):
    """LLM Designer に渡す入力（MVP版）。

    橋長 L [m] と 全幅 B [m] だけ。
    """

    span_length_m: float = Field(..., description="橋長 L [m]")
    total_width_m: float = Field(..., description="幅員 B [m]")


class Dimensions(BaseModel):
    """設計結果の全体寸法（単位 mm）。"""

    span_length_mm: float = Field(..., description="橋長 L [mm]")
    total_width_mm: float = Field(..., description="幅員 B [mm]")
    num_girders: int = Field(..., description="主桁本数")
    girder_spacing_mm: float = Field(..., description="主桁間隔 [mm]")
    panel_length_mm: float = Field(..., description="横桁ピッチ [mm]")


class GirderSection(BaseModel):
    """主桁の標準断面（I 形）。単位 mm。"""

    web_height_mm: float = Field(..., description="腹板高さ（フランジ間距離）[mm]")
    web_thickness_mm: float = Field(..., description="腹板板厚 [mm]")
    top_flange_width_mm: float = Field(..., description="上フランジ幅 [mm]")
    top_flange_thickness_mm: float = Field(..., description="上フランジ厚 [mm]")
    bottom_flange_width_mm: float = Field(..., description="下フランジ幅 [mm]")
    bottom_flange_thickness_mm: float = Field(..., description="下フランジ厚 [mm]")


class CrossbeamSection(BaseModel):
    """横桁の標準断面（I 形）。単位 mm。"""

    total_height_mm: float = Field(..., description="桁高 [mm]")
    web_thickness_mm: float = Field(..., description="腹板板厚 [mm]")
    flange_width_mm: float = Field(..., description="フランジ幅 [mm]")
    flange_thickness_mm: float = Field(..., description="フランジ厚 [mm]")


class Deck(BaseModel):
    """床版（MVPでは厚さだけ）。"""

    thickness_mm: float = Field(..., description="床版厚 [mm]")


class Sections(BaseModel):
    """断面情報のコンテナ。"""

    girder_standard: GirderSection
    crossbeam_standard: CrossbeamSection


class Components(BaseModel):
    """構成要素。MVPでは床版だけ。"""

    deck: Deck


class BridgeDesign(BaseModel):
    """Designer が返す設計結果のトップレベルモデル。"""

    dimensions: Dimensions
    sections: Sections
    components: Components
