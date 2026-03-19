from langgraph.graph.state import CompiledStateGraph
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import create_agent

from tools import get_all_cell_types, get_markers_by_cell_type, get_cell_types_by_marker


def create_ai_agent() -> CompiledStateGraph:
    # Initialize the LLM
    # We use gemini-2.5-flash which is generally available and cost-effective.
    # Note: If you specifically have access to "gemini-2.5-flash-lite", update the model name here.
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        temperature=0,
    )

    # List the tools the agent will have access to
    tools = [
        get_all_cell_types,
        get_markers_by_cell_type,
        get_cell_types_by_marker,
    ]

    # Create the ReAct agent using the prebuilt LangGraph function
    agent = create_agent(
        model=llm,
        tools=tools,
    )

    return agent
