# pred-docs

**PRED** — *Plataforma de Evaluación y Recomendación de modelos de Demanda*

This repository holds academic documentation, thesis materials, and project governance for the PRED capstone project. It is part of a three-repo fleet:

- `pred-engine` — Pure Python modeling and evaluation library
- `pred-platform` — FastAPI/Jinja/HTMX deliverable product
- `pred-docs` — This repo: thesis writing coordination, sprint records, and defense evidence

## Folder Map

| Folder | Purpose |
|--------|---------|
| `memoria/` | Thesis writing coordination: Overleaf exports, chapter notes, development log (`bitacora-vi.md`) feeding Chapter VI |
| `actas/` | Sprint review minutes (one file per sprint: `S0-acta.md`, `S1-acta.md`, etc.) |
| `defensa/` | Defense evidence pack: reproducible bundle, golden outputs, coverage report, errata register, demo script, architecture diagram |

## Engineering Decisions

The project's architecture, team workflow, evaluation protocol, and validation scope are documented in the Software Requirements Specification (SRS) and reflected throughout the team's thesis memoria as those documents are formalized. Specific decisions on branch protection, CI/CD expectations, and chapter ownership are documented in the team's internal engineering log and traced in the thesis narrative.

## License

MIT License. See `LICENSE` file.
