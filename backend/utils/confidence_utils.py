from typing import List, Dict

def calculate_average_confidence(scores: List[float]) -> float:
    """
    Calculates the average of a list of confidence scores.
    """
    if not scores:
        return 0.0
    return sum(scores) / len(scores)

def get_confidence_status(score: float) -> str:
    """
    Returns a status label based on the confidence score.
    """
    if score >= 85:
        return "HIGH"
    elif score >= 60:
        return "MEDIUM"
    else:
        return "LOW"
