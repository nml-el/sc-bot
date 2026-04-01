from typing import Literal

from pydantic import BaseModel, Field


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
    primary_markers: list[str] = Field(
        description="Primary canonical marker genes when the response is marker-centric. Empty for general responses.",
        default_factory=list,
    )
    secondary_markers: list[str] = Field(
        description="Secondary/supportive marker genes when the response is marker-centric. Empty for general responses.",
        default_factory=list,
    )
