from pydantic import BaseModel, Field


class AgentResponse(BaseModel):
    """
    Schema for parsing the final output of the AI agent.
    """

    response: str = Field(
        description="The natural language conversational response explaining the findings or answering the user's question."
    )
    genes: list[str] = Field(
        description="A list of specific genes mentioned in the response. Empty if no genes are mentioned.",
        default_factory=list,
    )
