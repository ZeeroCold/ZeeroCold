# HORUS Extensions

Versioned source for reusable HORUS capabilities and ChatGPT-facing integrations.

**Project boundary:** this repository is independent of SPARK. Do not place SPARK source, data, credentials, or workflow assumptions here.

## First MCP tool service

See [mcp-tools](mcp-tools/README.md) for the capability registry, task ledger, and evidence log service.

The source is committed, but it is **not yet deployed or connected to ChatGPT**. GitHub hosting alone does not expose code as callable ChatGPT tools. A public HTTPS deployment, persistent storage, and an authenticated MCP connection are still required.

## Security

Never commit API tokens, passwords, private keys, or production data. Use deployment secret storage and a persistent volume for the SQLite database.
