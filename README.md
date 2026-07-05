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

This project is governed by a set of locked decisions covering architecture, infrastructure, compliance, and team workflow. The decision pack is maintained in the captain's private decision repository at `/home/dereklinux/firstmate/data/pred-decisions/` and is read-only to the team. Key decision files:

- `11-repo-structure.md` — Repo boundaries, CI/CD expectations, branch protection
- `09-memoria-plan.md` — Thesis chapter map, ownership, page budget, writing schedule
- `07-academic-compliance.md` — Compliance requirements and validation gates
- Full pack available in the decision repository

## License

MIT License. See `LICENSE` file.
