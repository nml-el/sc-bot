<div align="center">
<pre>
███████╗ ██████╗       ██████╗  ██████╗ ████████╗
██╔════╝██╔════╝       ██╔══██╗██╔═══██╗╚══██╔══╝
███████╗██║      █████╗██████╔╝██║   ██║   ██║   
╚════██║██║      ╚════╝██╔══██╗██║   ██║   ██║   
███████║╚██████╗       ██████╔╝╚██████╔╝   ██║   
╚══════╝ ╚═════╝       ╚═════╝  ╚═════╝    ╚═╝   
</pre>
</div>

**sc-bot** is a terminal-based conversational interface for single-cell biology. It acts as an expert computational biology assistant, powered by a local multi-source SQLite database and LLM reasoning.

![sc-bot exhausted cd8 demo](assets/demo_exhausted_cd8.gif)

---

## Dual Workflows

sc-bot is split into two distinct, sticky session modes designed for different stages of your analysis. You can switch between them instantly using the `Tab` key.

### Assist Mode (`/assist`)
**For biological interpretation and conversational analysis.**
- **Reverse Cell Typing:** Paste a list of DEGs and ask "What cell type is this?" sc-bot combines internal biological reasoning with external Enrichr library queries to infer the identity.
- **Follow-up Analysis:** Ask clarifying questions about lineage, cell state vs. stable identity, clustering artifacts, or technical noise.
- **Contextual Guidance:** Get advice on tissue-specific markers or handling ambiguous sub-clustering.

### Fetch Mode (`/fetch`)
**For structured, database-only retrieval.**
- **Marker Retrieval:** Query markers for known populations (e.g., "endothelial cells in lung"). Results are strictly curated to the **top 8 Primary Canonical Markers** ranked by multi-source consensus.
- **Alias Resolution:** Translate common gene names and CD antigens (e.g., `CD16`, `CD161`) into canonical HGNC symbols.
- **Shared Markers:** Find overlapping marker genes between multiple cell types.
- **Structured Output:** Results are presented in clean code blocks with one-click copy buttons, bypassing conversational fluff.

---

## Interactive Terminal UI

sc-bot is built on Textual and features a modern, responsive CLI environment:

- **Per-Section Copy Actions:** Marker lists are rendered in isolated code blocks with a `📋` button to copy just that subset directly to your clipboard.
- **Keyboard Navigation:** 
  - `Tab` — Toggle instantly between Assist and Fetch modes
  - `↑` / `↓` — Cycle through your previous queries in the current session
  - `Escape` — Clear the input box
- **Commands:** Type `/help` at any time to see available modes, commands, and shortcuts.
- **Theming:** Status bars and UI elements are color-coded using the Tokyo Night theme for quick mode recognition.

---

## Installation

sc-bot requires `uv` for Python package management and a Google Gemini API key.

### 1. Install `uv`
To install on macOS via Homebrew:
```bash
brew install uv
```
*(Alternatively, use curl: `curl -LsSf https://astral.sh/uv/install.sh | sh`)*

### 2. Clone and Set Up
Clone the repository and install dependencies:
```bash
git clone https://github.com/nml-el/sc-bot.git
cd sc-bot
uv sync
```

### 3. Initialize the Database
sc-bot relies on PanglaoDB, CellMarker 2.0, ScType, CellTypist, and the Uberon ontology.
You do not need to download these files manually. Build the local SQLite database with the orchestrator script, which automatically downloads the required data sources, parses them, and maps tissues and cell types to the ontology.

```bash
uv run python scripts/setup_db.py
```

*Note: You can ingest specific databases using flags like `--panglao`, `--cellmarker2`, `--sctype`, or `--celltypist`, or preserve the schema while refreshing data with `--keep-schema`.*
sc-bot also rebuilds the local database automatically when the installed app version changes, so schema and source updates are applied on first launch after an upgrade.

### 4. Configure API Key
sc-bot requires a Google Gemini API key. Generate one in [Google AI Studio](https://aistudio.google.com/).
Copy the example environment file:
```bash
cp .env.example .env
```
*Open `.env` in a text editor (e.g., nano, vim, or VS Code) and replace the placeholder value for `GOOGLE_API_KEY`.*

### 5. Run sc-bot
Launch the interactive terminal UI:
```bash
uv run sc-bot
```

---

## Feature Showcase

Explore core sc-bot workflows through short GIF walkthroughs.

### Reverse Cell Typing From a Gene List
This workflow starts from a marker panel and uses enrichment-guided reasoning to infer the most likely cell identity.

![sc-bot gene list demo](assets/demo_gene_list.gif)

### Resolve Gene Aliases
This workflow translates names like `CD16` and `CD161` into the internal canonical symbols used by the database.

![sc-bot alias demo](assets/demo_aliases.gif)

---

## Contributing

Contributions are welcome.

### General project contributions

- Open an issue or discussion if you want to propose a feature, workflow improvement, or data-source change.
- Submit pull requests for bug fixes, agent behavior improvements, docs updates, tests, or database ingestion improvements.
- Keep changes focused, follow the existing code style, and include or update tests when behavior changes.

### Add your own marker CSV

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

---

## Features

*   **Multi-Source Marker Querying:** Retrieve canonical and supportive marker genes for specific cell types from multiple integrated databases (PanglaoDB + CellMarker 2.0 + ScType + CellTypist).
*   **Reverse Cell Type Identification:** Infer likely cell identities from a list of genes using local marker lookups and enrichment analysis.
*   **Gene Alias Resolution:** Translate common gene aliases to canonical symbols and account for them in queries.
*   **Tissue-Aware Filtering:** Filter marker genes based on specific tissue constraints (e.g., Lungs vs. Kidneys). Queries map automatically between diverse source nomenclatures (e.g., "Lung" -> "Lungs") and canonical tissue lists.
*   **Consensus Scoring:** Rank markers by counting their occurrence across multiple tissues (`tissue_count`) and disparate data sources (`source_count`), separating robust core primary markers from secondary context-specific ones.
*   **Ontology Resolution:** Automatically resolve synonyms and trace lineage within the cell ontology network.

---

## Data Sources

*   **PanglaoDB:** Marker genes and conservative tissue categories.
*   **CellMarker 2.0:** Additional marker coverage with more granular tissue labels mapped into the internal tissue system.
*   **ScType:** Positive marker definitions from the ScType reference database, normalized into the same local query workflow with mixed-case gene symbols promoted to human-style uppercase where appropriate.
*   **CellTypist:** Curated immune markers from the Pan-Immune CellTypist atlas, using the low-hierarchy cell type labels under the canonical `Immune system` tissue.
*   **Uberon / ontology graph:** Used to normalize and resolve cell type names, synonyms, and lineage relationships.

All data is stored locally in `~/.sc-bot/sc_markers.db` after setup.

---

## Architecture & Development

*   **Orchestration:** LangChain, LangGraph, and Google GenAI (Gemini).
*   **Interface:** Textual.
*   **Offline Data:** Local SQLite database (`~/.sc-bot/sc_markers.db`) mapped by Python scripts from PanglaoDB, CellMarker 2.0, ScType, and CellTypist.

### Development Commands
*   Run tests: `uv run pytest`
*   Format code: `uv run ruff format .`
*   Lint code: `uv run ruff check .`
*   Lint and auto-fix: `uv run ruff check --fix .`

---

## License

This project is released under the MIT License. See `LICENSE` for the full text.