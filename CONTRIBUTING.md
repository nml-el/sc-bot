# Contributing to sc-bot

Contributions are welcome!

## General Project Contributions

- Open an issue or discussion if you want to propose a feature, workflow improvement, or data-source change.
- Submit pull requests for bug fixes, agent behavior improvements, docs updates, tests, or database ingestion improvements.
- Keep changes focused, follow the existing code style, and include or update tests when behavior changes.

### Development Commands

*   Run tests: `uv run pytest`
*   Format code: `uv run ruff format .`
*   Lint code: `uv run ruff check .`
*   Lint and auto-fix: `uv run ruff check --fix .`

---

## Add Your Own Marker CSV

You can extend sc-bot with your own marker table by placing a CSV file at `~/.sc-bot/marker_data.csv` (see `marker_data.sample.csv` in the repo). If that file exists, sc-bot will automatically refresh it on launch as long as the main database has already been initialized.

Required columns:
- `species` (`Human` or `Mouse`)
- `cell_type`
- `tissue`
- `marker_gene`

Optional columns:
- `gene_aliases` - pipe-delimited aliases like `CD161|NKR-P1A`; leave blank if none
- `source` - source label for the row; defaults to `custom-source` when left blank

Example with aliases, blank optional fields, and custom sources:

```csv
species,cell_type,tissue,marker_gene,gene_aliases,source
Human,Natural killer cell,Blood,KLRB1,CD161|NKR-P1A,lab-flow-panel
Human,Plasma cell,Bone marrow,SDC1,CD138,lab-flow-panel
Human,CD8+ T cell,Blood,CD8A,,in-house-rnaseq
Human,Epithelial cell,Lung,EPCAM,,
Mouse,Regulatory T cell,Spleen,Foxp3,,in-house-rnaseq
Mouse,B cell,Bone marrow,Ms4a1,CD20,
```

Your personal markers are prioritized during ranking, so user-supplied evidence is surfaced before equally supported public markers.