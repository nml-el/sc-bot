from langgraph.graph.state import CompiledStateGraph
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain.agents import create_agent

from sc_bot.config import LLM_MODEL
from sc_bot.system_prompt import SC_BOT_SYSTEM_PROMPT
from sc_bot.models import AgentResponse
from sc_bot.tools import (
    get_all_cell_types,
    get_markers_by_cell_type,
    get_cell_types_by_marker,
    get_tissues_for_cell_type,
    query_enrichr,
)


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
        get_tissues_for_cell_type,
        query_enrichr,
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
                "You are an expert biological data extractor and assistant. "
                "Your task is to take the provided text, which may contain a raw list of genes from a database, "
                "and identify the most important, universally accepted canonical primary markers "
                "and a small set of secondary/supportive markers. "
                "The provided data often includes consensus scores: `tissue_count` (distinct tissues) and "
                "`source_count` (distinct databases). Use these to rank genes: "
                "1. Primary markers (3-10 genes): Genes with high consensus (e.g. source_count=2 AND tissue_count >= 3). "
                "These are confirmed universally. "
                "2. Secondary markers: Genes with lower consensus but still relevant. "
                "Extract these into the respective primary and secondary lists. "
                "Then, rewrite the natural language response to provide a minimal, high-level context explaining "
                "why these specific markers are defining for the cell type(s). Include any suggestions about tissue "
                "refinement if the agent mentioned them. "
                "CRITICALLY: Do NOT list the actual gene names inline in your natural language response, "
                "as they will be rendered as lists by the UI. Simply introduce the lists. "
                "If no genes are mentioned, return empty lists and keep the response helpful.",
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
        return AgentResponse(response=raw_message, primary_markers=[], secondary_markers=[])
