# HORUS V1.4 — Sentinel, Memory MCP, FreeLAMP discovery

Sentinel observes worker state and audit integrity and reports alerts only. It does not restart or kill processes.

MemoryMCPClient uses JSON-RPC against the existing HORUS MCP endpoint and only accesses the existing typed task/evidence tools. It requires HORUS_MCP_ENDPOINT and HORUS_API_TOKEN at runtime; no secret is committed.

FreeLAMP probe inspects common installation folders, PATH commands, and matching Windows services. It never starts or stops services.

The distributable V1.4 package passed 36 unit tests in the build environment. This does not prove a live MCP endpoint or FreeLAMP installation on the user's Windows machine.
