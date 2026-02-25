from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from .contracts import (
    ContractValidationError,
    Timer,
    error_response,
    new_request_id,
    success_response,
    validate_limit,
    validate_sort_field,
)
from .retriever import ZoteroApiError, ZoteroConfig, ZoteroRetriever


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="zotero-notes")
    sub = parser.add_subparsers(dest="command", required=True)

    latest = sub.add_parser("latest", help="Get latest items")
    latest.add_argument("--limit", type=int, default=5)
    latest.add_argument("--sort-field", default="dateAdded")
    latest.add_argument("--direction", default="desc", choices=["asc", "desc"])
    latest.add_argument("--collection-key")
    latest.add_argument("--tag")

    search = sub.add_parser("search", help="Search items")
    search.add_argument("--query", required=True)
    search.add_argument("--limit", type=int, default=5)

    item_notes = sub.add_parser("item-notes", help="List child notes for item")
    item_notes.add_argument("--item-key", required=True)

    note = sub.add_parser("get-note", help="Get note content by note key")
    note.add_argument("--note-key", required=True)

    return parser


def _run(args: argparse.Namespace) -> dict[str, Any]:
    request_id = new_request_id()
    timer = Timer()

    try:
        config = ZoteroConfig.from_env()
        client = ZoteroRetriever(config)

        if args.command == "latest":
            limit = validate_limit(args.limit)
            sort_field = validate_sort_field(args.sort_field)
            items = client.list_items(
                sort=sort_field,
                direction=args.direction,
                limit=limit,
                collection_key=args.collection_key,
                tag=args.tag,
            )
            data = {"items": items, "count": len(items)}

        elif args.command == "search":
            limit = validate_limit(args.limit)
            items = client.search_items(args.query, limit=limit)
            if len(items) > 1:
                return error_response(
                    request_id,
                    timer.stop_ms(),
                    code="NEEDS_DISAMBIGUATION",
                    message="Multiple items matched query; choose one candidate.",
                    retryable=False,
                ) | {"data": {"candidates": _candidate_items(items)}}
            data = {"items": items, "count": len(items)}

        elif args.command == "item-notes":
            notes = client.list_child_notes(args.item_key)
            data = {"item_key": args.item_key, "notes": notes, "count": len(notes)}

        elif args.command == "get-note":
            note = client.get_note(args.note_key)
            data = {"note": note}

        else:
            raise ContractValidationError(f"Unknown command: {args.command}")

        return success_response(request_id, timer.stop_ms(), data)

    except ContractValidationError as exc:
        return error_response(
            request_id,
            timer.stop_ms(),
            code="INVALID_INPUT",
            message=str(exc),
            retryable=False,
        )
    except ValueError as exc:
        return error_response(
            request_id,
            timer.stop_ms(),
            code="CONFIG_ERROR",
            message=str(exc),
            retryable=False,
        )
    except ZoteroApiError as exc:
        return error_response(
            request_id,
            timer.stop_ms(),
            code=f"ZOTERO_HTTP_{exc.status}" if exc.status else "ZOTERO_NETWORK_ERROR",
            message=str(exc),
            retryable=exc.retryable,
        )


def _candidate_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for it in items:
        data = it.get("data", {})
        creators = data.get("creators", [])
        first_author = ""
        if creators:
            c = creators[0]
            first_author = c.get("lastName") or c.get("name") or ""
        out.append(
            {
                "key": it.get("key"),
                "title": data.get("title", ""),
                "year": data.get("date", ""),
                "first_author": first_author,
                "date_added": data.get("dateAdded", ""),
            }
        )
    return out


def main() -> int:
    parser = _parser()
    args = parser.parse_args()
    result = _run(args)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
