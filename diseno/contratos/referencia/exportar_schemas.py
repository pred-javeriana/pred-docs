"""Exporta los esquemas v1 y v2 desde sus modelos de referencia."""

import importlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))


def main() -> None:
    base = HERE.parent / "schemas"
    for folder, module_name, version in (
        ("v1", "modelos_v1", "1.1.0"),
        ("v2", "modelos_v2", "2.2.0"),
    ):
        destination = base / folder
        destination.mkdir(parents=True, exist_ok=True)
        module = importlib.import_module(module_name)
        documents = module.DOCUMENTS
        for name, model in documents.items():
            schema = {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "$id": f"pred-contrato/{folder}/{name}.schema.json",
                "x-contract-version": version,
                **model.model_json_schema(),
            }
            (destination / f"{name}.schema.json").write_text(
                json.dumps(schema, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
            )
        print(f"{folder}: {len(documents)} esquemas exportados")


if __name__ == "__main__":
    main()
