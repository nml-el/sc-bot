import json
import os
import uuid
from dotenv import load_dotenv

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from rich.console import Console, Group
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.text import Text

from sc_bot.agent import create_ai_agent
from sc_bot.config import DB_PATH, LLM_MODEL
from sc_bot.logger import setup_session_logger
from sc_bot.models import AgentResponse

# Catppuccin Mocha Colors
CTP_MAUVE = "#cba6f7"
CTP_BLUE = "#89b4fa"
CTP_SAPPHIRE = "#74c7ec"
CTP_GREEN = "#a6e3a1"
CTP_RED = "#f38ba8"
CTP_TEXT = "#cdd6f4"

ASCII_ART = r"""
███████╗ ██████╗       ██████╗  ██████╗ ████████╗
██╔════╝██╔════╝       ██╔══██╗██╔═══██╗╚══██╔══╝
███████╗██║      █████╗██████╔╝██║   ██║   ██║   
╚════██║██║      ╚════╝██╔══██╗██║   ██║   ██║   
███████║╚██████╗       ██████╔╝╚██████╔╝   ██║   
╚══════╝ ╚═════╝       ╚═════╝  ╚═════╝    ╚═╝   
"""


def format_output(raw_message: str) -> AgentResponse:
    """
    Takes the raw output from the ReAct agent and extracts the conversation and any genes mentioned
    using a structured output LLM call.
    """
    llm = ChatGoogleGenerativeAI(model=LLM_MODEL, temperature=0)
    structured_llm = llm.with_structured_output(AgentResponse)

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are an expert biological data extractor. "
                "Extract the natural language response and any specific marker genes mentioned in the text. "
                "If no genes are mentioned, return an empty list for the genes.",
            ),
            ("human", "{text}"),
        ]
    )

    chain = prompt | structured_llm
    result = chain.invoke({"text": raw_message})

    if isinstance(result, AgentResponse):
        return result
    else:
        # Fallback if the structured LLM fails to return the exact type
        return AgentResponse(response=raw_message, genes=[])


def print_welcome_banner(console: Console, session_id: str) -> None:
    """Prints the styled ASCII art and welcome message in a panel."""
    # Clear terminal
    console.clear()

    # Create the text components
    art_text = Text(ASCII_ART, style=CTP_MAUVE, justify="center")
    welcome_text = Text("\nWelcome to sc-bot!\n", style=f"bold {CTP_TEXT}", justify="center")
    desc_text = Text("I can help you query cell type and marker gene information.\n", style=CTP_TEXT, justify="center")
    session_text = Text(f"Session ID: {session_id}\n", style=CTP_SAPPHIRE, justify="center")
    help_text = Text("Type 'quit' or 'exit' to leave.", style=f"dim {CTP_TEXT}", justify="center")

    # Group them together
    banner_group = Group(art_text, welcome_text, desc_text, session_text, help_text)

    # Wrap in a panel
    banner_panel = Panel(
        banner_group,
        border_style=CTP_BLUE,
        padding=(1, 2),
        expand=False,
    )

    # Print centered
    console.print(banner_panel, justify="center")
    console.print("\n")


def main() -> None:
    # Load environment variables (e.g., GEMINI_API_KEY)
    load_dotenv()

    console = Console()

    if not DB_PATH.exists():
        error_panel = Panel(
            Text(f"Database not found at {DB_PATH}\n\nPlease run: uv run python scripts/setup_db.py", style=CTP_TEXT),
            title="---Error---",
            title_align="left",
            border_style=CTP_RED,
        )
        console.print(error_panel)
        return

    if not os.environ.get("GEMINI_API_KEY"):
        error_panel = Panel(
            Text(
                "GEMINI_API_KEY not found in .env file or environment variables.\nPlease add your key to a .env file: GEMINI_API_KEY=your_key_here",
                style=CTP_TEXT,
            ),
            title="---Error---",
            title_align="left",
            border_style=CTP_RED,
        )
        console.print(error_panel)
        return

    session_id = uuid.uuid4().hex
    logger = setup_session_logger(session_id)

    print_welcome_banner(console, session_id)
    logger.info("Session started.")

    agent = create_ai_agent()

    # LangGraph state representation requires a dictionary with a messages key
    # but the prebuilt create_react_agent manages conversation history internally
    # if we pass it thread config or just loop through.
    # Let's use a simple list of messages to track conversation history.
    messages = []

    while True:
        try:
            # Prompt styling
            prompt_style = f"bold {CTP_SAPPHIRE}"
            user_input = Prompt.ask(f"[{prompt_style}](sc-bot) >[/{prompt_style}]")
        except (KeyboardInterrupt, EOFError):
            break

        if user_input.strip().lower() in ["quit", "exit"]:
            break

        if not user_input.strip():
            continue

        logger.info(f"User Input: {user_input}")

        # Echo user input in a styled panel
        user_panel = Panel(
            Text(user_input, style=CTP_TEXT),
            title="---User---",
            title_align="left",
            border_style=CTP_SAPPHIRE,
            padding=(0, 1),
        )
        console.print()
        console.print(user_panel)

        # Add user message to history
        messages.append(HumanMessage(user_input))

        # Track the length of messages before the agent invocation
        initial_msg_len = len(messages)

        try:
            with console.status(f"[{CTP_MAUVE}]Thinking...[/{CTP_MAUVE}]", spinner="dots"):
                response = agent.invoke({"messages": messages})

            # Update history with the final state
            messages = response["messages"]

            # Log the agent's internal thinking process
            for msg in messages[initial_msg_len:]:
                if isinstance(msg, AIMessage):
                    if msg.tool_calls:
                        for tool_call in msg.tool_calls:
                            logger.info(
                                f"Agent decided to call tool: {tool_call['name']} with args: {tool_call['args']}"
                            )
                    if msg.content:
                        logger.info(f"Agent Thought/Output: {msg.content}")
                elif isinstance(msg, ToolMessage):
                    logger.info(f"Tool executed. Name: {msg.name}, Result: {str(msg.content)[:500]}...")

            # The final response from the agent is the last message
            raw_ai_message = messages[-1].content

            # Extract structured data
            with console.status(f"[{CTP_BLUE}]Formatting output...[/{CTP_BLUE}]", spinner="dots"):
                structured_data = format_output(raw_ai_message)

            # Build the AI response visual components
            renderables = [Markdown(structured_data.response)]

            if structured_data.genes:
                genes_list_str = json.dumps(structured_data.genes)
                markdown_code_block = f"```python\n{genes_list_str}\n```"
                renderables.append(Text(""))  # Spacing
                renderables.append(Markdown(markdown_code_block))

            ai_group = Group(*renderables)

            # Wrap in an AI Response panel
            ai_panel = Panel(
                ai_group,
                title="---AI Response---",
                title_align="left",
                border_style=CTP_GREEN,
                padding=(1, 2),
            )

            console.print(ai_panel)
            console.print("\n")

        except Exception as e:
            error_panel = Panel(
                Text(str(e), style=CTP_TEXT),
                title="---Error---",
                title_align="left",
                border_style=CTP_RED,
            )
            console.print(error_panel)


if __name__ == "__main__":
    main()
