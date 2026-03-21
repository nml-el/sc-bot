import json
import logging
from typing import Any

from rich.console import RenderableType
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text
from textual import work
from textual.app import App, ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Input, Static
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


class ChatMessage(Static):
    """A widget to display a chat message within a styled Rich Panel."""

    def __init__(self, content: RenderableType | str, role: str, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._content = content
        self.role = role

    def render(self) -> RenderableType:
        if self.role == "user":
            border_style = COLOR_USER
            title = "User"
            title_align = "right"
            subtitle = ""
        elif self.role == "ai":
            border_style = COLOR_AI
            title = "sc-bot"
            title_align = "left"
            subtitle = ""
        elif self.role == "error":
            border_style = COLOR_ERROR
            title = "Error"
            title_align = "left"
            subtitle = ""
        elif self.role == "system":
            border_style = THEME_FG
            title = "System"
            title_align = "center"
            subtitle = ""
        elif self.role == "thinking":
            border_style = COLOR_THINKING
            title = "sc-bot is thinking..."
            title_align = "left"
            subtitle = ""
        else:
            border_style = THEME_FG
            title = ""
            title_align = "left"
            subtitle = ""

        return Panel(
            self._content,
            title=title,
            title_align=title_align,
            border_style=border_style,
            subtitle=subtitle,
            padding=(1, 2),
        )


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
    }}

    #chat-input {{
        dock: bottom;
        margin: 1 2;
        background: #24283b;
        color: {THEME_FG};
        border: solid {COLOR_USER};
    }}
    #chat-input:focus {{
        border: bold {COLOR_AI};
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
        if response_data.genes:
            genes_list_str = json.dumps(response_data.genes)
            content += f"\n\n```python\n{genes_list_str}\n```"

        container.mount(ChatMessage(Markdown(content), role="ai"))
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
