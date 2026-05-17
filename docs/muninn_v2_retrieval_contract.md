# Muninn v2 Retrieval Contract

Muninn v2 retrieval is an opt-in diagnostic/shadow retrieval surface. It does not replace v1 live recall and does not change MCP/Codex defaults.

## Inputs

Retrieval callers provide:

- `query`: required text query.
- `space_key`: optional project/space filter.
- `limit`: optional result window, defaulting to 10 in CLI evaluation.
- `filters`: optional future structured filters.
- `ontology_profile`: optional future profile metadata.
- `include_evidence`: optional report/detail expansion.
- `include_explanations`: optional score explanation expansion.
- `retrieval_mode`: diagnostic mode, currently `hybrid`, `lexical`, or `vector` for retrieval eval.

All DB writes remain explicit. Retrieval eval requires an explicit v2 DB path and never opens production v1 DBs. Recall parity can read v1 with SQLite read-only/query-only mode, but it remains measurement-only.

## Candidate Generation

Hybrid retrieval scores active v2 `MemoryCard` records in the requested scope. Candidate signals are:

- exact or phrase matches in card title
- lexical title token overlap
- lexical summary/body token overlap
- evidence ref/excerpt lexical overlap
- tag overlap
- project/space match
- campaign, version, and numeric token matches
- recency and salience boosts when present
- optional derived-vector similarity as a rescue signal

Association expansion, recall-history expansion, and ontology-guided expansion are deferred. They are hooks for later work, not part of this contract yet.

## Query Normalization

Normalization is deterministic:

- lowercase text
- split punctuation and separators
- split `_` and `-`, so metric names like `sonar_clutter_wrong_binding_rate` match natural-language queries
- preserve meaningful alphanumeric tokens such as `004a`, `005a`, `006a`, `007a`, and `readyplayer1`
- remove only a small set of low-value stop words

No stemming, synonym expansion, model calls, or hidden randomization are used.

## Scoring Components

Hybrid score components are additive and exposed in result explanations:

- `title_phrase_match`
- `summary_phrase_match`
- `body_phrase_match`
- `evidence_phrase_match`
- `title_token_overlap`
- `summary_token_overlap`
- `body_token_overlap`
- `evidence_token_overlap`
- `tags_token_overlap`
- `title_coverage_boost`
- `body_coverage_boost`
- `numeric_token_match`
- `campaign_token_match`
- `project_space_match`
- `recency_boost`
- `salience_boost`
- `vector_similarity_rescue`

Penalties are also explicit:

- `low_specificity_match`
- `broad_token_match`
- `evidence_only_weak_match`
- `missing_project_space_match`

Vectors are optional derived indexes. In hybrid mode, vector similarity can rescue or break ties, but it does not replace precise lexical/title/body/evidence matching.

## Explanation Format

Each result can explain:

- `retrieval_path`
- `score_semantics`
- `candidate_sources`
- `matched_tokens`
- `matched_fields`
- `score_components`
- `penalties`
- `vector_used`
- `vector_score`

Retrieval eval reports compact top-result explanations so failed cases can be debugged without replaying the scorer.

## Ranking Policy

Ranking is deterministic:

- higher score ranks first
- score ties are broken by `updated_at`, then record id
- no randomization
- low-specificity matches below the hybrid minimum score are excluded from the result window

Top-N should favor precise project-specific title/body/metric matches over broad weak matches. Evidence contributes, but evidence-only weak matches are penalized to avoid flooding.

## Boundary

This is retrieval, not Mimir cognition. Muninn v2 hybrid retrieval must not implement salience propagation, spreading activation, motif detection, hidden-link discovery, or project-topology reasoning. Mimir may later consume retrieval diagnostics, but Muninn v2 remains the memory substrate and evaluation surface.
