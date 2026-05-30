from pydantic import BaseModel, Field


class AnalysisRequest(BaseModel):
    idea: str = Field(min_length=3)
    region: str | None = None
    industry: str | None = None


class SwotData(BaseModel):
    strengths: list[str]
    weaknesses: list[str]
    opportunities: list[str]
    threats: list[str]


class AnalysisResponseData(BaseModel):
    swot: SwotData
    audience: str
    value_proposition: str


class AnalysisResponse(BaseModel):
    success: bool = True
    data: AnalysisResponseData
