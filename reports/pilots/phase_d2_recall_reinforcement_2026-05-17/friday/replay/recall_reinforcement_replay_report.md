# Muninn v2 Recall Reinforcement Replay

- Mode: `offline_replay`
- v2 DB: `reports/pilots/phase_d2_recall_reinforcement_2026-05-17/friday_phase_d2_shadow_v2.db`
- Dry run: `false`
- Write state: `true`
- As of: `2026-05-18T00:00:00Z`
- Scope key: `repo:f8cc7f64d3636a4e`
- Eligible cards: 47
- Recall events: 1
- Boosted: 5
- Suppressed: 3
- Preserved: 38
- Decayed: 1
- Neutral: 0

## Top States

- `ea8d2c51-9a13-4736-8b12-45c068c6a783` Friday bridge and tools now expose read-only /mnt/data workspace access status=`boosted` score=`3.847247`
- `6c7f8245-1952-4464-8998-79725736746e` Althing memory audit identifies bridge/direct split and missing private whiteboard status=`boosted` score=`3.797247`
- `7fcab1ba-2af2-498d-b712-d6c79520fd6e` Friday direct chat now auto-routes code prompts to coder and injects repo file context end-to-end status=`boosted` score=`3.797247`
- `849362c5-ed42-43a2-9084-897ecf2c7de1` Friday root now has explicit Mimir repo-cognition entrypoints separated from runtime memory status=`boosted` score=`3.797247`
- `d0510e00-574e-4960-87b1-ad33a99e6546` Run Friday corpus runner in dry-run, smoke, and resume modes status=`boosted` score=`3.797247`
- `596c1020-e868-4fc7-80a4-3d67b2893b71` Friday root compose wrapper plus dedicated coder service wiring status=`preserved` score=`1.15`
- `9e2eb8de-7ecf-4939-9352-ef6ed159603e` Friday coder runtime hardening: volume-init ownership fix, coder health route, and fallback checks status=`preserved` score=`1.1`
- `26a394bd-c6f2-4aef-85b7-8929bbafaca4` Friday Android verification pass confirmed persistence and non-streaming mobile routes status=`preserved` score=`1.05`
- `440c39d5-5839-4722-b5eb-2c7761df4781` Friday eval execution now uses a recorder-only corpus runner with resumable JSONL artifacts status=`preserved` score=`1.05`
- `5ba9d678-421f-4264-bfed-249375da8adb` Friday remediation v1 validation artifacts and rerun IDs status=`preserved` score=`1.05`
- `5f79c511-c602-4b38-9c76-f4e7ebee9f95` Friday eval corpus v1 uses frozen 50-task gold set plus generated 300-variant extension status=`preserved` score=`1.05`
- `8abb22ae-9318-4e39-94d3-86e92361d958` Regenerate Friday corpus_v1 from gold_tasks_v1 with strict validation gates status=`preserved` score=`1.05`

## Safety

- Derived reinforcement state only.
- Canonical card truth is unchanged.
- v1 and live MCP defaults are untouched.
