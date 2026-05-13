# Muninn Memory MCP Bridge

This app exposes a private HTTPS-ready MCP bridge for ChatGPT under the connector name `Muninn Memory`.

Muninn is durable user and project memory. Mimir is repository topology and world-state. This bridge only talks to Muninn memory routes and does not expose Mimir, shell, file, admin, debug, or arbitrary network access.

## Tools

- `search(query: str)`
  - Compatibility search tool for ChatGPT.
  - Calls `POST /v0/memory/retrieve`.
  - Returns JSON text with `results` entries shaped as `id`, `title`, `url`, and `snippet`.
- `fetch(id: str)`
  - Compatibility fetch tool for ChatGPT.
  - Retrieves candidates with `POST /v0/memory/retrieve`, returns only an exact `id` match or one unambiguous exact `entity_id` match, then calls `POST /v0/memory/render_cards` when found.
- `search_memory(query, namespace="default", entity_id=None, limit=8)`
  - Richer retrieve wrapper.
  - Clamps `limit` to `1..20`.
- `fetch_memory(memory_id, namespace="default")`
  - Richer exact fetch wrapper preserving the retrieved item and rendered cards when available.
- `rehydrate_project(project, task=None, namespace="default", profile="friday", limit=8)`
  - Calls `POST /v0/memory/rehydrate`.
  - Clamps `limit` to `1..20`.
  - Allows only `generic`, `lexi`, or `friday` profiles.
- `stage_memory_candidates(candidates, namespace="default", ttl_seconds=86400)`
  - Validates and stages proposed memories through `POST /v0/memory/stage_candidates`.
  - Normalizes provenance to the live Muninn schema: `source_type="tool"`, `source_id="chatgpt_mcp"`, and a note containing `source=chatgpt_mcp`, `tool=stage_memory_candidates`, and `write_mode=staged`.
- `list_pending_memory(namespace="default", entity_id=None, status="pending", limit=50)`
  - Calls `POST /v0/memory/list_pending`.
  - Clamps `limit` to `1..100`.
- `confirm_memory_candidates(pending_ids, decision, note=None, namespace="default", confirmation_phrase="")`
  - Calls `POST /v0/memory/confirm_candidates` only when `confirmation_phrase` is exactly `CONFIRM MUNINN WRITE`.
  - Uses `decided_by="chatgpt_mcp"`.

## Security Model

- Read tools are safe by default.
- Staged writes are allowed.
- Confirmation requires the exact phrase `CONFIRM MUNINN WRITE`.
- Direct writes, admin routes, debug routes, shell access, arbitrary file access, and arbitrary network fetches are not exposed.
- The adapter rejects calls to `/v0/memory/write_candidates`, `/v0/memory/upsert_embeddings`, `/v0/admin/*`, and `/v0/debug/*`.
- OAuth or stronger auth should be added later if this becomes more than a private prototype.
- The current private-prototype protection is a long secret path prefix plus existing TLS termination. Treat the path prefix as a secret.

## Run Locally

