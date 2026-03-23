import json
import logging
from typing import Any

from rich.console import RenderableType
from rich.markdown import Markdown
from rich.text import Text
from textual import work
from textual.app import App, ComposeResult
from textual.containers import VerticalScroll, Container, Horizontal
from textual.widgets import Input, Static, Button
from textual.worker import get_current_worker
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

from sc_bot.agent import format_output
from sc_bot.models import AgentResponse


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


class ChatMessage(Container):
    """A widget to display a chat message within a styled container."""

    def __init__(
        self,
        content: RenderableType | str,
        role: str,
        copy_actions: dict[str, str] | None = None,
        copy_all_text: str | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._msg_content = content
        self.role = role
        self.copy_actions = copy_actions
        self.copy_all_text = copy_all_text

    def compose(self) -> ComposeResult:
        if self.copy_all_text:
            yield Button("📋", id=f"copy-all-{id(self)}", classes="copy-all-btn")

        yield Static(self._msg_content, classes="msg-content")

        if self.copy_actions:
            with Horizontal(classes="action-buttons"):
                for label in self.copy_actions:
                    yield Button(label, id=f"copy-{id(self)}-{label.replace(' ', '_')}", classes="copy-btn")

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
        elif event.button.has_class("copy-btn") and self.copy_actions:
            label = str(event.button.label)
            text_to_copy = self.copy_actions.get(label)
            if text_to_copy:
                self.app.copy_to_clipboard(text_to_copy)
                action_name = label.replace("Copy ", "").lower()
                self.app.notify(f"Copied {action_name}!", timeout=3)


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

    .copy-btn {{
        margin-top: 1;
        margin-right: 1;
        background: #24283b;
        color: {COLOR_AI};
        border: none;
        height: 3;
        min-width: 20;
    }}
    .copy-btn:hover {{
        background: {COLOR_AI};
        color: {THEME_BG};
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

    .action-buttons {{
        height: auto;
        align: left middle;
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
    """

    def __init__(self, agent: Any, logger: logging.Logger, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.agent = agent
        self.logger = logger
        self.chat_history: list = []

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield VerticalScroll(id="chat-container")
        yield Input(placeholder="Type your query here... (e.g. 'What are markers for T cells?')", id="chat-input")

    def on_mount(self) -> None:
        """Called when app starts."""
        container = self.query_one("#chat-container", VerticalScroll)

        # Add ASCII Art
        ascii_text = Text(ASCII_ART, style=f"bold {COLOR_USER}", justify="center")
        container.mount(ChatMessage(ascii_text, role="system"))

        # Add Use Cases Box
        use_cases = Markdown(
            "**Welcome to sc-bot!**\n\n"
            "Query single-cell transcriptomics data locally.\n"
            "- Find common markers between cells (e.g., 'common genes between T cells and B cells')\n"
            "- Identify cell types by marker (e.g., 'what expresses CD3E and CD8A?')\n"
            "- List all available cell types.\n\n"
            "*Type 'quit' or 'exit' to leave.*"
        )
        container.mount(ChatMessage(use_cases, role="ai"))

        # Focus the input
        self.query_one("#chat-input", Input).focus()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle user input."""
        user_text = event.value.strip()
        if not user_text:
            return

        input_widget = self.query_one("#chat-input", Input)
        input_widget.value = ""

        if user_text.lower() in ["quit", "exit"]:
            self.exit()
            return

        self.logger.info(f"User Input: {user_text}")

        # Display user message
        container = self.query_one("#chat-container", VerticalScroll)
        await container.mount(ChatMessage(user_text, role="user"))
        container.scroll_end(animate=False)

        # Add user message to LangChain history
        self.chat_history.append(HumanMessage(user_text))

        # Mount a "Thinking..." placeholder
        thinking_widget = ChatMessage("...", role="thinking")
        await container.mount(thinking_widget)
        container.scroll_end(animate=False)

        # Disable input while processing
        input_widget.disabled = True

        # Process the response in a background thread
        self.process_message(self.chat_history.copy(), thinking_widget)

    @work(thread=True)
    def process_message(self, messages_copy: list, thinking_widget: ChatMessage) -> None:
        """Runs the LangGraph agent in a background thread so UI doesn't freeze."""
        worker = get_current_worker()
        initial_len = len(messages_copy)

        try:
            # Synchronous blocking call
            response = self.agent.invoke({"messages": messages_copy})

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

            # Extract the structured final response
            raw_ai_message = new_messages[-1].content
            structured_data = format_output(raw_ai_message)

            self.call_from_thread(self._render_ai_response, structured_data, thinking_widget)

        except Exception as e:
            self.logger.error(f"Error during agent invocation: {e}", exc_info=True)
            self.call_from_thread(self._render_error, str(e), thinking_widget)

    def _render_ai_response(self, response_data: AgentResponse, thinking_widget: ChatMessage) -> None:
        """Runs on the UI thread to update the UI with the final response."""
        # Replace the thinking widget with the actual response
        thinking_widget.remove()

        container = self.query_one("#chat-container", VerticalScroll)

        content = response_data.response
        copy_actions = None
        copy_all_text = None

        if response_data.primary_markers or response_data.secondary_markers:
            copy_actions = {}
            combined_markers = {}

            if response_data.primary_markers:
                primary_json_copy = json.dumps(response_data.primary_markers, indent=2)
                primary_json_display = json.dumps(response_data.primary_markers)
                copy_actions["Copy Primary"] = primary_json_copy
                combined_markers["primary"] = response_data.primary_markers
                content += f"\n\n**Primary Canonical Markers:**\n```python\n{primary_json_display}\n```"

            if response_data.secondary_markers:
                secondary_json_copy = json.dumps(response_data.secondary_markers, indent=2)
                secondary_json_display = json.dumps(response_data.secondary_markers)
                copy_actions["Copy Secondary"] = secondary_json_copy
                combined_markers["secondary"] = response_data.secondary_markers
                content += f"\n\n**Secondary/Supportive Markers:**\n```python\n{secondary_json_display}\n```"

            copy_all_text = json.dumps(combined_markers, indent=2)

        container.mount(
            ChatMessage(Markdown(content), role="ai", copy_actions=copy_actions, copy_all_text=copy_all_text)
        )
        container.scroll_end(animate=False)

        # Re-enable input
        input_widget = self.query_one("#chat-input", Input)
        input_widget.disabled = False
        input_widget.focus()

    def _render_error(self, error_msg: str, thinking_widget: ChatMessage) -> None:
        """Runs on the UI thread to display an error."""
        thinking_widget.remove()

        container = self.query_one("#chat-container", VerticalScroll)
        container.mount(ChatMessage(f"An error occurred: {error_msg}", role="error"))
        container.scroll_end(animate=False)

        input_widget = self.query_one("#chat-input", Input)
        input_widget.disabled = False
        input_widget.focus()
