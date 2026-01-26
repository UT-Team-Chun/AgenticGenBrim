# 評価基盤 Phase 1 実装計画

## 概要

EVALUATION.md に基づき、評価基盤（Phase 1）を実装する。

## 実装項目

### 1. 評価用モデル定義（`src/evaluation/models.py`）

```python
# 評価ケース定義
class EvaluationCase(BaseModel):
    case_id: str              # "L50_B10"
    bridge_length_m: float
    total_width_m: float

# 試行結果（1回分）
class TrialResult(BaseModel):
    case_id: str              # "L50_B10_rag_true_trial_1"
    bridge_length_m: float
    total_width_m: float
    use_rag: bool
    trial: int
    converged: bool
    num_iterations: int
    first_pass: bool
    first_max_util: float
    first_utilization: dict[str, float]  # deck/bend/shear/deflection/web_slenderness
    final_pass: bool
    final_max_util: float
    per_check_first_pass: dict[str, bool]  # 照査項目別の初回合格

# 集計結果
class AggregatedMetrics(BaseModel):
    first_pass_rate: float
    convergence_rate: float
    avg_iterations: float
    final_pass_rate: float
    per_check_first_pass_rate: dict[str, float]
```

### 2. 指標計算ロジック（`src/evaluation/metrics.py`）

```python
def calc_first_pass_rate(results: list[TrialResult]) -> float:
    """初回合格率を計算"""

def calc_convergence_rate(results: list[TrialResult]) -> float:
    """収束率を計算"""

def calc_avg_iterations(results: list[TrialResult]) -> float:
    """平均修正回数を計算（収束ケースのみ）"""

def calc_final_pass_rate(results: list[TrialResult]) -> float:
    """最終合格率を計算"""

def calc_per_check_first_pass_rate(results: list[TrialResult]) -> dict[str, float]:
    """照査項目別の初回合格率を計算"""

def aggregate_metrics(results: list[TrialResult]) -> AggregatedMetrics:
    """全指標を集計"""
```

### 3. RAG なし生成オプション追加

**対象ファイル**: `src/bridge_agentic_generate/designer/services.py`

```python
def generate_design_with_rag_log(
    inputs: DesignerInput,
    top_k: int,
    model_name: LlmModel,
    use_rag: bool = True,  # 新規追加
) -> DesignResult:
    """
    use_rag=False の場合:
    - RAG 検索をスキップ
    - 空のコンテキストで LLM を呼び出す
    - rag_log.hits は空リスト
    """
```

**RAG なし時の対応**:
- プロンプトは後で作成（今回は空コンテキストで placeholder）
- `rag_log.query = "no_rag"`
- `rag_log.hits = []`

### 4. バッチ評価 CLI（`src/evaluation/runner.py`）

```python
from concurrent.futures import ThreadPoolExecutor

class EvaluationRunner:
    """評価バッチ実行（ThreadPoolExecutor で並列化）"""

    def __init__(
        self,
        model_name: LlmModel = LlmModel.GPT_5_1,
        max_iterations: int = 5,
        num_trials: int = 3,
        max_workers: int = 3,  # 同一条件で3並列
    ):
        pass

    def run_single_trial(
        self,
        case: EvaluationCase,
        use_rag: bool,
        trial: int,
    ) -> TrialResult:
        """1回の試行を実行（同期）"""
        pass

    def run_case(
        self,
        case: EvaluationCase,
        use_rag: bool,
    ) -> list[TrialResult]:
        """1ケース×1条件を num_trials 回並列実行（ThreadPoolExecutor）"""
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [
                executor.submit(self.run_single_trial, case, use_rag, trial)
                for trial in range(1, self.num_trials + 1)
            ]
            return [f.result() for f in futures]

    def run_all(
        self,
        cases: list[EvaluationCase],
    ) -> list[TrialResult]:
        """全ケースを実行（RAG あり/なし両方）"""
        pass
```

### 5. CLI エントリーポイント（`src/evaluation/main.py`）

```python
class EvaluationCLI:
    def run(
        self,
        output_dir: str | None = None,
        model_name: str = "gpt-5.1",
        max_iterations: int = 5,
        num_trials: int = 3,
        max_workers: int = 3,
    ) -> None:
        """全評価ケースを実行"""
        pass

    def single_case(
        self,
        bridge_length_m: float,
        total_width_m: float,
        use_rag: bool = True,
        output_dir: str | None = None,
    ) -> None:
        """単一ケースのテスト実行"""
        pass

if __name__ == "__main__":
    fire.Fire(EvaluationCLI)
```

