from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from .item_schema import ItemSchema

class BillAnalysisResponse(BaseModel):
    """
    API Response Schema for Bill Analysis.
    """
    items: List[ItemSchema]
    total: float
    confidence_scores: Dict[str, float]
    errors: List[str]
    workflow_decision: str  # "AUTO_SAVE" | "PARTIAL_REVIEW" | "FULL_REVIEW"
