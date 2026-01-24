# PROJECT_SPEC: AgenticGenBrim

## Epics

- E1: RAG パイプラインの安定化と精度評価
- E2: Judge の拡張（座屈照査、疲労照査等）
- E3: 代表ケースでの end-to-end 評価

## Tasks

- [x] PDF 抽出スクリプト（pdfplumber / pypdf / pymupdf4llm）
- [x] チャンク化 & 埋め込みインデックス生成
- [x] RAG 付き Designer（BridgeDesign + RAG ログ出力）
- [x] BridgeDesign → 詳細 JSON → IFC 変換パイプライン
- [x] Judge の基本実装（曲げ・せん断・たわみ・床版厚・横桁配置）
- [ ] (E1) RAG ヒットの精度評価・チューニング
- [ ] (E2) Judge の拡張（座屈照査、疲労照査等）
- [ ] (E3) 代表ケースでの評価・挙動確認（設計値の妥当性チェック）
