"""SenkeiSpec形式のPydanticモデル定義。

json_spec形式（bridge-bimシステム用）のデータモデルを定義する。
"""

from __future__ import annotations

from enum import IntEnum, StrEnum

from pydantic import BaseModel, ConfigDict, Field


class SideExport(IntEnum):
    """エクスポート側面。"""

    LOWER_ONLY = -1  # 下側のみ
    UPPER_ONLY = 1  # 上側のみ
    BOTH = 2  # 両側（デフォルト）


class PanelType(StrEnum):
    """パネルタイプ。"""

    W = "W"  # Web（ウェブ）
    UF = "UF"  # Upper Flange（上フランジ）
    LF = "LF"  # Lower Flange（下フランジ）
    WL = "WL"  # Web Left（左側のみ）
    WR = "WR"  # Web Right（右側のみ）


class YokogetaReference(StrEnum):
    """横桁配置基準。"""

    TOP = "Top"  # 上フランジ基準（横桁上フランジ上面 = 主桁上フランジ下面）
    BOTTOM = "Bottom"  # 下フランジ基準（横桁下フランジ下面 = 主桁下フランジ上面）


# =============================================================================
# 基本情報
# =============================================================================


class Infor(BaseModel):
    """橋梁基本情報。"""

    name_bridge: str = Field(..., alias="NameBridge", description="橋梁名")
    side_export: int = Field(default=SideExport.BOTH, alias="SideExport", description="エクスポート側 2=両側")

    model_config = ConfigDict(populate_by_name=True)


# =============================================================================
# 線形データ
# =============================================================================


class SenkeiPoint(BaseModel):
    """線形の1点。"""

    name: str = Field(..., alias="Name", description="点名称 例: S1, C1, E1")
    x: float = Field(..., alias="X", description="X座標 [mm]（橋軸方向）")
    y: float = Field(..., alias="Y", description="Y座標 [mm]（幅方向）")
    z: float = Field(..., alias="Z", description="Z座標 [mm]（高さ方向）")

    model_config = ConfigDict(populate_by_name=True)


class Senkei(BaseModel):
    """線形データ。"""

    name: str = Field(..., alias="Name", description="線形名 例: TG1, TG1L, BG2R")
    point: list[SenkeiPoint] = Field(..., alias="Point", description="座標点リスト")

    model_config = ConfigDict(populate_by_name=True)


# =============================================================================
# MainPanel関連
# =============================================================================


class GirderBlockType(BaseModel):
    """パネルのタイプ情報。"""

    girder: str = Field(..., alias="Girder", description="桁番号 例: G1")
    block: str = Field(..., alias="Block", description="ブロック番号 例: B1")
    type_panel: str = Field(..., alias="TypePanel", description="パネルタイプ W/UF/LF")

    model_config = ConfigDict(populate_by_name=True)


class PanelMaterial(BaseModel):
    """パネル材料情報。"""

    thick1: float = Field(..., alias="Thick1", description="厚さ1 [mm]")
    thick2: float = Field(..., alias="Thick2", description="厚さ2 [mm]")
    mat: str = Field(default="SM490A", alias="Mat", description="材料名")
    split_thickness: bool | None = Field(
        default=None, alias="SplitThickness", description="厚み分割フラグ（UF/LFで使用）"
    )

    model_config = ConfigDict(populate_by_name=True)


class PanelExpand(BaseModel):
    """パネル延長設定。"""

    e1: int | str = Field(default=0, alias="E1", description="左側延長 [mm] または 'A'")
    e2: int | str = Field(default=0, alias="E2", description="右側延長 [mm] または 'A'")
    e3: int | str = Field(default=0, alias="E3", description="上側延長 [mm] または 'A'")
    e4: int | str = Field(default=0, alias="E4", description="下側延長 [mm] または 'A'")

    model_config = ConfigDict(populate_by_name=True)


class PanelJbut(BaseModel):
    """パネル継手設定。"""

    s: list[str] = Field(default_factory=list, alias="S", description="始端側継手")
    e: list[str] = Field(default_factory=list, alias="E", description="終端側継手")

    model_config = ConfigDict(populate_by_name=True)


class PanelBreak(BaseModel):
    """パネル分割情報。"""

    lenght: list[float] = Field(default_factory=list, alias="Lenght", description="各区間長さ [mm]")
    extend: list[int] = Field(default_factory=list, alias="Extend", description="各区間延長")
    thick: list[str] = Field(default_factory=list, alias="Thick", description="各区間厚さ 'Thick1/Thick2'形式")

    model_config = ConfigDict(populate_by_name=True)


class MainPanel(BaseModel):
    """主桁パネル。"""

    name: str = Field(..., alias="Name", description="パネル名 例: G1B1W")
    line: list[str] = Field(..., alias="Line", description="使用線形名リスト")
    sec: list[str] = Field(..., alias="Sec", description="使用断面点リスト")
    type: GirderBlockType = Field(..., alias="Type")
    material: PanelMaterial = Field(..., alias="Material")
    expand: PanelExpand = Field(default_factory=PanelExpand, alias="Expand")
    jbut: PanelJbut = Field(default_factory=PanelJbut, alias="Jbut")
    break_: PanelBreak | dict = Field(default_factory=dict, alias="Break")
    corner: list = Field(default_factory=list, alias="Corner")
    lrib: list = Field(default_factory=list, alias="Lrib")
    vstiff: list = Field(default_factory=list, alias="Vstiff")
    hstiff: list = Field(default_factory=list, alias="Hstiff")
    atm: list = Field(default_factory=list, alias="Atm")
    cutout: list = Field(default_factory=list, alias="Cutout")
    stud: list = Field(default_factory=list, alias="Stud")

    model_config = ConfigDict(populate_by_name=True)


