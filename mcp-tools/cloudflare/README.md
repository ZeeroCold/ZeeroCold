# HORUS MCP Worker

Cloudflare Worker endpoint for the HORUS capability, task, and evidence tools.

## Runtime

- Worker: `horus-mcp-tools`
- MCP endpoint: `https://horus-mcp-tools.zeerocoold0007.workers.dev/mcp`
- Health endpoint: `https://horus-mcp-tools.zeerocoold0007.workers.dev/health`
- Storage: Cloudflare D1 binding `DB`, database `horus-memory`
- Authentication: `Authorization: Bearer <HORUS_API_TOKEN>`
- MCP protocol versions: `2026-07-28` (current request-metadata transport) plus legacy compatibility for `2025-03-26` and `2025-11-25`
- Tools: capability upsert/list, task upsert/get, evidence append/list

## Cloudflare configuration

Set `HORUS_API_TOKEN` as a Worker Secret. Never commit it to Git.
Optionally set `ALLOWED_ORIGINS` as a comma-separated allowlist for browser-based clients. Requests without an Origin header are allowed for server-to-server MCP clients; requests with an Origin must match the allowlist.

The D1 tables were initially created through the Cloudflare D1 Console. The idempotent migration in `migrations/0001_init.sql` keeps the schema reproducible for fresh deployments. It does not need to be manually re-run against the existing database.

## Local checks

```sh
npm install
npm run check
npm test
```

## Manual protocol smoke test

Set the secret in your local shell without placing it in source control:

```sh
export HORUS_API_TOKEN='your-secret'
curl -i https://horus-mcp-tools.zeerocoold0007.workers.dev/mcp \
  -H "Authorization: Bearer $HORUS_API_TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  --data '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"smoke-test","version":"1.0"}}}'
```

Then call `tools/list` using a separate POST with the same headers and body `{"jsonrpc":"2.0","id":2,"method":"tools/list"}`.

## Security and scope

This server only records and retrieves capability assessments, task states, and evidence. It does not execute shell commands, access arbitrary files, perform arbitrary network requests, or write to GitHub. A stored assessment is not proof that a capability is live or independently verified.

## Free-plan policy

The design targets Cloudflare Workers Free and D1 Free. Do not enable paid billing or upgrade automatically. If a free quota is exhausted, requests may fail until reset; stop and reassess rather than enabling a paid plan.
