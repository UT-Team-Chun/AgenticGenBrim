# タスク: [タスク名]

## 概要

[このタスクで何を実現するかを1-2文で記述]

## 要件

- [ ] 要件1
- [ ] 要件2
- [ ] 要件3

## 対象ディレクトリ

<!-- 該当するものにチェック -->
- [ ] `src/bridge_agentic_generate/designer/` - 設計生成
- [ ] `src/bridge_agentic_generate/rag/` - RAG（検索拡張生成）
- [ ] `src/bridge_agentic_generate/judge/` - 設計評価
- [ ] `src/bridge_agentic_generate/extractor/` - 設計制約抽出
- [ ] `src/bridge_json_to_ifc/` - IFC変換

## 対象ファイル

- `...`

## 受け入れ条件

### コード品質
- [ ] `make fmt` - フォーマットが適用済み
- [ ] `make lint` - Lintエラーなし
- [ ] 型アノテーションが付与されている
- [ ] Google スタイル Docstring が記述されている

### 機能
- [ ] 要件がすべて満たされていること
- [ ] テストが追加されていること（LLM呼び出しはモック）

### その他
- [ ] 未使用コード・コメントアウトがないこと
- [ ] マジックナンバーがないこと

## 備考

[補足事項があれば記述]

---

## 使い方

1. このテンプレートをコピーしてタスクファイルを作成
   ```bash
   cp tasks/template.md tasks/[タスク名].md
   ```

2. 上記の各セクションを記入

3. Claude Code に渡す
   ```bash
   claude "tasks/[タスク名].md を読んで実装して"
   ```
