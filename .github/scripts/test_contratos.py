"""Regresiones del contrato de lectura M3 y de su validación en CI."""

import importlib.util
import json
import shutil
import sys
from copy import deepcopy
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "diseno/contratos"


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def models():
    return load(CONTRACT / "referencia/modelos_v2.py", "contrato_v2_test")


@pytest.fixture(scope="module")
def models_v1():
    return load(CONTRACT / "referencia/modelos_v1.py", "contrato_v1_test")


def example(name):
    return json.loads((CONTRACT / "ejemplos/v2" / f"{name}.json").read_text())


def example_v1(name):
    return json.loads((CONTRACT / "ejemplos/v1" / f"{name}.json").read_text())


def test_publicada_cuenta_todos_los_productos_y_separa_significancia(models):
    doc = models.M3Evidence.model_validate(example("m3_evidence.publicada"))
    assert doc.funnel.total_productos == 7
    assert doc.funnel.excluded_count == 2
    assert doc.funnel.evaluados == 2
    assert doc.funnel.no_evaluados == 3
    assert [row.veredicto for row in doc.items] == [
        "VALIDADO", "EXPLORATORIO", "FALLO_TECNICO",
        "NO_EVALUABLE", "EVIDENCIA_INSUFICIENTE",
    ]
    validado = doc.items[0]
    assert (validado.n_ventanas, validado.n_min, validado.razon_sn) == (40, 30, 0.8)
    assert validado.dm_p_ajustado == 0.08
    assert validado.dm_significativa is False
    assert doc.late_launches.items[0].causa == "lanzado despues del corte"


@pytest.mark.parametrize("case,cause,synthetic,declared", [
    ("sintetica", "datos_sinteticos", True, True),
    ("origen_desconocido", "origen_desconocido", False, False),
])
def test_origen_no_real_conserva_causa_sin_inferencia(models, case, cause, synthetic, declared):
    doc = models.M3Evidence.model_validate(example(f"m3_evidence.{case}"))
    row = doc.items[0]
    assert (row.datos_sinteticos, row.origen_declarado) == (synthetic, declared)
    assert (row.veredicto, row.dm_p_valor, row.dm_causa) == ("EXPLORATORIO", None, cause)


def test_rechazada_solo_expone_estado_y_causa(models):
    status = models.M3RunStatus.model_validate(example("m3_run_status.rechazada"))
    evidence = models.M3Evidence.model_validate(example("m3_evidence.rechazada"))
    assert status.run.estado == "RECHAZADA"
    assert status.run.causa_rechazo == "manifiesto incompatible con la ingesta"
    assert (evidence.availability.reason_code, evidence.items, evidence.funnel) == (
        "not_published", [], None,
    )
    invalid = example("m3_evidence.publicada")
    invalid["run"] = status.run.model_dump(mode="json")
    with pytest.raises(ValidationError, match="PUBLICADA"):
        models.M3Evidence.model_validate(invalid)


def test_corridas_publicadas_duplicadas_tienen_aviso_y_seleccion_explicita(models):
    doc = models.M3Runs.model_validate(example("m3_runs.varias_publicadas"))
    assert doc.selected_run_id == "m3-real-02"
    assert doc.items[0].aviso == "varias_publicadas_misma_identidad"
    assert doc.items[0].publicadas_misma_identidad == ["m3-real-02", "m3-real-01"]
    invalid = example("m3_runs.varias_publicadas")
    invalid["items"][0]["aviso"] = None
    with pytest.raises(ValidationError, match="aviso"):
        models.M3Runs.model_validate(invalid)


