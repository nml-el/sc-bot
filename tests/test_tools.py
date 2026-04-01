from sc_bot.tools import (
    get_all_cell_types,
    get_cell_types_by_marker,
    get_markers_by_cell_type,
    get_tissues_for_cell_type,
    resolve_gene_aliases,
)


def test_get_all_cell_types() -> None:
    cell_types = get_all_cell_types.invoke({})
    assert "T cell" in cell_types
    assert "B cell" in cell_types


def test_t_cell_markers() -> None:
    markers = get_markers_by_cell_type.invoke({"cell_types": ["T cell"]})
    assert isinstance(markers, list)
    assert len(markers) > 0
    marker_genes = [m["marker_gene"] for m in markers]
    assert "CD3E" in marker_genes


def test_b_cell_markers() -> None:
    markers = get_markers_by_cell_type.invoke({"cell_types": ["B cell"]})
    assert isinstance(markers, list)
    assert len(markers) > 0
    marker_genes = [m["marker_gene"] for m in markers]
    assert "CD19" in marker_genes


def test_common_markers_t_and_b_cells() -> None:
    markers = get_markers_by_cell_type.invoke({"cell_types": ["T cell", "B cell"]})
    assert isinstance(markers, list)
    marker_genes = [m["marker_gene"] for m in markers]
    assert "CXCR4" in marker_genes


def test_cell_types_by_marker_cd3e() -> None:
    cell_types = get_cell_types_by_marker.invoke({"marker_genes": ["CD3E"]})
    assert isinstance(cell_types, list)
    cell_type_names = [c["cell_type"] for c in cell_types]
    assert "T cell" in cell_type_names


def test_cell_types_by_multiple_markers() -> None:
    cell_types = get_cell_types_by_marker.invoke({"marker_genes": ["CD3E", "CD8A"]})
    assert isinstance(cell_types, list)
    cell_type_names = [c["cell_type"] for c in cell_types]
    assert "T cell" in cell_type_names


def test_cell_types_by_marker_alias_cd20() -> None:
    cell_types = get_cell_types_by_marker.invoke({"marker_genes": ["CD20"], "species": "Human"})
    assert isinstance(cell_types, list)
    cell_type_names = [c["cell_type"] for c in cell_types]
    assert "B cell" in cell_type_names


def test_resolve_gene_aliases_cd16_defaults_to_human() -> None:
    resolved = resolve_gene_aliases.invoke({"genes": ["CD16"]})
    assert len(resolved) == 1
    assert resolved[0]["species"] == "Human"
    assert "FCGR3A" in resolved[0]["canonical_symbols"]
    assert "CD16" in resolved[0]["aliases"]


def test_resolve_gene_aliases_cd161_defaults_to_human() -> None:
    resolved = resolve_gene_aliases.invoke({"genes": ["CD161"]})
    assert len(resolved) == 1
    assert resolved[0]["species"] == "Human"
    assert "KLRB1" in resolved[0]["canonical_symbols"]
    assert "CD161" in resolved[0]["aliases"]
    assert "NKR-P1A" in resolved[0]["aliases"]


def test_resolve_cell_type_lineage() -> None:
    markers = get_markers_by_cell_type.invoke({"cell_types": ["T cells"]})
    assert len(markers) > 0


def test_nan_genes_excluded() -> None:
    markers = get_markers_by_cell_type.invoke({"cell_types": ["T cell"]})
    marker_genes = [m["marker_gene"] for m in markers]
    assert "nan" not in marker_genes


def test_markers_include_consensus_scores() -> None:
    markers = get_markers_by_cell_type.invoke({"cell_types": ["T cell"]})
    for m in markers:
        assert "tissue_count" in m
        assert "source_count" in m
        assert isinstance(m["tissue_count"], int)
        assert isinstance(m["source_count"], int)


def test_tissue_filter_reduces_results() -> None:
    all_markers = get_markers_by_cell_type.invoke({"cell_types": ["epithelial cell"]})
    lung_markers = get_markers_by_cell_type.invoke({"cell_types": ["epithelial cell"], "tissue": "Lung"})

    assert len(lung_markers) < len(all_markers)
    assert len(lung_markers) > 0


