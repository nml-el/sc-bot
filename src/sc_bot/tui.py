import json
import logging
import re
from typing import Any

from rich.console import RenderableType
from rich.markdown import Markdown
from rich.text import Text
from rich.align import Align
from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll, Container
from textual.widgets import Input, Static, Button
from textual.worker import get_current_worker
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

from sc_bot.agent import format_output
from sc_bot.config import LLM_MODEL
from sc_bot.models import AgentResponse, InteractionMode


# Block font ASCII Art
ASCII_ART = """
███████╗ ██████╗       ██████╗  ██████╗ ████████╗
██╔════╝██╔════╝       ██╔══██╗██╔═══██╗╚══██╔══╝
███████╗██║      █████╗██████╔╝██║   ██║   ██║   
╚════██║██║      ╚════╝██╔══██╗██║   ██║   ██║   
███████║╚██████╗       ██████╔╝╚██████╔╝   ██║   
╚══════╝ ╚═════╝       ╚═════╝  ╚═════╝    ╚═╝   
"""

# Tokyo Night Theme Colors
THEME_BG = "#1a1b26"
THEME_FG = "#c0caf5"
COLOR_USER = "#7aa2f7"
COLOR_AI = "#9ece6a"
COLOR_ERROR = "#f7768e"
COLOR_THINKING = "#e0af68"
COLOR_STATUS = "#7dcfff"


