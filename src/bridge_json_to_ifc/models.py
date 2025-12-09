from pydantic import BaseModel, Field


class GirdersGeometry(BaseModel):
    """主桁ジオメトリ。"""

    num_girders: int = Field(..., description="主桁本数")
    spacing_x: float = Field(..., description="主桁間隔 [mm]")
    spacing_z: float = Field(default=0, description="Z方向間隔 [mm]")
    length: float = Field(..., description="主桁長さ [mm]")
    x_offset: float = Field(..., description="主桁開始位置 X [mm]")
    web_height: float = Field(..., description="腹板高さ [mm]")
    web_thickness: float = Field(..., description="腹板厚 [mm]")
    top_flange_width: float = Field(..., description="上フランジ幅 [mm]")
    top_flange_thickness: float = Field(..., description="上フランジ厚 [mm]")
    bottom_flange_width: float = Field(..., description="下フランジ幅 [mm]")
    bottom_flange_thickness: float = Field(..., description="下フランジ厚 [mm]")


class DeckGeometry(BaseModel):
    """床版ジオメトリ。"""

    length: float = Field(..., description="床版長さ [mm]")
    width: float = Field(..., description="床版幅 [mm]")
    thickness: float = Field(..., description="床版厚 [mm]")
    points: list[list[float]] = Field(..., description="床版輪郭座標（反時計回り）")


class Partition(BaseModel):
    """格間定義。"""

    x_positions: list[float] = Field(..., description="X軸分割（床版分割）位置 [mm]")
    y_positions: list[float] = Field(..., description="Y軸分割（主桁分割）位置 [mm]")


class Geometry(BaseModel):
    """ジオメトリ情報のコンテナ。"""

    girders: GirdersGeometry = Field(..., description="主桁ジオメトリ")
    deck: DeckGeometry = Field(..., description="床版ジオメトリ")
    partition: Partition = Field(..., description="格間定義")


class Crossbeams(BaseModel):
    """横桁情報。"""

    use_crossbeams: bool = Field(default=True, description="横桁使用フラグ")
    use_i_section: bool = Field(default=True, description="I形断面使用フラグ")
    num_cross_girders: int = Field(..., description="横桁本数")
    spacing_z: float = Field(..., description="縦方向ピッチ [mm]")
    initial_position_z: float = Field(..., description="最初の配置位置 [mm]")
    height: float = Field(..., description="横桁高さ [mm]")
    flange_width: float = Field(..., description="フランジ幅 [mm]")
    flange_thickness: float = Field(..., description="フランジ厚 [mm]")
    web_thickness: float = Field(..., description="腹板厚 [mm]")
    thickness: float = Field(..., description="厚さ [mm]（互換性用）")
    length: float = Field(..., description="横桁長さ [mm]")


class DetailedBridgeJson(BaseModel):
    """IFC 生成用の詳細 JSON スキーマ。"""

    bridge_type: str = Field(default="Steel Girder", description="橋梁タイプ")
    geometry: Geometry = Field(..., description="ジオメトリ情報")
    crossbeams: Crossbeams = Field(..., description="横桁情報")
