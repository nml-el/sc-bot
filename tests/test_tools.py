from tools import get_all_cell_types, get_cell_types_by_marker, get_markers_by_cell_type


def test_get_all_cell_types() -> None:
    cell_types = get_all_cell_types.invoke({})
    assert "T cells" in cell_types
    assert "B cells" in cell_types


def test_t_cell_markers() -> None:
    markers = get_markers_by_cell_type.invoke({"cell_type": "T cells"})
    assert isinstance(markers, list)
    assert len(markers) > 0
    # Find CD3E in the returned markers
    marker_genes = [m["marker_gene"] for m in markers]
    assert "CD3E" in marker_genes

    # Verify properties
    cd3e_marker = next(m for m in markers if m["marker_gene"] == "CD3E")
    assert cd3e_marker["tissue"] == "Immune system"


def test_b_cell_markers() -> None:
    markers = get_markers_by_cell_type.invoke({"cell_type": "B cells"})
    assert isinstance(markers, list)
    assert len(markers) > 0
    marker_genes = [m["marker_gene"] for m in markers]
    assert "CD19" in marker_genes


def test_cell_types_by_marker_cd3e() -> None:
    cell_types = get_cell_types_by_marker.invoke({"marker_gene": "CD3E"})
    assert isinstance(cell_types, list)
    cell_type_names = [c["cell_type"] for c in cell_types]
    assert "T cells" in cell_type_names


def test_cell_types_by_marker_cd19() -> None:
    cell_types = get_cell_types_by_marker.invoke({"marker_gene": "CD19"})
    assert isinstance(cell_types, list)
    cell_type_names = [c["cell_type"] for c in cell_types]
    assert "B cells" in cell_type_names
