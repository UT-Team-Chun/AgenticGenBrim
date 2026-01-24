"""生成から IFC までを一気通貫で実行する CLI エントリーポイント。"""

from __future__ import annotations

import time
from datetime import datetime
from pathlib import Path

from fire import Fire
from pydantic import BaseModel

from src.bridge_agentic_generate.config import app_config
from src.bridge_agentic_generate.judge.models import RepairLoopResult
from src.bridge_agentic_generate.judge.report import generate_repair_report
from src.bridge_agentic_generate.llm_client import LlmModel
from src.bridge_agentic_generate.logger_config import logger
from src.bridge_agentic_generate.main import run_single_case, run_with_repair_loop
from src.bridge_agentic_generate.rag.embedding_config import TOP_K
from src.bridge_json_to_ifc.run_convert import FileSuffixes
from src.bridge_json_to_ifc.run_convert import convert as bridge_convert

DEFAULT_BRIDGE_LENGTH_M = 40.0
DEFAULT_TOTAL_WIDTH_M = 10.0
DEFAULT_JUDGE_ENABLED = True
DEFAULT_MAX_ITERATIONS = 5


class RunResult(BaseModel):
    """CLI 実行結果の出力モデル。

    Attributes:
        design_json (str): 生成された BridgeDesign JSON のパス。
        senkei_json (str): 生成された SenkeiSpec JSON のパス。
        ifc (str): 生成された IFC ファイルのパス。
    """

    design_json: str
    senkei_json: str
    ifc: str


