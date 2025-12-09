# bridge-llm-mvp

橋長 `L` [m] と幅員 `B` [m] から、
鋼プレートガーダー橋（RC 床版）の**断面モデルを LLM で生成・評価する**ための MVP プロジェクト。

- **RAG**: 教科書／道路橋示方書 PDF をテキスト化・チャンク化・埋め込みし、
  「どの文書／どの章・ページ付近を参照すべきか」を決めるための索引用レイヤ
- **Extractor**: RAG で候補になった章・ページ情報をもとに、
  **Responses API の file input で元 PDF を LLM に読ませ**、
  「床版厚さ・腹板厚さなどの設計ルール（制約）」を構造化して抽出するエージェント
- **Designer**: Extractor が抽出した制約＋入力条件（L, B）を使い、
  必要に応じて同じ PDF を file input で参照しながら、
  断面モデル（BridgeDesign JSON）を自律的に生成するエージェント
- **Judge**: 同じ示方書を参照し、Designer の出力が寸法規定を満たしているか評価する LLM エージェント（本研究では補助的な位置づけ）

---

## 技術スタック

- Python 3.13.5
- [uv](https://github.com/astral-sh/uv)（パッケージ管理 & 仮想環境）
  - ライブラリを追加する際は `uv add {ライブラリ名}`
- [Ruff](https://github.com/astral-sh/ruff)（フォーマッタ & リンタ）
- OpenAI API
  - 埋め込み: `text-embedding-3-small`
  - 検証用: `gpt-5-mini`
  - 本番用: `gpt-5.1`
- VS Code (+ Python 拡張 + Ruff 拡張) 推奨

---

## 実装ルール

- CLI での引数管理には必ず fire を使う。argparse の使用禁止。
- 必ず google スタイルの docstring と型アノテーションをつける。
- マジックナンバーの使用禁止。必ず `MAX_LENGTH=5` のように定義した上で `MAX_LENGTH` を使う。
- 文字列ハードコーディングの禁止。`StrEnum` や Pydantic の `BaseModel` を使用する。
- 返り値の型に `dict`, `tuple` を使わない。必ず `BaseModel`, `RootModel` 等で適切な型を定義する。
- 型定義に `dataclass` は使わない。原則 `BaseModel`。
- Pydantic の `Field` に `description` を必ず書く。
- push 前には必ず `make fmt`, `make fix`, `make lint` を通す。
- パス操作は必ず `pathlib.Path` を使う。`os` は使用しない。
- ディレクトリやファイルパスは `config.py` などにまとめて定義する。
- ログ出力は `logger` で行う。`print` の使用禁止。
  - `from src.bridge_llm_mvp.logger_config import get_logger` で統一する。
- `try: ... except: pass` は絶対禁止。必ず `except ValidationError as e:` のように捕捉するエラーを明示する。
- `typing` の `List`, `Dict` などは使わず、`list`, `dict` 等を使う。
- `Optional` は使わず、`str | None` のように記述する。

---

## プロジェクト構成

````text
data/
  design_knowledge/          # 教科書・示方書 PDF 置き場
  extracted_by_pdfplumber/   # pdfplumber で抽出したテキスト（推奨）
  extracted_by_pypdf/        # pypdf で抽出したテキスト
  extracted_by_pymupdf4llm/  # pymupdf4llm で抽出したテキスト
  generated_bridge_json/     # Designer が生成した設計結果 JSON

rag_index/
  pdfplumber/                # pdfplumber 版の埋め込みインデックス
    meta.jsonl               # チャンクメタデータ
    embeddings.npy           # 埋め込みベクトル

src/
  bridge_llm_mvp/
    __init__.py
    main.py                  # メイン実行スクリプト
    config.py                # パス・ファイル名・共通定数の集中管理
    logger_config.py         # ロガー設定と get_logger() の定義
    llm_client.py            # OpenAI クライアントの共通ラッパ

    extractor/
      __init__.py
      models.py              # Extractor の入出力スキーマ（ConstraintItem, ConstraintSet 等）
      prompts.py             # 制約抽出用プロンプト組み立て
      services.py            # extract_constraints() - RAG+LLM で設計ルールを抽出

    designer/
      __init__.py
      models.py              # Designer の入出力スキーマ（BridgeDesign 等）
      prompts.py             # Designer 用プロンプト組み立て
      services.py            # generate_design() - Extractor の制約を使って設計生成

    judge/
      __init__.py
      models.py              # Judge の入出力スキーマ（JudgeResult 等）
      prompts.py             # Judge 用プロンプト組み立て
      services.py            # judge_design() - 設計結果を評価（補助的）

    rag/
      __init__.py
      embedding_config.py    # 埋め込み設定・RagIndex・SearchResult モデル
      loader.py              # テキストチャンク化 & 埋め込み生成
      search.py              # search_text() による類似検索 API
      extract_pdfs_with_pdfplumber.py   # PDF→TXT 抽出（pdfplumber）
      extract_pdfs_with_pypdf.py        # PDF→TXT 抽出（pypdf）
      extract_pdfs_with_pymupdf4llm.py  # PDF→TXT 抽出（pymupdf4llm）

.vscode/
  settings.json              # Ruff 自動フォーマット設定
  launch.json                # デバッグ実行設定（PYTHONPATH 設定済み）


---

## セットアップ

### 前提

- Python は **uv** 経由で **3.13.5** を使用します。
- `uv` がインストール済みであること。

```bash
uv --version
````

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
from src.bridge_llm_mvp.rag.search import search_text
from src.bridge_llm_mvp.llm_client import get_llm_client

client = get_llm_client()
results = search_text("プレートガーダーの設計", client=client, top_k=5)
for result in results:
    print(f"Score: {result.score:.4f}, Source: {result.chunk.source}")
    print(f"Text: {result.chunk.text[:100]}...")
```

> **補足（file input との関係）**
>
> RAG（埋め込み）はあくまで「どの文書のどの辺を見に行くか」を決めるための索引用です。
> 実際に設計ルールを読む段階（Extractor / Designer からの LLM 呼び出し）では、
> Responses API の file input 機能を使って、
> `data/design_knowledge/` 内の元 PDF を LLM に渡し、
> 数式や記号を含めた元の紙面を直接読ませる想定です。

---

## Extractor & Designer & Judge

### Extractor

RAG で関連チャンクを取得し、LLM に Structured Output で「設計制約（寸法ルール）」を抽出させる。

```python
from src.bridge_llm_mvp.extractor.models import ExtractorInput, ConstraintTarget, ConstraintSet
from src.bridge_llm_mvp.extractor.services import extract_constraints

inputs = ExtractorInput(
    bridge_length_m=50.0,
    total_width_m=10.0,
    targets=[
        ConstraintTarget.DECK_THICKNESS,
        ConstraintTarget.WEB_THICKNESS,
    ],
)
constraints: ConstraintSet = extract_constraints(inputs)
logger.info(constraints.model_dump_json(indent=2, ensure_ascii=False))
```

**抽出される情報の例**

- どの文書・どの節に書かれていたか (source_doc, section_hint, page_hint)
- 条件式のテキスト (expression_text)
- 自然文での要約 (natural_language_summary)
- どの設計変数に関する制約か (related_variables)

### Designer

Extractor が抽出した制約＋入力条件（L, B）を使って、LLM に BridgeDesign を生成させる。

```python
from src.bridge_llm_mvp.designer.models import DesignerInput
from src.bridge_llm_mvp.designer.services import generate_design
from src.bridge_llm_mvp.llm_client import LlmModel

inputs = DesignerInput(bridge_length_m=50.0, total_width_m=10.0)
design = generate_design(inputs, top_k=5, model_name=LlmModel.GPT_5_MINI)
print(design.model_dump_json(indent=2))
```

**出力スキーマ (BridgeDesign):**

- `dimensions`: 橋長、幅員、主桁本数、桁間隔、横桁ピッチ
- `sections.girder_standard`: 主桁断面（腹板高さ/厚、上下フランジ幅/厚）
- `sections.crossbeam_standard`: 横桁断面
- `components.deck`: 床版厚

### Judge

Designer の出力が道路橋示方書の寸法規定を満たすか評価する。

```python
from src.bridge_llm_mvp.judge.models import JudgeInput
from src.bridge_llm_mvp.judge.services import judge_design

judge_input = JudgeInput(
    bridge_length_m=50.0,
    total_width_m=10.0,
    design=design,
)
result = judge_design(judge_input)
print(result.overall_status)  # OK / NG / PARTIAL
```

---

## メイン実行

```bash
uv run python -m src.bridge_llm_mvp.main
```

- L=50m, B=10m で Extractor→Designer を実行
- 結果を `data/generated_bridge_json/design_L50_B10_{timestamp}.json` に保存

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

**VSCode 設定**

`.vscode/settings.json` で保存時に Ruff が自動でフォーマット & lint を行います。

---

## VS Code でのデバッグ実行

`.vscode/launch.json` が設定済みなので、F5 キーまたは右上の三角ボタンでファイルを実行できます。
`PYTHONPATH` が自動設定されるため、`ModuleNotFoundError: No module named 'src'` エラーは発生しません。

---

## TODO

**RAG**

- [x] 教科書／示方書 PDF を data/ に配置
- [x] PDF → テキスト抽出スクリプト実装（pdfplumber / pypdf / pymupdf4llm）
- [x] rag/loader.py でテキストチャンク化 & 埋め込み生成
- [x] rag/search.py の search_text() を実装
- [x] SearchResult モデルで検索結果を返す（スコア付き）
- [ ] 検索精度の評価・チューニング

**Extractor**

- [ ] extractor/models.py に ConstraintItem, ConstraintSet, ExtractorInput を定義
- [ ] RAG を組み込んだ extract_constraints() を実装
- [ ] プレートガーダー橋（L=50m, B=10m）で制約抽出の挙動を確認
- [ ] 抽出された制約と示方書の真の条文との対応をサンプル比較

**Designer**

- [x] プロンプト本文を designer/prompts.py に整理
- [x] RAG を組み込んだ generate_design() を実装
- [x] 設計結果を JSON ファイルに出力
- [ ] Extractor の ConstraintSet を使うように内部ロジックをリファクタリング

**Judge**

- [x] judge/models.py に JudgeResult スキーマを定義
- [ ] RAG を組み込んだ judge_design() を本実装（現在はダミー）
- [ ] Python 側の簡易ルール（床版厚さ、腹板厚さなど）で Designer の精度を評価する仕組み検討

**実験**

- [ ] 代表 3〜5 ケースで Extracter→Designer→Judge を実行
- [ ] 結果を表/図として整理（卒論用）
- [ ] ルール抽出（Extractor）と設計（Designer）を分けた場合のメリット・課題を整理
