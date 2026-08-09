# PRED — Product Requirements Document (Design Context)

**PRED** — *Plataforma de Evaluación y Recomendación de modelos de Demanda*.

This document exists to brief a design system / UI generation tool on what PRED
is, who uses it, and what constraints its interface must respect. It is not a
screen-by-screen spec — it's the context a designer would want before proposing
a visual language.

## 1. What PRED is

PRED is a fully local, offline demand-forecasting benchmarking platform. A
company exports its historical transaction data; PRED ingests it, characterizes
every product (SKU) series, benchmarks several forecasting model families
against each series under one controlled experimental protocol, picks a
"champion" model per SKU through a deterministic selection cascade, and then
verifies that champion by testing it against demand it never saw during
selection (retrospective backtesting).

Put simply: it answers *"which forecasting method should we trust for this
product, and how do we know it actually works?"* — for potentially thousands
of SKUs at once — and shows its work at every step (every statistical decision
is traceable and reproducible).

The reference case study is an industrial spare-parts distributor (water
filters), forecasting daily/weekly demand for a closed catalog of critical
SKUs.

**This is not a consumer product.** It's an internal operational tool used by
a small number of named users inside one company, running entirely on a local
machine with no internet dependency at runtime.

## 2. Who uses it

Two roles, deliberately separated:

| Role | Mental model | What they do |
|------|--------------|---------------|
| **Operador** (commercial layer) | "I sell/plan around this product and need to know what to expect" | Views champion forecasts per SKU, browses simplified results, uploads and validates new transaction data (they own the source files and know the business context) |
| **Administrador** (pipeline/ops layer) | "I run and audit the analytical pipeline" | Configures and launches benchmark runs, monitors execution in real time, reviews full statistical results, runs retrospective validation, manages accounts/backups |

Login routes each user straight to their role's home screen. An Operador never
sees statistical internals (DM test matrices, p-values); an Administrador sees
everything.

## 3. Domain vocabulary

A short glossary, since these terms recur throughout the UI:

- **SKU** — a single product/part being forecast.
- **Series / demand profile** — a SKU's historical demand pattern, classified
  as `regular` or `intermitente/lumpy` (sparse, bursty demand — common for
  slow-moving spare parts). This classification changes how it's scored.
- **ABC / XYZ classification** — standard inventory-management segmentation by
  value (ABC) and demand variability (XYZ); shown as small classification
  badges next to a SKU.
- **Ingest** — one immutable, hash-verified snapshot of an uploaded data file.
  Every run is bound to exactly one ingest.
- **Run** — one full execution of the benchmarking pipeline against one ingest.
  Composed of many **tasks** (one per SKU × model × time-cut).
- **Champion** — the model selected, per SKU, as the best-performing and
  statistically justified forecaster, via a fixed ranking + significance-test
  cascade.
- **Walk-forward / cuts** — the model-testing protocol: repeatedly training on
  an expanding history window and testing on the next unseen chunk.
- **Retrospective validation / backtest** — a final, held-out check of whether
  the champion's forecast holds up against real demand it never touched during
  model selection. Produces a per-SKU verdict.

## 4. Product shape (screens, for context only — not to be designed here)

| Screen | Role(s) | Purpose |
|--------|---------|---------|
| Login | both | Authenticate, route by role |
| Panel de pronósticos | Operador (home), Administrador | Commercial home: champion forecast per SKU at a glance |
| Carga y validación de datos | both | Upload transaction files, see ingest quality/summary |
| Configuración de ejecución | Administrador | Define and launch a benchmark run against one ingest |
| Monitoreo de ejecución | Administrador | Real-time run progress, per-task status, stop/resume, error drill-down |
| Resultados por SKU / familia | both (role-gated detail) | Champion + evidence; full statistical detail for admins, simplified for operators |
| Validación retrospectiva | Administrador | Backtest verdicts per SKU + portfolio summary |
| Administración | Administrador | User accounts, config history, backups |

**Design polish is not uniform across these.** Three screens carry the full
brand treatment because they're what evaluators/stakeholders actually look at:
**Panel de pronósticos**, **Resultados**, and **Monitoreo de ejecución**. The
rest (Login, Carga, Configuración, Administración) are utilitarian — clear and
consistent, but don't need the same visual investment.

