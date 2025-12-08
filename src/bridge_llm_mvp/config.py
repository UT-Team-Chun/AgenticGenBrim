from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, ConfigDict


class AppConfig(BaseModel):
    """パスや共通定数を集中管理する設定モデル。"""

    model_config = ConfigDict(frozen=True)

    project_root: Path
    src_dir: Path
    data_dir: Path
    generated_bridge_json_dir: Path
    rag_index_dir: Path
    rag_index_dir_plumber: Path
    rag_index_dir_pymupdf: Path
    env_file: Path


@lru_cache(maxsize=1)
def get_app_config() -> AppConfig:
    """リポジトリルートを基点とした設定を返す。

    Returns:
        AppConfig: パス・プロバイダ情報を含む設定。
    """
    project_root = Path(__file__).resolve().parent.parent.parent
    return AppConfig(
        project_root=project_root,
        src_dir=project_root / "src",
        data_dir=project_root / "data",
        generated_bridge_json_dir=project_root / "data" / "generated_bridge_json",
        rag_index_dir=project_root / "rag_index",
        rag_index_dir_plumber=project_root / "rag_index" / "pdfplumber",
        rag_index_dir_pymupdf=project_root / "rag_index" / "pymupdf",
        env_file=project_root / ".env",
    )
