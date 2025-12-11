# COMPONENT_DESIGNER

橋長 L と幅員 B を受け取り、RAG 文脈を踏まえた BridgeDesign（構造化 JSON）を生成する Designer の概要。

## 入力パラメータ

`src/bridge_agentic_generate/designer/models.py` の `DesignerInput` クラスで定義されています。

- **bridge_length_m** (`float`): 橋長 $L$ [m]。
- **total_width_m** (`float`): 幅員 $B$ [m]。

## 出力 JSON スキーマ (BridgeDesign)

`src/bridge_agentic_generate/designer/models.py` の `BridgeDesign` クラスで定義される構造化データです。
主な構成要素は以下の通りです。

### 1. Dimensions (全体寸法)

- `bridge_length`: 橋長 [mm]
- `total_width`: 全幅 [mm]
- `num_girders`: 主桁本数
- `girder_spacing`: 主桁間隔 [mm]
- `panel_length`: パネル長 [mm]
- `num_panels`（任意）: 明示指定がなければ `bridge_length / panel_length` で自動計算

### 2. Sections (部材断面)

- **girder_standard** (主桁標準断面 I 形)
  - `web_height`, `web_thickness`: 腹板の高さ・厚さ [mm]
  - `top_flange_width`, `top_flange_thickness`: 上フランジの幅・厚さ [mm]
  - `bottom_flange_width`, `bottom_flange_thickness`: 下フランジの幅・厚さ [mm]
- **crossbeam_standard** (横桁標準断面 I 形)
  - `total_height`: 桁高 [mm]
  - `web_thickness`: 腹板厚さ [mm]
  - `flange_width`, `flange_thickness`: フランジの幅・厚さ [mm]

### 3. Components (構成要素)

- **deck** (床版)
  - `thickness`: 床版厚 [mm]

## 利用する RAG コンテキスト

Designer は設計生成時に、以下のクエリを用いて RAG 検索を行い、関連する条文や設計知識を取得してプロンプトに含めます。

- **検索クエリ**: `"橋長 {L} m, 幅員 {B} m の鋼プレートガーダー橋の断面設計に関係する条文・式を探してください。"`
- **参照ソース**: `data/design_knowledge/` 以下の PDF (道路橋示方書、鋼橋設計の基本など) から抽出されたテキストチャンク。
- **プロンプトへの反映**: 検索でヒットした上位 $k$ 件（デフォルト $k=5$）のチャンクが、参考文献として LLM に提示されます。

## 代表的なユースケース

1. **概略設計の自動生成**
   - ユーザーが橋長と幅員を指定するだけで、示方書や教科書に基づいた妥当な断面寸法（桁高、板厚など）の初期案を自動生成する。
2. **設計根拠の確認**
   - 生成結果には RAG のログ (`DesignerRagLog`) が含まれるため、どの条文（ソースファイル名、ページ番号）を根拠にその寸法が決定されたかを確認できる。
3. **BIM/CIM モデルへの連携**
   - 出力された JSON は `bridge_json_to_ifc` モジュールを通じて IFC ファイルに変換され、3D モデルとして可視化・活用される。
