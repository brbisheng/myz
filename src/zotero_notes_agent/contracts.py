from __future__ import annotations

from dataclasses import asdict, dataclass
from time import perf_counter
from typing import Any
from uuid import uuid4


MAX_LIMIT = 20


@dataclass
class ErrorPayload:
    code: str
    message: str
    retryable: bool = False


@dataclass
class MetaPayload:
    request_id: str
    latency_ms: int
    source: str = "zotero"


@dataclass
class ToolResponse:
    ok: bool
    data: dict[str, Any] | None
    error: ErrorPayload | None
    meta: MetaPayload

    def to_dict(self) -> dict[str, Any]:
        body = asdict(self)
        if self.error is not None:
            body["error"] = asdict(self.error)
        return body


class ContractValidationError(ValueError):
    pass


class Timer:
    def __init__(self) -> None:
        self._start = perf_counter()

    def stop_ms(self) -> int:
        return int((perf_counter() - self._start) * 1000)


def new_request_id() -> str:
    return uuid4().hex


def validate_limit(limit: int) -> int:
    if limit < 1:
        raise ContractValidationError("limit must be >= 1")
    if limit > MAX_LIMIT:
        raise ContractValidationError(f"limit must be <= {MAX_LIMIT}")
    return limit


def validate_sort_field(sort_field: str) -> str:
    allowed = {"dateAdded", "dateModified", "title"}
    if sort_field not in allowed:
        raise ContractValidationError(
            f"sort_field must be one of {', '.join(sorted(allowed))}"
        )
    return sort_field


def success_response(
    request_id: str,
    latency_ms: int,
    data: dict[str, Any],
    source: str = "zotero",
) -> dict[str, Any]:
    return ToolResponse(
        ok=True,
        data=data,
        error=None,
        meta=MetaPayload(request_id=request_id, latency_ms=latency_ms, source=source),
    ).to_dict()


def error_response(
    request_id: str,
    latency_ms: int,
    code: str,
    message: str,
    retryable: bool = False,
    source: str = "zotero",
) -> dict[str, Any]:
    return ToolResponse(
        ok=False,
        data=None,
        error=ErrorPayload(code=code, message=message, retryable=retryable),
        meta=MetaPayload(request_id=request_id, latency_ms=latency_ms, source=source),
    ).to_dict()
