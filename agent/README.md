# HORUS Codex Bridge (read-only) — implementation checkpoint

This directory contains the first bounded Codex App Server bridge implementation.

## Requirements
- Windows or another supported local environment with Python 3.10+
- Existing Codex CLI installation and user sign-in
- No copied credentials and no paid API key required by this adapter

## Configure allowed project roots

Windows PowerShell:
```powershell
$env:HORUS_ALLOWED_WORKSPACES = "D:\chat program\SS;C:\HORUS"
```

Check CLI/login:
```powershell
python -c "from agent.codex_bridge import CodexAppServerBridge; print(CodexAppServerBridge().status())"
```

The distributable HORUS package exposes this through `codex-status` and the `codex_readonly` task tool.

## Security properties
- Uses `codex app-server` over stdio JSONL.
- No public WebSocket listener.
- Enforces configured workspace roots.
- Starts Codex threads in read-only sandbox.
- Declines every server-initiated approval request in unattended operation.
- Never reads or exports credential files.

## Current limits
- This is an initial read-only inspection bridge.
- It does not authorize Codex file writes.
- A live connection must be verified on the target Windows machine.
- Do not describe the bridge as fully connected until that test passes.
