# HORUS ↔ Codex Integration Architecture

**Status:** Partial implementation — read-only Codex App Server bridge source committed; live Windows connection not yet verified  
**Date:** 2026-11-26  
**Repository boundary:** HORUS only. SPARK remains an independent project.

## 1. Decision

HORUS should reuse the user's already-established Codex installation and authentication inside the SPARK workshop platform where technically and explicitly authorized. Do not install a second Codex runtime, create a second paid API dependency, or copy SPARK source/data into HORUS.

Codex is the engineering execution runtime. HORUS remains the orchestration, context, evidence, policy, and completion layer.

FreeLAMP is included as a separate local PHP/MySQL application runtime and test environment. It is not a substitute for Codex and is not assumed to expose an API or MCP endpoint.

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
        |
        | application files in designated local workspace
        v
FreeLAMP Runtime (PHP + web server + MySQL, as installed/configured)
        |
        | localhost HTTP/browser tests and runtime diagnostics
        v
HORUS Evidence Ledger + Completion Gate
```

Logical responsibilities:
- **HORUS:** orchestration, task policy, context, approvals, evidence collection, and completion decision.
- **Codex Adapter:** narrow broker between HORUS and the existing Codex runtime.
- **Codex:** code inspection, implementation, and bounded engineering execution.
- **FreeLAMP connector/runner:** starts or inspects only the authorized local web/database services and gathers runtime test results.
- **Browser/HTTP test harness:** validates the application through localhost routes; it does not grant arbitrary network access.

The adapter and FreeLAMP connector are separate logical components. HORUS must not gain a generic shell or unrestricted local-machine interface by combining them.

## 4. FreeLAMP runtime contract (proposed, not yet inspected)

Before implementation, inspect the actual FreeLAMP installation and establish:
- product/distribution and version;
- web server and PHP versions/modules;
- MySQL/MariaDB version and service management method;
- configured document roots and virtual hosts;
- ports and localhost binding behavior;
- project-specific database provisioning and test-data isolation;
- logs, health checks, startup/shutdown behavior, and failure recovery.

Rules:
- Do not assume FreeLAMP exposes a stable API, MCP server, CLI contract, or remote control endpoint until verified.
- Bind development services to localhost by default; do not expose them publicly.
- Restrict document roots to explicitly selected project workspaces.
- Do not auto-start services at boot or change global machine settings without separate authorization.
- Do not execute arbitrary commands or accept arbitrary paths from HORUS.
- Keep credentials out of source control, prompts, test output, and evidence records. Use local secret/config stores and redact logs.
- Use isolated test databases and non-production data. Never run destructive migrations against a production database as part of routine tests.

Intended workflow: Codex edits code in an approved workspace; FreeLAMP serves that application locally; browser/HTTP tests exercise it; HORUS records the exact test evidence and evaluates the completion gate.

## 5. Reuse contract

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

## 6. Adapter API (proposed, not yet implemented)

Expose only typed operations:
- `codex_status`: runtime/version/auth readiness (never return tokens).
- `codex_job_start`: start a bounded engineering task with project ID, task text, and an approved permission profile.
- `codex_job_events`: stream or page task progress and structured results.
- `codex_job_interrupt`: interrupt a running task.
- `codex_job_result`: return summary, changed-file list, test evidence, and unresolved blockers.

FreeLAMP operations, if supported by the inspected installation, should be separately typed and narrowly scoped, for example:
- `runtime_status`: report configured local service health and versions.
- `project_serve`: serve only an approved project root using an approved local host/port profile.
- `project_test`: run a predefined HTTP/browser test suite against the local project.
- `runtime_logs`: return bounded, redacted diagnostics.

No arbitrary shell command, arbitrary path, unrestricted filesystem, or unrestricted network tool is exposed.

## 7. Security and permission profiles

- **Inspect:** read-only project inspection and diagnostics.
- **Propose:** prepare patches/diffs without applying them.
- **Apply-approved:** apply changes only inside an explicitly selected project root after approval.
- **Release:** commit, publish, deploy, or modify external systems only through a separate explicit approval gate.

Fail closed if the project root, task scope, user identity, sandbox, or permission mode is missing or ambiguous. Keep tokens in the existing secure credential store. Never put secrets in GitHub, logs, prompts, or HORUS evidence records.

Local runtime authority is separately bounded: inspect service status; start/stop only explicitly approved development services; serve only approved project roots; use isolated test databases; never expose local services publicly by default.

## 8. ChatGPT connectivity is a separate gate

A local Codex integration inside SPARK does not automatically make Codex callable from this ChatGPT conversation. A callable path requires a supported connected tool/connector or an authenticated, reachable service that the current ChatGPT account and client can actually connect to.

Do not assume a custom MCP connection is available on every ChatGPT plan. Verify current plan and client support before depending on it. Until then, the GitHub connector and installed HORUS skills remain the tools callable in this chat; the Codex bridge remains an external integration target.

## 9. Acceptance gates

1. Inspect the real SPARK platform Codex implementation and record its transport and permissions.
2. Inspect the actual FreeLAMP installation/configuration and identify supported local control surfaces.
3. Confirm no SPARK data or source is copied into the HORUS repository.
4. Build the adapter as a separate local companion, reusing the existing Codex runtime/sign-in where safe.
5. Build a separate least-privilege FreeLAMP runner/connector only for verified interfaces.
6. Unit-test JSON-RPC lifecycle, malformed responses, timeouts, cancellation, and permission enforcement.
7. Verify a harmless read-only job against a dedicated test workspace.
8. Verify a proposed diff without applying it.
9. Verify write access is blocked unless the explicit apply-approved gate is satisfied.
10. Verify a local PHP application can be served and tested using an isolated test database.
11. Verify local services remain private to localhost and unauthorized paths/commands are rejected.
12. Verify logs redact secrets and record task ID, project ID, permission profile, timestamps, changed files, and test results.
13. Separately verify whether ChatGPT can call the adapter in the user's current plan/client.

## 10. SPARK ONE V1.0.2 source audit (uploaded package)

The uploaded archive contains SPARK ONE V1.0.2 and workshop platform source V1.3.64. The actual Codex integration is `workshop_platform/codex_client.py`:
- It launches the installed Codex CLI with `app-server` through a local Qt `QProcess`; JSON-RPC messages are exchanged over the process stdin/stdout.
- It resolves the Codex executable from `SPARK_CODEX_BIN`, known Windows install paths, or PATH; it checks `codex --version` and `codex login status`.
- New threads are started with `sandbox=read-only`, `approvalPolicy=on-request`, and `cwd` set to the platform application directory. Existing thread IDs are stored in a local JSON state file.
- The client prompts the user before accepting command-execution approval requests. The code comments and system instructions state that file-change/elevation approvals are not granted. This is an embedded UI approval flow, not a safe external-client API.
- The code supplies Codex with a live context snapshot from `workshop_summary()`, `search_orders('', limit=10)`, and `approved_workshop_memory(limit=50)`. This can include customer names and phone numbers from recent orders. Therefore, despite older V1.3.1 release notes saying customer/order data is not automatically sent, the inspected V1.3.64 source does attach recent-order context to each Codex message. Review/minimize/redact this context before extending access to HORUS.
- The archive's SPARK ONE documentation says workshop and accounts databases are separate, fresh data stores under `%LOCALAPPDATA%\\SPARK ONE`; it does not establish a FreeLAMP dependency.

Verification performed against the extracted uploaded archive:
- Focused Codex source tests: 13 passed.
- Full packaged test suite: 121 passed.
- These are source-level tests in this environment. They do not prove Windows GUI behavior, a live Codex login, real App Server connectivity, or FreeLAMP integration.

Key integration conclusion: HORUS should not connect as a second client to SPARK's existing QProcess/session without a deliberate supported interface. Prefer a separate narrow local adapter that starts its own bounded Codex App Server process, reuses the user's installed CLI/sign-in without copying credentials, and has an explicit project-root and permission allowlist. Do not add an external client to SPARK's current thread/session by sharing its thread ID alone.

## 11. HORUS Autonomous Agent V1.2 — implementation update

A runnable, standard-library-only supervised worker package was built separately from SPARK:
- Durable SQLite task queue with queued/running/pending-approval/completed/failed/cancelled states.
- Foreground worker loop with start/stop lifecycle and restart recovery for interrupted tasks.
- CLI for submit, serve, status, list, approve, cancel, human takeover, and resume.
- Explicit trusted-handler registry; proposed dynamic tools remain non-executable.
- Approval gate for sensitive, external-write, and destructive risk classes.
- Persisted human takeover control across separate CLI invocations, bounded read-only workspace listing, and hash-chained audit records.
- No paid API, network listener, arbitrary shell, or arbitrary code execution.

Verification:
- V1.1 core tests plus V1.2 worker tests: 18 passed, including cross-process persistent human takeover.
- CLI smoke test: task submitted, processed to completed, returned expected result, and audit integrity verified.
- This proves the local reference worker package in this execution environment. It does not prove deployment on the user's Windows PC or integration with HORUS MEMORY, Codex App Server, FreeLAMP, or ChatGPT connectors.

Package artifact: `HORUS_AUTONOMOUS_AGENT_V1.2.zip` (delivered in the current conversation).

## 12. Current evidence state

| Capability | State |
|---|---|
| Codex exists in the user's SPARK workshop platform | Source-verified in uploaded SPARK ONE V1.0.2 package |
| Codex transport and read-only policy | Source-verified; live Windows behavior not tested |
| SPARK forwards recent-order and approved-memory context to Codex | Source-verified; includes potentially identifying customer fields |
| FreeLAMP is available to the user | User-confirmed; not present or configured in uploaded package |
| HORUS V1.1 autonomy core | Implemented and unit-tested as isolated reference package |
| HORUS V1.2 persistent worker and CLI | Implemented; 18 tests, compile check, and CLI smoke test passed in this environment |
| HORUS V1.2 deployed on user's Windows PC | Not yet verified |
| HORUS MEMORY / VIRTUAL OFFICE integration | Not implemented |
| HORUS Codex adapter | Not implemented |
| FreeLAMP connector/runner | Not implemented or verified |
| SPARK-to-HORUS bridge | Not connected or verified |
| Codex callable from this ChatGPT conversation | Not established |

## 13. Non-goals

- Do not redesign or rebuild SPARK's Codex integration.
- Do not merge SPARK and HORUS repositories or memory stores.
- Do not install another local model or add paid API usage.
- Do not expose Codex App Server's experimental WebSocket listener publicly.
- Do not expose FreeLAMP services publicly by default.
- Do not claim deployment, connection, or successful execution until tested end-to-end.


## 12. V1.3.2 — Codex propose / review / apply gate

A strict unified-diff application layer is being added as a separate HORUS component. Codex remains in read-only mode and is asked to return a unified diff. HORUS validates the patch before storing a proposal. No workspace file changes during proposal generation.

The apply operation is a separate explicit user command and is not triggered by Codex. The applier supports text-file creation and modification only; it rejects deletion, rename, binary patches, absolute paths, traversal, symlinks, duplicate targets, oversized content, and context mismatches. Existing files are backed up under the HORUS data directory. Each successful application is written to the audit log with proposal ID and changed-file hashes.

Local tests currently cover successful modification with backup, file creation, traversal rejection, deletion rejection, context mismatch, and duplicate target rejection. These tests do not establish a live Codex App Server session on the user's Windows device.

This design intentionally does not grant Codex unrestricted write access. It provides a reviewable diff and a separate approval-controlled application step.