# =============================================================================
# Yokogeta関連
# =============================================================================


class WebSpec(BaseModel):
    """横桁ウェブ仕様。"""

    thick: float = Field(..., alias="Thick", description="板厚 [mm]")
    mat: str = Field(default="SM490A", alias="Mat", description="材料名")

    model_config = ConfigDict(populate_by_name=True)


class FlangeSpec(BaseModel):
    """横桁フランジ仕様。"""

    thick: float = Field(..., alias="Thick", description="板厚 [mm]")
    width: float = Field(..., alias="Width", description="フランジ幅 [mm]")
    mat: str = Field(default="SM490A", alias="Mat", description="材料名")

    model_config = ConfigDict(populate_by_name=True)


class YokogetaBreak(BaseModel):
    """横桁分割設定。"""

    count: int = Field(default=1, alias="Count", description="厚み方向分割数")

    model_config = ConfigDict(populate_by_name=True)


class Yokogeta(BaseModel):
    """I形横桁。"""

    name: str = Field(..., alias="Name", description="横桁名 例: CB_G1_G2_C1")
    girder: list[str] = Field(..., alias="Girder", description="接続桁 ['G1', 'G2']")
    section: str = Field(..., alias="Section", description="配置断面 例: C1")
    reference: str = Field(
        default=YokogetaReference.TOP,
        alias="Reference",
        description="配置基準 Top/Bottom",
    )
    height: float = Field(..., alias="Height", description="横桁せい [mm]")
    z_offset: float = Field(default=0, alias="ZOffset", description="Z方向オフセット [mm]")
    web: WebSpec = Field(..., alias="Web")
    u_flange: FlangeSpec = Field(..., alias="UFlange")
    l_flange: FlangeSpec = Field(..., alias="LFlange")
    break_: YokogetaBreak = Field(default_factory=YokogetaBreak, alias="Break")

    model_config = ConfigDict(populate_by_name=True)


# =============================================================================
# Shouban関連
# =============================================================================


class ShoubanBreakX(BaseModel):
    """床版X方向分割設定。"""

    type: str = Field(..., alias="Type", description="分割タイプ sections/equal")
    sections: list[str] | None = Field(default=None, alias="Sections", description="断面点リスト")
    count: int | None = Field(default=None, alias="Count", description="等分割数")

    model_config = ConfigDict(populate_by_name=True)


class ShoubanBreakY(BaseModel):
    """床版Y方向分割設定。"""

    type: str = Field(..., alias="Type", description="分割タイプ webs/equal")
    girders: list[str] | None = Field(default=None, alias="Girders", description="桁リスト")
    count: int | None = Field(default=None, alias="Count", description="等分割数")

    model_config = ConfigDict(populate_by_name=True)


class ShoubanBreak(BaseModel):
    """床版分割設定。"""

    thick: int = Field(default=1, alias="Thick", description="厚さ方向分割数")
    x: ShoubanBreakX | int | dict = Field(default_factory=dict, alias="X", description="X方向分割")
    y: ShoubanBreakY | int | dict = Field(default_factory=dict, alias="Y", description="Y方向分割")

    model_config = ConfigDict(populate_by_name=True)


class Shouban(BaseModel):
    """床版。"""

    name: str = Field(..., alias="Name", description="床版名 例: Deck_Main")
    line: list[str] = Field(..., alias="Line", description="4隅の線形名（反時計回り）")
    sec: list[str] = Field(..., alias="Sec", description="使用断面点リスト")
    thick: float = Field(..., alias="Thick", description="床版厚 [mm]")
    overhang_left: float = Field(default=0, alias="OverhangLeft", description="左側張り出し [mm]")
    overhang_right: float = Field(default=0, alias="OverhangRight", description="右側張り出し [mm]")
    break_: ShoubanBreak | dict = Field(default_factory=dict, alias="Break")

    model_config = ConfigDict(populate_by_name=True)


# =============================================================================
# トップレベルモデル
# =============================================================================


class SenkeiSpec(BaseModel):
    """json_spec形式のトップレベルモデル。"""

    infor: Infor = Field(..., alias="Infor")
    senkei: list[Senkei] = Field(..., alias="Senkei")
    calculate: list = Field(default_factory=list, alias="Calculate")
    main_panel: list[MainPanel] = Field(..., alias="MainPanel")
    sub_panel: list = Field(default_factory=list, alias="SubPanel")
    taikeikou: list = Field(default_factory=list, alias="Taikeikou")
    yokokou: list = Field(default_factory=list, alias="Yokokou")
    yokogeta: list[Yokogeta] = Field(..., alias="Yokogeta")
    shouban: list[Shouban] = Field(..., alias="Shouban")
    member_spl: list = Field(default_factory=list, alias="MemberSPL")
    member_rib: list = Field(default_factory=list, alias="MemberRib")
    member_data: list = Field(default_factory=list, alias="MemberData")

    model_config = ConfigDict(populate_by_name=True)
