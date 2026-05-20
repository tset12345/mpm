from pydantic import BaseModel
from typing import Optional
from datetime import date

class StockSummary(BaseModel):
    stock_code: str
    stock_name: str
    current_price: int
    change_rate: float
    volume: int
    tags: list[str]

class IchimokuData(BaseModel):
    conversion_line: float
    base_line: float
    span_a: float
    span_b: float
    position: str

class StockMetrics(BaseModel):
    per: Optional[float]
    pbr: Optional[float]
    roe: Optional[float]

class StockDetail(BaseModel):
    stock_code: str
    metrics: StockMetrics
    ichimoku: IchimokuData

class AISummary(BaseModel):
    one_line: str
    key_points: list[str]
    keywords: list[str]

class ReportSummary(BaseModel):
    report_id: int
    title: str
    publisher: str
    publish_date: date
    target_stock_code: Optional[str]
    ai_summary: Optional[AISummary]
