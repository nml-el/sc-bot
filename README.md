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

**sc-bot** is a terminal-based conversational interface for single-cell biology. It provides functionality to query cell type markers, resolve cell ontology lineages, and explore single-cell data context directly from the command line.

![sc-bot demo](assets/demo.gif)

---

## Installation

sc-bot requires `uv` for Python package management and a Google Gemini API key.

### 1. Install `uv`
To install on macOS via Homebrew:
```bash
brew install uv
```
*(Alternatively, use curl: `curl -LsSf https://astral.sh/uv/install.sh | sh`)*

### 2. Clone and Setup
Clone the repository and install dependencies:
```bash
git clone https://github.com/nml-el/sc-bot.git
cd sc-bot
uv sync
```

### 3. Download Raw Data
sc-bot relies on PanglaoDB, CellMarker 2.0, and the Uberon ontology. 
PanglaoDB and Uberon must be downloaded manually into the `data/raw/` directory, while CellMarker 2.0 is downloaded automatically during database setup.

```bash
# Create the raw data directory if it doesn't exist
mkdir -p data/raw

# Download and unzip PanglaoDB markers
curl -o data/raw/PanglaoDB_markers_27_Mar_2020.tsv.gz https://panglaodb.se/markers/PanglaoDB_markers_27_Mar_2020.tsv.gz
gunzip data/raw/PanglaoDB_markers_27_Mar_2020.tsv.gz

# Download Uberon ontology
curl -L -o data/raw/uberon-full.json http://purl.obolibrary.org/obo/uberon/uberon-full.json
```

### 4. Initialize the Database
Build the local SQLite database from the data sources using the orchestrator script. This will parse PanglaoDB, download and parse CellMarker 2.0, and map tissues and cell types to the ontology.

```bash
uv run python scripts/setup_db.py
```

*Note: You can ingest specific databases using flags like `--panglao` or `--cellmarker2`, or preserve the schema while refreshing data with `--keep-schema`.*

### 5. Configure API Key
sc-bot requires a Google Gemini API key. Generate a key from Google AI Studio.
Create a `.env` file in the project directory:
```bash
echo "GOOGLE_API_KEY=" > .env
```
*Open the `.env` file in a text editor (e.g., nano, vim, or VS Code) and append your API key after the equals sign.*

### 6. Run sc-bot
Launch the interactive terminal UI:
```bash
uv run sc-bot
```

---

## Features

*   **Multi-Source Marker Querying:** Retrieve canonical and supportive marker genes for specific cell types from multiple integrated databases (PanglaoDB + CellMarker 2.0).
*   **Tissue-Aware Filtering:** Filter marker genes based on specific tissue constraints (e.g., Lungs vs. Kidneys). Queries map automatically between diverse source nomenclatures (e.g., "Lung" -> "Lungs") and canonical tissue lists.
*   **Consensus Scoring:** Rank markers by counting their occurrence across multiple tissues (`tissue_count`) and disparate data sources (`source_count`), separating robust core primary markers from secondary context-specific ones.
*   **Ontology Resolution:** Automatically resolve synonyms and trace lineage within the cell ontology network.
*   **Fuzzy Matching:** Support for approximate string matching on cell type queries.
*   **Clipboard Integration:** Built-in UI actions to copy structured marker data to the system clipboard.
*   **Terminal UI:** Text-based interface compatible with standard terminal emulators.

---

## Architecture & Development

*   **Orchestration:** LangChain, LangGraph, and Google GenAI (Gemini).
*   **Interface:** Textual.
*   **Offline Data:** Local SQLite database (`~/.sc-bot/sc_markers.db`) mapped by Python scripts from PanglaoDB and CellMarker 2.0.

### Development Commands
*   Run tests: `uv run pytest`
*   Format code: `uv run ruff format .`
*   Lint code: `uv run ruff check .`
