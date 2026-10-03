"""Verifica que los enlaces relativos de los documentos Markdown apunten a archivos existentes."""
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote

ENLACE = re.compile(r"!?\[[^\]]*\]\(\s*(<[^>]+>|[^)\s]+)")
fallos = 0

archivos = subprocess.run(["git", "ls-files", "-z", "*.md"], capture_output=True, text=True, check=True).stdout.split("\0")[:-1]
for archivo in archivos:
    en_codigo = False
    for n, linea in enumerate(Path(archivo).read_text(encoding="utf-8").splitlines(), 1):
        if linea.lstrip().startswith(("```", "~~~")):
            en_codigo = not en_codigo
        if en_codigo:
            continue
        for destino in ENLACE.findall(re.sub(r"`[^`]*`", "", linea)):
            destino = destino.strip("<>")
            if re.match(r"[a-z][a-z0-9+.-]*:|#|/", destino, re.I):
                continue
            ruta = unquote(destino.split("#")[0].split("?")[0])
            if ruta and not (Path(archivo).parent / ruta).exists():
                print(f"::error file={archivo},line={n}::enlace roto: {destino}")
                fallos += 1

sys.exit(1 if fallos else 0)
