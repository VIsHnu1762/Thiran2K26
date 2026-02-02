from typing import List, Dict
from ..schemas.item_schema import ItemSchema
from ..utils.confidence_utils import calculate_average_confidence

class ConfidenceAgent:
    """
    Analyzes OCR results and assigns confidence scores.
    """
    def analyze(self, items: List[ItemSchema]) -> Dict[str, float]:
        """
        Calculates field-level and overall confidence.
        """
        field_scores = {}
        
        # Calculate per-item average confidence
        item_confidences = [item.confidence for item in items]
        
        overall_score = calculate_average_confidence(item_confidences)
        field_scores["overall"] = overall_score
        
        # In a more detailed implementation, specific fields like "Total" 
        # would have their own tracked confidence if extracted separately.
        
        return field_scores
