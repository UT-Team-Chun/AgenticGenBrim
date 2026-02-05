"""BIM/CIM課題のアンケート調査結果を可視化するグラフ生成スクリプト。

出力:
    - data/graphs/bimcim_challenge_bar_h.png - 横棒グラフ
    - data/graphs/bimcim_challenge_pie.png - 円グラフ
    - data/graphs/bimcim_challenge_bar_v.png - 縦棒グラフ
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt

# 日本語フォント設定（macOS: Hiragino Sans, Windows: MS Gothic, Linux: IPAGothic）
plt.rcParams["font.family"] = ["Hiragino Sans", "MS Gothic", "IPAGothic", "sans-serif"]

# 出力先ディレクトリ
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "graphs"

# データ定義（集約後5項目）
DATA = [
    {"label": "モデル作成の手間", "value": 33, "category": "effort"},
    {"label": "基準把握の時間", "value": 25, "category": "effort"},
    {"label": "2次元図面との二重作成", "value": 16, "category": "dual"},
    {"label": "修正時の二重対応", "value": 9, "category": "dual"},
    {"label": "モデル妥当性確認", "value": 3, "category": "effort"},
    {"label": "その他・非効率なし", "value": 14, "category": "other"},
]

# カテゴリ別の色定義
COLORS = {
    "effort": "#E74C3C",  # 赤系（工数関連）
    "dual": "#3498DB",  # 青系（二重作業）
    "other": "#95A5A6",  # グレー（その他）
}


def get_colors(data: list[dict]) -> list[str]:
    """データのカテゴリに応じた色リストを取得する。

    Args:
        data: データリスト

    Returns:
        色コードのリスト
    """
    return [COLORS[item["category"]] for item in data]


def plot_horizontal_bar(data: list[dict], output_path: Path) -> None:
    """横棒グラフを出力する。

    Args:
        data: データリスト
        output_path: 出力ファイルパス
    """
    fig, ax = plt.subplots(figsize=(10, 6))

    labels = [item["label"] for item in data]
    values = [item["value"] for item in data]
    colors = get_colors(data)

    # 降順でソート（上から大きい順）
    sorted_indices = sorted(range(len(values)), key=lambda i: values[i])
    labels = [labels[i] for i in sorted_indices]
    values = [values[i] for i in sorted_indices]
    colors = [colors[i] for i in sorted_indices]

    bars = ax.barh(labels, values, color=colors, edgecolor="black", linewidth=0.5)

    ax.set_xlabel("割合 [%]", fontsize=12)
    ax.set_xlim(0, 40)

    # 各棒の右に値を表示
    for bar, val in zip(bars, values):
        ax.text(
            bar.get_width() + 0.5,
            bar.get_y() + bar.get_height() / 2,
            f"{val}%",
            ha="left",
            va="center",
            fontsize=10,
        )

    # 凡例（工数関連の合計を明記）
    effort_total = sum(item["value"] for item in data if item["category"] == "effort")
    from matplotlib.patches import Patch

    legend_elements = [
        Patch(facecolor=COLORS["effort"], edgecolor="black", label=f"工数関連 {effort_total}%"),
        Patch(facecolor=COLORS["dual"], edgecolor="black", label="二重作業"),
        Patch(facecolor=COLORS["other"], edgecolor="black", label="その他・非効率なし"),
    ]
    ax.legend(handles=legend_elements, loc="lower right", fontsize=10)

    ax.set_title("BIM/CIM導入における課題", fontsize=14, fontweight="bold")
    ax.grid(axis="x", linestyle="--", alpha=0.7)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_pie_chart(data: list[dict], output_path: Path) -> None:
    """円グラフを出力する。

    Args:
        data: データリスト
        output_path: 出力ファイルパス
    """
    fig, ax = plt.subplots(figsize=(10, 8))

    labels = [item["label"] for item in data]
    values = [item["value"] for item in data]
    colors = get_colors(data)

    # 円グラフ
    wedges, texts, autotexts = ax.pie(
        values,
        labels=None,
        colors=colors,
        autopct="%1.0f%%",
        startangle=90,
        counterclock=False,
        wedgeprops={"edgecolor": "white", "linewidth": 1.5},
        pctdistance=0.75,
    )

    # パーセント表示のスタイル
    for autotext in autotexts:
        autotext.set_fontsize(11)
        autotext.set_fontweight("bold")

    # 凡例（右側に配置）
    ax.legend(
        wedges,
        labels,
        loc="center left",
        bbox_to_anchor=(1.0, 0.5),
        fontsize=10,
    )

    # 工数関連の合計を注釈
    effort_total = sum(item["value"] for item in data if item["category"] == "effort")
    ax.annotate(
        f"工数関連: {effort_total}%",
        xy=(0.5, -0.05),
        xycoords="axes fraction",
        ha="center",
        fontsize=12,
        fontweight="bold",
        color=COLORS["effort"],
    )

    ax.set_title("BIM/CIM導入における課題", fontsize=14, fontweight="bold")

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_vertical_bar(data: list[dict], output_path: Path) -> None:
    """縦棒グラフを出力する。

    Args:
        data: データリスト
        output_path: 出力ファイルパス
    """
    fig, ax = plt.subplots(figsize=(12, 6))

    labels = [item["label"] for item in data]
    values = [item["value"] for item in data]
    colors = get_colors(data)

    # ラベルを改行で短縮表示
    short_labels = [label.replace("との", "\nとの").replace("の二重", "\nの二重") for label in labels]

    bars = ax.bar(short_labels, values, color=colors, edgecolor="black", linewidth=0.5)

    ax.set_ylabel("割合 [%]", fontsize=12)
    ax.set_ylim(0, 40)

    # 各棒の上に値を表示
    for bar, val in zip(bars, values):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.5,
            f"{val}%",
            ha="center",
            va="bottom",
            fontsize=10,
        )

    # 凡例
    effort_total = sum(item["value"] for item in data if item["category"] == "effort")
    from matplotlib.patches import Patch

    legend_elements = [
        Patch(facecolor=COLORS["effort"], edgecolor="black", label=f"工数関連 {effort_total}%"),
        Patch(facecolor=COLORS["dual"], edgecolor="black", label="二重作業"),
        Patch(facecolor=COLORS["other"], edgecolor="black", label="その他・非効率なし"),
    ]
    ax.legend(handles=legend_elements, loc="upper right", fontsize=10)

    ax.set_title("BIM/CIM導入における課題", fontsize=14, fontweight="bold")
    ax.grid(axis="y", linestyle="--", alpha=0.7)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    """メイン関数: 全グラフを生成する。"""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 横棒グラフ
    plot_horizontal_bar(DATA, OUTPUT_DIR / "bimcim_challenge_bar_h.png")

    # 円グラフ
    plot_pie_chart(DATA, OUTPUT_DIR / "bimcim_challenge_pie.png")

    # 縦棒グラフ
    plot_vertical_bar(DATA, OUTPUT_DIR / "bimcim_challenge_bar_v.png")


if __name__ == "__main__":
    main()
