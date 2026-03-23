# sc-bot: Your Single-Cell Biology Assistant 🧬

![sc-bot demo](assets/demo.gif)

**sc-bot** is a terminal-based chat assistant designed specifically for single-cell biology. It helps you quickly find cell type markers, resolve complex cell ontology queries, and explore single-cell data context—right from your command line, without needing a web browser or a clunky GUI.

---

## ⚡ Quick Setup (For Bioinformaticians)

We designed sc-bot to be lightweight and easy to install, even if you don't want to mess with complex Python environments. We use `uv`, an extremely fast Python package manager.

### Step 1: Install `uv`
If you are on a Mac, the easiest way is via Homebrew:
```bash
brew install uv
```
*(Alternatively, use curl: `curl -LsSf https://astral.sh/uv/install.sh | sh`)*

### Step 2: Get sc-bot
Clone this repository and let `uv` handle the rest automatically:
```bash
git clone https://github.com/nml-el/sc-bot.git
cd sc-bot
uv sync
```

### Step 3: Add your AI Key
sc-bot uses Google's Gemini AI to understand your biology questions. You need a free API key from Google AI Studio.
Create a `.env` file in the project folder to hold your key:
```bash
echo "GOOGLE_API_KEY=" > .env
```
*Open the `.env` file in your favorite text editor (e.g., nano, vim, or VS Code) and paste your API key after the equals sign.*

### Step 4: Run the bot!
You are all set. Launch the interactive terminal UI:
```bash
uv run sc-bot
```

---

## 🚀 Features

*   **Marker Gene Lookup:** Ask for markers for highly specific cell types (e.g., "What are the markers for exhausted CD8+ T cells?").
*   **Ontology Resolution:** Automatically resolves synonyms and traces lineage (e.g., it knows that a specific sub-type belongs to a broader lineage).
*   **Fuzzy Matching:** Don't worry about spelling complex cell ontology terms perfectly; the bot has built-in fuzzy matching.
*   **Clipboard Integration:** Easily copy cell markers or AI responses straight to your clipboard with built-in buttons.
*   **Distraction-Free:** A clean, beautiful terminal UI (Tokyo Night theme) that runs entirely inside your standard Mac Terminal, iTerm2, or Jupyter terminal.

---

## 🛠️ Under the Hood (For Developers)

For those curious about the mechanics:
*   **LLM & Orchestration:** Built with `LangChain`, `LangGraph`, and `Google GenAI` (Gemini 2.5 Flash Lite).
*   **Terminal UI:** Powered by the incredible `Textual` framework.
*   **Offline Data & Caching:** Uses a local SQLite database (`~/.sc-bot/sc_markers.db`) for lightning-fast, offline-capable ontology lookups and exact/fuzzy matching.

### Development Commands
*   Run tests: `uv run pytest`
*   Format code: `uv run ruff format .`
*   Lint code: `uv run ruff check .`
