class WorkflowDecisionAgent:
    """
    Decides the next step (Auto Save, Partial Review, Full Review) based on confidence.
    """
    def decide(self, overall_confidence: float) -> str:
        if overall_confidence >= 85:
            return "AUTO_SAVE"
        elif overall_confidence >= 60:
            return "PARTIAL_REVIEW"
        else:
            return "FULL_REVIEW"
