# タスク: run_output.py を convert_senkei_json_to_ifc.py に移動・リファクタ

## 概要

`src/bridge_json_to_ifc/ifc_utils_new/scripts/run_output.py` の内容を
`src/bridge_json_to_ifc/convert_senkei_json_to_ifc.py` に移動し、
既存の convert_*.py パターンに合わせてリファクタリングする。

## 変更対象ファイル

1. `src/bridge_json_to_ifc/convert_senkei_json_to_ifc.py` - 新規実装
2. `src/bridge_json_to_ifc/ifc_utils_new/scripts/run_output.py` - 削除

## 実装内容

### convert_senkei_json_to_ifc.py

既存パターンに従い以下の構造で実装：

```python
"""SenkeiSpec JSON を IFC に変換するモジュール。"""

from __future__ import annotations

from pathlib import Path

import fire

from src.bridge_agentic_generate.logger_config import logger
from src.bridge_json_to_ifc.ifc_utils_new.core import DefBridge, DefIFC


def convert_senkei_to_ifc(input_path: Path, output_path: Path) -> int:
    """SenkeiSpec JSON を IFC に変換。

    Args:
        input_path: 入力JSONファイルパス
        output_path: 出力IFCファイルパス

    Returns:
        生成された要素数
    """
    DefIFC.clear_generated_element_names()

    DefBridge.RunBridge(
        str(input_path.parent) + "/",
        input_path.name,
        str(output_path),
    )

    element_count = len(DefIFC.get_generated_element_names())
    logger.info(f"IFC生成完了: {element_count}個の要素")
    return element_count


def convert(
    input_path: str,
    output_path: str | None = None,
) -> None:
    """CLI エントリーポイント。

    Args:
        input_path: 入力JSONファイルパス
        output_path: 出力IFCファイルパス（省略時は入力と同名.ifc）
    """
    input_p = Path(input_path)

    if output_path is None:
        output_p = input_p.with_suffix(".ifc")
    else:
        output_p = Path(output_path)

    output_p.parent.mkdir(parents=True, exist_ok=True)

    logger.info(f"入力: {input_p}")
    logger.info(f"出力: {output_p}")

    convert_senkei_to_ifc(input_p, output_p)


def main() -> None:
    fire.Fire(convert)


if __name__ == "__main__":
    main()
```

### 変更点まとめ

| 項目 | Before (run_output.py) | After (convert_senkei_json_to_ifc.py) |
|------|------------------------|---------------------------------------|
| CLI | argparse | fire |
| ログ | print | logger |
| パス処理 | os.path + 複雑な resolve_path | pathlib.Path |
| 出力先 | output/ifc/ 固定 + タイムスタンプ | 引数で指定 or 入力と同名.ifc |
| 要素リスト出力 | txt ファイル出力 | logger のみ（必要なら後で追加可） |

## 参考ファイル

既存パターンの参考：
- `src/bridge_json_to_ifc/convert_simple_to_detailed_json.py`
- `src/bridge_json_to_ifc/convert_detailed_json_to_ifc.py`
- `src/bridge_json_to_ifc/convert_simple_to_senkei_json.py`

## 検証方法

```bash
# フォーマット・Lint
make fmt && make lint

# 動作確認（senkei形式JSONがあれば）
uv run python -m src.bridge_json_to_ifc.convert_senkei_json_to_ifc \
  data/generated_senkei_json/sample.json \
  data/generated_ifc/sample.ifc
```