def test_get_tissues_for_cell_type() -> None:
    tissues = get_tissues_for_cell_type.invoke({"cell_type": "T cell"})
    assert isinstance(tissues, list)
    assert len(tissues) > 0
    # Both of these are PanglaoDB canonicals mapped from T cell entries
    assert "Blood" in tissues
    assert "Immune system" in tissues


def test_custom_source_priority_field() -> None:
    markers = get_markers_by_cell_type.invoke({"cell_types": ["B cell"], "species": "Human"})
    assert isinstance(markers, list)
    assert len(markers) > 0
    assert "custom_source_count" in markers[0]


def test_marker_csv_ingestion(tmp_path) -> None:
    import sqlite3
    import os
    import sys

    sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

    from ingest_marker_csv import ingest_marker_csv
    from utils import create_schema, load_ontology

    csv_path = tmp_path / "marker_data.csv"
    csv_path.write_text(
        """species,cell_type,tissue,marker_gene,gene_aliases,source
Human,B cell,Blood,MS4A1,CD20,custom-source
""",
        encoding="utf-8",
    )

    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()
    create_schema(cursor)
    lbl_to_id, id_to_lbl, choices = load_ontology(cursor, skip_db_write=True)

    rows = ingest_marker_csv(conn, str(csv_path), lbl_to_id, id_to_lbl, choices, default_source="custom-source")
    assert rows == 1

    cursor.execute("SELECT marker_gene FROM cell_markers WHERE source = 'custom-source'")
    assert cursor.fetchone()[0] == "MS4A1"

    cursor.execute("SELECT alias FROM gene_aliases WHERE canonical_symbol = 'MS4A1'")
    assert cursor.fetchone()[0] == "CD20"


def test_query_enrichr_tool_structure(monkeypatch):
    """
    Test that the query_enrichr tool returns the expected format and structure
    when given mocked Enrichr output.
    """
    from sc_bot.tools import query_enrichr
    import pandas as pd

    class MockEnrichr:
        def __init__(self, gene_list, **kwargs):
            self.gene_list = gene_list

        def get_cell_type_enrichment(self, gene_sets, max_workers):
            # Mock the raw DataFrame returned by Enrichr
            data = [
                {
                    "term name": "T Cell",
                    "adjusted p-value": 0.001,
                    "combined score": 150.5,
                    "overlapping genes": ["CD3D", "CD3E"],
                    "gene_set": "PanglaoDB_Augmented_2021",
                },
                {
                    "term name": "T Cell",
                    "adjusted p-value": 0.005,
                    "combined score": 120.0,
                    "overlapping genes": ["CD3D", "CD8A"],
                    "gene_set": "CellMarker_2024",
                },
                {
                    "term name": "B Cell",
                    "adjusted p-value": 0.05,
                    "combined score": 50.0,
                    "overlapping genes": ["CD19"],
                    "gene_set": "CellMarker_2024",
                },
            ]
            return pd.DataFrame(data)

    monkeypatch.setattr("sc_bot.tools.Enrichr", MockEnrichr)

    genes = ["CD3D", "CD3E", "CD8A", "CD19"]
    result = query_enrichr.invoke({"genes": genes})

    assert len(result) == 2  # Combined T Cell + B Cell

    # Check that T Cell is first due to lower adjusted_p_value
    t_cell = result[0]
    assert t_cell["term_name"] == "T Cell"
    assert t_cell["adjusted_p_value"] == 0.001  # Best across the group
    assert t_cell["combined_score"] == 150.5  # Taken from the best row

    # Overlapping genes should be unioned and returned as list
    overlapping = set(t_cell["overlapping_genes"])
    assert overlapping == {"CD3D", "CD3E", "CD8A"}

    # Both gene sets should be included
    gene_sets = set(t_cell["gene_sets"])
    assert gene_sets == {"PanglaoDB_Augmented_2021", "CellMarker_2024"}
