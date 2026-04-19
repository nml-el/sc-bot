import importlib
import os
import sqlite3
import sys

import pandas as pd

SCRIPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts")


def _load_script_modules() -> tuple[object, object, object, object]:
    if SCRIPTS_DIR not in sys.path:
        sys.path.append(SCRIPTS_DIR)

    ingest_sctype_module = importlib.import_module("ingest_sctype")
    setup_db_module = importlib.import_module("setup_db")
    utils_module = importlib.import_module("utils")
    return ingest_sctype_module, setup_db_module, utils_module.create_schema, utils_module.load_ontology


def test_normalize_sctype_gene_symbol_converts_mouse_style_casing() -> None:
    ingest_sctype_module, _, _, _ = _load_script_modules()

    assert ingest_sctype_module._normalize_sctype_gene_symbol("Pax6") == "PAX6"
    assert ingest_sctype_module._normalize_sctype_gene_symbol("ApoE") == "APOE"
    assert ingest_sctype_module._normalize_sctype_gene_symbol("SLC17a6") == "SLC17A6"
    assert ingest_sctype_module._normalize_sctype_gene_symbol("C5orf20") == "C5orf20"
    assert ingest_sctype_module._normalize_sctype_gene_symbol("nan") == ""


def test_ingest_sctype_inserts_human_markers(monkeypatch) -> None:
    ingest_sctype_module, _, create_schema, load_ontology = _load_script_modules()

    mock_df = pd.DataFrame(
        {
            "tissueType": ["Blood", "Lung"],
            "cellName": ["B cells", "epithelial cells"],
            "geneSymbolmore1": ["Pax5, CD79A, C5orf20, nan", "Epcam, KRT19"],
        }
    )

    monkeypatch.setattr(ingest_sctype_module, "download_sctype", lambda _dest: None)
    monkeypatch.setattr(ingest_sctype_module.pd, "read_excel", lambda *_args, **_kwargs: mock_df)

    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()
    create_schema(cursor)
    lbl_to_id, id_to_lbl, choices = load_ontology(cursor, skip_db_write=True)

    rows = ingest_sctype_module.ingest_sctype(conn, lbl_to_id, id_to_lbl, choices)
    assert rows == 5

    cursor.execute("SELECT DISTINCT species_id FROM cell_markers WHERE source = 'ScType'")
    assert cursor.fetchall() == [(1,)]

    cursor.execute("SELECT marker_gene FROM cell_markers WHERE source = 'ScType' ORDER BY marker_gene")
    assert [row[0] for row in cursor.fetchall()] == ["C5orf20", "CD79A", "EPCAM", "KRT19", "PAX5"]


def test_setup_database_defaults_include_sctype(monkeypatch, tmp_path) -> None:
    _, setup_db_module, _, _ = _load_script_modules()

    calls: list[str] = []

    monkeypatch.setattr(setup_db_module, "DB_PATH", tmp_path / "sc_markers.db")
    monkeypatch.setattr(setup_db_module, "create_schema", lambda _cursor: None)
    monkeypatch.setattr(setup_db_module, "load_ontology", lambda _cursor, skip_db_write: ({}, {}, []))
    monkeypatch.setattr(setup_db_module, "ingest_panglao", lambda *_args: calls.append("panglao"))
    monkeypatch.setattr(setup_db_module, "ingest_cellmarker2", lambda *_args: calls.append("cellmarker2"))
    monkeypatch.setattr(setup_db_module, "ingest_sctype", lambda *_args: calls.append("sctype"))
    monkeypatch.setattr(setup_db_module, "ingest_celltypist", lambda *_args: calls.append("celltypist"))
    monkeypatch.setattr(setup_db_module, "set_database_version", lambda _cursor, _version: None)
    monkeypatch.setattr(setup_db_module, "get_app_version", lambda: "9.9.9")

    assert setup_db_module.setup_database(panglao=False, cellmarker2=False, sctype=False, celltypist=False) == 0
    assert calls == ["panglao", "cellmarker2", "sctype", "celltypist"]