class ChatMessage(Container):
    """A widget to display a chat message within a styled container."""

    def __init__(
        self,
        content: RenderableType | str,
        role: str,
        marker_sections: list[tuple[str, str, str]] | None = None,
        copy_all_text: str | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._msg_content = content
        self.role = role
        self.marker_sections = marker_sections
        self.copy_all_text = copy_all_text

    def compose(self) -> ComposeResult:
        if self.copy_all_text:
            yield Button("📋", id=f"copy-all-{id(self)}", classes="copy-all-btn")

        yield Static(self._msg_content, classes="msg-content")

        if self.marker_sections:
            for idx, (label, display_json, _copy_json) in enumerate(self.marker_sections):
                yield Static(Markdown(f"**{label}:**"), classes="section-label")
                with Container(classes="code-box"):
                    yield Static(Markdown(f"```python\n{display_json}\n```"), classes="code-content")
                    yield Button("📋", id=f"section-copy-{id(self)}-{idx}", classes="section-copy-btn")

    def on_mount(self) -> None:
        if self.role == "user":
            self.border_title = "User"
            self.classes = "role-user"
        elif self.role == "ai":
            self.border_title = "sc-bot"
            self.classes = "role-ai"
        elif self.role == "error":
            self.border_title = "Error"
            self.classes = "role-error"
        elif self.role == "system":
            self.border_title = "System"
            self.classes = "role-system"
        elif self.role == "thinking":
            self.border_title = "sc-bot is thinking..."
            self.classes = "role-thinking"
        else:
            self.classes = "role-system"

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.has_class("copy-all-btn") and self.copy_all_text:
            self.app.copy_to_clipboard(self.copy_all_text)
            self.app.notify("Copied all markers!", timeout=3)
        elif event.button.has_class("section-copy-btn") and self.marker_sections:
            button_id = event.button.id or ""
            prefix = f"section-copy-{id(self)}-"
            if button_id.startswith(prefix):
                try:
                    idx = int(button_id[len(prefix) :])
                except ValueError:
                    return
                if 0 <= idx < len(self.marker_sections):
                    label, _display, copy_json = self.marker_sections[idx]
                    self.app.copy_to_clipboard(copy_json)
                    self.app.notify(f"Copied {label.lower()}!", timeout=3)


class ModeInput(Input):
    """Chat input widget with a local Tab binding for mode switching."""

    BINDINGS = [
        Binding("tab", "app.toggle_mode", "Toggle Mode", show=False),
        Binding("up", "app.cycle_history(-1)", "History Up", show=False),
        Binding("down", "app.cycle_history(1)", "History Down", show=False),
        Binding("escape", "app.clear_input", "Clear Input", show=False),
    ]


class ScBotApp(App):
    """A Textual App for sc-bot."""

    CSS = f"""
    Screen {{
        background: {THEME_BG};
        color: {THEME_FG};
    }}
    
    #chat-container {{
        height: 1fr;
        padding: 1 2;
    }}
    
    ChatMessage {{
        margin-bottom: 1;
        width: 100%;
        padding: 0 1;
        height: auto;
        background: {THEME_BG};
        position: relative;
    }}

    ChatMessage.role-user {{
        border: solid {COLOR_USER};
        border-title-align: right;
        border-title-color: {COLOR_USER};
    }}
    
    ChatMessage.role-ai {{
        border: solid {COLOR_AI};
        border-title-align: left;
        border-title-color: {COLOR_AI};
    }}
    
    ChatMessage.role-error {{
        border: solid {COLOR_ERROR};
        border-title-color: {COLOR_ERROR};
    }}
    
    ChatMessage.role-system {{
        border: solid {THEME_FG};
        border-title-align: center;
        border-title-color: {THEME_FG};
    }}
    
    ChatMessage.role-thinking {{
        border: solid {COLOR_THINKING};
        border-title-color: {COLOR_THINKING};
    }}

    .msg-content {{
        height: auto;
        padding-top: 1;
    }}

    .section-label {{
        height: auto;
        padding-top: 1;
    }}

    .code-box {{
        height: auto;
        position: relative;
        background: #24283b;
    }}

    .code-content {{
        height: auto;
    }}

    .section-copy-btn {{
        dock: right;
        background: transparent;
        color: {THEME_FG};
        border: none;
        min-width: 5;
        height: 1;
        padding: 0;
    }}
    .section-copy-btn:hover {{
        color: {COLOR_AI};
        background: transparent;
    }}

    .copy-all-btn {{
        dock: right;
        background: transparent;
        color: {THEME_FG};
        border: none;
        min-width: 5;
        height: 1;
        padding: 0;
    }}
    .copy-all-btn:hover {{
        color: {COLOR_AI};
        background: transparent;
    }}

    #chat-input {{
        dock: bottom;
        margin: 1 2;
        background: #24283b;
        color: {THEME_FG};
        border: solid {COLOR_USER};
    }}
    #chat-input:focus {{
        border: thick {COLOR_AI};
    }}

    #mode-status {{
        dock: bottom;
        margin: 0 2;
        padding: 0 1;
        background: #24283b;
        color: {COLOR_STATUS};
        height: 1;
    }}
    """

    def __init__(self, agents: dict[InteractionMode, Any], logger: logging.Logger, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.agents = agents
        self.logger = logger
        self.chat_history: list = []
        self.user_messages: list[str] = []
        self.history_index: int = -1
        self.mode: InteractionMode = "assist"

    def _mode_status_text(self) -> Text:
        """
        Returns the one-line mode status text with model name, color-coded.

        Args:
            None

        Returns:
            Text: Styled status text with color-coded mode and model name.

        Raises:
            None
        """
        mode_color = COLOR_AI if self.mode == "assist" else COLOR_USER  # green for Assist, blue for Fetch
        mode_name = self.mode.capitalize()
        model_text = Text(f"Model: {LLM_MODEL}", style=THEME_FG)
        return Text.from_markup(f"Mode: [{mode_color}]{mode_name}[/{mode_color}] · ") + model_text

    def _input_placeholder(self) -> str:
        """
        Returns the input placeholder for the active session mode.

        Args:
            None

        Returns:
            str: Mode-specific placeholder text.

        Raises:
            None
        """
        if self.mode == "fetch":
            return "Fetch mode: retrieve marker genes, cell-type matches, and aliases from the database..."

        return "Assist mode: ask follow-up questions, biological interpretation, or cell type identification from gene lists..."

    def _set_mode(self, mode: InteractionMode) -> None:
        """
        Updates the active session mode and refreshes the input placeholder.

        Args:
            mode (InteractionMode): The new session mode.

        Returns:
            None

        Raises:
            None
        """
        self.mode = mode
        self.query_one("#chat-input", ModeInput).placeholder = self._input_placeholder()
        self.query_one("#mode-status", Static).update(self._mode_status_text())

    def action_toggle_mode(self) -> None:
        """
        Toggles between assist and fetch modes.

        Args:
            None

        Returns:
            None

        Raises:
            None
        """
        next_mode: InteractionMode = "fetch" if self.mode == "assist" else "assist"
        self._set_mode(next_mode)

    def action_cycle_history(self, direction: int) -> None:
        """
        Cycles through previous user messages in the input field.

        Args:
            direction (int): -1 to go to older message, 1 to go to newer message.

        Returns:
            None

        Raises:
            None
        """
        if not self.user_messages:
            return

        if self.history_index == -1:
            if direction == -1:
                self.history_index = len(self.user_messages) - 1
            else:
                return
        else:
            new_index = self.history_index + direction
            if new_index < 0 or new_index >= len(self.user_messages):
                return
            self.history_index = new_index

        input_widget = self.query_one("#chat-input", ModeInput)
        input_widget.value = self.user_messages[self.history_index]
        input_widget.cursor_position = len(input_widget.value)

    def action_clear_input(self) -> None:
        """
        Clears the input field without submitting.

        Args:
            None

        Returns:
            None

        Raises:
            None
        """
        input_widget = self.query_one("#chat-input", ModeInput)
        input_widget.value = ""
        self.history_index = -1

    def _render_system_message(self, message: str) -> None:
        """
        Mounts a system message in the chat container.

        Args:
            message (str): Text to display.

        Returns:
            None

        Raises:
            None
        """
        container = self.query_one("#chat-container", VerticalScroll)
        container.mount(ChatMessage(Markdown(message), role="system"))
        container.scroll_end(animate=False)

    def _handle_mode_command(self, user_text: str) -> bool:
        """
        Handles slash commands for session mode changes.

        Args:
            user_text (str): Raw user input.

        Returns:
            bool: `True` if the input was handled as a command, otherwise `False`.

        Raises:
            None
        """
        normalized = user_text.strip().lower()
        if normalized == "/assist":
            self._set_mode("assist")
            self._render_system_message(
                "Switched to **Assist** mode. Conversational analysis and biological interpretation are now the default."
            )
            return True

        if normalized == "/fetch":
            self._set_mode("fetch")
            self._render_system_message(
                "Switched to **Fetch** mode. Database-only retrieval of markers, aliases, and cell-type matches are now the default."
            )
            return True

        if normalized == "/help":
            self._render_help_message()
            return True

        return False

    def _render_help_message(self) -> None:
        """
        Renders the help message with mode descriptions and keyboard shortcuts.

        Args:
            None

        Returns:
            None

        Raises:
            None
        """
        help_text = Markdown(
            "**sc-bot Help**\n\n"
            "## Modes\n"
            "- **Assist** — Conversational analysis, biological interpretation, cell type ID from gene lists\n"
            "- **Fetch** — Database-only retrieval of markers, aliases, tissues, cell-type matches\n\n"
            "## Commands\n"
            "- `/assist` — Switch to Assist mode\n"
            "- `/fetch` — Switch to Fetch mode\n"
            "- `/help` — Show this help message\n\n"
            "## Keyboard Shortcuts\n"
            "- `Tab` — Toggle between Assist/Fetch modes\n"
            "- `↑` / `↓` — Cycle through previous messages in session\n"
            "- `Escape` — Clear input box\n\n"
            "*Type 'quit' or 'exit' to leave.*"
        )
        container = self.query_one("#chat-container", VerticalScroll)
        container.mount(ChatMessage(help_text, role="system"))
        container.scroll_end(animate=False)

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield VerticalScroll(id="chat-container")
        yield Static(self._mode_status_text(), id="mode-status")
        yield ModeInput(placeholder=self._input_placeholder(), id="chat-input")

    def on_mount(self) -> None:
        """Called when app starts."""
        container = self.query_one("#chat-container", VerticalScroll)

        # Add ASCII Art
        ascii_text = Text(ASCII_ART, style=f"bold {COLOR_USER}")
        centered_ascii = Align.center(ascii_text)
        container.mount(ChatMessage(centered_ascii, role="system"))

        # Add Use Cases Box
        use_cases = Markdown(
            "**Welcome to sc-bot!**\n\n"
            "Query single-cell transcriptomics data locally.\n"
            f"- Current mode: **{self.mode.capitalize()}**\n"
            "- Press `Tab` in the chat box to toggle modes\n"
            "- Use `/assist` for biological interpretation, cell type ID from genes, and follow-up questions\n"
            "- Use `/fetch` for database-only retrieval of markers, aliases, tissues, or cell-type matches\n"
            "- Find common markers between cells (e.g., 'common genes between T cells and B cells')\n"
            "- Identify cell types by marker (e.g., 'what expresses CD3E and CD8A?')\n"
            "- List all available cell types.\n\n"
            "*Type 'quit' or 'exit' to leave.*"
        )
        container.mount(ChatMessage(use_cases, role="ai"))

        # Focus the input
        self.query_one("#chat-input", ModeInput).focus()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle user input."""
        user_text = event.value.strip()
        if not user_text:
            return

        input_widget = self.query_one("#chat-input", ModeInput)
        input_widget.value = ""

        if user_text.lower() in ["quit", "exit"]:
            self.exit()
            return

        if self._handle_mode_command(user_text):
            return

        self.logger.info(f"User Input: {user_text}")

        # Display user message
        container = self.query_one("#chat-container", VerticalScroll)
        await container.mount(ChatMessage(user_text, role="user"))
        container.scroll_end(animate=False)

        # Add user message to LangChain history
        self.chat_history.append(HumanMessage(user_text))

        # Track user messages for history cycling and reset history index
        self.user_messages.append(user_text)
        self.history_index = -1

        # Mount a "Thinking..." placeholder
        thinking_widget = ChatMessage("...", role="thinking")
        await container.mount(thinking_widget)
        container.scroll_end(animate=False)

        # Disable input while processing
        input_widget.disabled = True

        # Process the response in a background thread
        self.process_message(self.chat_history.copy(), thinking_widget, self.mode)

    @work(thread=True)
    def process_message(self, messages_copy: list, thinking_widget: ChatMessage, mode: InteractionMode) -> None:
        """Runs the LangGraph agent in a background thread so UI doesn't freeze."""
        worker = get_current_worker()
        initial_len = len(messages_copy)

        try:
            # Synchronous blocking call
            response = self.agents[mode].invoke({"messages": messages_copy})

            if worker.is_cancelled:
                return

            new_messages = response["messages"]

            # Log what happened
            for msg in new_messages[initial_len:]:
                if isinstance(msg, AIMessage):
                    if msg.tool_calls:
                        for tool_call in msg.tool_calls:
                            self.logger.info(f"Tool Call: {tool_call['name']} {tool_call['args']}")
                    if msg.content:
                        self.logger.info(f"Agent Thought: {msg.content}")
                elif isinstance(msg, ToolMessage):
                    self.logger.info(f"Tool executed. Name: {msg.name}")

            # Update master history
            self.chat_history = new_messages

            # Extract the structured final response — walk backwards for the last
            # AIMessage with actual text content.  When the LLM returns an empty
            # content string (common with Gemini after tool-only turns), fall back
            # to concatenating the ToolMessage outputs from this turn so the
            # formatter still receives useful data.
            raw_ai_message = ""
            for msg in reversed(new_messages[initial_len:]):
                if isinstance(msg, AIMessage) and msg.content:
                    raw_ai_message = msg.content
                    # Handle Gemini returning list instead of string
                    if isinstance(raw_ai_message, list):
                        raw_ai_message = "\n".join(str(item) for item in raw_ai_message)
                    break

            if not raw_ai_message:
                tool_parts = [
                    str(msg.content)
                    for msg in new_messages[initial_len:]
                    if isinstance(msg, ToolMessage) and msg.content
                ]
                raw_ai_message = "\n\n".join(tool_parts)

            structured_data = format_output(raw_ai_message, mode=mode)

            self.call_from_thread(self._render_ai_response, structured_data, thinking_widget, mode)

        except Exception as e:
            self.logger.error(f"Error during agent invocation: {e}", exc_info=True)
            self.call_from_thread(self._render_error, str(e), thinking_widget)

    def _highlight_response_terms(self, content: str, response_data: AgentResponse, mode: InteractionMode) -> str:
        """
        Wraps supported response terms in inline-code markdown for display.

        Args:
            content (str): Base prose content to highlight.
            response_data (AgentResponse): Structured response data.
            mode (InteractionMode): Session mode that produced the response.

        Returns:
            str: Content with inline-code formatting applied to supported terms.

        Raises:
            None
        """
        highlighted = content
        highlight_specs: list[tuple[str, int]] = []
        seen_keys: set[str] = set()

        for section in response_data.marker_sections:
            for gene in section.genes:
                gene_clean = gene.strip()
                if not gene_clean or gene_clean in seen_keys:
                    continue

                seen_keys.add(gene_clean)
                highlight_specs.append((gene_clean, 0))

        if mode == "assist":
            for cell_type in response_data.cell_types:
                cell_type_clean = cell_type.strip()
                cell_type_key = cell_type_clean.casefold()
                if not cell_type_clean or cell_type_key in seen_keys:
                    continue

                seen_keys.add(cell_type_key)
                highlight_specs.append((cell_type_clean, re.IGNORECASE))

        for term, flags in sorted(highlight_specs, key=lambda item: len(item[0]), reverse=True):
            pattern = re.compile(rf"(?<![\w`])({re.escape(term)})(?![\w`])", flags)
            highlighted = pattern.sub(lambda match: f"`{match.group(1)}`", highlighted)

        return highlighted

    def _render_ai_response(
        self, response_data: AgentResponse, thinking_widget: ChatMessage, mode: InteractionMode
    ) -> None:
        """Runs on the UI thread to update the UI with the final response."""
        # Replace the thinking widget with the actual response
        thinking_widget.remove()

        container = self.query_one("#chat-container", VerticalScroll)

        content = self._highlight_response_terms(response_data.response, response_data, mode)
        marker_sections_data: list[tuple[str, str, str]] | None = None
        copy_all_text = None

        if response_data.response_type == "markers" and response_data.marker_sections:
            marker_sections_data = []
            combined_markers = {}

            for section in response_data.marker_sections:
                if not section.genes:
                    continue
                display_json = json.dumps(section.genes)
                copy_json = json.dumps(section.genes, indent=2)
                marker_sections_data.append((section.label, display_json, copy_json))
                combined_markers[section.label] = section.genes

            copy_all_text = json.dumps(combined_markers, indent=2)

        container.mount(
            ChatMessage(Markdown(content), role="ai", marker_sections=marker_sections_data, copy_all_text=copy_all_text)
        )
        container.scroll_end(animate=False)

        # Re-enable input
        input_widget = self.query_one("#chat-input", ModeInput)
        input_widget.disabled = False
        input_widget.focus()

    def _render_error(self, error_msg: str, thinking_widget: ChatMessage) -> None:
        """Runs on the UI thread to display an error."""
        thinking_widget.remove()

        container = self.query_one("#chat-container", VerticalScroll)
        container.mount(ChatMessage(f"An error occurred: {error_msg}", role="error"))
        container.scroll_end(animate=False)

        input_widget = self.query_one("#chat-input", ModeInput)
        input_widget.disabled = False
        input_widget.focus()
