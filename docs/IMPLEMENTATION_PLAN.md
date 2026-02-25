# Implementation Plan (Post-M1)

## Completed in M1
- Tool contract envelope: `ok/data/error/meta`.
- Input validation for `limit` and `sort_field`.
- Retriever endpoints:
  - latest items
  - search items
  - item child notes
  - get note
- CLI for agent/tool execution.

## Next (M2)
1. Add note normalization: HTML -> Markdown.
2. Emit stable schema blocks grouped by paper.
3. Add `schema_version` and `extractor_version` fields.
4. Add cache by `noteKey + dateModified/content_hash`.

## Next (M3)
1. Add extraction pipeline for summary/claims/methods.
2. Add confidence and provenance metadata.
3. Golden-test set for extraction quality.

## Optional (M4)
- Write back summary notes/tags to Zotero with write-permission key.
