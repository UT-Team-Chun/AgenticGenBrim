"""評価結果のグラフ出力モジュール。"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
from pydantic import BaseModel, Field

from src.bridge_agentic_generate.logger_config import logger
from src.evaluation.models import TrialResult

# 日本語フォント設定（macOS: Hiragino Sans, Windows: MS Gothic, Linux: IPAGothic）
plt.rcParams["font.family"] = ["Hiragino Sans", "MS Gothic", "IPAGothic", "sans-serif"]


class PassRate(BaseModel):
    """合格率データ。

    Attributes:
        first_pass_rate: 初回合格率（0.0〜1.0）
        final_pass_rate: 最終合格率（0.0〜1.0）
    """

    first_pass_rate: float = Field(..., ge=0.0, le=1.0, description="初回合格率")
    final_pass_rate: float = Field(..., ge=0.0, le=1.0, description="最終合格率")


class PassRateEntry(BaseModel):
    """ラベル付き合格率エントリ。

    Attributes:
        label: 表示ラベル（例: "20", "With RAG"）
        pass_rate: 合格率データ
    """

    label: str = Field(..., description="表示ラベル")
    pass_rate: PassRate = Field(..., description="合格率データ")


def load_trial_results(results_dir: Path) -> list[TrialResult]:
    """results/ フォルダから全 TrialResult を読み込む。

    Args:
        results_dir: results/ ディレクトリのパス

    Returns:
        全試行結果のリスト
    """
    results: list[TrialResult] = []
    for json_path in results_dir.glob("*.json"):
        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))
            results.append(TrialResult(**data))
        except Exception as e:
            logger.warning("Failed to load %s: %s", json_path, e)
    logger.info("Loaded %d trial results from %s", len(results), results_dir)
    return results


def calc_pass_rate_by_length(results: list[TrialResult]) -> list[PassRateEntry]:
    """橋長別の合格率を計算する。

    Args:
        results: 試行結果リスト

    Returns:
        橋長別の合格率エントリリスト（橋長昇順）
    """
    by_length: dict[int, list[TrialResult]] = defaultdict(list)
    for r in results:
        length = int(r.bridge_length_m)
        by_length[length].append(r)

    entries: list[PassRateEntry] = []
    for length, trials in sorted(by_length.items()):
        first_pass_count = sum(1 for t in trials if t.first_pass)
        final_pass_count = sum(1 for t in trials if t.final_pass)
        n = len(trials)
        entries.append(
            PassRateEntry(
                label=str(length),
                pass_rate=PassRate(
                    first_pass_rate=first_pass_count / n,
                    final_pass_rate=final_pass_count / n,
                ),
            )
        )
    return entries


def calc_pass_rate_by_width(results: list[TrialResult]) -> list[PassRateEntry]:
    """幅員別の合格率を計算する。

    Args:
        results: 試行結果リスト

    Returns:
        幅員別の合格率エントリリスト（幅員昇順）
    """
    by_width: dict[int, list[TrialResult]] = defaultdict(list)
    for r in results:
        width = int(r.total_width_m)
        by_width[width].append(r)

    entries: list[PassRateEntry] = []
    for width, trials in sorted(by_width.items()):
        first_pass_count = sum(1 for t in trials if t.first_pass)
        final_pass_count = sum(1 for t in trials if t.final_pass)
        n = len(trials)
        entries.append(
            PassRateEntry(
                label=str(width),
                pass_rate=PassRate(
                    first_pass_rate=first_pass_count / n,
                    final_pass_rate=final_pass_count / n,
                ),
            )
        )
    return entries


def calc_pass_rate_by_rag(results: list[TrialResult]) -> list[PassRateEntry]:
    """RAG有無別の合格率を計算する。

    Args:
        results: 試行結果リスト

    Returns:
        RAG有無別の合格率エントリリスト（RAG有→RAG無の順）
    """
    by_rag: dict[bool, list[TrialResult]] = defaultdict(list)
    for r in results:
        by_rag[r.use_rag].append(r)

    rag_labels = {True: "RAGあり", False: "RAGなし"}
    entries: list[PassRateEntry] = []
    # RAG有 → RAG無 の順で出力
    for use_rag in [True, False]:
        if use_rag not in by_rag:
            continue
        trials = by_rag[use_rag]
        first_pass_count = sum(1 for t in trials if t.first_pass)
        final_pass_count = sum(1 for t in trials if t.final_pass)
        n = len(trials)
        entries.append(
            PassRateEntry(
                label=rag_labels[use_rag],
                pass_rate=PassRate(
                    first_pass_rate=first_pass_count / n,
                    final_pass_rate=final_pass_count / n,
                ),
            )
        )
    return entries


def plot_bar_chart(
    entries: list[PassRateEntry],
    output_path: Path,
    xlabel: str,
    ylabel: str,
    *,
    use_first_pass: bool,
) -> None:
    """棒グラフを出力する（凡例なし）。

    Args:
        entries: 合格率エントリリスト
        output_path: 出力ファイルパス
        xlabel: X軸ラベル
        ylabel: Y軸ラベル
        use_first_pass: True なら初回合格率、False なら最終合格率を使用
    """
    fig, ax = plt.subplots(figsize=(10, 6))

    x_labels = [e.label for e in entries]
    y_values = [(e.pass_rate.first_pass_rate if use_first_pass else e.pass_rate.final_pass_rate) * 100 for e in entries]

    bars = ax.bar(x_labels, y_values, color="steelblue", edgecolor="black")

    ax.set_xlabel(xlabel, fontsize=12)
    ax.set_ylabel(ylabel, fontsize=12)
    ax.set_ylim(0, 100)
    ax.set_yticks(range(0, 101, 10))

    # 各棒の上に値を表示
    for bar, val in zip(bars, y_values):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 1,
            f"{val:.1f}%",
            ha="center",
            va="bottom",
            fontsize=9,
        )

    ax.grid(axis="y", linestyle="--", alpha=0.7)
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close(fig)
    logger.info("Saved plot to %s", output_path)


def generate_all_plots(data_dir: Path, output_dir: Path) -> None:
    """全グラフを生成する。

    Args:
        data_dir: 評価データのルートディレクトリ（results/ を含む）
        output_dir: グラフ出力先ディレクトリ
    """
    results_dir = data_dir / "results"
    if not results_dir.exists():
        raise FileNotFoundError(f"Results directory not found: {results_dir}")

    results = load_trial_results(results_dir)
    if not results:
        raise ValueError("No trial results found")

    output_dir.mkdir(parents=True, exist_ok=True)

    # RAGあり/なしでフィルタリング
    results_rag_true = [r for r in results if r.use_rag]
    results_rag_false = [r for r in results if not r.use_rag]

    # 橋長別（RAGあり）
    length_entries_rag_true = calc_pass_rate_by_length(results_rag_true)
    plot_bar_chart(
        entries=length_entries_rag_true,
        output_path=output_dir / "length_first_pass_rag_true.png",
        xlabel="橋長 [m]",
        ylabel="初回合格率 [%]",
        use_first_pass=True,
    )
    plot_bar_chart(
        entries=length_entries_rag_true,
        output_path=output_dir / "length_final_pass_rag_true.png",
        xlabel="橋長 [m]",
        ylabel="最終合格率 [%]",
        use_first_pass=False,
    )

    # 橋長別（RAGなし）
    length_entries_rag_false = calc_pass_rate_by_length(results_rag_false)
    plot_bar_chart(
        entries=length_entries_rag_false,
        output_path=output_dir / "length_first_pass_rag_false.png",
        xlabel="橋長 [m]",
        ylabel="初回合格率 [%]",
        use_first_pass=True,
    )
    plot_bar_chart(
        entries=length_entries_rag_false,
        output_path=output_dir / "length_final_pass_rag_false.png",
        xlabel="橋長 [m]",
        ylabel="最終合格率 [%]",
        use_first_pass=False,
    )

    # 幅員別（RAGあり）
    width_entries_rag_true = calc_pass_rate_by_width(results_rag_true)
    plot_bar_chart(
        entries=width_entries_rag_true,
        output_path=output_dir / "width_first_pass_rag_true.png",
        xlabel="幅員 [m]",
        ylabel="初回合格率 [%]",
        use_first_pass=True,
    )
    plot_bar_chart(
        entries=width_entries_rag_true,
        output_path=output_dir / "width_final_pass_rag_true.png",
        xlabel="幅員 [m]",
        ylabel="最終合格率 [%]",
        use_first_pass=False,
    )

    # 幅員別（RAGなし）
    width_entries_rag_false = calc_pass_rate_by_width(results_rag_false)
    plot_bar_chart(
        entries=width_entries_rag_false,
        output_path=output_dir / "width_first_pass_rag_false.png",
        xlabel="幅員 [m]",
        ylabel="初回合格率 [%]",
        use_first_pass=True,
    )
    plot_bar_chart(
        entries=width_entries_rag_false,
        output_path=output_dir / "width_final_pass_rag_false.png",
        xlabel="幅員 [m]",
        ylabel="最終合格率 [%]",
        use_first_pass=False,
    )

    # RAG有無別
    rag_entries = calc_pass_rate_by_rag(results)
    plot_bar_chart(
        entries=rag_entries,
        output_path=output_dir / "rag_first_pass.png",
        xlabel="RAG使用",
        ylabel="初回合格率 [%]",
        use_first_pass=True,
    )
    plot_bar_chart(
        entries=rag_entries,
        output_path=output_dir / "rag_final_pass.png",
        xlabel="RAG使用",
        ylabel="最終合格率 [%]",
        use_first_pass=False,
    )

    logger.info("All plots generated in %s", output_dir)
