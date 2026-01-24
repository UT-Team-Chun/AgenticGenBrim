# ARCHITECTURE

## ディレクトリ構成

```text
data/
  design_knowledge/               # 元 PDF 配置場所
  extracted_by_pdfplumber/        # pdfplumber で抽出したテキスト
  extracted_by_pypdf/             # pypdf で抽出したテキスト
  extracted_by_pymupdf4llm/       # pymupdf4llm で抽出したテキスト
  generated_simple_bridge_json/   # Designer 出力 JSON（BridgeDesign）
  generated_bridge_raglog_json/   # RAG ヒットログ
  generated_judge_json/           # Judge 出力 JSON（JudgeReport）
  generated_senkei_json/          # IFC 変換用の Senkei JSON（推奨）
  generated_detailed_bridge_json/ # IFC 変換用の詳細 JSON（旧方式）
  generated_report_md/            # 修正ループレポート（Markdown）
  generated_ifc/                  # IFC 出力
rag_index/
  pdfplumber/{meta.jsonl,embeddings.npy}
  pymupdf/{meta.jsonl,embeddings.npy}
src/
  main.py                         # Designer→IFC の統合 CLI (Fire)
  bridge_agentic_generate/
    main.py                       # Designer/Judge CLI (Fire)
    config.py                     # パス定義（AppConfig）
    llm_client.py                 # Responses API / Structured Output ラッパー
    logger_config.py              # 共通ロガー
    designer/                     # モデル・プロンプト・RAG付き生成
      models.py                   # Pydantic モデル（BridgeDesign 等）
      prompts.py                  # LLM プロンプト生成
      services.py                 # 生成ロジック
    judge/                        # 照査・修正提案（決定論計算+LLM）
      models.py                   # 入出力モデル（JudgeReport, PatchPlan 等）
      prompts.py                  # PatchPlan 生成プロンプト
      services.py                 # 照査計算・修正適用
      report.py                   # 修正ループレポート生成
    rag/                          # PDF 抽出・チャンク化・埋め込み・検索
      embedding_config.py         # 埋め込み設定・インデックス構造
      loader.py                   # チャンク化・埋め込み生成
      search.py                   # ベクトル検索
      extract_pdfs_with_*.py      # PDF抽出スクリプト（3種）
  bridge_json_to_ifc/
    run_convert.py                # 変換 CLI
    models.py                     # 詳細 JSON スキーマ（DetailedBridgeSpec）
    senkei_models.py              # Senkei JSON スキーマ（SenkeiSpec）
    convert_simple_to_detailed_json.py  # BridgeDesign -> 詳細 JSON
    convert_simple_to_senkei_json.py    # BridgeDesign -> Senkei JSON
    convert_detailed_json_to_ifc.py     # 詳細 JSON -> IFC
    convert_senkei_json_to_ifc.py       # Senkei JSON -> IFC
    ifc_utils/                    # 旧 IFC ユーティリティ
    ifc_utils_new/                # 新 IFC ユーティリティ（Senkei用）
      core/                       # DefBridge, DefIFC, DefMath 等
      components/                 # DefBracing, DefPanel, DefStiffener 等
      io/                         # DefExcel, DefJson, DefStrings
      utils/                      # DefBridgeUtils, logger
```

## コンポーネント概要

### RAG

指定 PDF をテキスト化・埋め込みし、設計時に参照する条文チャンクを検索。

- **対象 PDF**: 鋼橋設計の基本（第一章、第四章、第六章、第七章）、道路橋示方書\_鋼橋・鋼部材編
- **埋め込みモデル**: text-embedding-3-small（OpenAI）
- **マルチクエリ検索**: 寸法・主桁配置・主桁断面・床版・横桁の 5 観点で並行検索

### Designer

橋長 L と幅員 B を受け取り、RAG 文脈を踏まえた BridgeDesign（構造化 JSON）を生成。

- **入力**: 橋長 L [m]、幅員 B [m]
- **出力**: BridgeDesign（dimensions, sections, components）
- **LLM**: OpenAI Responses API + Structured Output

### Judge

決定論的な照査計算（曲げ・せん断・たわみ・床版厚・腹板幅厚比・横桁配置）を行い、不合格時は LLM で PatchPlan を生成。

- **入力**: JudgeInput（BridgeDesign + 荷重 + 材料 + パラメータ）
- **出力**: JudgeReport（pass_fail, utilization, diagnostics, patch_plan）
- **詳細**: [COMPONENT_JUDGE.md](COMPONENT_JUDGE.md) 参照

### Designer-Judge ループ

不合格時に PatchPlan を適用し、合格するまで繰り返す修正ループ（`run_with_repair_loop`）。

- **最大イテレーション**: 設定可能（デフォルト 5）
- **出力**: RepairLoopResult（converged, iterations, final_design, final_report）

### IFC Export

BridgeDesign → 中間 JSON（Senkei または Detailed）→ IFC に変換して BrIM 環境に渡す。

- **変換パイプライン**:
  - BridgeDesign → Senkei JSON → IFC（推奨、新方式）
  - BridgeDesign → 詳細 JSON → IFC（旧方式）
- **生成要素**: 床版（Brep）、主桁（SweptSolid）、横桁（SweptSolid）
- **ライブラリ**: ifcopenshell

## データフロー

```text
入力（橋長 L, 幅員 B）
    ↓
RAG 検索（マルチクエリ 5 観点）
    ↓
LLM で BridgeDesign 生成
    ↓
Judge（決定論的照査計算）
    ↓
合格？
  ├ Yes → final_design
  └ No → LLM で PatchPlan 生成
        ↓
      PatchPlan 適用
        ↓
      (最大イテレーションまで繰り返し)
    ↓
BridgeDesign JSON 保存
    ↓
Senkei JSON 変換 → IFC 変換
    ↓
IFC ファイル出力
```
