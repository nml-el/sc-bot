from langgraph.graph.state import CompiledStateGraph
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain.agents import create_agent

from sc_bot.config import LLM_MODEL
from sc_bot.annotation_guidance import ANNOTATION_GUIDANCE
from sc_bot.system_prompt import SC_BOT_SYSTEM_PROMPT
from sc_bot.models import AgentResponse
from sc_bot.tools import (
    get_all_cell_types,
    get_markers_by_cell_type,
    get_cell_types_by_marker,
    get_tissues_for_cell_type,
    query_enrichr,
    resolve_gene_aliases,
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
        resolve_gene_aliases,
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
                "You are an expert single-cell annotation assistant that converts raw agent outputs into a structured response. "
                "Default to a GENERAL conversational answer unless the user explicitly asked for marker genes or the answer is clearly marker-centric. "
                "Only return `response_type='markers'` when the primary deliverable is a marker list. Otherwise return `response_type='general'` and leave marker lists empty. "
                "Use these principles when interpreting the message: "
                f"{ANNOTATION_GUIDANCE} "
                "If the text contains marker tables or consensus scores like `tissue_count` and `source_count`, you may extract marker lists only when they are central to the answer. "
                "For gene-list-to-cell-type inference, alias explanations, ambiguity discussions, tissue refinement advice, and cell state interpretation, prefer a general response. "
                "For reverse cell typing from a gene list, present the answer as an enrichment-guided interpretation driven by the strongest overlapping genes and the top enrichment libraries, rather than as a local marker-table lookup. "
                "When you do return markers, rank them using the consensus information in the text and avoid listing raw gene names inline in the prose, since the UI renders them separately. "
                "Keep the response concise, helpful, and biologically grounded.",
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
        return AgentResponse(response_type="general", response=raw_message, primary_markers=[], secondary_markers=[])
