# PROJECT_SPEC: AgenticGenBrim

## Epics

- E1: RAG パイプラインの安定化と精度評価
- E2: Extractor（設計制約抽出エージェント）の実装
- E3: Judge の本実装（RAG + LLM）
- E4: 代表ケースでの end-to-end 評価

## Tasks

- [x] PDF 抽出スクリプト（pdfplumber / pypdf / pymupdf4llm）
- [x] チャンク化 & 埋め込みインデックス生成
- [x] RAG 付き Designer（BridgeDesign + RAG ログ出力）
- [x] BridgeDesign → 詳細 JSON → IFC 変換パイプライン
- [ ] (E2) Extractor（設計制約抽出エージェント）の実装
- [ ] (E1) RAG ヒットの精度評価・チューニング
- [ ] (E3) Judge を RAG + LLM で本実装する
- [ ] (E4) 代表ケースでの評価・挙動確認（設計値の妥当性チェック）
