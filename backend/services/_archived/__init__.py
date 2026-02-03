"""
ARCHIVED - Legacy OCR Services
==============================
These files have been replaced by the new OCR service architecture in:
- backend/app/services/ocr/

The new architecture includes:
- MistralOCR: Primary OCR engine with bounding box support
- GPT4VisionOCR: Fallback OCR engine
- DigitizerAgent: Orchestrates OCR with retry and fallback logic

Files in this folder are kept for reference only.
DO NOT import from this folder in production code.
"""
