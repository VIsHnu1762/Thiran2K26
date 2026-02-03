"""
BillAgent Pro - GPT-4 Vision OCR Implementation
================================================
Fallback OCR engine using OpenAI's GPT-4o Vision model.
Used when Mistral OCR fails or as a secondary verification.
"""

import asyncio
import base64
import json
import logging
import time
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional, Tuple

import httpx

from .base import (
    OCREngine,
    OCREngineType,
    OCRResult,
    OCRField,
    OCRLineItem,
    BoundingBox,
)

logger = logging.getLogger(__name__)


# =============================================================================
# GPT-4o Vision Prompts
# =============================================================================

BILL_EXTRACTION_PROMPT = """You are an expert OCR system specialized in extracting structured data from bills, invoices, and receipts.

TASK: Analyze this bill image and extract ALL information with confidence scores.

Return a JSON object with this EXACT structure:
{
    "vendor": {
        "name": "Vendor/Company Name",
        "confidence": 0.95
    },
    "invoice_number": {
        "value": "INV-12345",
        "confidence": 0.95
    },
    "invoice_date": {
        "value": "2024-01-15",
        "confidence": 0.90
    },
    "due_date": {
        "value": "2024-02-15",
        "confidence": 0.85
    },
    "currency": "INR",
    "line_items": [
        {
            "description": "Product/Service name",
            "quantity": 2,
            "unit": "pcs",
            "unit_price": 150.00,
            "total_price": 300.00,
            "confidence": 0.92
        }
    ],
    "subtotal": {
        "value": 300.00,
        "confidence": 0.95
    },
    "tax_amount": {
        "value": 54.00,
        "confidence": 0.90
    },
    "total_amount": {
        "value": 354.00,
        "confidence": 0.98
    }
}

EXTRACTION RULES:
1. Extract EVERY line item with description, quantity, unit price, and total
2. Dates should be in ISO format (YYYY-MM-DD)
3. Confidence scores should be 0.0 to 1.0 (1.0 = very confident)
4. For handwritten text, be extra careful and lower confidence if unsure
5. Default currency is INR (Indian Rupees) unless clearly stated otherwise
6. Handle partial/unclear text by providing best guess with lower confidence
7. If a field is not found, omit it from the response

IMPORTANT: Return ONLY valid JSON. No markdown, no explanations, no code blocks."""


