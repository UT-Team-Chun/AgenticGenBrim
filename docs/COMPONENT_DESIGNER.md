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

## 利用する RAG コンテキスト（マルチクエリ検索）

Designer は設計生成時に、以下の 5 観点でマルチクエリ RAG 検索を行い、関連する条文や設計知識を取得してプロンプトに含めます。

### 検索クエリ（5 観点）

1. **寸法関連（dimensions）**
   - クエリ: `"鋼プレートガーダー橋 橋長{L}m 幅員{B}m 桁配置 主桁本数 桁間隔 パネル長"`

2. **主桁配置（girder_layout）**
   - クエリ: `"並列I桁 主桁間隔 幅員と主桁本数の関係 標準断面 主桁本数"`

3. **主桁断面（girder_section）**
   - クエリ: `"プレートガーダー橋 橋長{L}m 主桁断面 桁高 腹板厚さ フランジ幅 フランジ厚さ 経済的桁高 h/L"`

4. **RC 床版（deck）**
   - クエリ: `"RC床版合成桁 床版厚さ 最小床版厚 床版厚と支間の比"`

5. **横桁（crossbeam）**
   - クエリ: `"横桁 対傾構 横構 設計"`

### 検索結果の利用

- **参照ソース**: `data/design_knowledge/` 以下の PDF（道路橋示方書、鋼橋設計の基本など）から抽出されたテキストチャンク。
- **top_k**: 各クエリで上位 5 件（合計最大 25 チャンク）を取得。
- **プロンプトへの反映**: 検索でヒットしたチャンクが、参考文献として LLM に提示されます。
- **RAG ログ**: `DesignerRagLog` として検索結果（rank, score, source, page, text）を記録し、`data/generated_bridge_raglog_json/` に保存。

## LLM 出力スキーマ (DesignerOutput)

`src/bridge_agentic_generate/designer/models.py` の `DesignerOutput` クラスで定義されます。
LLM は BridgeDesign だけでなく、設計根拠や適用ルールも構造化して返します。

- **reasoning** (`str`): 設計プロセス全体の思考・判断根拠（なぜその寸法を選んだか等）
- **rules** (`list[DesignRule]`): 今回の設計で適用した設計ルール一覧
- **dependency_rules** (`list[DependencyRule]`): 部材間の依存関係ルール（修正ループでの連動用）
- **bridge_design** (`BridgeDesign`): 生成された断面設計

### DesignRule

RAG コンテキストから抽出した設計ルール 1 件分。

- `rule_id`: ルール ID（例: "R1"）
- `category`: カテゴリ（`dimensions` / `girder_section` / `deck` / `crossbeam_section` / `other`）
- `summary`: 日本語要約
- `condition_expression`: 条件式（例: `"web_height ≒ L/20〜L/25"`）
- `formula_latex`: LaTeX 風数式（任意）
- `applies_to_fields`: 影響する BridgeDesign のフィールド名一覧
- `source_hit_ranks`: 根拠となる RAG ヒットの rank 番号（根拠なしなら空）

### DependencyRule

部材間の依存関係（例: 横桁高さ = 主桁高さ × 係数）。PatchPlan 適用後に自動連動させるために使用。

- `rule_id`: ルール ID（例: "D1"）
- `target_field`: 更新対象（例: `"crossbeam.total_height"`）
- `source_field`: 参照元（例: `"girder.web_height"`）
- `factor`: 係数（例: `0.8`）
- `source_hit_ranks`: 根拠となる RAG ヒットの rank 番号

## 生成フロー

```text
DesignerInput（橋長 L, 幅員 B）
    ↓
マルチクエリ RAG 検索（5 観点）
    ↓
プロンプト構築（RAG コンテキスト + 設計指示）
    ↓
LLM 呼び出し（Structured Output → DesignerOutput）
    ↓
DesignerOutput を分解:
  - bridge_design → BridgeDesign
  - reasoning, rules, dependency_rules → DesignerRagLog に記録
    ↓
DesignResult（design + rag_log + rules + dependency_rules）
    ↓
JSON 保存 + RAG ログ保存
```

## 代表的なユースケース

1. **概略設計の自動生成**
   - ユーザーが橋長と幅員を指定するだけで、示方書や教科書に基づいた妥当な断面寸法（桁高、板厚など）の初期案を自動生成する。

2. **設計根拠の確認**
   - 生成結果には RAG のログ (`DesignerRagLog`) が含まれるため、どの条文（ソースファイル名、ページ番号）を根拠にその寸法が決定されたかを確認できる。

3. **BIM/CIM モデルへの連携**
   - 出力された JSON は `bridge_json_to_ifc` モジュールを通じて IFC ファイルに変換され、3D モデルとして可視化・活用される。

4. **Judge との連携**
   - 生成された BridgeDesign は Judge コンポーネントで照査され、不合格時は PatchPlan に基づいて修正される。

## 関連ファイル

- `src/bridge_agentic_generate/designer/models.py`: Pydantic モデル定義（BridgeDesign, DesignerOutput, DesignRule, DependencyRule 等）
- `src/bridge_agentic_generate/designer/services.py`: 生成ロジック（`generate_design_with_rag_log()`）
- `src/bridge_agentic_generate/designer/prompts.py`: プロンプト構築（`build_designer_prompt()`）
- `src/bridge_agentic_generate/rag/search.py`: RAG 検索（`search_text()`）
