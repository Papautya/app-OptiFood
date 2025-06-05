from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class WasteInput(BaseModel):
    country: str
    category: str
    purchased_tons: float
    wasted_tons: float
    total_value: float
    sales_volume: Optional[float] = None
    storage_temperature: Optional[float] = None
    rotation_method: Optional[str] = None
    additional_context: Optional[str] = None

class WasteAnalysis(BaseModel):
    waste_percentage: float
    economic_loss: float
    loss_per_ton: float
    sales_to_waste_ratio: Optional[float]
    recommendations: List[str]

class PredictInput(BaseModel):
    country: str
    category: str
    # Un array de históricos sencillos, p.ej. [{"year":2020, "waste_tons":23000}, ...]
    historical_data: List[Dict[str, Any]]
    # Variables externas opcionales, p.ej. {"gdp_per_capita":6000, "avg_temp":24}
    external_variables: Optional[Dict[str, Any]] = None

class PredictOutput(BaseModel):
    recommended_tons: float
    min_tons: float
    max_tons: float
    explanation: str
    
class WasteInput(BaseModel):
    country: str = "Colombia"
    category: str
    purchased_tons: float
    wasted_tons: float
    total_value: float
    sales_volume: Optional[float] = None
    storage_temperature: Optional[float] = None
    rotation_method: Optional[str] = None

class WasteAnalysis(BaseModel):
    waste_percentage: float
    economic_loss: float
    loss_per_ton: float
    sales_to_waste_ratio: Optional[float]
    recommendations: List[str]


class RecommendationItem(BaseModel):
    action: str
    responsible: str
    deadline_days: int
    kpi_target: str
    estimated_savings_cop: float

class CombinedOutput(BaseModel):
    waste_percentage: float
    economic_loss: float
    loss_per_ton: float
    sales_to_waste_ratio: Optional[float]

    root_causes: List[str]
    quick_wins: List[RecommendationItem]
    mid_term: List[RecommendationItem]
    long_term: List[RecommendationItem]

    recommended_order_tons: float
    min_order_tons: float
    max_order_tons: float

    # Si lo calculas, puedes incluir ahorro anual total
    estimated_annual_savings_cop: Optional[float] = None

    prediction_explanation: str