class RunWithRepairResult(BaseModel):
    """run_with_repair の結果モデル。

    Attributes:
        converged: 収束したかどうか
        num_iterations: 実行されたイテレーション数
        iteration_design_jsons: 各イテレーションの設計JSONパスのリスト
        iteration_judge_jsons: 各イテレーションの照査結果JSONパスのリスト
        iteration_senkei_jsons: 各イテレーションの SenkeiSpec JSON パスのリスト
        iteration_ifcs: 各イテレーションの IFC パスのリスト
        final_design_json: 最終設計のJSONパス
        final_senkei_json: 最終設計の SenkeiSpec JSON のパス
        final_ifc: 最終設計の IFC ファイルのパス
        raglog_json: RAG ログの JSON パス
        report_md: 修正ループレポート（Markdown）のパス
    """

    converged: bool
    num_iterations: int
    iteration_design_jsons: list[str]
    iteration_judge_jsons: list[str]
    iteration_senkei_jsons: list[str]
    iteration_ifcs: list[str]
    final_design_json: str
    final_senkei_json: str
    final_ifc: str
    raglog_json: str
    report_md: str


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
    senkei_json_path: str | None = None,
    ifc_output_path: str | None = None,
) -> RunResult:
    """BridgeDesign 生成から IFC 出力までを一度に実行する。

    Args:
        bridge_length_m (float, optional): 橋長 (m)。デフォルトは DEFAULT_BRIDGE_LENGTH_M。
        total_width_m (float, optional): 全幅員 (m)。デフォルトは DEFAULT_TOTAL_WIDTH_M。
        model_name (str | LlmModel, optional): 使用する LLM モデル名。デフォルトは LlmModel.GPT_5_MINI。
        top_k (int, optional): RAG 検索時の取得件数。デフォルトは TOP_K。
        judge_enabled (bool, optional): Judge エージェントによる評価を行うかどうか。デフォルトは DEFAULT_JUDGE_ENABLED。
        senkei_json_path (str | None, optional): SenkeiSpec JSON の出力パス。指定しない場合は自動生成される。
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
    senkei_path = (
        Path(senkei_json_path)
        if senkei_json_path is not None
        else app_config.generated_senkei_json_dir / f"{design_path.stem}{FileSuffixes.SENKEI}"
    )
    ifc_path = (
        Path(ifc_output_path)
        if ifc_output_path is not None
        else app_config.generated_ifc_dir / f"{design_path.stem}{FileSuffixes.IFC}"
    )
    bridge_convert(str(design_path), str(senkei_path), str(ifc_path))

    logger.info("Senkei JSON: %s", senkei_path)
    logger.info("IFC: %s", ifc_path)
    return RunResult(design_json=str(design_path), senkei_json=str(senkei_path), ifc=str(ifc_path))


class _SavedIterationPaths(BaseModel):
    """_save_repair_loop_results の戻り値。"""

    design_jsons: list[str]
    judge_jsons: list[str]
    senkei_jsons: list[str]
    ifcs: list[str]
    final_design_json: str
    final_senkei_json: str
    final_ifc: str
    raglog_json: str
    report_md: str


def _save_repair_loop_results(
    loop_result: RepairLoopResult,
    base_name: str,
) -> _SavedIterationPaths:
    """修正ループの結果を保存し、各イテレーションの IFC も生成する。

    Args:
        loop_result: 修正ループの結果
        base_name: ファイル名のベース部分

    Returns:
        _SavedIterationPaths: 保存されたファイルパスの情報
    """
    simple_json_dir = app_config.generated_simple_bridge_json_dir
    judge_json_dir = app_config.generated_judge_json_dir
    senkei_json_dir = app_config.generated_senkei_json_dir
    raglog_json_dir = app_config.generated_bridge_raglog_json_dir
    ifc_dir = app_config.generated_ifc_dir
    report_md_dir = app_config.generated_report_md_dir

    simple_json_dir.mkdir(parents=True, exist_ok=True)
    judge_json_dir.mkdir(parents=True, exist_ok=True)
    senkei_json_dir.mkdir(parents=True, exist_ok=True)
    raglog_json_dir.mkdir(parents=True, exist_ok=True)
    ifc_dir.mkdir(parents=True, exist_ok=True)
    report_md_dir.mkdir(parents=True, exist_ok=True)

    iteration_design_paths: list[str] = []
    iteration_judge_paths: list[str] = []
    iteration_senkei_paths: list[str] = []
    iteration_ifc_paths: list[str] = []

    # 各イテレーションの結果を保存
    for iteration in loop_result.iterations:
        iter_suffix = f"_iter{iteration.iteration}"
        design_path = simple_json_dir / f"{base_name}{iter_suffix}.json"
        judge_path = judge_json_dir / f"{base_name}{iter_suffix}_judge.json"
        senkei_path = senkei_json_dir / f"{base_name}{iter_suffix}{FileSuffixes.SENKEI}"
        ifc_path = ifc_dir / f"{base_name}{iter_suffix}{FileSuffixes.IFC}"

        # Design JSON を保存
        design_path.write_text(
            iteration.design.model_dump_json(indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        # Judge JSON を保存
        judge_path.write_text(
            iteration.report.model_dump_json(indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        # IFC に変換
        bridge_convert(str(design_path), str(senkei_path), str(ifc_path))

        iteration_design_paths.append(str(design_path))
        iteration_judge_paths.append(str(judge_path))
        iteration_senkei_paths.append(str(senkei_path))
        iteration_ifc_paths.append(str(ifc_path))

        logger.info("Saved iteration %d design to %s", iteration.iteration, design_path)
        logger.info("Saved iteration %d judge to %s", iteration.iteration, judge_path)
        logger.info("Saved iteration %d IFC to %s", iteration.iteration, ifc_path)

    # 最終設計を保存
    final_design_path = simple_json_dir / f"{base_name}_final.json"
    final_senkei_path = senkei_json_dir / f"{base_name}_final{FileSuffixes.SENKEI}"
    final_ifc_path = ifc_dir / f"{base_name}_final{FileSuffixes.IFC}"

    final_design_path.write_text(
        loop_result.final_design.model_dump_json(indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    bridge_convert(str(final_design_path), str(final_senkei_path), str(final_ifc_path))

    logger.info("Saved final design to %s", final_design_path)
    logger.info("Saved final IFC to %s", final_ifc_path)

    # RAG ログを保存
    raglog_path = raglog_json_dir / f"{base_name}_design_log.json"
    raglog_path.write_text(
        loop_result.rag_log.model_dump_json(indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    logger.info("Saved RAG log to %s", raglog_path)

    # 修正ループレポートを生成・保存
    report_path = report_md_dir / f"{base_name}_report.md"
    generate_repair_report(loop_result, output_path=report_path)
    logger.info("Saved repair loop report to %s", report_path)

    return _SavedIterationPaths(
        design_jsons=iteration_design_paths,
        judge_jsons=iteration_judge_paths,
        senkei_jsons=iteration_senkei_paths,
        ifcs=iteration_ifc_paths,
        final_design_json=str(final_design_path),
        final_senkei_json=str(final_senkei_path),
        final_ifc=str(final_ifc_path),
        raglog_json=str(raglog_path),
        report_md=str(report_path),
    )


def run_with_repair(
    bridge_length_m: float = DEFAULT_BRIDGE_LENGTH_M,
    total_width_m: float = DEFAULT_TOTAL_WIDTH_M,
    model_name: str | LlmModel = LlmModel.GPT_5_MINI,
    top_k: int = TOP_K,
    max_iterations: int = DEFAULT_MAX_ITERATIONS,
) -> RunWithRepairResult:
    """Designer → Judge → 修正ループを実行し、途中経過をすべて保存してIFCまで出力する。

    各イテレーションの design, judge, senkei, ifc をすべて保存し、
    最終設計の IFC も生成する。

    Args:
        bridge_length_m: 橋長 (m)。デフォルトは DEFAULT_BRIDGE_LENGTH_M。
        total_width_m: 全幅員 (m)。デフォルトは DEFAULT_TOTAL_WIDTH_M。
        model_name: 使用する LLM モデル名。デフォルトは LlmModel.GPT_5_MINI。
        top_k: RAG 検索時の取得件数。デフォルトは TOP_K。
        max_iterations: 最大反復回数。デフォルトは DEFAULT_MAX_ITERATIONS。

    Returns:
        RunWithRepairResult: 実行結果（途中経過のパスを含む）
    """
    # 修正ループを実行
    loop_result = run_with_repair_loop(
        bridge_length_m=bridge_length_m,
        total_width_m=total_width_m,
        model_name=_coerce_model(model_name),
        top_k=top_k,
        max_iterations=max_iterations,
    )

    # ファイル名のベース部分を生成
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = f"design_L{int(bridge_length_m)}_B{int(total_width_m)}_{timestamp}"

    # 途中経過を保存（各イテレーションの IFC も生成）
    saved_paths = _save_repair_loop_results(
        loop_result=loop_result,
        base_name=base_name,
    )

    logger.info(
        "Final result: converged=%s, pass_fail=%s, max_util=%.3f, governing=%s",
        loop_result.converged,
        loop_result.final_report.pass_fail,
        loop_result.final_report.utilization.max_util,
        loop_result.final_report.utilization.governing_check,
    )

    return RunWithRepairResult(
        converged=loop_result.converged,
        num_iterations=len(loop_result.iterations),
        iteration_design_jsons=saved_paths.design_jsons,
        iteration_judge_jsons=saved_paths.judge_jsons,
        iteration_senkei_jsons=saved_paths.senkei_jsons,
        iteration_ifcs=saved_paths.ifcs,
        final_design_json=saved_paths.final_design_json,
        final_senkei_json=saved_paths.final_senkei_json,
        final_ifc=saved_paths.final_ifc,
        raglog_json=saved_paths.raglog_json,
        report_md=saved_paths.report_md,
    )


class CLI:
    """統合CLI（Designer → Judge → IFC）。

    Usage:
        # Designer → IFC（Judge 1回のみ）
        uv run python -m src.main run --bridge_length_m=50 --total_width_m=10

        # Designer → Judge → 修正ループ → IFC（途中経過をすべて保存）
        uv run python -m src.main run_with_repair --bridge_length_m=50 --total_width_m=10
    """

    def run(
        self,
        bridge_length_m: float = DEFAULT_BRIDGE_LENGTH_M,
        total_width_m: float = DEFAULT_TOTAL_WIDTH_M,
        model_name: LlmModel = LlmModel.GPT_5_MINI,
        top_k: int = TOP_K,
        judge_enabled: bool = DEFAULT_JUDGE_ENABLED,
        senkei_json_path: str | None = None,
        ifc_output_path: str | None = None,
    ) -> RunResult:
        """Designer → (任意で Judge) → IFC を実行する。"""
        return run(
            bridge_length_m=bridge_length_m,
            total_width_m=total_width_m,
            model_name=model_name,
            top_k=top_k,
            judge_enabled=judge_enabled,
            senkei_json_path=senkei_json_path,
            ifc_output_path=ifc_output_path,
        )

    def run_with_repair(
        self,
        bridge_length_m: float = DEFAULT_BRIDGE_LENGTH_M,
        total_width_m: float = DEFAULT_TOTAL_WIDTH_M,
        model_name: LlmModel = LlmModel.GPT_5_MINI,
        top_k: int = TOP_K,
        max_iterations: int = DEFAULT_MAX_ITERATIONS,
    ) -> RunWithRepairResult:
        """Designer → Judge → 修正ループ → IFC を実行する（各イテレーションの IFC も生成）。"""
        return run_with_repair(
            bridge_length_m=bridge_length_m,
            total_width_m=total_width_m,
            model_name=model_name,
            top_k=top_k,
            max_iterations=max_iterations,
        )


if __name__ == "__main__":
    Fire(CLI)
