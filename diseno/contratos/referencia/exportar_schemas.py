"""Exporta los esquemas v2 desde sus modelos de referencia."""

import json
from pathlib import Path

from modelos_v2 import DOCUMENTS


def main() -> None:
    destination = Path(__file__).resolve().parents[1] / "schemas/v2"
    destination.mkdir(parents=True, exist_ok=True)
    for name, model in DOCUMENTS.items():
        schema = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$id": f"pred-contrato/v2/{name}.schema.json",
            "x-contract-version": "2.0.0",
            **model.model_json_schema(),
        }
        (destination / f"{name}.schema.json").write_text(
            json.dumps(schema, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
    print(f"v2: {len(DOCUMENTS)} esquemas exportados")


if __name__ == "__main__":
    main()
