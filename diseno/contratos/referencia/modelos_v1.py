"""Modelos Pydantic v2 de REFERENCIA del contrato frontend <-> motor (v1.0.0).

Fuente de los esquemas de `../schemas/v1/` y de las reglas entre campos que
JSON Schema no expresa. No es la implementacion de la plataforma: TASK-UI-1.1-B4
la copia a `pred-platform` y la completa (ADR-05-001).

Exportar un esquema:
    python -c "import json, modelos_v1 as m; print(json.dumps(m.DOCUMENTS['run_status'].model_json_schema(), indent=2))"
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    StringConstraints,
    model_validator,
)

Semver = Annotated[str, StringConstraints(pattern=r"^1\.[0-9]+\.[0-9]+$")]
Sha256 = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
GapId = Annotated[str, StringConstraints(pattern=r"^G[1-8]$")]
ErrorCode = Annotated[str, StringConstraints(pattern=r"^[a-z_]+\.[a-z_]+$")]

SkuClass = Literal["smooth", "intermittent", "erratic", "lumpy"]
Family = Literal["classical", "ml", "dl", "foundation"]
Profile = Literal["dense_stable", "dense_variable", "sparse_stable", "sparse_variable"]
Source = Literal["engine", "fixture"]
StageId = Literal["L1", "L2", "L3", "L4"]
EstadoCorrida = Literal["nueva", "en_progreso", "interrumpida", "completada", "fallida"]
EstadoTrial = Literal["pendiente", "corriendo", "completado", "podado", "fallido"]


class _Base(BaseModel):
    model_config = ConfigDict(extra="forbid")


# --------------------------------------------------------------------- comunes
class Availability(_Base):
    """Si el dato existe hoy. Sostiene estados vacios y acciones deshabilitadas."""

    status: Literal["available", "unavailable"]
    reason_code: (
        Literal["no_data", "engine_gap", "stage_not_implemented", "prerequisite_missing"]
        | None
    ) = None
    blocked_by: list[GapId] = Field(default_factory=list)
    detail: str | None = None

    @model_validator(mode="after")
    def _coherente(self) -> Availability:
        if self.status == "available" and (self.reason_code or self.blocked_by):
            raise ValueError("available no lleva reason_code ni blocked_by")
        if self.status == "unavailable" and self.reason_code is None:
            raise ValueError("unavailable exige reason_code")
        if self.reason_code == "engine_gap" and not self.blocked_by:
            raise ValueError("engine_gap exige blocked_by")
        return self


class Documento(_Base):
    """Sobre comun de todo documento de lectura."""

    schema_version: Semver
    generated_at: AwareDatetime
    source: Source
    availability: Availability


class Page(_Base):
    number: int = Field(ge=1)
    size: int = Field(ge=1, le=500)
    total: int = Field(ge=0)


class ErrorInfo(_Base):
    """Error normalizado. El frontend traduce `code` a texto en espanol."""

    code: ErrorCode
    stage: Literal["L0", "L1", "L2", "L3", "L4", "platform"]
    severity: Literal["error", "warning"] = "error"
    detail: str | None = None
    field: str | None = None
    row_index: int | None = Field(default=None, ge=0)
    column: str | None = None
    source_exception: str | None = None
    retryable: bool = False


class TopologyMetrics(_Base):
    sku_id: str = Field(min_length=1)
    n_periods: int = Field(ge=1)
    n_positive: int = Field(ge=0)
    adi: float = Field(gt=0)
    cv2: float = Field(ge=0)
    sku_class: SkuClass


# ------------------------------------------------------------ engine_capabilities
CapabilityId = Literal[
    "parquet_read",
    "ingest_report_persisted",
    "topology_persisted",
    "family_comparison",
    "selection_results_persisted",
    "trial_detail_persisted",
    "walkforward_evidence_persisted",
    "run_state_persisted",
    "champion_selection",
    "retrospective_validation",
    "synthetic_log_read",
]


class Capability(_Base):
    id: CapabilityId
    available: bool
    reason_code: Literal["engine_gap", "stage_not_implemented"] | None = None
    blocked_by: list[GapId] = Field(default_factory=list)

    @model_validator(mode="after")
    def _coherente(self) -> Capability:
        if self.available and (self.reason_code or self.blocked_by):
            raise ValueError("available no lleva reason_code ni blocked_by")
        if not self.available and self.reason_code is None:
            raise ValueError("no disponible exige reason_code")
        return self


class EngineCapabilities(Documento):
    items: list[Capability]


# ------------------------------------------------------------------ ingest_report
class SourceFile(_Base):
    name: str
    sha256: Sha256
    row_count: int = Field(ge=0)


class Deposit(_Base):
    raw_path: str
    status: Literal["deposited", "already_present_identical", "already_present_different"]
    would_overwrite: bool


class DiagnosticEntry(_Base):
    field: str
    severity: Literal["error", "info"] = "error"
    message: str
    action: str | None = None


class HeaderDiagnostic(_Base):
    status: Literal["accepted", "rejected"]
    entries: list[DiagnosticEntry] = Field(default_factory=list)


class ValidationSummary(_Base):
    rows_validated: int = Field(ge=0)
    rows_daily_panel: int = Field(ge=0)
    n_skus: int = Field(ge=0)


class PublishedArtifact(_Base):
    parquet_path: str
    rows: int = Field(ge=0)
    n_skus: int = Field(ge=0)
    columns: list[str]


class IngestReport(Documento):
    ingest_id: Sha256
    status: Literal["accepted", "rejected", "failed", "needs_confirmation"]
    source_file: SourceFile
    deposit: Deposit | None = None
    header_diagnostic: HeaderDiagnostic | None = None
    validation: ValidationSummary | None = None
    published: PublishedArtifact | None = None
    error: ErrorInfo | None = None


class IngestSummary(_Base):
    ingest_id: Sha256 | None = None
    name: str
    status: Literal["accepted", "rejected", "failed", "needs_confirmation"] | None = None
    parquet_path: str
    rows: int | None = Field(default=None, ge=0)
    n_skus: int | None = Field(default=None, ge=0)
    published_at: AwareDatetime | None = None


class IngestList(Documento):
    items: list[IngestSummary]
    page: Page


# --------------------------------------------------------------- topology_report
class Thresholds(_Base):
    adi: float
    cv2: float


class TopologySummary(_Base):
    n_skus: int = Field(ge=0)
    by_class: dict[SkuClass, int]


class TopologyReport(Documento):
    ingest_id: Sha256
    thresholds: Thresholds
    summary: TopologySummary
    items: list[TopologyMetrics]
    page: Page


# -------------------------------------------------------------------- run_status
class StageState(_Base):
    id: StageId
    name: str
    maturity: Literal["implemented", "partial", "absent", "caller_provided"]
    state: Literal["pending", "completed", "blocked", "failed"]
    capability: str = ""
    message: str = ""


class EvaluationSettings(_Base):
    min_train: int = Field(ge=1)
    horizon: int = Field(ge=1)
    step: int = Field(ge=1)
    metric: Literal["mae", "rmse", "smape", "mase"]
    seasonality: int = Field(ge=1)
    aggregation: Literal["media", "mediana", "media_recortada"]
    trim: float = Field(ge=0, lt=0.5)


class Study(_Base):
    """Un estudio HPO = un `ManifiestoCorrida` del motor (familia x SKU)."""

    study_id: str = Field(min_length=1)
    family: Family
    sku_id: str
    estado: EstadoCorrida
    seed: int
    metrica_objetivo: str
    n_trials_objetivo: int = Field(ge=1)
    n_trials_finalizados: int = Field(ge=0)
    fingerprint_configuracion: str
    backend: Literal["optuna"]
    backend_checkpoint: str | None = None
    manifest_schema_version: int = Field(ge=1)


class Progress(_Base):
    studies_total: int = Field(ge=0)
    studies_by_estado: dict[EstadoCorrida, int]
    trials_objetivo: int = Field(ge=0)
    trials_finalizados: int = Field(ge=0)


class RunStatus(Documento):
    run_id: str | None = None
    ingest_id: Sha256 | None = None
    policy_version: str | None = None
    settings: EvaluationSettings | None = None
    complete: bool
    blocked_stage: StageId | None = None
    stages: list[StageState]
    progress: Progress | None = None
    started_at: AwareDatetime | None = None
    finished_at: AwareDatetime | None = None
    studies: list[Study]
    page: Page | None = None


# ----------------------------------------------------------------- sku_selection
class TrialRow(_Base):
    id: str
    configuracion: dict[str, JsonValue]
    estado: EstadoTrial
    valor: float | None = None
    n_ventanas: int = Field(ge=0)
    motivo: str | None = None
    timestamp: AwareDatetime | None = None


class WindowResult(_Base):
    indice: int = Field(ge=0)
    inicio_train: int
    fin_train: int
    inicio_val: int
    fin_val: int
    metricas: dict[str, float | None]
    duracion_s: float | None = None
    fallo: str | None = None


class WalkForwardSummary(_Base):
    metrica_objetivo: Literal["mae", "rmse", "smape", "mase"]
    valor_agregado: float | None = None
    completo: bool
    n_ventanas_evaluadas: int = Field(ge=0)
    n_ventanas_totales: int = Field(ge=0)
    selection_scope: Literal["same_history"] = "same_history"
    statistical_comparison_available: bool = False
    windows: list[WindowResult] | None = None


class _EvidenciaHPO(_Base):
    metrica_objetivo: str
    valor: float
    n_ventanas: int = Field(ge=0)
    n_trials: int = Field(ge=0)
    n_completados: int = Field(ge=0)
    n_podados: int = Field(ge=0)
    n_fallidos: int = Field(ge=0)
    seed: int


class EvidenciaClasica(_EvidenciaHPO):
    family: Literal["classical"]
    order: Annotated[list[int], Field(min_length=3, max_length=3)]
    seasonal_order: Annotated[list[int], Field(min_length=4, max_length=4)]


class EvidenciaML(_EvidenciaHPO):
    family: Literal["ml"]
    hiperparametros: dict[str, JsonValue]


class EvidenciaDL(_EvidenciaHPO):
    family: Literal["dl"]
    hiperparametros: dict[str, JsonValue]


class EvidenciaFundacional(_Base):
    family: Literal["foundation"]
    configuracion: dict[str, JsonValue]
    optimizado: Literal[False] = False


Evidence = Annotated[
    EvidenciaClasica | EvidenciaML | EvidenciaDL | EvidenciaFundacional,
    Field(discriminator="family"),
]


class Exclusion(_Base):
    reason_code: Literal[
        "not_in_policy_matrix", "not_configured", "series_too_short", "execution_failed"
    ]
    detail: str | None = None


class FamilyEntry(_Base):
    family: Family
    state: Literal["excluded", "pending", "running", "completed", "failed", "not_executable"]
    exclusion: Exclusion | None = None
    study_id: str | None = None
    produced_by: str | None = None
    evidence: Evidence | None = None
    forecast_config: dict[str, JsonValue] | None = None
    forecast_seed: int | None = None
    trials: list[TrialRow] | None = None
    walk_forward: WalkForwardSummary | None = None
    error: ErrorInfo | None = None

    @model_validator(mode="after")
    def _coherente(self) -> FamilyEntry:
        if self.state in ("excluded", "not_executable") and self.exclusion is None:
            raise ValueError(f"{self.state} exige exclusion")
        if self.state not in ("excluded", "not_executable") and self.exclusion:
            raise ValueError("exclusion solo aplica a excluded/not_executable")
        if self.state == "failed" and self.error is None:
            raise ValueError("failed exige error")
        if self.evidence is not None and self.evidence.family != self.family:
            raise ValueError("evidence.family no coincide con family")
        return self


class Champion(_Base):
    family: Family
    decided_by: Literal["m3"]


class SkuSelection(Documento):
    ingest_id: Sha256 | None = None
    run_id: str | None = None
    sku_id: str
    sku_class: SkuClass
    profile: Profile
    policy_version: str | None = None
    topology: TopologyMetrics | None = None
    families: list[FamilyEntry]
    champion: Champion | None = None


class FamilyBrief(_Base):
    family: Family
    state: Literal["excluded", "pending", "running", "completed", "failed", "not_executable"]
    metrica_objetivo: str | None = None
    valor: float | None = None


class SkuSelectionRow(_Base):
    sku_id: str
    sku_class: SkuClass
    profile: Profile
    families: list[FamilyBrief]
    champion_family: Family | None = None


class SkuSelectionList(Documento):
    ingest_id: Sha256 | None = None
    run_id: str | None = None
    items: list[SkuSelectionRow]
    page: Page


# ------------------------------------------------------------ validation_verdicts
class SkuVerdict(_Base):
    sku_id: str
    verdict: Literal["hold", "partial", "fail"]
    evidence: dict[str, JsonValue] = Field(default_factory=dict)


class ValidationVerdicts(Documento):
    run_id: str | None = None
    items: list[SkuVerdict]
    audit_bundle: dict[str, JsonValue] | None = None


# ----------------------------------------------------------------- synthetic_run
class SyntheticLog(_Base):
    """Espejo de `BitacoraCorrida` (aumentacion/bitacora.py)."""

    semilla_ruta: str
    semilla_aleatoria: int
    contract_version: str
    period: int
    n_series_por_sku: int
    skus_procesados: int
    skus_omitidos: int
    tolerancia_divergencia: float
    tasa_rechazo: float
    intentos_bootstrap: int
    n_demanda_rectificada: int
    n_lead_time_acotado: int
    row_count: int
    artefacto_sha256: Sha256
    artefacto_path: str
    iniciada_en: AwareDatetime
    finalizada_en: AwareDatetime | None = None


class SyntheticArtifact(_Base):
    file_name: str
    sha256: Sha256
    rows: int = Field(ge=0)
    media_type: Literal["text/csv"] = "text/csv"
    columns: list[str]


class SyntheticRun(Documento):
    run_ref: str = Field(min_length=1)
    log_file: str
    log: SyntheticLog
    artifact: SyntheticArtifact


class SyntheticList(Documento):
    items: list[SyntheticRun]
    page: Page


DOCUMENTS: dict[str, type[BaseModel]] = {
    "engine_capabilities": EngineCapabilities,
    "ingest_report": IngestReport,
    "ingest_list": IngestList,
    "topology_report": TopologyReport,
    "run_status": RunStatus,
    "sku_selection": SkuSelection,
    "sku_selection_list": SkuSelectionList,
    "validation_verdicts": ValidationVerdicts,
    "synthetic_run": SyntheticRun,
    "synthetic_list": SyntheticList,
    "error": ErrorInfo,
}
