from langgraph.graph.state import CompiledStateGraph
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent

from config import LLM_MODEL
from system_prompt import SC_BOT_SYSTEM_PROMPT
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
    agent = create_react_agent(
        model=llm,
        tools=tools,
        prompt=SC_BOT_SYSTEM_PROMPT,
    )

    return agent