From this directory:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
MUNINN_BASE_URL=http://127.0.0.1:18000 python server.py
```

The streamable HTTP endpoint is:

```text
http://127.0.0.1:8000/mcp
```

## Docker Deployment

From the Muninn repo root:

```bash
PUBLIC_BASE_URL=https://<host> \
MUNINN_MCP_HOST=<host> \
MCP_PUBLIC_PATH_PREFIX=/mcp-<long-secret> \
docker compose -f docker-compose.mcp.yml up -d --build
```

The bridge service is `muninn-mcp`. It joins both external Docker networks:

- `friday_net`
- `edge`

It calls Muninn internally through:

```text
MUNINN_BASE_URL=http://friday-muninn-1:8000
```

Do not use `localhost` from inside the MCP container.

### Logs

```bash
docker logs -f muninn-mcp
```

### Inspect Networks

```bash
docker inspect muninn-mcp | jq '.[0].NetworkSettings.Networks | keys'
```

Expected keys:

```json
["edge", "friday_net"]
```

### Health From Inside Bridge

```bash
docker exec -it muninn-mcp sh -lc 'python - <<PY
import os, httpx
base = os.getenv("MUNINN_BASE_URL")
print(base)
print(httpx.get(base + "/health", timeout=5).json())
PY'
```

## Traefik Setup

The active `lex-traefik-1` container uses Traefik v3.1 with Docker provider, `edge` as the provider network, `web`/`websecure` entrypoints, and `exposedByDefault=false`. No cert resolver is configured in the inspected Traefik command, so this compose file does not set a cert resolver.

The included `docker-compose.mcp.yml` labels follow the existing entrypoint/network style:

- `traefik.enable=true`
- `traefik.docker.network=edge`
- router rule: `Host(<host>) && PathPrefix(/mcp-<long-secret>)`
- router entrypoint: `websecure` by default, override with `MUNINN_MCP_TRAEFIK_ENTRYPOINT`
- `tls=true` on the router, with no cert resolver assumed
- additional Funnel router entrypoint: `web`
- the Funnel router has no Traefik TLS requirement because Tailscale Funnel terminates public HTTPS and forwards local HTTP to Traefik
- strip-prefix middleware for `/mcp-<long-secret>`
- service port: `8000`

Public ChatGPT MCP URL:

```text
https://<host>/mcp-<long-secret>/mcp
```

After Traefik strips `/mcp-<long-secret>`, the bridge receives `/mcp`, which is the FastMCP streamable HTTP endpoint.

### Public Endpoint Smoke

```bash
curl -i https://<host>/mcp-<long-secret>/mcp
```

A raw curl to an MCP endpoint may not return a normal webpage. The key failures to avoid are a Traefik `404`, `502`, TLS failure, or timeout.

## Tailscale Funnel Deployment

SSH local tunnels do not work for ChatGPT web MCP because ChatGPT needs a public HTTPS endpoint reachable from OpenAI's infrastructure. Tailscale Serve is tailnet-only, so it also does not work for ChatGPT. Tailscale Funnel is the no-Cloudflare option because it exposes public HTTPS on the machine's Tailscale DNS name.

Detect the server's Tailscale DNS name:

```bash
TAILSCALE_FUNNEL_HOST="$(tailscale status --json | jq -r '.Self.DNSName' | sed 's/\.$//')"
printf '%s\n' "$TAILSCALE_FUNNEL_HOST"
```

Rotate the secret path whenever it has been pasted into chat, logs, tickets, or screenshots:

```bash
MCP_PUBLIC_PATH_PREFIX="/mcp-$(openssl rand -hex 32)"
```

Write the local deployment env file with private permissions:

```bash
umask 077
cat > .env.mcp <<EOF
MUNINN_MCP_HOST=${TAILSCALE_FUNNEL_HOST}
MCP_PUBLIC_PATH_PREFIX=${MCP_PUBLIC_PATH_PREFIX}
PUBLIC_BASE_URL=https://${TAILSCALE_FUNNEL_HOST}${MCP_PUBLIC_PATH_PREFIX}
MUNINN_BASE_URL=http://friday-muninn-1:8000
EOF
chmod 600 .env.mcp
```

Deploy the bridge with the rotated host/path values:

```bash
docker compose --env-file .env.mcp -f docker-compose.mcp.yml up -d --build
```

Start Funnel to local Traefik HTTP:

```bash
sudo tailscale funnel --bg --https=443 http://127.0.0.1:80
```

If Tailscale reports `Funnel is not enabled on your tailnet`, enable Funnel in the Tailscale admin console using the URL printed by the CLI, then rerun the same command.

If the installed Tailscale CLI rejects that target form, check:

```bash
tailscale funnel --help
```

Use the equivalent supported syntax that exposes local Traefik HTTP on `127.0.0.1:80`. Do not funnel directly to raw Muninn.

Check Funnel status:

```bash
tailscale funnel status
```

ChatGPT MCP URL format:

```text
https://<tailscale-funnel-host>/mcp-<long-secret>/mcp
```

Raw endpoint smoke:

```bash
curl -i "https://${TAILSCALE_FUNNEL_HOST}${MCP_PUBLIC_PATH_PREFIX}/mcp"
```

Good raw-curl outcomes are a FastMCP `406`, MCP/protocol-style `400`, or `405`. Bad outcomes are Traefik `404`, `502`, TLS failure, or timeout.

MCP SDK smoke:

```bash
python apps/muninn_mcp/smoke_test.py "https://${TAILSCALE_FUNNEL_HOST}${MCP_PUBLIC_PATH_PREFIX}/mcp"
```

The smoke test should list exactly these tools:

- `search`
- `fetch`
- `search_memory`
- `fetch_memory`
- `rehydrate_project`
- `stage_memory_candidates`
- `list_pending_memory`
- `confirm_memory_candidates`

The secret path remains a private-prototype control. Staged writes still require explicit review and `confirm_memory_candidates` still requires the exact phrase `CONFIRM MUNINN WRITE`. OAuth or stronger authentication remains future hardening.

## Cloudflare Tunnel Note

The inspected Lex deployment also uses Cloudflared for public TLS with routes in `/mnt/data/Lex/cloudflared/config.yml`. If that remains the active public ingress, add a Cloudflared ingress route equivalent to the Traefik route and make sure the tunnel container can reach `muninn-mcp:8000` on a shared Docker network. Keep the public URL format the same:

```text
https://<host>/mcp-<long-secret>/mcp
```

Do not commit tunnel credentials or secret path values.

## MCP SDK Smoke Test

After the container is reachable:

```bash
python apps/muninn_mcp/smoke_test.py https://<host>/mcp-<long-secret>/mcp
```

The smoke test:

1. Connects to the streamable HTTP MCP endpoint.
2. Initializes a session.
3. Lists tools.
4. Asserts expected tools exist.
5. Asserts forbidden tool names do not exist.
6. Calls `search` with query `Mimir`.
7. Calls `rehydrate_project` with project `Mimir`.
8. Calls `list_pending_memory`.

## ChatGPT Setup

1. Enable Developer Mode in ChatGPT.
2. Create a custom app / MCP connector.
3. Name it `Muninn Memory`.
4. Use MCP URL:

```text
https://<host>/mcp-<long-secret>/mcp
```

Test prompt:

```text
Use Muninn Memory to rehydrate the Mimir project. Focus on durable decisions around Muninn vs Mimir, world-state, and MCP integration.
```

Write/staging test prompt:

```text
Use Muninn Memory to stage a memory candidate summarizing this decision: Muninn is durable project/user memory, while Mimir is repository world-state. Do not confirm it yet.
```

Confirm test prompt:

```text
Use Muninn Memory to list pending memory candidates. Then confirm candidate <id> with confirmation phrase CONFIRM MUNINN WRITE.
```

## Muninn Host Binding Hardening

The currently running Muninn container exposes `0.0.0.0:18000->8000`. The MCP bridge does not need that host port because it uses `http://friday-muninn-1:8000` on `friday_net`.

When local workflows have been checked, prefer changing the Friday compose port binding to one of:

```yaml
ports:
  - "127.0.0.1:${FRIDAY_HOST_MUNINN_PORT:-18000}:8000"
```

or remove the host port entirely if no local host workflow depends on it.

## Limitations

- No OAuth or per-user auth is implemented yet.
- The long path prefix is a private-prototype control, not a durable authorization model.
- `fetch` has no direct get-by-id Muninn route; it searches by id and returns only exact matches.
- Staged-write provenance is encoded into the currently deployed Muninn `Provenance` schema instead of sending arbitrary extra fields.
