from langgraph.graph.state import CompiledStateGraph
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import create_agent

from config import LLM_MODEL
from tools import get_all_cell_types, get_markers_by_cell_type, get_cell_types_by_marker


def create_ai_agent() -> CompiledStateGraph:
    # Initialize the LLM
    llm = ChatGoogleGenerativeAI(
        model=LLM_MODEL,
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
