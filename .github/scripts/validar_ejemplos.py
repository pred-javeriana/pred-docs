"""Valida modelos, esquemas publicados y ejemplos de cada version del contrato."""

import importlib.util
import json
import re
import sys
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import SchemaError

BASE = Path(__file__).resolve().parents[2] / "diseno/contratos"
WRAPPER_KEYS = {"$schema", "$id", "x-contract-version"}


def load_models(path: Path):
    name = f"_contrato_{path.stem}"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module.DOCUMENTS


def _invalid_constant(value: str):
    raise ValueError(f"constante no valida en JSON: {value}")


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"), parse_constant=_invalid_constant)


def schema_errors(error):
    if error.context:
        for child in error.context:
            yield from schema_errors(child)
    else:
        location = "/".join(map(str, error.absolute_path)) or "(raiz)"
        yield f"{location}: {error.message}"


def validate_contract(base: Path) -> list[str]:
    versions = {
        p.name for folder in ("schemas", "ejemplos")
        for p in (base / folder).glob("v*") if p.is_dir()
    } | {p.stem.removeprefix("modelos_") for p in (base / "referencia").glob("modelos_v*.py")}
    if not versions:
        return ["no se encontraron versiones del contrato"]
    errors = []
    for version in sorted(versions):
        model_path = base / "referencia" / f"modelos_{version}.py"
        if not model_path.is_file():
            errors.append(f"{version}: faltan modelos de referencia")
            continue
        documents = load_models(model_path)
        if not documents:
            errors.append(f"{version}: no se declararon documentos")
        paths = {p.name.removesuffix(".schema.json"): p
                 for p in (base / "schemas" / version).glob("*.schema.json")}
        if set(paths) != set(documents):
            errors.append(f"{version}: los esquemas no corresponden a DOCUMENTS")
        schemas = {}
        declared_versions = set()
        for name, path in sorted(paths.items()):
            try:
                schema = read_json(path)
                Draft202012Validator.check_schema(schema)
                if schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
                    raise ValueError("el esquema debe declarar Draft 2020-12")
                declared = schema.get("x-contract-version", "")
                if not re.fullmatch(rf"{re.escape(version[1:])}\.[0-9]+\.[0-9]+", declared):
                    raise ValueError("x-contract-version no corresponde a la carpeta mayor")
                declared_versions.add(declared)
                bare = {k: v for k, v in schema.items() if k not in WRAPPER_KEYS}
                if name in documents and bare != documents[name].model_json_schema():
                    errors.append(f"{version}/{path.name}: el esquema difiere del modelo")
                schemas[name] = schema
            except (ValueError, TypeError, OSError, SchemaError) as exc:
                errors.append(f"{version}/{path.name}: {exc}")
        if len(declared_versions) != 1:
            errors.append(f"{version}: los esquemas deben declarar una unica version")
        covered = set()
        examples = sorted((base / "ejemplos" / version).glob("*.json"))
        for path in examples:
            name = path.name.split(".")[0]
            if name not in schemas or name not in documents:
                errors.append(f"{version}/{path.name}: no existe esquema y modelo")
                continue
            covered.add(name)
            try:
                data = read_json(path)
                validator = Draft202012Validator(schemas[name], format_checker=FormatChecker())
                for error in validator.iter_errors(data):
                    errors.extend(f"{version}/{path.name}: {detail}" for detail in schema_errors(error))
                documents[name].model_validate(data)
            except (ValueError, OSError) as exc:
                errors.append(f"{version}/{path.name}: {exc}")
        if covered != set(documents):
            missing = sorted(set(documents) - covered)
            errors.append(f"{version}: faltan ejemplos para {missing}")
    return errors


def main() -> int:
    errors = validate_contract(BASE)
    for error in errors:
        print(f"::error::{error}")
    if not errors:
        print("Modelos, esquemas y ejemplos de todas las versiones son coherentes.")
    return int(bool(errors))


if __name__ == "__main__":
    sys.exit(main())
