"""Strict unified-diff validator and approval-gated applier for HORUS."""
from __future__ import annotations
import hashlib, os, re, time, uuid
from pathlib import Path

class PatchError(ValueError):
    pass

def _safe_path(raw: str) -> str:
    raw = raw.strip().split("\\t", 1)[0]
    if raw.startswith(("a/", "b/")): raw = raw[2:]
    if raw == "/dev/null": return raw
    p = Path(raw)
    if p.is_absolute() or re.match(r"^[A-Za-z]:", raw) or raw.startswith("\\\\"):
        raise PatchError("Absolute patch path rejected")
    if any(part in ("..", "") for part in p.parts) or "\\x00" in raw:
        raise PatchError("Path traversal rejected")
    return p.as_posix()

def parse_unified_diff(text: str):
    if len(text.encode("utf-8")) > 1_000_000: raise PatchError("Patch exceeds 1 MB")
    lines = text.replace("\\r\\n","\\n").replace("\\r","\\n").splitlines(keepends=True)
    files=[]; i=0
    while i < len(lines):
        if not lines[i].startswith("--- "): i+=1; continue
        old=_safe_path(lines[i][4:].rstrip("\\n")); i+=1
        if i>=len(lines) or not lines[i].startswith("+++ "): raise PatchError("Missing +++ header")
        new=_safe_path(lines[i][4:].rstrip("\\n")); i+=1
        if old=="/dev/null" and new!="/dev/null": op, rel="create", new
        elif new=="/dev/null": raise PatchError("Deletion is prohibited")
        elif old==new: op, rel="modify", new
        else: raise PatchError("Rename/move is prohibited")
        hunks=[]
        while i<len(lines) and not lines[i].startswith("--- "):
            if lines[i].startswith(("diff ","index ","new file mode","deleted file mode","rename ","Binary files")):
                raise PatchError("Git metadata, rename and binary patches are prohibited")
            if not lines[i].startswith("@@"): i+=1; continue
            m=re.match(r"^@@ -(\\d+)(?:,(\\d+))? \\+(\\d+)(?:,(\\d+))? @@",lines[i])
            if not m: raise PatchError("Malformed hunk header")
            old_start=int(m.group(1)); old_n=int(m.group(2) or 1); new_n=int(m.group(4) or 1)
            i+=1; body=[]; seen_old=seen_new=0
            while i<len(lines) and (seen_old<old_n or seen_new<new_n):
                line=lines[i]
                if line.startswith("\\\\ No newline"): i+=1; continue
                if not line or line[0] not in " +-": raise PatchError("Malformed hunk body")
                body.append(line); seen_old += line[0] in " -"; seen_new += line[0] in " +"; i+=1
            if (seen_old,seen_new)!=(old_n,new_n): raise PatchError("Hunk count mismatch")
            hunks.append((old_start,body))
        if not hunks: raise PatchError("File section has no hunks")
        files.append({"path":rel,"operation":op,"hunks":hunks})
    if not files: raise PatchError("No unified diff found")
    paths=[f["path"] for f in files]
    if len(paths)!=len(set(paths)): raise PatchError("Duplicate target path")
    return files

def apply_unified_diff(workspace: str, diff_text: str, backup_root: str):
    root=Path(workspace).resolve(); specs=parse_unified_diff(diff_text); staged=[]
    for spec in specs:
        target=(root/spec["path"]).resolve()
        if target!=root and root not in target.parents: raise PatchError("Target escapes workspace")
        cursor=root
        for part in Path(spec["path"]).parts:
            cursor=cursor/part
            if cursor.is_symlink(): raise PatchError("Symlink target rejected")
        exists=target.exists()
        if spec["operation"]=="modify" and not exists: raise PatchError("Modify target missing")
        if spec["operation"]=="create" and exists: raise PatchError("Create target already exists")
        original=target.read_text(encoding="utf-8") if exists else ""
        src=original.splitlines(keepends=True); out=[]; pos=0
        for old_start,body in spec["hunks"]:
            start=max(old_start-1,0)
            if start<pos or start>len(src): raise PatchError("Invalid hunk offset")
            out.extend(src[pos:start]); pos=start
            for line in body:
                mark, value=line[0],line[1:]
                if mark==" ":
                    if pos>=len(src) or src[pos].rstrip("\\n")!=value.rstrip("\\n"): raise PatchError("Context mismatch")
                    out.append(src[pos]); pos+=1
                elif mark=="-":
                    if pos>=len(src) or src[pos].rstrip("\\n")!=value.rstrip("\\n"): raise PatchError("Removal mismatch")
                    pos+=1
                else: out.append(value if value.endswith("\\n") else value+"\\n")
        out.extend(src[pos:]); content="".join(out)
        if len(content.encode("utf-8"))>5_000_000: raise PatchError("Target file exceeds 5 MB")
        staged.append((target,content,original if exists else None))
    backup_base=Path(backup_root).resolve()/time.strftime("%Y%m%d_%H%M%S")/uuid.uuid4().hex[:8]
    changed=[]
    for target,content,original in staged:
        rel=target.relative_to(root).as_posix()
        if original is not None:
            backup=backup_base/rel; backup.parent.mkdir(parents=True,exist_ok=True); backup.write_text(original,encoding="utf-8")
        target.parent.mkdir(parents=True,exist_ok=True)
        tmp=target.with_name(target.name+".horus-tmp"); tmp.write_text(content,encoding="utf-8"); os.replace(tmp,target)
        changed.append({"path":rel,"operation":"modified" if original is not None else "created",
                        "sha256":hashlib.sha256(content.encode("utf-8")).hexdigest()})
    return {"workspace":str(root),"changed_files":changed,"file_count":len(changed),
            "backup_directory":str(backup_base) if any(x[2] is not None for x in staged) else None}
