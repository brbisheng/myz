# zotero-notes-agent

M1 implementation for a Claude/OpenClaw-callable Zotero notes retriever.

## Features (M1)
- Tool contract with stable output shape: `ok/data/error/meta`.
- Zotero API retriever for:
  - latest items
  - search items
  - list child notes
  - get note content
- CLI wrapper for agent/tool invocation.

## Environment
Set your Zotero API key:

```bash
export ZOTERO_API_KEY=your_key
```

Optional defaults:

```bash
export ZOTERO_LIBRARY_TYPE=user
export ZOTERO_LIBRARY_ID=123456
```

## CLI examples

```bash
zotero-notes latest --limit 3
zotero-notes search --query "Acemoglu 2020"
zotero-notes item-notes --item-key ABCD1234
```

## Contract response
Every command returns JSON:

```json
{
  "ok": true,
  "data": {},
  "error": null,
  "meta": {
    "request_id": "...",
    "latency_ms": 12,
    "source": "zotero"
  }
}
```
