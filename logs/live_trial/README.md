# Muninn v2 Live Trial Logs

This directory is for Auston's personal/local Muninn v2 live trial.

Log these events here during the trial:

- v2 bridge read requests
- v2 bridge/context errors
- denied policy requests
- fallback to v1 MCP/context
- write attempts and write failures
- missing or confusing context
- cross-project contamination suspicions
- adaptive-state or degradation concerns

The helper `scripts/muninn_v2_live_context.py` appends structured events to
`muninn_v2_live_trial_events.jsonl`. That JSONL file and generated context
artifacts are local runtime output and are ignored by git.

Do not log secrets, bearer tokens, API keys, raw private credentials, or bulky
full context dumps here. Use bridge request ids, trace ids, file paths, and
short operator notes instead.
