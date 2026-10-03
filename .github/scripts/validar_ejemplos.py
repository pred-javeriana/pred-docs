"""Valida cada ejemplo JSON de v1 contra su esquema (<nombre>.<caso>.json -> <nombre>.schema.json)."""
import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

base = Path("diseno/contratos")
schemas = {p.name.removesuffix(".schema.json"): p for p in (base / "schemas/v1").glob("*.schema.json")}
fallos = 0

for schema_path in schemas.values():
    Draft202012Validator.check_schema(json.loads(schema_path.read_text()))

for ejemplo in sorted((base / "ejemplos/v1").glob("*.json")):
    nombre = ejemplo.name.split(".")[0]
    if nombre not in schemas:
        print(f"::error file={ejemplo}::no existe esquema {nombre}.schema.json para este ejemplo")
        fallos += 1
        continue
    validador = Draft202012Validator(json.loads(schemas[nombre].read_text()))
    for e in validador.iter_errors(json.loads(ejemplo.read_text())):
        ruta = "/".join(map(str, e.absolute_path)) or "(raiz)"
        print(f"::error file={ejemplo}::{ruta}: {e.message} [{schemas[nombre]}]")
        fallos += 1

sys.exit(1 if fallos else 0)
