import importlib
import os
import sqlite3
import sys

import pandas as pd

SCRIPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts")


def _load_script_modules() -> tuple[object, object, object, object]:
    if SCRIPTS_DIR not in sys.path:
        sys.path.append(SCRIPTS_DIR)

    ingest_celltypist_module = importlib.import_module("ingest_celltypist")
    setup_db_module = importlib.import_module("setup_db")
    utils_module = importlib.import_module("utils")
    return ingest_celltypist_module, setup_db_module, utils_module.create_schema, utils_module.load_ontology


def test_ingest_celltypist_inserts_immune_markers(monkeypatch) -> None:
    ingest_celltypist_module, _, create_schema, load_ontology = _load_script_modules()

    mock_df = pd.DataFrame(
        {
            "Low-hierarchy cell types": ["Naive B cells", "Memory B cells"],
            "Curated markers": ["IGHM, IGHD, TCL1A", "CR2, CD27, MS4A1"],
        }
    )

    monkeypatch.setattr(ingest_celltypist_module, "download_celltypist", lambda _dest: None)
    monkeypatch.setattr(ingest_celltypist_module.pd, "read_excel", lambda *_args, **_kwargs: mock_df)

    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()
    create_schema(cursor)
    lbl_to_id, id_to_lbl, choices = load_ontology(cursor, skip_db_write=True)

    rows = ingest_celltypist_module.ingest_celltypist(conn, lbl_to_id, id_to_lbl, choices)
    assert rows == 6

    cursor.execute("SELECT DISTINCT species_id FROM cell_markers WHERE source = 'CellTypist'")
    assert cursor.fetchall() == [(1,)]

    cursor.execute("SELECT DISTINCT tissue FROM cell_markers WHERE source = 'CellTypist'")
    assert cursor.fetchall() == [("Immune system",)]

    cursor.execute("SELECT marker_gene FROM cell_markers WHERE source = 'CellTypist' ORDER BY marker_gene")
    assert [row[0] for row in cursor.fetchall()] == ["CD27", "CR2", "IGHD", "IGHM", "MS4A1", "TCL1A"]


def test_setup_database_defaults_include_celltypist(monkeypatch, tmp_path) -> None:
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
    monkeypatch.setattr(setup_db_module, "get_app_version", lambda: "0.1.1")

    assert setup_db_module.setup_database(panglao=False, cellmarker2=False, sctype=False, celltypist=False) == 0
    assert calls == ["panglao", "cellmarker2", "sctype", "celltypist"]
