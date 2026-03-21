from langgraph.graph.state import CompiledStateGraph
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import create_agent

from sc_bot.config import LLM_MODEL
from sc_bot.system_prompt import SC_BOT_SYSTEM_PROMPT
from sc_bot.tools import get_all_cell_types, get_markers_by_cell_type, get_cell_types_by_marker


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

    # Creates an agent graph that calls tools in a loop until a stopping condition is met.
    agent = create_agent(
        model=llm,
        tools=tools,
        system_prompt=SC_BOT_SYSTEM_PROMPT,
    )

    return agent
