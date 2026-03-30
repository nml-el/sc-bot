from sc_bot.tools import (
    get_all_cell_types,
    get_cell_types_by_marker,
    get_markers_by_cell_type,
    get_tissues_for_cell_type,
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
