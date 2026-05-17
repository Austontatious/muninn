# Muninn v2 Contracts

This directory contains opt-in Muninn v2 contract artifacts. These contracts are not live v1 API, MCP, or Codex defaults.

## RehydrateResponseV1

- Schema: `schemas/rehydrate-response.v1.schema.json`
- Valid example: `examples/valid/rehydrate-response.shadow-preview.v1.json`
- Version manifest: `versions.json`
- Contract version: `1.0.0`
- Schema version: `muninn.v2.rehydrate_response.v1`

`RehydrateResponseV1` is the stable JSON response envelope for v2 shadow rehydration previews and future agent-context experiments. It carries request metadata, selected memory cards/events/evidence, explanations, uncertainty, budget usage, retrieval provenance, and fallback/degradation markers.

The envelope is a v2 shadow/evaluation contract only. It does not change live v1 retrieval, live MCP behavior, or Codex defaults.
