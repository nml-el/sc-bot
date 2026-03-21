from langgraph.graph.state import CompiledStateGraph
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain.agents import create_agent

from sc_bot.config import LLM_MODEL
from sc_bot.system_prompt import SC_BOT_SYSTEM_PROMPT
from sc_bot.models import AgentResponse
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
