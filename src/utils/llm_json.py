import json
import re
from typing import Any, Callable

from langchain_core.messages import HumanMessage, SystemMessage

from src.config import get_azure_llm


def extract_llm_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict):
                text = block.get("text")
                if isinstance(text, str):
                    parts.append(text)
        return "\n".join(parts)
    if isinstance(content, dict):
        text = content.get("text")
        if isinstance(text, str):
            return text
    return str(content)


def coerce_text(value: Any, *, separator: str = "\n") -> str:
    """Flatten an LLM field into plain text. Models often return a list where a string is expected."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (list, tuple, set)):
        parts = [coerce_text(item, separator=separator) for item in value]
        return separator.join(part for part in parts if part)
    if isinstance(value, dict):
        parts = [f"{key}: {coerce_text(item, separator=' ')}" for key, item in value.items()]
        return separator.join(part for part in parts if part)
    return str(value)


def coerce_str_list(value: Any) -> list[str]:
    """Normalize an LLM field into a list of strings, without splitting a bare string into characters."""
    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value.strip() else []
    if isinstance(value, (list, tuple, set)):
        items = [coerce_text(item, separator=" ").strip() for item in value]
        return [item for item in items if item]
    text = coerce_text(value).strip()
    return [text] if text else []


def parse_llm_json(content: Any) -> dict[str, Any]:
    text = extract_llm_text(content).strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            raise
        payload = json.loads(match.group(0))
    if not isinstance(payload, dict):
        raise ValueError("LLM response JSON must be an object.")
    return payload


def invoke_llm_json(
    prompt: str,
    *,
    system_prompt: str,
    llm_factory: Callable[[], Any] | None = None,
    max_retries: int = 2,
) -> dict[str, Any]:
    llm = llm_factory() if llm_factory else get_azure_llm()
    last_error: Exception | None = None

    for attempt in range(max_retries + 1):
        suffix = "\n\nRespond with valid JSON only."
        if attempt > 0:
            suffix = (
                "\n\nYour previous response was not valid JSON. "
                "Return only a single valid JSON object with no markdown fences."
            )
        try:
            response = llm.invoke(
                [
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=prompt + suffix),
                ]
            )
            return parse_llm_json(response.content)
        except (json.JSONDecodeError, ValueError) as exc:
            last_error = exc

    assert last_error is not None
    raise last_error
