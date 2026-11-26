"""Read-only discovery of common local PHP stacks; never starts/stops services."""
from __future__ import annotations
import os,shutil,subprocess,json
from pathlib import Path
CANDIDATES=[r"C:\FreeLAMP",r"C:\FreeLAMP64",r"C:\Program Files\FreeLAMP",r"C:\xampp",r"C:\wamp64",r"C:\laragon",r"C:\UniServerZ"]
def inspect():
    found=[]
    for raw in CANDIDATES:
        p=Path(raw)
        if p.exists():
            found.append({"path":str(p),"apache":(p/"apache").exists() or (p/"Apache").exists(),"php":(p/"php").exists() or (p/"PHP").exists(),"mysql":(p/"mysql").exists() or (p/"mariadb").exists()})
    commands={name:shutil.which(name) for name in ("php","mysql","mariadb","httpd","mysqld")}
    services=[]
    if os.name=="nt":
        try:
            result=subprocess.run(["powershell","-NoProfile","-Command","Get-Service | Where-Object {$_.Name -match 'apache|mysql|maria|wamp|xampp|lamp'} | Select-Object Name,Status,StartType | ConvertTo-Json -Compress"],capture_output=True,text=True,timeout=8)
            if result.returncode==0 and result.stdout.strip():
                value=json.loads(result.stdout); services=value if isinstance(value,list) else [value]
        except Exception: pass
    return {"installations":found,"commands":commands,"services":services,"inspection_only":True}
