from __future__ import annotations

import logging
from functools import lru_cache

LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DEFAULT_LEVEL = logging.INFO


@lru_cache(maxsize=None)
def get_logger(name: str = "bridge_llm_mvp") -> logging.Logger:
    """共通ロガーを返す。

    Args:
        name: ロガー名。モジュール単位で指定。

    Returns:
        logging.Logger: ストリームハンドラ付きロガー。
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(LOG_FORMAT))
        logger.addHandler(handler)

    logger.setLevel(DEFAULT_LEVEL)
    logger.propagate = False
    return logger
