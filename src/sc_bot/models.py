from typing import Literal

from pydantic import BaseModel, Field


InteractionMode = Literal["assist", "fetch"]


class MarkerSection(BaseModel):
    """
    A single labeled block of marker genes for TUI rendering.
    """

    label: str = Field(
        description=(
            "Display label for this marker block, e.g. 'Primary Canonical Markers', "
            "'Secondary/Supportive Markers', or 'Epithelial cell Markers'."
        ),
    )
    genes: list[str] = Field(
        default_factory=list,
        description="Ordered marker genes for this section.",
    )


class AgentResponse(BaseModel):
    """
    Schema for parsing the final output of the AI agent.
    """

    response_type: Literal["general", "markers"] = Field(
        description="Whether the response is a general conversational answer or a marker-centric answer.",
        default="general",
    )

    response: str = Field(
        description="The final user-facing response. Keep it concise, helpful, and grounded in the tool outputs."
    )
    marker_sections: list[MarkerSection] = Field(
        description=(
            "Ordered marker sections for the TUI to render. "
            "Each section has a display label and a list of genes. "
            "Empty for general responses."
        ),
        default_factory=list,
    )
    cell_types: list[str] = Field(
        description=(
            "Canonical ontological cell type labels mentioned in the response. "
            "Populate this in assist mode for inline highlighting, and leave it empty in fetch mode."
        ),
        default_factory=list,
    )