class GPT4VisionOCR(OCREngine):
    """
    GPT-4o Vision OCR implementation for bill digitization.
    Used as a fallback when Mistral OCR fails.
    """
    
    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o",  # gpt-4o for best vision capabilities
        base_url: str = "https://api.openai.com/v1",
        timeout: float = 90.0,  # GPT-4o can be slower
        max_retries: int = 3,
        retry_delay: float = 2.0,
    ):
        """
        Initialize GPT-4o Vision client.
        
        Args:
            api_key: OpenAI API key
            model: Model to use (gpt-4o recommended)
            base_url: OpenAI API base URL
            timeout: Request timeout in seconds
            max_retries: Number of retry attempts
            retry_delay: Initial delay between retries (exponential backoff)
        """
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        self._client: Optional[httpx.AsyncClient] = None
    
    @property
    def engine_type(self) -> OCREngineType:
        return OCREngineType.GPT4_VISION
    
    @property
    def supports_bounding_boxes(self) -> bool:
        # GPT-4o doesn't natively return bounding boxes
        return False
    
    @property
    def supports_handwritten(self) -> bool:
        return True
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                timeout=httpx.Timeout(self.timeout),
            )
        return self._client
    
    async def close(self):
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    async def extract(self, image_bytes: bytes) -> OCRResult:
        """
        Extract structured data from bill image using GPT-4o Vision.
        
        Args:
            image_bytes: Raw image bytes
            
        Returns:
            OCRResult with extracted data (no bounding boxes)
        """
        start_time = time.perf_counter()
        
        try:
            # Encode image to base64
            image_b64 = base64.b64encode(image_bytes).decode("utf-8")
            
            # Detect image type
            image_type = self._detect_image_type(image_bytes)
            
            # Prepare API request
            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": BILL_EXTRACTION_PROMPT,
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{image_type};base64,{image_b64}",
                                    "detail": "high",  # High detail for OCR
                                },
                            },
                        ],
                    }
                ],
                "max_tokens": 4096,
                "temperature": 0.1,
            }
            
            # Call API with retries
            response_data = await self._call_api_with_retry(payload)
            
            # Parse response
            result = self._parse_response(response_data)
            result.processing_time_ms = int((time.perf_counter() - start_time) * 1000)
            result.raw_response = response_data
            
            # Calculate overall confidence
            result.calculate_overall_confidence()
            
            logger.info(
                f"GPT-4o Vision extracted {len(result.line_items)} items "
                f"with {result.overall_confidence:.1%} confidence "
                f"in {result.processing_time_ms}ms"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"GPT-4o Vision extraction failed: {e}", exc_info=True)
            result = self._create_error_result(str(e))
            result.processing_time_ms = int((time.perf_counter() - start_time) * 1000)
            return result
    
    async def _call_api_with_retry(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Call OpenAI API with exponential backoff retry."""
        client = await self._get_client()
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                response = await client.post("/chat/completions", json=payload)
                response.raise_for_status()
                return response.json()
                
            except httpx.HTTPStatusError as e:
                last_error = e
                if e.response.status_code == 429:  # Rate limited
                    delay = self.retry_delay * (2 ** attempt)
                    logger.warning(f"Rate limited, retrying in {delay}s...")
                    await asyncio.sleep(delay)
                elif e.response.status_code >= 500:  # Server error
                    delay = self.retry_delay * (2 ** attempt)
                    logger.warning(f"Server error {e.response.status_code}, retrying in {delay}s...")
                    await asyncio.sleep(delay)
                else:
                    raise
                    
            except httpx.TimeoutException as e:
                last_error = e
                delay = self.retry_delay * (2 ** attempt)
                logger.warning(f"Timeout, retrying in {delay}s...")
                await asyncio.sleep(delay)
        
        raise last_error or Exception("Max retries exceeded")
    
    def _parse_response(self, response_data: Dict[str, Any]) -> OCRResult:
        """Parse OpenAI API response into OCRResult."""
        result = OCRResult(success=True, engine=self.engine_type)
        
        try:
            # Extract content from response
            content = response_data["choices"][0]["message"]["content"]
            
            # Clean up markdown if present
            content = self._clean_json_response(content)
            
            # Parse JSON
            data = json.loads(content)
            
            # Parse vendor
            if "vendor" in data:
                vendor_data = data["vendor"]
                result.vendor_name = OCRField(
                    name="vendor_name",
                    value=vendor_data.get("name", ""),
                    confidence=float(vendor_data.get("confidence", 0.9)),
                    raw_text=vendor_data.get("name"),
                )
            
            # Parse invoice number
            if "invoice_number" in data:
                inv_data = data["invoice_number"]
                result.invoice_number = OCRField(
                    name="invoice_number",
                    value=inv_data.get("value", ""),
                    confidence=float(inv_data.get("confidence", 0.9)),
                    raw_text=str(inv_data.get("value")),
                )
            
            # Parse dates
            if "invoice_date" in data:
                date_data = data["invoice_date"]
                parsed_date = self._parse_date(date_data.get("value"))
                result.invoice_date = OCRField(
                    name="invoice_date",
                    value=parsed_date,
                    confidence=float(date_data.get("confidence", 0.85)),
                    raw_text=str(date_data.get("value")),
                )
            
            if "due_date" in data:
                date_data = data["due_date"]
                parsed_date = self._parse_date(date_data.get("value"))
                result.due_date = OCRField(
                    name="due_date",
                    value=parsed_date,
                    confidence=float(date_data.get("confidence", 0.85)),
                    raw_text=str(date_data.get("value")),
                )
            
            # Parse amounts
            for amount_field in ["subtotal", "tax_amount", "total_amount"]:
                if amount_field in data:
                    amount_data = data[amount_field]
                    parsed_amount = self._parse_decimal(amount_data.get("value"))
                    field_obj = OCRField(
                        name=amount_field,
                        value=parsed_amount,
                        confidence=float(amount_data.get("confidence", 0.9)),
                        raw_text=str(amount_data.get("value")),
                    )
                    setattr(result, amount_field, field_obj)
            
            # Parse currency
            if "currency" in data:
                currency_val = data["currency"]
                if isinstance(currency_val, dict):
                    currency_val = currency_val.get("value", "INR")
                result.currency = OCRField(
                    name="currency",
                    value=currency_val,
                    confidence=0.95,
                )
            
            # Parse line items
            if "line_items" in data:
                for idx, item_data in enumerate(data["line_items"]):
                    line_item = OCRLineItem(
                        description=str(item_data.get("description", "")),
                        quantity=self._parse_decimal(item_data.get("quantity", 1)),
                        unit=item_data.get("unit"),
                        unit_price=self._parse_decimal(item_data.get("unit_price", 0)),
                        total_price=self._parse_decimal(item_data.get("total_price", 0)),
                        confidence=float(item_data.get("confidence", 0.9)),
                        sort_order=idx,
                    )
                    result.line_items.append(line_item)
            
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse GPT-4o response as JSON: {e}")
            return self._create_error_result(f"Invalid JSON response: {e}")
        except Exception as e:
            logger.error(f"Failed to parse GPT-4o response: {e}", exc_info=True)
            return self._create_error_result(f"Parse error: {e}")
    
    def _parse_date(self, value: Any) -> Optional[date]:
        """Parse date from various formats."""
        if value is None:
            return None
        
        if isinstance(value, date):
            return value
        
        if isinstance(value, datetime):
            return value.date()
        
        if isinstance(value, str):
            formats = [
                "%Y-%m-%d",
                "%d-%m-%Y",
                "%d/%m/%Y",
                "%m/%d/%Y",
                "%Y/%m/%d",
                "%d %b %Y",
                "%d %B %Y",
                "%B %d, %Y",
            ]
            for fmt in formats:
                try:
                    return datetime.strptime(value.strip(), fmt).date()
                except ValueError:
                    continue
        
        return None
    
    def _parse_decimal(self, value: Any) -> Decimal:
        """Parse decimal from various formats."""
        if value is None:
            return Decimal("0")
        
        if isinstance(value, Decimal):
            return value
        
        if isinstance(value, (int, float)):
            return Decimal(str(value))
        
        if isinstance(value, str):
            value = value.strip()
            value = value.replace(",", "")
            value = value.replace("₹", "").replace("$", "").replace("Rs", "").replace("rs", "")
            value = value.strip()
            
            try:
                return Decimal(value)
            except InvalidOperation:
                return Decimal("0")
        
        return Decimal("0")
    
    def _clean_json_response(self, content: str) -> str:
        """Clean up JSON response by removing markdown code blocks."""
        import re
        
        content = content.strip()
        content = re.sub(r'^```json\s*', '', content, flags=re.MULTILINE)
        content = re.sub(r'^```\s*', '', content, flags=re.MULTILINE)
        content = re.sub(r'\s*```$', '', content, flags=re.MULTILINE)
        
        return content.strip()
    
    def _detect_image_type(self, image_bytes: bytes) -> str:
        """Detect image MIME type from bytes."""
        if image_bytes[:8] == b'\x89PNG\r\n\x1a\n':
            return "image/png"
        elif image_bytes[:2] == b'\xff\xd8':
            return "image/jpeg"
        elif image_bytes[:6] in (b'GIF87a', b'GIF89a'):
            return "image/gif"
        elif image_bytes[:4] == b'RIFF' and image_bytes[8:12] == b'WEBP':
            return "image/webp"
        else:
            return "image/jpeg"
    
    async def health_check(self) -> Tuple[bool, str]:
        """Check if OpenAI API is accessible."""
        try:
            client = await self._get_client()
            response = await client.get("/models")
            if response.status_code == 200:
                return True, "OpenAI API is healthy"
            else:
                return False, f"OpenAI API returned status {response.status_code}"
        except Exception as e:
            return False, f"OpenAI API health check failed: {str(e)}"
