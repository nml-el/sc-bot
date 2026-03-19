import os
from dotenv import load_dotenv
from rich.console import Console
from rich.markdown import Markdown
from rich.prompt import Prompt
from langchain.messages import HumanMessage

from agent import create_ai_agent


def main() -> None:
    # Load environment variables (e.g., GEMINI_API_KEY)
    load_dotenv()

    if not os.environ.get("GEMINI_API_KEY"):
        print("Error: GEMINI_API_KEY not found in .env file or environment variables.")
        print("Please add your key to a .env file: GEMINI_API_KEY=your_key_here")
        return

    console = Console()
    console.print("[bold green]Welcome to sc-bot![/bold green] Type 'quit' or 'exit' to leave.")
    console.print("I can help you query cell type and marker gene information.\n")

    agent = create_ai_agent()

    # LangGraph state representation requires a dictionary with a messages key
    # but the prebuilt create_react_agent manages conversation history internally
    # if we pass it thread config or just loop through.
    # Let's use a simple list of messages to track conversation history.
    messages = []

    while True:
        try:
            user_input = Prompt.ask("[bold cyan](sc-bot) >[/bold cyan]")
        except (KeyboardInterrupt, EOFError):
            break

        if user_input.strip().lower() in ["quit", "exit"]:
            break

        if not user_input.strip():
            continue

        # Add user message to history
        messages.append(HumanMessage(user_input))

        try:
            with console.status("[bold yellow]Thinking...[/bold yellow]", spinner="dots"):
                response = agent.invoke({"messages": messages})

            # Update history with the final state
            messages = response["messages"]

            # The final response from the agent is the last message
            ai_message = messages[-1].content
            console.print("\n")
            console.print(Markdown(ai_message))
            console.print("\n")

        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] {e}")


if __name__ == "__main__":
    main()
