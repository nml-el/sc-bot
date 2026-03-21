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
    # CXCR4 is a known common marker between T cells and B cells in PanglaoDB (Human)
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


def test_mouse_t_cell_markers() -> None:
    markers = get_markers_by_cell_type.invoke({"cell_types": ["T cells"], "species": "Mouse"})
    assert isinstance(markers, list)
    assert len(markers) > 0
    marker_genes = [m["marker_gene"] for m in markers]
    assert "CD3E" in marker_genes


def test_species_isolation_mouse_exclusive() -> None:
    # TRY4 is a Mouse-exclusive marker for Acinar cells in PanglaoDB
    human_cell_types = get_cell_types_by_marker.invoke({"marker_genes": ["TRY4"], "species": "Human"})
    mouse_cell_types = get_cell_types_by_marker.invoke({"marker_genes": ["TRY4"], "species": "Mouse"})

    assert len(human_cell_types) == 0, "TRY4 should not return results for Human"

    assert len(mouse_cell_types) > 0, "TRY4 should return results for Mouse"
    cell_type_names = [c["cell_type"] for c in mouse_cell_types]
    assert "Acinar cells" in cell_type_names


def test_species_isolation_human_exclusive() -> None:
    # CTRB2 is a Human-exclusive marker for Acinar cells in PanglaoDB
    human_cell_types = get_cell_types_by_marker.invoke({"marker_genes": ["CTRB2"], "species": "Human"})
    mouse_cell_types = get_cell_types_by_marker.invoke({"marker_genes": ["CTRB2"], "species": "Mouse"})

    assert len(mouse_cell_types) == 0, "CTRB2 should not return results for Mouse"

    assert len(human_cell_types) > 0, "CTRB2 should return results for Human"
    cell_type_names = [c["cell_type"] for c in human_cell_types]
    assert "Acinar cells" in cell_type_names
