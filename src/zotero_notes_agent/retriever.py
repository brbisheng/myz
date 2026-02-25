from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


ZOTERO_BASE = "https://api.zotero.org"


@dataclass
class ZoteroConfig:
    api_key: str
    library_type: str = "user"
    library_id: str = ""
    timeout_s: int = 30

    @classmethod
    def from_env(cls) -> "ZoteroConfig":
        api_key = os.getenv("ZOTERO_API_KEY", "")
        if not api_key:
            raise ValueError("ZOTERO_API_KEY is required")
        library_type = os.getenv("ZOTERO_LIBRARY_TYPE", "user")
        library_id = os.getenv("ZOTERO_LIBRARY_ID", "")
        if library_type not in {"user", "group"}:
            raise ValueError("ZOTERO_LIBRARY_TYPE must be user or group")
        if not library_id:
            raise ValueError("ZOTERO_LIBRARY_ID is required")
        return cls(api_key=api_key, library_type=library_type, library_id=library_id)


class ZoteroApiError(RuntimeError):
    def __init__(self, status: int, message: str, retryable: bool = False):
        super().__init__(message)
        self.status = status
        self.retryable = retryable


class ZoteroRetriever:
    def __init__(self, config: ZoteroConfig):
        self.config = config

    def list_items(
        self,
        *,
        sort: str = "dateAdded",
        direction: str = "desc",
        limit: int = 5,
        collection_key: str | None = None,
        tag: str | None = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {
            "sort": sort,
            "direction": direction,
            "limit": limit,
            "format": "json",
        }
        if collection_key:
            params["collection"] = collection_key
        if tag:
            params["tag"] = tag
        return self._get_json(f"/{self.config.library_type}s/{self.config.library_id}/items", params)

    def search_items(self, query: str, *, limit: int = 5) -> list[dict[str, Any]]:
        params = {
            "q": query,
            "qmode": "titleCreatorYear",
            "limit": limit,
            "format": "json",
        }
        return self._get_json(f"/{self.config.library_type}s/{self.config.library_id}/items", params)

    def list_child_notes(self, item_key: str) -> list[dict[str, Any]]:
        params = {
            "itemType": "note",
            "format": "json",
        }
        return self._get_json(
            f"/{self.config.library_type}s/{self.config.library_id}/items/{item_key}/children",
            params,
        )

    def get_note(self, note_key: str) -> dict[str, Any]:
        result = self._get_json(
            f"/{self.config.library_type}s/{self.config.library_id}/items/{note_key}",
            {"format": "json"},
        )
        if isinstance(result, list):
            if not result:
                raise ZoteroApiError(404, f"Note {note_key} not found")
            return result[0]
        return result

    def _get_json(self, path: str, params: dict[str, Any]) -> Any:
        query = urlencode(params)
        url = f"{ZOTERO_BASE}{path}?{query}"
        req = Request(
            url,
            headers={
                "Zotero-API-Key": self.config.api_key,
                "Accept": "application/json",
            },
            method="GET",
        )
        try:
            with urlopen(req, timeout=self.config.timeout_s) as resp:
                payload = resp.read().decode("utf-8")
                return json.loads(payload)
        except HTTPError as exc:
            retryable = exc.code in {429, 500, 502, 503, 504}
            detail = exc.read().decode("utf-8", errors="ignore")
            raise ZoteroApiError(exc.code, f"HTTP {exc.code}: {detail}", retryable=retryable) from exc
        except URLError as exc:
            raise ZoteroApiError(0, f"Network error: {exc}", retryable=True) from exc