@pytest.mark.parametrize("mutation", [
    lambda d: d["funnel"].update(total_productos=8),
    lambda d: d["funnel"]["conteos"].update(VALIDADO=2),
    lambda d: d["late_launches"].update(excluded_count=1),
    lambda d: d["late_launches"]["items"].append(deepcopy(d["late_launches"]["items"][0])),
    lambda d: d["late_launches"]["items"][0].update(sku="SKU-VALIDADO"),
    lambda d: d["items"][0].update(run_id="otra-corrida"),
    lambda d: d["items"][0].update(ingesta_sha256="b" * 64),
    lambda d: d["items"][0].update(sku="SKU-EXPLORATORIO"),
    lambda d: d["items"][0].update(dm_p_valor=None),
    lambda d: d["items"][0].update(dm_causa="sin_prueba"),
    lambda d: d["items"][0].update(datos_sinteticos=True),
    lambda d: d["items"][0].update(n_min=31),
    lambda d: d["items"][0].update(veredicto="mantiene"),
    lambda d: d.update(schema_version="1.0.0"),
    lambda d: d["items"][0].pop("ingesta_sha256"),
])
def test_rechaza_evidencia_incoherente(models, mutation):
    data = example("m3_evidence.publicada")
    mutation(data)
    with pytest.raises(ValidationError):
        models.M3Evidence.model_validate(data)


def test_metricas_conservan_causa_y_no_admiten_smape(models):
    data = example("m3_metrics.campeon_y_base")
    doc = models.M3Metrics.model_validate(data)
    assert [(r.metrica, r.valor, r.causa) for r in doc.items[:3]] == [
        ("mae", 2.0, None), ("rmse", 4.0, None), ("mase", None, "escala_cero"),
    ]
    data["items"][0]["metrica"] = "smape"
    with pytest.raises(ValidationError):
        models.M3Metrics.model_validate(data)
    data = example("m3_metrics.campeon_y_base")
    data["items"][2]["causa"] = None
    with pytest.raises(ValidationError, match="causa"):
        models.M3Metrics.model_validate(data)


@pytest.mark.parametrize("value", ["4.0", True, float("nan"), float("inf")])
def test_metricas_rechazan_coercion_y_valores_no_finitos(models, value):
    data = example("m3_metrics.campeon_y_base")
    data["items"][0]["valor"] = value
    with pytest.raises(ValidationError):
        models.M3Metrics.model_validate(data)


def test_validado_sin_prueba_no_cambia_de_veredicto(models):
    doc = models.M3Evidence.model_validate(example("m3_evidence.sin_p_valor"))
    row = doc.items[0]
    assert (row.veredicto, row.dm_p_ajustado, row.dm_causa) == (
        "VALIDADO", None, "varianza_no_positiva",
    )


def test_campeon_linea_base_no_exige_identificador_legacy(models):
    doc = models.M3Evidence.model_validate(example("m3_evidence.linea_base"))
    row = doc.items[0]
    assert (row.familia_campeona, row.candidato_campeon, row.dm_causa) == (
        "seasonal_naive", "SKU-BASE/seasonal_naive/seasonal_naive", "campeon_es_linea_base",
    )


def test_filtro_preserva_embudo_global_y_metadatos_ausentes_no_son_cero(models):
    doc = models.M3Evidence.model_validate(example("m3_evidence.filtrada"))
    assert (len(doc.items), doc.page.total, doc.funnel.total_productos) == (1, 1, 7)
    missing = models.M3Evidence.model_validate(example("m3_evidence.sin_metadatos"))
    assert (missing.availability.reason_code, missing.funnel, missing.late_launches) == (
        "metadata_missing", None, None,
    )


def test_evidencia_auxiliar_preserva_nulos_fallos_y_agregados(models):
    units = models.M3Units.model_validate(example("m3_units.confirmada_y_fallida"))
    assert [(row.estado, row.causa) for row in units.items] == [
        ("confirmada", None), ("fallida", "El candidato no produjo pronosticos finitos."),
    ]
    portfolio = models.M3Portfolio.model_validate(example("m3_portfolio.distribuciones"))
    assert (portfolio.items[1].n_calculables, portfolio.items[1].mediana) == (0, None)
    forecasts = models.M3Forecasts.model_validate(example("m3_forecasts.normal_y_nulo"))
    assert [row.valor for row in forecasts.items] == [10.0, None]
    category = models.M3Categories.model_validate(example("m3_categories.por_clase"))
    assert (category.items[0].sku, category.items[0].conteos.FALLO_TECNICO) == (None, 1)
    failure = models.M3Failures.model_validate(example("m3_failures.candidato_invalido"))
    assert (failure.items[0].sku, failure.items[0].campo) == ("SKU-FALLO", "artefacto")


