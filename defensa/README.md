# Defense Evidence Pack (Defensa)

This folder holds the reproducible evidence bundle and checklist for the thesis defense.

## Contents Checklist

The defense pack must include:

- **Reproducible Run Bundle** — Complete steps to re-run the pipeline end-to-end (data, training, evaluation) on the jury's hardware; includes environment spec, data URLs, and seed values for determinism
  
- **Golden-Number Output** — Benchmark results, metrics tables, and decision matrices (DM/HLN) frozen at the final evaluation state; exported from the evaluation layer

- **Coverage Report** — Unit test and integration test coverage report (≥80% floor per G4); snapshot of the CI/CD status at submission time

- **Errata Register** — Complete list of specification corrections (SRS v1.1 errata), with resolution for each (whether incorporated into design or documented as a threat to validity in the conclusions)

- **Demo Script** — Step-by-step walkthrough for the live demonstration: scenario, expected outputs, and fallback static screenshots if interaction fails

- **Cascade Diagram** — Visual representation of the 4-layer architecture (ingesta/caracterización, modelamiento, evaluación, validación retrospectiva) showing data and decision flow

## Assembly Schedule

The defense pack is assembled in Sprint 6 after final evaluation results are frozen. All artifacts are collected and cross-checked against the checklist before submission.

## References

- Decision pack 11: `11-repo-structure.md` — repo structure and CI/CD expectations
- Decision pack 04: `04-validation-alerts.md` — validation layer requirements (feeds reproducible run)
- Decision pack 03: `03-evaluation-layer.md` — metrics and evaluation protocol
