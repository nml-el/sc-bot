from pydantic import BaseModel, Field


class AgentResponse(BaseModel):
    """
    Schema for parsing the final output of the AI agent.
    """

    response: str = Field(
        description="The natural language context explaining the biological relevance of the primary and secondary markers to the requested cell type(s). Keep it minimal and highly relevant. MUST NOT contain the raw list of genes inline."
    )
    primary_markers: list[str] = Field(
        description="A concise list of the most important, universally accepted canonical marker genes (usually 3-10 genes). Empty if no genes are found.",
        default_factory=list,
    )
    secondary_markers: list[str] = Field(
        description="A small set of secondary or supportive marker genes. Empty if no secondary genes are found.",
        default_factory=list,
    )