def test_fallo_conserva_nombre_de_modelo_vacio_en_modelo_y_esquema(models):
    data = example("m3_failures.modelo_vacio")
    doc = models.M3Failures.model_validate(data)
    assert doc.items[0].modelo == ""
    assert doc.model_dump(mode="json")["items"][0]["modelo"] == ""
    schema = json.loads((CONTRACT / "schemas/v2/m3_failures.schema.json").read_text())
    Draft202012Validator(schema).validate(data)


@pytest.mark.parametrize("name", [
    "m3_metrics.campeon_y_base", "m3_categories.por_clase", "m3_portfolio.distribuciones",
    "m3_forecasts.normal_y_nulo", "m3_failures.candidato_invalido", "m3_units.confirmada_y_fallida",
])
def test_ninguna_tabla_auxiliar_publica_filas_de_otra_corrida(models, name):
    data = example(name)
    data["items"][0]["run_id"] = "otra-corrida"
    with pytest.raises(ValidationError, match="run_id"):
        models.DOCUMENTS[name.split(".")[0]].model_validate(data)
    data = example(name)
    data["run"]["estado"] = "EN_CURSO"
    data["run"]["publicadas_misma_identidad"] = []
    with pytest.raises(ValidationError, match="PUBLICADA"):
        models.DOCUMENTS[name.split(".")[0]].model_validate(data)


def test_estado_no_expone_metricas_parciales_y_avance_conserva_unidades(models):
    data = example("m3_run_status.en_curso")
    doc = models.M3RunStatus.model_validate(data)
    assert (doc.progress.n_resueltas, doc.progress.n_confirmadas, doc.progress.n_fallidas) == (
        30, 25, 5,
    )
    data["metricas"] = [{"valor": 3.0}]
    with pytest.raises(ValidationError, match="Extra inputs"):
        models.M3RunStatus.model_validate(data)
    data = example("m3_run_status.en_curso")
    data["progress"]["n_resueltas"] = 31
    with pytest.raises(ValidationError, match="unidades resueltas"):
        models.M3RunStatus.model_validate(data)


def test_validacion_ci_comprueba_modelos_y_esquemas(tmp_path):
    validator = load(ROOT / ".github/scripts/validar_ejemplos.py", "validacion_test")
    assert validator.validate_contract(CONTRACT) == []
    # Un contrato sin modelos ni ejemplos no puede dar un verde vacío.
    assert validator.validate_contract(tmp_path) == ["no se encontraron versiones del contrato"]


@pytest.fixture
def contract_copy(tmp_path):
    for folder in ("schemas/v2", "ejemplos/v2", "referencia"):
        shutil.copytree(CONTRACT / folder, tmp_path / folder)
    # La copia reducida solo declara v2.
    (tmp_path / "referencia/modelos_v1.py").unlink()
    return tmp_path


