from __future__ import annotations

from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    price: float = Field(gt=0, description="Average price per product unit.")
    customers_year1: int = Field(gt=0, description="Number of customers acquired in year 1.")
    cac: float = Field(gt=0, description="Customer acquisition cost per customer.")


class AnalyzeResponseData(BaseModel):
    revenue_12m: int
    profit_12m: int
    breakeven_month: int
    ltv_cac_ratio: float


class AnalyzeResponse(BaseModel):
    success: bool = True
    data: AnalyzeResponseData
