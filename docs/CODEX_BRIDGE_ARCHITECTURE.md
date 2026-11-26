# HORUS ↔ Codex Integration Architecture

**Status:** Architecture proposal — not implemented or connected  
**Date:** 2026-11-26  
**Repository boundary:** HORUS only. SPARK remains an independent project.

## 1. Decision

HORUS should reuse the user's already-established Codex installation and authentication inside the SPARK workshop platform where technically and explicitly authorized. Do not install a second Codex runtime, create a second paid API dependency, or copy SPARK source/data into HORUS.

Codex is the engineering execution runtime. HORUS remains the orchestration, context, evidence, policy, and completion layer.

## 2. Official integration surface

Use **Codex App Server** when Codex is embedded as a persistent agent inside an application. It exposes JSON-RPC lifecycle operations for initialization, threads, turns, streamed events, approvals, and interruption. The default transport is stdio (JSONL). The documented WebSocket listener is experimental/unsupported for production; do not expose it directly to the public internet.

Use the **Codex SDK** for bounded non-interactive jobs or CI automation. Do not build new integrations around the removed `codex mcp-server` command.

Official references:
- https://learn.chatgpt.com/docs/app-server
- https://learn.chatgpt.com/docs/codex-sdk
- https://developers.openai.com/blog/codex-as-a-platform

## 3. Target architecture

```text
HORUS (policy + project context + evidence + completion gate)
        |
        | approved, typed engineering job
        v
HORUS Codex Adapter (local companion service)
        |
        | JSON-RPC over stdio
        v
Existing Codex App Server in SPARK platform
        |
        v
Selected workspace / explicitly authorized project directory
```

The adapter is a narrow job broker, not a generic remote shell. It must not grant HORUS unrestricted access to the workshop PC or to every SPARK project.

## 4. Reuse contract

Before implementation, discover the actual Codex integration already present in the workshop platform:
- executable/launch method and version;
- app-server or SDK transport;
- authentication/session ownership;
- working-directory selection and sandbox policy;
- approval mode and write permissions;
- thread lifecycle and event streaming;
- current allowlist of project roots;
- audit/logging and cancellation behavior.

Reuse the existing process/session only if its owner and lifecycle can safely support a second client. Otherwise use a separate Codex App Server process that reuses the installed CLI and the user's existing sign-in state, without copying credentials.

Do not assume the current SPARK implementation uses App Server merely because it has Codex functionality. Inspect its source before choosing the adapter.

## 5. Adapter API (proposed, not yet implemented)

Expose only typed operations:
- `codex_status`: runtime/version/auth readiness (never return tokens).
- `codex_job_start`: start a bounded engineering task with project ID, task text, and an approved permission profile.
- `codex_job_events`: stream or page task progress and structured results.
- `codex_job_interrupt`: interrupt a running task.
- `codex_job_result`: return summary, changed-file list, test evidence, and unresolved blockers.

No arbitrary shell command, arbitrary path, unrestricted filesystem, or unrestricted network tool is exposed.

## 6. Security and permission profiles

- **Inspect:** read-only project inspection and diagnostics.
- **Propose:** prepare patches/diffs without applying them.
- **Apply-approved:** apply changes only inside an explicitly selected project root after approval.
- **Release:** commit, publish, deploy, or modify external systems only through a separate explicit approval gate.

Fail closed if the project root, task scope, user identity, sandbox, or permission mode is missing or ambiguous. Keep tokens in the existing secure credential store. Never put secrets in GitHub, logs, prompts, or HORUS evidence records.

## 7. ChatGPT connectivity is a separate gate

A local Codex integration inside SPARK does not automatically make Codex callable from this ChatGPT conversation. A callable path requires a supported connected tool/connector or an authenticated, reachable service that the current ChatGPT account and client can actually connect to.

Do not assume a custom MCP connection is available on every ChatGPT plan. Verify current plan and client support before depending on it. Until then, the GitHub connector and installed HORUS skills remain the tools callable in this chat; the Codex bridge remains an external integration target.

## 8. Acceptance gates

1. Inspect the real SPARK platform Codex implementation and record its transport and permissions.
2. Confirm no SPARK data or source is copied into the HORUS repository.
3. Build the adapter as a separate local companion, reusing the existing Codex runtime/sign-in where safe.
4. Unit-test JSON-RPC lifecycle, malformed responses, timeouts, cancellation, and permission enforcement.
5. Verify a harmless read-only job against a dedicated test workspace.
6. Verify a proposed diff without applying it.
7. Verify write access is blocked unless the explicit apply-approved gate is satisfied.
8. Verify logs redact secrets and record task ID, project ID, permission profile, timestamps, changed files, and test results.
9. Separately verify whether ChatGPT can call the adapter in the user's current plan/client.

## 9. Current evidence state

| Capability | State |
|---|---|
| Codex exists in the user's SPARK workshop platform | User-confirmed; implementation not inspected here |
| Official App Server / SDK integration approach | Documented by OpenAI |
| HORUS orchestration and evidence skills | Present in private HORUS plugin v1.1.0 |
| HORUS MCP source and CI tests | Present; CI-tested |
| HORUS Codex adapter | Not implemented |
| SPARK-to-HORUS bridge | Not connected or verified |
| Codex callable from this ChatGPT conversation | Not established |

## 10. Non-goals

- Do not redesign or rebuild SPARK's Codex integration.
- Do not merge SPARK and HORUS repositories or memory stores.
- Do not install another local model or add paid API usage.
- Do not expose Codex App Server's experimental WebSocket listener publicly.
- Do not claim deployment, connection, or successful execution until tested end-to-end.