### 6. config.py への追加

```python
# AppConfig に追加
evaluation_dir: Path  # data/evaluation/
```

## ディレクトリ構成

```
src/
└── evaluation/
    ├── __init__.py
    ├── models.py        # Pydantic モデル定義
    ├── metrics.py       # 指標計算ロジック
    ├── runner.py        # バッチ評価ランナー
    └── main.py          # CLI エントリーポイント

data/
└── evaluation/              # 評価専用フォルダ（新規）
    ├── designs/             # BridgeDesign JSON
    │   ├── L30_B6_rag_true_trial_1.json
    │   └── ...
    ├── judges/              # JudgeReport JSON
    │   ├── L30_B6_rag_true_trial_1.json
    │   └── ...
    ├── senkeis/             # Senkei JSON
    │   ├── L30_B6_rag_true_trial_1.senkei.json
    │   └── ...
    ├── ifcs/                # IFC ファイル
    │   ├── L30_B6_rag_true_trial_1.ifc
    │   └── ...
    ├── results/             # TrialResult JSON（評価指標）
    │   ├── L30_B6_rag_true_trial_1.json
    │   └── ...
    └── summary.json         # 集計結果
```

## 評価ケース（EVALUATION.md より）

| No | L (m) | B (m) |
|----|-------|-------|
| 1 | 30 | 6 |
| 2 | 30 | 10 |
| 3 | 40 | 8 |
| 4 | 40 | 12 |
| 5 | 50 | 6 |
| 6 | 50 | 10 |
| 7 | 50 | 14 |
| 8 | 60 | 10 |
| 9 | 60 | 14 |
| 10 | 70 | 10 |
| 11 | 70 | 14 |

## 並列実行の設計

```
ケース1 (L30_B6)
├─ RAG あり
│   ├─ trial 1 ─┐
│   ├─ trial 2 ─┼─ ThreadPoolExecutor(max_workers=3)
│   └─ trial 3 ─┘
└─ RAG なし
    ├─ trial 1 ─┐
    ├─ trial 2 ─┼─ ThreadPoolExecutor(max_workers=3)
    └─ trial 3 ─┘

※ ケース間は順次実行（API レート制限考慮）
※ 同一条件（ケース×RAG条件）内で ThreadPoolExecutor で 3 並列
```

## 出力形式

### 評価専用フォルダ（data/evaluation/）

```
data/evaluation/
├── designs/                           # 各試行の BridgeDesign
│   ├── L30_B6_rag_true_trial_1.json
│   └── ...
├── judges/                            # 各試行の最終 JudgeReport
│   ├── L30_B6_rag_true_trial_1.json
│   └── ...
├── senkeis/                           # Senkei JSON
│   ├── L30_B6_rag_true_trial_1.senkei.json
│   └── ...
├── ifcs/                              # IFC ファイル
│   ├── L30_B6_rag_true_trial_1.ifc
│   └── ...
├── results/                           # TrialResult（評価指標）
│   ├── L30_B6_rag_true_trial_1.json
│   └── ...
└── summary.json                       # 集計結果
```

## 実装順序

1. `src/evaluation/__init__.py` 作成
2. `src/evaluation/models.py` - Pydantic モデル定義
3. `src/bridge_agentic_generate/config.py` - パス追加
4. `src/bridge_agentic_generate/designer/services.py` - `use_rag` オプション追加
5. `src/evaluation/metrics.py` - 指標計算ロジック
6. `src/evaluation/runner.py` - バッチ評価ランナー
7. `src/evaluation/main.py` - CLI エントリーポイント
8. `make fmt && make lint` で検証

## 検証方法

```bash
# 単一ケースのテスト実行
uv run python -m src.evaluation.main single_case \
  --bridge_length_m 50 \
  --total_width_m 10 \
  --use_rag True

# 全ケース実行（本番）
uv run python -m src.evaluation.main run
```

## 注意事項

- LLM 呼び出しは `ThreadPoolExecutor` で並列化するが、API レート制限に注意
- 各試行の `TrialResult` は即座にファイル保存（中断対策）
- `print` 禁止、`logger` を使用
- 型アノテーション必須
