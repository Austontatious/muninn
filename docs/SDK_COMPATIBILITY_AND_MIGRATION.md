# SDK Compatibility and Migration Notes

Date: 2026-04-05

## Summary
This refactor introduces a new SDK-first core (`muninn.core`) while keeping existing HTTP/MCP/CLI surfaces intact. The runtime layer remains the compatibility surface for existing consumers.

## What Remains Compatible
- FastAPI `/v0/*` endpoints and request/response shapes
- MCP tools and tool names (`muninn.spaces.resolve`, `muninn.rehydrate.bundle`, `muninn.cards.*`, `muninn.policy.*`)
- CLI commands (`muninn up`, `muninn mcp`, `muninn audit`, `muninn doctor`)
- `muninn.client.http.MuninnClient` for HTTP consumers

## New SDK Surface
- Importable SDK:

```python
from muninn import Muninn
from muninn.packs import LexiPack

mem = Muninn(app_pack=LexiPack())
```

- Apps supply memory types and bundle specs via `AppSpec`/`MemorySpec`/`BundleSpec`.

## Adapter Policy
- Runtime adapters should call the core SDK or `HumanMemoryStore` rather than duplicating logic.
- Adapters must preserve current payload formats and error codes.
- Runtime wrappers are exposed under `muninn.runtime` for HTTP/MCP/CLI bootstrapping.

## Migration Guidance
- Existing HTTP/MCP integrations require no change.
- New app integrations should use app packs + SDK contract.
- Existing data remains stored in `human_memory.db` and `muninn.db` (no migration performed in this phase).

## Known Gaps
- Two DB planes remain (human-memory + v0). The SDK currently targets the human-memory plane.
- Full SDK wrappers for `/v0/*` endpoints will be addressed in a later phase.
