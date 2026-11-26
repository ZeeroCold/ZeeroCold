# HORUS MCP Tools — Cloudflare deployment

Cloudflare Workers + D1 port of the Python reference service. Uses only native Worker APIs and the D1 binding.

## Free-plan target
- Workers Free: 100,000 requests/day and 10 ms CPU per request.
- D1 Free: 5 million rows read/day, 100,000 rows written/day, 5 GB total storage, up to 10 databases.
- Exceeding free daily limits causes requests/queries to fail until reset; this project must not upgrade itself or switch to paid billing.

See official pricing: https://developers.cloudflare.com/workers/platform/pricing/

## Deploy (manual account authorization required)
1. Create or sign in to a Cloudflare account and open Workers & Pages.
2. In this folder, install Wrangler locally: `npm install --save-dev wrangler`.
3. Authenticate with `npx wrangler login`.
4. Create the D1 database: `npx wrangler d1 create horus-memory`.
5. Copy the returned database ID into `wrangler.toml` (replace the placeholder).
6. Apply schema: `npx wrangler d1 migrations apply horus-memory --remote`.
7. Set a strong secret: `npx wrangler secret put HORUS_API_TOKEN`.
8. Deploy: `npx wrangler deploy`.
9. Test `https://<worker>.<account>.workers.dev/health`, then use `/mcp` with a Bearer token and Streamable HTTP POST.

No payment method or paid plan should be enabled for this deployment. If the dashboard asks to upgrade or add paid billing, stop and do not proceed.

## ChatGPT connection
Deployment alone does not connect tools to ChatGPT. A compatible MCP app connection must be configured with the deployed HTTPS endpoint and bearer authentication. The existing HORUS skills plugin is separate from this server connection; do not claim the tools are live until they appear in chat and a tool call succeeds.

## Security and limits
- Store `HORUS_API_TOKEN` only as a Worker secret; never commit it.
- D1 binding is persistent storage.
- No shell execution, filesystem access, arbitrary fetch, GitHub write, or autonomous background execution is exposed.
- Free-tier quota exhaustion should fail closed; never upgrade automatically.
