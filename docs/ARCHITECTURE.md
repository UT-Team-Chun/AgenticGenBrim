# ARCHITECTURE

## ディレクトリ構成

```text
data/
  design_knowledge/               # 元 PDF 配置場所
  extracted_by_pdfplumber/        # pdfplumber で抽出したテキスト
  extracted_by_pypdf/             # pypdf で抽出したテキスト
  extracted_by_pymupdf4llm/       # pymupdf4llm で抽出したテキスト
  generated_simple_bridge_json/   # Designer 出力 JSON
  generated_bridge_raglog_json/   # RAG ヒットログ
  generated_detailed_bridge_json/ # IFC 変換用の詳細 JSON
  generated_ifc/                  # IFC 出力
rag_index/
  pdfplumber/{meta.jsonl,embeddings.npy}
  pymupdf/{meta.jsonl,embeddings.npy}
src/
  main.py                         # Designer→IFC の統合 CLI (Fire)
  bridge_agentic_generate/
    main.py                       # Designer + (任意) Judge 実行
    config.py                     # パス定義
    llm_client.py                 # Responses API / Structured Output ラッパー
    logger_config.py              # 共通ロガー
    designer/                     # モデル・プロンプト・RAG付き生成
    judge/                        # 評価モデル（現状はダミー）
    rag/                          # PDF 抽出・チャンク化・埋め込み・検索
    extractor/                    # 設計制約抽出エージェント（これから実装予定）
  bridge_json_to_ifc/
    convert_simple_to_detailed_json.py  # BridgeDesign -> 詳細 JSON
    convert_detailed_json_to_ifc.py     # 詳細 JSON -> IFC
    run_convert.py                      # 変換 CLI
```

## コンポーネント概要

- RAG: 指定 PDF をテキスト化・埋め込みし、設計時に参照する条文チャンクを検索。
- Extractor (計画中): RAG で得た条文を元に設計制約を構造化抽出するエージェント。
- Designer: 橋長 L と幅員 B を受け取り、RAG 文脈を踏まえた BridgeDesign（構造化 JSON）を生成。
- Judge: 道路橋示方書に基づき設計結果を評価する予定（現状はダミー実装）。
- IFC Export: BridgeDesign → 詳細 JSON → IFC に変換して BrIM 環境に渡す。
