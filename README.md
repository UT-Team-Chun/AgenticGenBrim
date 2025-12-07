# bridge-llm-mvp

橋長 `L` [m] と幅員 `B` [m] から、
鋼プレートガーダー橋（RC 床版）の**断面モデルを LLM で生成・評価する**ための MVP プロジェクト。

- **Designer**: 教科書＋道路橋示方書を RAG で参照しながら、断面モデル（JSON）を生成する LLM エージェント
- **Judge**: 同じ示方書を参照し、Designer の出力が寸法規定を満たしているか評価する LLM エージェント
- **RAG**: 教科書／示方書 PDF をチャンク化・埋め込みし、類似検索する層

---

## 技術スタック

- Python 3.13.5
- [uv](https://github.com/astral-sh/uv)（パッケージ管理 & 仮想環境）
  - ライブラリを追加する際は`uv add {ライブラリ名}`
- [Ruff](https://github.com/astral-sh/ruff)（フォーマッタ & リンタ）
- OpenAI API（埋め込み: `text-embedding-3-small`、検証: `gpt-5-mini`, 本番: `gpt-5.1` ）
- VS Code (+ Python 拡張 + Ruff 拡張) 推奨

---

## 実装ルール

- CLI での引数管理には必ず fire を使う。argparse の使用禁止。
- 必ず google スタイルの docstring と型アノテーションをつける。
- マジックナンバーの使用禁止。必ず `MAX_LENGTH=5` のように定義した上で `MAX_LENGTH` を使う。
- 文字列ハードコーディングの禁止。`StrEnum` や Pydantic の`BaseModel` を使用する。
- 返り値の型に `dict`, `tuple` を使わない。必ず `BaseModel`, `RootModel` 等で適切な型を定義する。
- 型定義に `dataclass` は使わない。原則`BaseModel`。
- Pydantic の `Field` に `description` を必ず書く。
- push 前には必ず `make fmt`, `make fix`, `make lint` を通す。
- パス操作は必ず `pathlib.Path` を使う。`os` は使用しない。
- ディレクトリやファイルパスは `config.py` などにまとめて定義する。
- ログ出力は`logger`で行う。`print`の使用禁止。
  - from src.bridge_llm_mvp.logger_config import get_logger で統一する。
- `try: ... except: pass` は絶対禁止です。必ず`except ValidationError as e:`のように捕捉するエラーを明示してください。

---

## プロジェクト構成

```text
data/
  design_knowledge/          # 教科書・示方書 PDF 置き場
  extracted_by_pdfplumber/   # pdfplumber で抽出したテキスト（推奨）
  extracted_by_pypdf/        # pypdf で抽出したテキスト
  extracted_by_pymupdf4llm/  # pymupdf4llm で抽出したテキスト

rag_index/
  pdfplumber/                # pdfplumber 版の埋め込みインデックス
    meta.jsonl               # チャンクメタデータ
    embeddings.npy           # 埋め込みベクトル

src/
  main.py                    # 簡易動作確認用
  bridge_llm_mvp/
    __init__.py
    main.py                  # メイン実行スクリプト
    config.py                # パス・ファイル名・共通定数の集中管理
    logger_config.py         # ロガー設定と get_logger() の定義
    llm_client.py            # OpenAI クライアントの共通ラッパ

    designer/
      __init__.py
      models.py              # Designer の入出力スキーマ（Pydantic）
      prompts.py             # Designer 用プロンプト
      services.py            # generate_design() の入り口

    judge/
      __init__.py
      models.py              # Judge の入出力スキーマ（Pydantic）
      prompts.py             # Judge 用プロンプト
      services.py            # judge_design() の入り口

    rag/
      __init__.py
      embedding_config.py    # 埋め込みモデル名・次元・対象ファイル名などの設定
      loader.py              # テキストチャンク化 & 埋め込み生成
      search.py              # search_chunks() による類似検索 API
      extract_pdfs_with_pdfplumber.py   # PDF→TXT 抽出（pdfplumber）
      extract_pdfs_with_pypdf.py        # PDF→TXT 抽出（pypdf）
      extract_pdfs_with_pymupdf4llm.py  # PDF→TXT 抽出（pymupdf4llm）
```

---

## セットアップ

### 前提

- Python は **uv** 経由で **3.13.5** を使用します。
- `uv` がインストール済みであること。

```bash
uv --version
```

### 1. リポジトリ取得

```bash
git clone <このリポジトリURL>
cd bridge-llm-mvp
```

### 2. Python 3.13.5 & 仮想環境(.venv)

```bash
uv python install 3.13.5
uv venv .venv --python 3.13.5

# 動作確認（任意）
. .venv/bin/activate  # Windows は .venv\Scripts\activate
python -V             # -> Python 3.13.5
```

※ VS Code のインタープリタは .venv を選択してください。

### 3. 依存ライブラリ同期

```bash
uv sync
```

### 4. 環境変数

`.env` ファイルをプロジェクトルートに作成し、OpenAI API キーを設定:

```bash
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxx
```

---

## RAG パイプライン

### 対象ファイル

`embedding_config.py` の `FileNamesUsedForRag` で定義されている PDF のみが処理対象:

- 鋼橋設計の基本\_第一章 概論.pdf
- 鋼橋設計の基本\_第四章 鋼橋の設計法.pdf
- 鋼橋設計の基本\_第六章 床版.pdf
- 鋼橋設計の基本\_第七章 プレートガーダー橋.pdf
- 道路橋示方書\_鋼橋・鋼部材編.pdf

### Step 1: PDF からテキスト抽出

複数の抽出エンジンを試して品質を比較した結果、**pdfplumber** を推奨:

```bash
# pdfplumber で抽出（推奨）
uv run python -m src.bridge_llm_mvp.rag.extract_pdfs_with_pdfplumber

# pypdf で抽出（代替）
uv run python -m src.bridge_llm_mvp.rag.extract_pdfs_with_pypdf

# pymupdf4llm で抽出（実験的）
uv run python -m src.bridge_llm_mvp.rag.extract_pdfs_with_pymupdf4llm
```

出力先:

- `data/extracted_by_pdfplumber/*.txt`
- `data/extracted_by_pypdf/*.txt`
- `data/extracted_by_pymupdf4llm/*.md`

### Step 2: チャンク化 & 埋め込み生成

```bash
uv run python -m src.bridge_llm_mvp.rag.loader
```

- 入力: `data/extracted_by_pdfplumber/` 配下の `.txt`
- 出力: `rag_index/pdfplumber/meta.jsonl`, `rag_index/pdfplumber/embeddings.npy`

### Step 3: 類似検索（search.py）

```python
from src.bridge_llm_mvp.rag.search import search_chunks

results = search_chunks("プレートガーダーの設計", top_k=5)
for chunk in results:
    print(chunk.source, chunk.text[:100])
```

---

## フォーマット＆Lint

このプロジェクトでは Ruff を使ってフォーマット & lint を行います。

**Makefile タスク**

```bash
# コード整形だけ（Ruff format）
make fmt

# Lint + 自動修正（Ruff check --fix + format）
make fix

# Lint だけ（CI 相当）
make lint
```

**VSCode 設定(ワークスペース)**

.vscode/settings.json に以下のような設定を入れておくと、保存時に Ruff が自動でフォーマット & lint を行います。

```json
{
  "python.formatting.provider": "none",
  "editor.formatOnSave": true,
  "ruff.enable": true,
  "ruff.lint.run": "onSave",
  "ruff.format.enable": true
}
```

---

## 実装の流れ

1. `DesignerInput(span_length_m=L, total_width_m=B)` を作成

2. `generate_design(input: DesignerInput) -> BridgeDesign` を呼ぶ

3. `JudgeInput(span_length_m=L, total_width_m=B, design=BridgeDesign)` を作成

4. `judge_design(judge_input: JudgeInput) -> JudgeResult` を呼ぶ

5. 複数ケース（例: L=30,40,50,60,70 m）で一括実行するスクリプトとして main.py を利用

```bash
uv run python src/bridge_llm_mvp/main.py
```

---

## TODO

**RAG**

- [x] 教科書／示方書 PDF を data/ に配置
- [x] PDF → テキスト抽出スクリプト実装（pdfplumber / pypdf / pymupdf4llm）
- [x] rag/loader.py でテキストチャンク化 & 埋め込み生成
- [x] rag/search.py の search_chunks() を実装
- [ ] 検索精度の評価・チューニング

**Designer**

- [ ] プロンプト本文を designer/prompts.py に整理
- [ ] RAG を組み込んだ generate_design() を実装

**Judge**

- [ ] プロンプト本文を judge/prompts.py に整理
- [ ] RAG を組み込んだ judge_design() を実装

**実験**

- [ ] 代表 3〜5 ケースで Designer→Judge を実行
- [ ] 結果を表/図として整理（卒論用）
