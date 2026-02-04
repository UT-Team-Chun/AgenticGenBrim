# タスク: 橋長×幅員の最終合格率ヒートマップ機能追加

## 概要

橋長（L）×幅員（B）の2軸での最終合格率ヒートマップを `src/evaluation/plot.py` に追加する。

## 要件

- RAGあり・なし**両方**のヒートマップを出力
- セルには数値を表示しない（色のみ）
- `generate_all_plots()` に統合
- 出力ファイル:
  - `heatmap_final_pass_rag_true.png`
  - `heatmap_final_pass_rag_false.png`

## 対象ディレクトリ・ファイル

- `src/evaluation/plot.py` - メイン実装対象

## 実装内容

### 1. import追加

```python
import numpy as np
```

### 2. HeatmapData モデル追加（42行目付近）

```python
class HeatmapData(BaseModel):
    """ヒートマップ用2次元データ。

    Attributes:
        lengths: 橋長の昇順リスト [m]
        widths: 幅員の昇順リスト [m]
        values: 2次元配列 [width_idx][length_idx] の合格率（0.0-1.0 or None）
    """
    lengths: list[int] = Field(..., description="橋長リスト（昇順）")
    widths: list[int] = Field(..., description="幅員リスト（昇順）")
    values: list[list[float | None]] = Field(..., description="合格率2次元配列")
```

### 3. calc_pass_rate_heatmap() 関数追加

```python
def calc_pass_rate_heatmap(results: list[TrialResult]) -> HeatmapData:
    """橋長 x 幅員の2次元合格率を計算する。

    Args:
        results: 試行結果リスト（RAGでフィルタリング済み）

    Returns:
        橋長 x 幅員のヒートマップデータ
    """
    # 橋長・幅員のユニーク値を抽出
    lengths = sorted({int(r.bridge_length_m) for r in results})
    widths = sorted({int(r.total_width_m) for r in results})

    # (length, width) -> list[TrialResult] のマッピング
    by_key: dict[tuple[int, int], list[TrialResult]] = defaultdict(list)
    for r in results:
        key = (int(r.bridge_length_m), int(r.total_width_m))
        by_key[key].append(r)

    # 2次元配列の構築（widths x lengths）
    values: list[list[float | None]] = []
    for width in widths:
        row: list[float | None] = []
        for length in lengths:
            trials = by_key.get((length, width))
            if trials:
                pass_count = sum(1 for t in trials if t.final_pass)
                row.append(pass_count / len(trials))
            else:
                row.append(None)
        values.append(row)

    return HeatmapData(lengths=lengths, widths=widths, values=values)
```

### 4. plot_heatmap() 関数追加

```python
def plot_heatmap(
    heatmap_data: HeatmapData,
    output_path: Path,
    title: str,
) -> None:
    """ヒートマップを出力する（セル内数値なし）。

    Args:
        heatmap_data: ヒートマップデータ
        output_path: 出力ファイルパス
        title: グラフタイトル
    """
    # numpy array に変換（None -> np.nan）
    arr = np.array([
        [v if v is not None else np.nan for v in row]
        for row in heatmap_data.values
    ])

    # マスク配列（NaNをマスク）
    masked_arr = np.ma.masked_invalid(arr)

    fig, ax = plt.subplots(figsize=(10, 8))

    # カラーマップ（0%=赤, 100%=緑）
    cmap = plt.cm.RdYlGn.copy()
    cmap.set_bad(color='lightgray')

    # imshow で描画
    im = ax.imshow(
        masked_arr,
        cmap=cmap,
        vmin=0.0,
        vmax=1.0,
        aspect='auto',
        origin='lower',
    )

    # 軸ラベル設定
    ax.set_xticks(range(len(heatmap_data.lengths)))
    ax.set_xticklabels(heatmap_data.lengths)
    ax.set_yticks(range(len(heatmap_data.widths)))
    ax.set_yticklabels(heatmap_data.widths)

    ax.set_xlabel("橋長 [m]", fontsize=12)
    ax.set_ylabel("幅員 [m]", fontsize=12)
    ax.set_title(title, fontsize=14)

    # カラーバー
    cbar = plt.colorbar(im, ax=ax)
    cbar.set_label("最終合格率", fontsize=12)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close(fig)
    logger.info("Saved heatmap to %s", output_path)
```

### 5. generate_all_plots() 拡張

既存のRAG有無別グラフ生成の後に以下を追加:

```python
# ヒートマップ（RAGあり）
heatmap_rag_true = calc_pass_rate_heatmap(results_rag_true)
plot_heatmap(
    heatmap_data=heatmap_rag_true,
    output_path=output_dir / "heatmap_final_pass_rag_true.png",
    title="最終合格率ヒートマップ（RAGあり）",
)

# ヒートマップ（RAGなし）
heatmap_rag_false = calc_pass_rate_heatmap(results_rag_false)
plot_heatmap(
    heatmap_data=heatmap_rag_false,
    output_path=output_dir / "heatmap_final_pass_rag_false.png",
    title="最終合格率ヒートマップ（RAGなし）",
)
```

## 受け入れ条件

- [ ] `make lint` が通る
- [ ] `uv run python -m src.evaluation.main plot --data_dir data/evaluation_v5` が正常終了
- [ ] 以下のファイルが生成される:
  - `heatmap_final_pass_rag_true.png`
  - `heatmap_final_pass_rag_false.png`
- [ ] ヒートマップが正しく表示される（X軸=橋長、Y軸=幅員、色=合格率）

## 検証コマンド

```bash
# フォーマット・Lint
make fmt && make lint

# グラフ生成
uv run python -m src.evaluation.main plot --data_dir data/evaluation_v5
```
