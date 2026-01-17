from __future__ import annotations

from enum import StrEnum
from functools import lru_cache
from typing import Any, Type, TypeVar

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel

from src.bridge_agentic_generate.config import app_config
from src.bridge_agentic_generate.logger_config import logger

T = TypeVar("T", bound=BaseModel)


class LlmModel(StrEnum):
    """サポートする LLM モデル名。"""

    GPT_5_MINI = "gpt-5-mini"
    GPT_5_1 = "gpt-5.1"


@lru_cache(maxsize=1)
def get_llm_client() -> OpenAI:
    """共通の OpenAI クライアントを返す。

    Returns:
        OpenAI: 認証済みクライアント。
    """
    load_dotenv(app_config.env_file)
    logger.debug("Loaded environment variables from %s", app_config.env_file)
    return OpenAI()


def call_llm_and_get_response(
    input: str,
    model: LlmModel,
    **kwargs: Any,
) -> str:
    """Responses API をラップする。

    Args:
        input: LLM への入力文字列。
        model: 使用するモデル Enum。必須。
        **kwargs: OpenAI API にそのまま渡す追加パラメータ。

    Returns:
        Any: OpenAI Responses API レスポンス。
    """
    client = get_llm_client()
    logger.debug("Calling OpenAI responses.create with model=%s", model)
    response = client.responses.create(
        model=model,
        input=input,
        **kwargs,
    )
    return response.output_text


def call_llm_with_structured_output(
    input: str,
    model: LlmModel,
    text_format: Type[T],
    **kwargs: Any,
) -> T:
    """構造化出力を伴う LLM 呼び出しを行う。

    Args:
        input: LLM への入力文字列。
        model: 使用するモデル Enum。必須。
        text_format: 構造化出力のスキーマとなる Pydantic モデルクラス
            (BaseModel / RootModel を想定)。
        **kwargs: OpenAI API にそのまま渡す追加パラメータ。
    Returns:
        T: text_format に対応する Pydantic モデルインスタンス。
    """
    client = get_llm_client()
    logger.debug(
        "Calling OpenAI responses.create with model=%s and output_schema=%s",
        model,
        text_format,
    )
    response = client.responses.parse(
        model=model,
        input=input,
        text_format=text_format,
        **kwargs,
    )
    if response.output_parsed is None:
        raise ValueError("LLM did not return a valid structured output.")
    return response.output_parsed