@pytest.mark.parametrize("fault,expected", [
    ("drift", "el esquema difiere del modelo"),
    ("missing_example", "faltan ejemplos"),
    ("missing_schema", "los esquemas no corresponden"),
    ("cross_field", "dm_causa exige resultados inferenciales nulos"),
    ("wrong_major", "x-contract-version no corresponde"),
    ("bad_date", "is not a 'date'"),
])
def test_ci_rechaza_desajustes_y_reglas_que_json_schema_no_expresa(contract_copy, fault, expected):
    validator = load(ROOT / ".github/scripts/validar_ejemplos.py", "validacion_mutacion_test")
    schema = contract_copy / "schemas/v2/m3_evidence.schema.json"
    sample = contract_copy / "ejemplos/v2/m3_evidence.publicada.json"
    if fault in ("drift", "wrong_major"):
        data = json.loads(schema.read_text())
        if fault == "drift":
            data["title"] = "Titulo distinto"
        else:
            data["x-contract-version"] = "1.0.0"
        schema.write_text(json.dumps(data))
    elif fault == "missing_example":
        (contract_copy / "ejemplos/v2/m3_metrics.campeon_y_base.json").unlink()
    elif fault == "missing_schema":
        schema.unlink()
    else:
        data = json.loads(sample.read_text())
        if fault == "cross_field":
            data["items"][0]["dm_causa"] = "sin_prueba"
        else:
            data["late_launches"]["t_star"] = "2026-02-30"
        sample.write_text(json.dumps(data))
    errors = validator.validate_contract(contract_copy)
    assert any(expected in error for error in errors), errors


def test_observaciones_rechaza_claves_duplicadas(models):
    data = example("m3_observations.reserva")
    doc = models.M3Observations.model_validate(data)
    assert len(doc.items) == 6
    dup = deepcopy(data)
    dup["items"].append(deepcopy(dup["items"][0]))
    dup["page"]["total"] = len(dup["items"])
    with pytest.raises(ValidationError, match="observaciones"):
        models.M3Observations.model_validate(dup)


def test_campeones_exige_suma_total_de_evaluados_y_no_evaluados(models):
    data = example("m3_champions.por_clase_y_cartera")
    doc = models.M3Champions.model_validate(data)
    assert doc.items[0].n_skus == doc.items[0].n_evaluados + doc.items[0].n_no_evaluados
    invalid = deepcopy(data)
    invalid["items"][0]["n_skus"] = invalid["items"][0]["n_skus"] + 1
    with pytest.raises(ValidationError, match="n_skus debe sumar evaluados y no evaluados"):
        models.M3Champions.model_validate(invalid)


def test_campeones_admite_fila_cartera_con_clase_nula(models):
    data = example("m3_champions.por_clase_y_cartera")
    doc = models.M3Champions.model_validate(data)
    portfolio_rows = [r for r in doc.items if r.sku_class is None]
    assert len(portfolio_rows) == 1
    cartera = portfolio_rows[0]
    assert (cartera.sku, cartera.familia, cartera.n_skus, cartera.n_evaluados, cartera.n_no_evaluados) == (
        None, "classical", 5, 2, 3,
    )


def test_topologia_rechaza_umbrales_nulos_si_esta_disponible(models_v1):
    data = example_v1("topology_report.normal")
    doc = models_v1.TopologyReport.model_validate(data)
    assert doc.thresholds is not None
    data["thresholds"] = None
    with pytest.raises(ValidationError, match="available exige thresholds"):
        models_v1.TopologyReport.model_validate(data)
    no_aceptada = example_v1("topology_report.no_aceptada")
    doc_no_aceptada = models_v1.TopologyReport.model_validate(no_aceptada)
    assert doc_no_aceptada.thresholds is None


def test_run_settings_exige_ambos_o_ninguno_en_agregacion_y_recorte(models_v1):
    data = example_v1("run_status.normal")["settings"]
    settings = models_v1.RunSettings.model_validate(data)
    assert (settings.aggregation, settings.trim) == ("media_recortada", 0.1)

    both_null = deepcopy(data)
    both_null["aggregation"] = None
    both_null["trim"] = None
    valid_null = models_v1.RunSettings.model_validate(both_null)
    assert valid_null.aggregation is None and valid_null.trim is None

    only_agg = deepcopy(data)
    only_agg["trim"] = None
    with pytest.raises(ValidationError, match="aggregation y trim"):
        models_v1.RunSettings.model_validate(only_agg)

    only_trim = deepcopy(data)
    only_trim["aggregation"] = None
    with pytest.raises(ValidationError, match="aggregation y trim"):
        models_v1.RunSettings.model_validate(only_trim)

