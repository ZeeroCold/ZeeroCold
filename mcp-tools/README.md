# HORUS MCP Tools

A minimal, stdlib-only MCP Streamable HTTP service providing six callable tools for HORUS after deployment and connection.

## Tools
- `horus_capability_upsert` and `horus_capability_list`: record capability assessments. A recorded status is not proof of live availability.
- `horus_task_upsert` and `horus_task_get`: track task state. This is not a background executor.
- `horus_evidence_append` and `horus_evidence_list`: append and retrieve source-tagged evidence.

## Run
Python 3.10+; runtime uses only the standard library.

```bash
export HORUS_API_TOKEN="use-a-long-random-secret"
export HORUS_DB_PATH="./data/horus.sqlite3"
python server.py
```

- Health check: `GET /health`
- MCP endpoint: `POST /mcp`
- Authentication: `Authorization: Bearer <HORUS_API_TOKEN>`

For Docker, pass the token as a deployment secret and mount persistent storage at `/app/data`.

## ChatGPT connection status
This source is not callable from ChatGPT merely because it is on GitHub. It still needs:
1. Deployment to a public HTTPS host.
2. Persistent storage for the SQLite database.
3. An MCP connection in ChatGPT configured for the deployed `/mcp` endpoint and bearer authentication.
4. A live tool-list and tool-call verification.

No hosting provider has been selected and no server has been deployed yet.

## Safety
- No shell execution, arbitrary file access, arbitrary network fetch, or GitHub write tool is exposed.
- The server records structured data only.
- Capability status records must be backed by separate evidence.
- It does not approve sensitive actions, execute background tasks, or modify model behavior.
- Never commit the bearer token or database file.

## Tests
```bash
python -m unittest discover -s tests -v
python -m py_compile server.py tests/test_server.py
```
