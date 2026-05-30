from __future__ import annotations

from math import ceil

from src.schemas import AnalyzeRequest, AnalyzeResponse, AnalyzeResponseData

AVERAGE_MARKET_TURNS_PER_YEAR = 24
OPERATING_MARGIN = 0.12
CONTRIBUTION_MARGIN_FOR_PAYBACK = 0.55
LTV_MONTHS = 12


class AnalysisService:
    async def analyze(self, payload: AnalyzeRequest) -> AnalyzeResponse:
        if payload.price <= 0:
            raise ValueError("price must be greater than 0")
        if payload.customers_year1 < 0:
            raise ValueError("customers_year1 must be greater than or equal to 0")
        if payload.cac <= 0:
            raise ValueError("cac must be greater than 0")
        
        revenue_12m = round(payload.price * payload.customers_year1 * AVERAGE_MARKET_TURNS_PER_YEAR)
        profit_12m = round(revenue_12m * OPERATING_MARGIN)

        purchases_per_month = AVERAGE_MARKET_TURNS_PER_YEAR / 12
        ltv = payload.price * purchases_per_month * LTV_MONTHS * CONTRIBUTION_MARGIN_FOR_PAYBACK
        ltv_cac_ratio = round(ltv / payload.cac, 2)

        monthly_margin_per_customer = payload.price * purchases_per_month * CONTRIBUTION_MARGIN_FOR_PAYBACK
        breakeven_month = ceil(payload.cac / monthly_margin_per_customer)

        return AnalyzeResponse(
            data=AnalyzeResponseData(
                revenue_12m=revenue_12m,
                profit_12m=profit_12m,
                breakeven_month=breakeven_month,
                ltv_cac_ratio=ltv_cac_ratio,
            )
        )