## 5. Tone & presentation context

This product will be demonstrated live during an academic thesis defense in
front of faculty evaluators, and used day-to-day as a real operational tool.
Both audiences read the same interface, so it needs to feel:

- **Credible and analytical**, not playful or consumer-flashy — this is
  evaluation software, closer in spirit to a lab/monitoring tool than a SaaS
  landing page.
- **Calm under data density** — screens routinely show hundreds to thousands
  of rows, many concurrent task states, and statistical output. The interface
  should make that legible, not overwhelming.
- **Trustworthy** — the product's entire value proposition is "we show our
  work and prove the forecast holds up." The UI should reinforce that:
  transparent states, visible provenance (hashes, seeds, timestamps), no
  hidden magic.

## 6. What the UI is mostly made of

Expect the component language to be exercised mainly by:

- **Task/results tables** — dense, sortable, filterable rows (SKU × model ×
  cut; or SKU × champion × metrics).
- **Status indicators** — a 5-state task lifecycle (see §8) shown at scale,
  potentially dozens of times per screen.
- **Stat tiles / numeric callouts** — portfolio-level headline numbers (e.g.
  "% of SKUs whose champion holds on backtest").
- **Simple charts** — forecast-vs-actual line/sparkline per SKU; nothing more
  elaborate than that.
- **Classification badges** — profile (regular/intermitente), ABC, XYZ.
- **Forms** — file upload, run configuration, login, user management.
- **Progress indication** — a live-updating global run progress bar plus
  per-task granularity, refreshed via HTMX polling (no full page reloads).

There is no marketing content, onboarding flow, social/collaboration surface,
or rich media anywhere in this product.

## 7. Binding technical constraints

Whatever visual/component system gets proposed has to work within this stack —
these are locked engineering decisions, not open questions:

- **Server-rendered**: FastAPI + Jinja2 templates + HTMX for interactivity.
  No SPA framework, no React/Vue, no client-side build toolchain.
- **Styling approach**: a vendored Pico.css base (~80 KB, classless/semantic-
  first) plus a small hand-written brand layer on top. No CSS framework CDN.
- **Fully local / offline**: the app has no internet access at runtime. No
  CDN-hosted fonts, icons, or scripts — anything used must be vendored
  (self-hosted font files, inline SVG icons, etc.), or fall back to system
  font stacks.
- **Desktop only**: minimum supported viewport 1366×768. No mobile/responsive
  requirement.
- **Performance**: interactive views must feel fast — sub-3-second p95 for
  typical queries. Avoid heavy client-side animation or rendering cost.
- **Language**: all UI copy (labels, buttons, messages, error text) is in
  Spanish.
- **Accessibility baseline**: status must never be conveyed by color alone
  (see §8) — assume some readers are colorblind or viewing on a projector
  during the defense.

## 8. Status semantics the component language must express

Two related but distinct state scales recur throughout the product and need
clear, distinguishable (not just color-coded) visual treatments:

**Task lifecycle** (used heavily in Monitoreo de ejecución, at high density):
`pendiente` (queued) → `ejecutando` (running) → `exitosa` (succeeded) |
`fallida` (failed) | `no_ejecutable` (skipped — e.g. series too short).

**Retrospective validation verdict** (used in Validación retrospectiva and
summarized in Resultados): `se sostiene` (holds), `se sostiene parcialmente`
(partially holds), `no se sostiene` (fails).

## 9. Explicit non-goals

- No alerts/notifications module (was in early scope, formally dropped —
  future work only, not present anywhere in this product).
- No ERP/Odoo or any live external system integration.
- No mobile app or responsive layout requirement.
- No multi-tenant or networked/cloud deployment — single local install per
  company.
- No real-time streaming data — batch file ingestion only.

## 10. What's still genuinely open

Palette and component visual language have **not** been decided yet — that's
the open design question this document is meant to support. Nothing here
should be read as constraining color/typography choices, only structure,
content density, and technical delivery constraints.

One optional data point, not a requirement: the institution's own thesis
templates use a dark institutional blue (`#003770` / `#003D80`) — worth
knowing about, not necessarily worth using.
