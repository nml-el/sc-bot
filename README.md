```text
███████╗ ██████╗       ██████╗  ██████╗ ████████╗
██╔════╝██╔════╝       ██╔══██╗██╔═══██╗╚══██╔══╝
███████╗██║      █████╗██████╔╝██║   ██║   ██║   
╚════██║██║      ╚════╝██╔══██╗██║   ██║   ██║   
███████║╚██████╗       ██████╔╝╚██████╔╝   ██║   
╚══════╝ ╚═════╝       ╚═════╝  ╚═════╝    ╚═╝   
```

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

### 3. Configure API Key
sc-bot requires a Google Gemini API key. Generate a key from Google AI Studio.
Create a `.env` file in the project directory:
```bash
echo "GOOGLE_API_KEY=" > .env
```
*Open the `.env` file in a text editor (e.g., nano, vim, or VS Code) and append your API key after the equals sign.*

### 4. Run sc-bot
Launch the interactive terminal UI:
```bash
uv run sc-bot
```

---

## Features

*   **Marker Gene Querying:** Retrieve canonical and supportive marker genes for specific cell types.
*   **Ontology Resolution:** Automatically resolve synonyms and trace lineage within the cell ontology network.
*   **Fuzzy Matching:** Support for approximate string matching on cell type queries.
*   **Clipboard Integration:** Built-in UI actions to copy structured marker data to the system clipboard.
*   **Terminal UI:** Text-based interface compatible with standard terminal emulators.

---

## Architecture & Development

*   **Orchestration:** LangChain, LangGraph, and Google GenAI (Gemini 2.5 Flash Lite).
*   **Interface:** Textual.
*   **Offline Data:** Local SQLite database (`~/.sc-bot/sc_markers.db`) for ontology lookups and matching.

### Development Commands
*   Run tests: `uv run pytest`
*   Format code: `uv run ruff format .`
*   Lint code: `uv run ruff check .`
