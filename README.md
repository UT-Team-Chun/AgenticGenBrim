# bridge-llm-mvp

橋長 `L` [m] と幅員 `B` [m] から、
鋼プレートガーダー橋（RC 床版）の**断面モデルを LLM で生成・評価する**ための MVP プロジェクト。

- **Designer**: 教科書＋道路橋示方書を RAG で参照しながら、断面モデル（JSON）を生成する LLM エージェント
- **Judge**: 同じ示方書を参照し、Designer の出力が寸法規定を満たしているか評価する LLM エージェント
- **RAG**: 教科書／示方書 PDF をチャンク化して検索する層（まだダミー）

> ※現時点では LLM 呼び出し部分は未実装で、型と骨組みだけ存在します。

---

## 技術スタック

- Python 3.13.5
- [uv](https://github.com/astral-sh/uv)（パッケージ管理 & 仮想環境）
- [Ruff](https://github.com/astral-sh/ruff)（フォーマッタ & リンタ）
- VS Code (+ Python 拡張 + Ruff 拡張) 推奨

---

## プロジェクト構成

```text
src/
  bridge_llm_mvp/
    __init__.py

    designer/
      __init__.py
      models.py   # Designer の入出力スキーマ（Pydantic）
      prompts.py  # Designer 用プロンプト（TODO）
      services.py  # generate_design() の入り口（LLM 呼び出しは TODO）

    judge/
      __init__.py
      models.py   # Judge の入出力スキーマ（Pydantic）
      prompts.py  # Judge 用プロンプト（TODO）
      services.py  # judge_design() の入り口（LLM 呼び出しは TODO）

    rag/
      __init__.py
      loader.py   # PDF ロード & チャンク化（TODO）
      search.py   # search_text() などの RAG API（いまはダミー）

    main.py
      # 複数ケースに対して
      #   DesignerInput -> BridgeDesign -> JudgeInput -> JudgeResult
      # を回すエントリポイント（実装途中）
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

### 2. Pythin 3.13.5 & 仮想環境(.venv)

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

※ まだ LLM 呼び出しが未実装のため、ここは今後のターゲットです。

1. DesignerInput(span_length_m=L, total_width_m=B) を作成

2. generate_design(input: DesignerInput) -> BridgeDesign を呼ぶ

3. JudgeInput(span_length_m=L, total_width_m=B, design=BridgeDesign) を作成

4. judge_design(judge_input: JudgeInput) -> JudgeResult を呼ぶ

5. 複数ケース（例: L=30,40,50,60,70 m）で一括実行するスクリプトとして main.py を利用

```bash
uv run python src/bridge_llm_mvp/main.py
```

（現時点では NotImplementedError が出る想定）

---

## TODO

**RAG**

- [ ] 教科書／示方書 PDF を data/ 等に配置

- [ ] rag/loader.py でテキスト抽出 & チャンク化

- [ ] rag/search.py の search_text() を実装

**Designer**

- [ ] プロンプト本文を designer/prompts.py に整理

- [ ] OpenAI 等の LLM クライアントを使って generate_design() を実装

**Judge**

- [ ] プロンプト本文を judge/prompts.py に整理

- [ ] LLM を使って judge_design() を実装

**実験**

- [ ] 代表 3〜5 ケースで Designer→Judge を実行

- [ ] 結果を表/図として整理（卒論用）
