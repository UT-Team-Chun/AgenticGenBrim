"""生成から IFC までを一気通貫で実行する CLI エントリーポイント。"""

from __future__ import annotations

import time
from pathlib import Path

from fire import Fire
from pydantic import BaseModel

from src.bridge_agentic_generate.config import app_config
from src.bridge_agentic_generate.llm_client import LlmModel
from src.bridge_agentic_generate.logger_config import logger
from src.bridge_agentic_generate.main import run_single_case
from src.bridge_agentic_generate.rag.embedding_config import TOP_K
from src.bridge_json_to_ifc.run_convert import FileSuffixes
from src.bridge_json_to_ifc.run_convert import convert as bridge_convert

DEFAULT_BRIDGE_LENGTH_M = 30.0
DEFAULT_TOTAL_WIDTH_M = 10.0
DEFAULT_JUDGE_ENABLED = True


class RunResult(BaseModel):
    """CLI 実行結果の出力モデル。

    Attributes:
        design_json (str): 生成された BridgeDesign JSON のパス。
        detailed_json (str): 生成された詳細 JSON のパス。
        ifc (str): 生成された IFC ファイルのパス。
    """

    design_json: str
    detailed_json: str
    ifc: str


def _coerce_model(model_name: str | LlmModel) -> LlmModel:
    """CLI から受けたモデル名を Enum に変換する。

    Args:
        model_name (str | LlmModel): モデル名または LlmModel Enum。

    Returns:
        LlmModel: 対応する LlmModel Enum。

    Raises:
        ValueError: 無効なモデル名が指定された場合。
    """
    if isinstance(model_name, LlmModel):
        return model_name
    try:
        return LlmModel(model_name)
    except ValueError as exc:  # pragma: no cover - Fire がパースするため通常は例外にならない
        valid = ", ".join(m.value for m in LlmModel)
        raise ValueError(f"model_name must be one of: {valid}") from exc


def _latest_design_file(created_after: float) -> Path:
    """生成された BridgeDesign JSON のうち最新のものを取得する。

    Args:
        created_after (float): この時刻以降に作成されたファイルを対象とする（UNIXタイムスタンプ）。

    Returns:
        Path: 最新の BridgeDesign JSON ファイルのパス。

    Raises:
        FileNotFoundError: 条件に一致する JSON ファイルが見つからない場合。
    """
    design_dir = app_config.generated_simple_bridge_json_dir
    design_dir.mkdir(parents=True, exist_ok=True)
    candidates = [p for p in design_dir.glob("*.json") if p.is_file() and p.stat().st_mtime >= created_after]
    if not candidates:
        raise FileNotFoundError("Designer の出力 JSON が見つかりません。生成処理が失敗していないか確認してください。")
    return max(candidates, key=lambda path: path.stat().st_mtime)


def generate(
    bridge_length_m: float = DEFAULT_BRIDGE_LENGTH_M,
    total_width_m: float = DEFAULT_TOTAL_WIDTH_M,
    model_name: str | LlmModel = LlmModel.GPT_5_MINI,
    top_k: int = TOP_K,
    judge_enabled: bool = DEFAULT_JUDGE_ENABLED,
) -> str:
    """Designer→(任意で Judge) を実行し、生成した JSON のパスを返す。

    Args:
        bridge_length_m (float, optional): 橋長 (m)。デフォルトは DEFAULT_BRIDGE_LENGTH_M。
        total_width_m (float, optional): 全幅員 (m)。デフォルトは DEFAULT_TOTAL_WIDTH_M。
        model_name (str | LlmModel, optional): 使用する LLM モデル名。デフォルトは LlmModel.GPT_5_MINI。
        top_k (int, optional): RAG 検索時の取得件数。デフォルトは TOP_K。
        judge_enabled (bool, optional): Judge エージェントによる評価を行うかどうか。デフォルトは DEFAULT_JUDGE_ENABLED。

    Returns:
        str: 生成された BridgeDesign JSON ファイルのパス。
    """
    start_time = time.time()
    run_single_case(
        bridge_length_m=bridge_length_m,
        total_width_m=total_width_m,
        model_name=_coerce_model(model_name),
        top_k=top_k,
        judge_enabled=judge_enabled,
    )
    design_file = _latest_design_file(created_after=start_time)
    logger.info("BridgeDesign JSON: %s", design_file)
    return str(design_file)


def run(
    bridge_length_m: float = DEFAULT_BRIDGE_LENGTH_M,
    total_width_m: float = DEFAULT_TOTAL_WIDTH_M,
    model_name: str | LlmModel = LlmModel.GPT_5_MINI,
    top_k: int = TOP_K,
    judge_enabled: bool = DEFAULT_JUDGE_ENABLED,
    detailed_json_path: str | None = None,
    ifc_output_path: str | None = None,
) -> RunResult:
    """BridgeDesign 生成から IFC 出力までを一度に実行する。

    Args:
        bridge_length_m (float, optional): 橋長 (m)。デフォルトは DEFAULT_BRIDGE_LENGTH_M。
        total_width_m (float, optional): 全幅員 (m)。デフォルトは DEFAULT_TOTAL_WIDTH_M。
        model_name (str | LlmModel, optional): 使用する LLM モデル名。デフォルトは LlmModel.GPT_5_MINI。
        top_k (int, optional): RAG 検索時の取得件数。デフォルトは TOP_K。
        judge_enabled (bool, optional): Judge エージェントによる評価を行うかどうか。デフォルトは DEFAULT_JUDGE_ENABLED。
        detailed_json_path (str | None, optional): 詳細 JSON の出力パス。指定しない場合は自動生成される。
        ifc_output_path (str | None, optional): IFC ファイルの出力パス。指定しない場合は自動生成される。

    Returns:
        RunResult: 生成されたファイルのパスを含むモデル。
    """
    design_path = Path(
        generate(
            bridge_length_m=bridge_length_m,
            total_width_m=total_width_m,
            model_name=model_name,
            top_k=top_k,
            judge_enabled=judge_enabled,
        )
    )
    detailed_path = (
        Path(detailed_json_path)
        if detailed_json_path is not None
        else app_config.generated_detailed_bridge_json_dir / f"{design_path.stem}{FileSuffixes.DETAILED}"
    )
    ifc_path = (
        Path(ifc_output_path)
        if ifc_output_path is not None
        else app_config.generated_ifc_dir / f"{design_path.stem}{FileSuffixes.IFC}"
    )
    bridge_convert(str(design_path), str(detailed_path), str(ifc_path))

    logger.info("Detailed JSON: %s", detailed_path)
    logger.info("IFC: %s", ifc_path)
    return RunResult(design_json=str(design_path), detailed_json=str(detailed_path), ifc=str(ifc_path))


if __name__ == "__main__":
    Fire(run)
