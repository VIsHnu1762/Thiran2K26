"""
BillAgent Pro - Services Module
================================
Business logic and external service integrations.
"""

from .ocr import (
    OCREngine,
    OCREngineType,
    OCRResult,
    OCRField,
    OCRLineItem,
    BoundingBox,
    MistralOCR,
    GPT4VisionOCR,
    OCRParser,
)

from .bill_service import (
    BillProcessingService,
    ProcessingResult,
    ProcessingStage,
    ProcessingStepResult,
)

__all__ = [
    # OCR Services
    "OCREngine",
    "OCREngineType",
    "OCRResult",
    "OCRField",
    "OCRLineItem",
    "BoundingBox",
    "MistralOCR",
    "GPT4VisionOCR",
    "OCRParser",
    
    # Bill Processing Service
    "BillProcessingService",
    "ProcessingResult",
    "ProcessingStage",
    "ProcessingStepResult",
]
