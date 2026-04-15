from langgraph.graph.state import CompiledStateGraph
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain.agents import create_agent
from functools import lru_cache

from sc_bot.config import LLM_MODEL
from sc_bot.annotation_guidance import ANNOTATION_GUIDANCE
from sc_bot.system_prompt import build_system_prompt
from sc_bot.models import AgentResponse, InteractionMode
from sc_bot.tools import (
    get_all_cell_types,
    get_markers_by_cell_type,
    get_cell_types_by_marker,
    get_tissues_for_cell_type,
    query_enrichr,
    resolve_gene_aliases,
)


@lru_cache(maxsize=2)
def create_ai_agent(mode: InteractionMode = "assist") -> CompiledStateGraph:
    """
    Creates and caches the AI agent graph for the requested interaction mode.

    Args:
        mode (InteractionMode, optional): The active session mode. Defaults to "assist".

    Returns:
        CompiledStateGraph: The configured agent graph.

    Raises:
        None
    """
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
        system_prompt=build_system_prompt(mode),
    )

    return agent


def format_output(raw_message: str, mode: InteractionMode = "assist") -> AgentResponse:
    """
    Takes the raw output from the ReAct agent and extracts the conversation and any genes mentioned
    using a structured output LLM call.

    Args:
        raw_message (str): The raw text produced by the agent.
        mode (InteractionMode, optional): The active session mode. Defaults to "assist".

    Returns:
        AgentResponse: Structured response content for UI rendering.

    Raises:
        None
    """
    llm = ChatGoogleGenerativeAI(model=LLM_MODEL, temperature=0)
    structured_llm = llm.with_structured_output(AgentResponse)

    if mode == "assist":
        mode_guidance = (
            "The current session mode is `assist`. This is a conversational single-cell expert mode. "
            "Favor `response_type='general'` by default for interpretation, annotation, ambiguity handling, DEG reasoning, and follow-up scientific guidance. "
            "Only return `response_type='markers'` when the user explicitly asked to fetch markers or genes as the primary deliverable."
        )
    else:
        mode_guidance = (
            "The current session mode is `fetch`. This is an internal-database retrieval mode. "
            "Favor `response_type='markers'` when the deliverable is a marker list, gene list, alias mapping, or fetched database result. "
            "Use `response_type='general'` only for short clarifications that do not themselves need marker extraction."
        )

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are an expert single-cell annotation assistant that converts raw agent outputs into a structured response. "
                "Choose `response_type='general'` for conversational interpretation and `response_type='markers'` for structured retrieval outputs. "
                f"{mode_guidance} "
                "Prefer canonical ontological cell type labels in the final prose. If a shorter alias is useful, introduce it only after the canonical label. "
                "Use these principles when interpreting the message: "
                f"{ANNOTATION_GUIDANCE} "
                "If the message uses a structured cell type identification report with sections like Primary Identity, Summary, Lineage markers, Subset heterogeneity, Technical noise, and Final Verdict, preserve that structure in the output instead of flattening it into generic prose. "
                "If the text contains marker tables or consensus scores like `tissue_count` and `source_count`, you may extract marker lists only when they are central to the answer. "
                "For assist-mode gene-list-to-cell-type inference, ambiguity discussions, tissue refinement advice, and cell state interpretation, prefer a general response. "
                "For reverse cell typing from a gene list, present the answer as an enrichment-guided interpretation driven by the strongest overlapping genes and the top enrichment libraries, rather than as a local marker-table lookup. "
                "For fetch-mode internal database retrieval, prefer marker extraction when the result is fundamentally a fetched gene or marker set. "
                "When you do return markers, rank them using the consensus information in the text and avoid listing raw gene names inline in the prose, since the UI renders them separately. "
                "Populate `cell_types` only in assist mode. Extract canonical ontological cell type labels that are explicitly supported by the message and appear in the prose. "
                "In fetch mode, return `cell_types=[]`. "
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
        return AgentResponse(
            response_type="general",
            response=raw_message,
            primary_markers=[],
            secondary_markers=[],
            cell_types=[],
        )
