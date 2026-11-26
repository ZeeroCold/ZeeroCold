# HORUS V1.3.2 — Codex propose / review / apply

## Purpose
Allow HORUS to obtain a code-change proposal from the existing Codex CLI/App Server while keeping Codex in read-only mode. A separate explicit local command applies a reviewed patch.

## Windows setup
Extract the release ZIP. Open PowerShell in the extracted folder.

Set the exact project directory as the only permitted workspace:
```powershell
$env:HORUS_ALLOWED_WORKSPACES = "D:\Projects\MyApp"
```

Check Codex:
```powershell
python -m horus_autonomy.cli --data-dir .\horus_data codex-status
```

Ask Codex for a proposal:
```powershell
python -m horus_autonomy.cli --data-dir .\horus_data codex-propose --workspace "D:\Projects\MyApp" --prompt "Add validation to the signup form. Do not change unrelated files."
```

Inspect the proposal using its returned ID:
```powershell
python -m horus_autonomy.cli --data-dir .\horus_data patch-show --proposal-id PROPOSAL_ID
```

Apply only after reviewing:
```powershell
python -m horus_autonomy.cli --data-dir .\horus_data patch-apply --proposal-id PROPOSAL_ID --confirm
```

## Safety properties
- Codex App Server remains in `read-only` sandbox.
- Workspace must be inside `HORUS_ALLOWED_WORKSPACES`.
- Proposal generation does not write to the project.
- Apply is a separate explicit user action.
- Existing text files are backed up under `horus_data/backups`.
- The apply operation is recorded in the audit log.
- Deletion, rename, binary, symlink, absolute/traversal path, duplicate target, and context-mismatch patches are rejected.
- No arbitrary shell command or unrestricted filesystem access is introduced.

## Verification
V1.3.2: 29 unit tests passed, plus a CLI integration smoke test for the explicit apply gate and backup creation. A live Codex exchange on the target Windows machine remains to be verified.
