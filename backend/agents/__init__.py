"""
BillAgent Pro - Agents Module
==============================
Intelligent agents for bill processing pipeline.

Agent Architecture:
1. DigitizerAgent - OCR extraction with Mistral + GPT-4o fallback
2. AuditorAgent - Math validation and business rule checking  
3. ControllerAgent - Duplicate detection and deduplication
4. AccountantAgent - GL code assignment and expense categorization
"""

from .digitizer import DigitizerAgent, DigitizationResult, DigitizationStatus, create_digitizer_agent
from .auditor import AuditorAgent, ValidationResult, ValidationError, ValidationSeverity
from .controller import ControllerAgent, DuplicateCheckResult, DuplicateMatch
from .accountant import AccountantAgent, AccountantResult, GLCodeAssignment, GLCodeSource

__all__ = [
    # Digitizer Agent (Agent 1)
    "DigitizerAgent",
    "DigitizationResult", 
    "DigitizationStatus",
    "create_digitizer_agent",
    
    # Auditor Agent (Agent 2)
    "AuditorAgent",
    "ValidationResult",
    "ValidationError",
    "ValidationSeverity",
    
    # Controller Agent (Agent 3)
    "ControllerAgent",
    "DuplicateCheckResult",
    "DuplicateMatch",
    
    # Accountant Agent (Agent 4)
    "AccountantAgent",
    "AccountantResult",
    "GLCodeAssignment",
    "GLCodeSource",
]
