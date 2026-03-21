from sc_bot.tools import get_all_cell_types, get_cell_types_by_marker, get_markers_by_cell_type


def test_get_all_cell_types() -> None:
    cell_types = get_all_cell_types.invoke({})
    assert "T cells" in cell_types
    assert "B cells" in cell_types


def test_t_cell_markers() -> None:
    markers = get_markers_by_cell_type.invoke({"cell_types": ["T cells"]})
    assert isinstance(markers, list)
    assert len(markers) > 0
    # Find CD3E in the returned markers
    marker_genes = [m["marker_gene"] for m in markers]
    assert "CD3E" in marker_genes


def test_b_cell_markers() -> None:
    markers = get_markers_by_cell_type.invoke({"cell_types": ["B cells"]})
    assert isinstance(markers, list)
    assert len(markers) > 0
    marker_genes = [m["marker_gene"] for m in markers]
    assert "CD19" in marker_genes


def test_common_markers_t_and_b_cells() -> None:
    markers = get_markers_by_cell_type.invoke({"cell_types": ["T cells", "B cells"]})
    assert isinstance(markers, list)
    marker_genes = [m["marker_gene"] for m in markers]
    # CXCR4 is a known common marker between T cells and B cells in PanglaoDB
    assert "CXCR4" in marker_genes


def test_cell_types_by_marker_cd3e() -> None:
    cell_types = get_cell_types_by_marker.invoke({"marker_genes": ["CD3E"]})
    assert isinstance(cell_types, list)
    cell_type_names = [c["cell_type"] for c in cell_types]
    assert "T cells" in cell_type_names


def test_cell_types_by_marker_cd19() -> None:
    cell_types = get_cell_types_by_marker.invoke({"marker_genes": ["CD19"]})
    assert isinstance(cell_types, list)
    cell_type_names = [c["cell_type"] for c in cell_types]
    assert "B cells" in cell_type_names


def test_cell_types_by_multiple_markers() -> None:
    # A cell type that expresses both CD3E and CD8A
    cell_types = get_cell_types_by_marker.invoke({"marker_genes": ["CD3E", "CD8A"]})
    assert isinstance(cell_types, list)
    cell_type_names = [c["cell_type"] for c in cell_types]
    assert "T cells" in cell_type_names
