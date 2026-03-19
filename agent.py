from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import create_react_agent
from langchain_google_genai import ChatGoogleGenerativeAI

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

    # Define the system prompt
    system_prompt = (
        "You are an expert biological AI assistant. "
        "When you return a list of marker genes or any specific genes to the user, "
        "ALWAYS format them as a comma-separated list inside a markdown code block so they are easy to copy.\n"
        "Example:\n`CD3E, CD4, CD8A`\n"
    )

    # Create the ReAct agent using the prebuilt LangGraph function
    agent = create_react_agent(
        model=llm,
        tools=tools,
        state_modifier=system_prompt,
    )

    return agent
