import os
import json
from dotenv import load_dotenv
from rich.console import Console
from rich.markdown import Markdown
from rich.prompt import Prompt
from langchain.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate

from agent import create_ai_agent
from config import LLM_MODEL
from models import AgentResponse


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
            raw_ai_message = messages[-1].content

            # Extract structured data
            with console.status("[bold blue]Formatting output...[/bold blue]", spinner="dots"):
                structured_data = format_output(raw_ai_message)

            console.print("\n")
            # Print the natural language response
            console.print(Markdown(structured_data.response))
            console.print("\n")

            # Print the python list of genes if they exist
            if structured_data.genes:
                # Create a string representation of the python list
                genes_list_str = json.dumps(structured_data.genes)
                # Format as a python code block for easy copying
                markdown_code_block = f"```python\n{genes_list_str}\n```"
                console.print(Markdown(markdown_code_block))
                console.print("\n")

        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] {e}")


if __name__ == "__main__":
    main()
