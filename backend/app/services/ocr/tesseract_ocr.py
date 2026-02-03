"""
BillAgent Pro - Tesseract OCR Implementation
=============================================
Free, local OCR engine using Tesseract.
Fast and privacy-friendly (no API calls).
"""

import asyncio
import base64
import io
import json
import logging
import os
import re
import time
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pytesseract
from PIL import Image

from .base import (
    OCREngine,
    OCREngineType,
    OCRResult,
    OCRField,
    OCRLineItem,
    BoundingBox,
)

logger = logging.getLogger(__name__)


# Configure Tesseract path
possible_paths = [
    r'C:\Program Files\Tesseract-OCR\tesseract.exe',
    r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
    '/usr/bin/tesseract',
    '/usr/local/bin/tesseract',
]
for path in possible_paths:
    if os.path.exists(path):
        pytesseract.pytesseract.tesseract_cmd = path
        logger.info(f"✅ Tesseract found at: {path}")
        break


class TesseractOCR(OCREngine):
    """
    Local Tesseract OCR engine.
    Free, no API calls, supports multiple languages.
    """
    
    def __init__(self, language: str = "eng"):
        """
        Initialize Tesseract OCR.
        
        Args:
            language: Language code (eng, fra, deu, etc.)
        """
        self.language = language
        logger.info(f"Tesseract OCR initialized with language: {language}")
    
    @property
    def engine_type(self) -> OCREngineType:
        return OCREngineType.TESSERACT
    
    @property
    def supports_bounding_boxes(self) -> bool:
        return True
    
    @property
    def supports_handwritten(self) -> bool:
        return False  # Tesseract is better for printed text
    
    async def extract(self, image_bytes: bytes) -> OCRResult:
        """
        Extract text from image using Tesseract OCR.
        
        Args:
            image_bytes: Raw image bytes
            
        Returns:
            OCRResult with extracted data
        """
        start_time = time.perf_counter()
        
        try:
            # Load image
            image = Image.open(io.BytesIO(image_bytes))
            image_array = np.array(image)
            image_width, image_height = image.size
            
            # Run OCR
            ocr_data = pytesseract.image_to_data(
                image_array,
                lang=self.language,
                output_type=pytesseract.Output.DICT
            )
            
            # Extract words with bounding boxes
            words = []
            n_boxes = len(ocr_data['text'])
            for i in range(n_boxes):
                text = ocr_data['text'][i].strip()
                conf = float(ocr_data['conf'][i])
                
                if text and conf >= 0:
                    words.append({
                        "text": text,
                        "confidence": conf / 100.0,  # Convert to 0-1 range
                        "left": ocr_data['left'][i],
                        "top": ocr_data['top'][i],
                        "width": ocr_data['width'][i],
                        "height": ocr_data['height'][i],
                    })
            
            logger.info(f"Tesseract extracted {len(words)} words")
            
            # Parse structured data from words
            result = self._parse_bill_data(words, image_width, image_height)
            
            # Calculate processing time
            processing_time = int((time.perf_counter() - start_time) * 1000)
            result.processing_time_ms = processing_time
            
            logger.info(
                f"Tesseract OCR completed in {processing_time}ms, "
                f"confidence: {result.overall_confidence:.1%}"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Tesseract OCR failed: {str(e)}")
            return self._create_error_result(f"Tesseract OCR error: {str(e)}")
    
    def _parse_bill_data(
        self,
        words: List[Dict],
        image_width: int,
        image_height: int,
    ) -> OCRResult:
        """
        Parse structured bill data from extracted words.
        
        Args:
            words: List of word dictionaries with text, confidence, and bbox
            image_width: Image width in pixels
            image_height: Image height in pixels
            
        Returns:
            OCRResult with structured data
        """
        result = OCRResult(
            success=True,
            engine=self.engine_type,
        )
        
        # Group words into lines based on Y coordinate
        lines = self._group_into_lines(words, threshold=15)
        
        # Extract vendor name (usually at top)
        vendor = self._extract_vendor(lines)
        if vendor:
            bbox = self._create_bbox(vendor["words"], image_width, image_height)
            result.vendor_name = OCRField(
                name="vendor_name",
                value=vendor["text"],
                confidence=vendor["confidence"],
                bounding_box=bbox,
            )
        
        # Extract invoice number
        invoice_num = self._extract_field(lines, ["invoice", "inv", "bill", "receipt", "#"])
        if invoice_num:
            bbox = self._create_bbox([invoice_num], image_width, image_height)
            result.invoice_number = OCRField(
                name="invoice_number",
                value=invoice_num["text"],
                confidence=invoice_num["confidence"],
                bounding_box=bbox,
            )
        
        # Extract dates
        dates = self._extract_dates(lines, image_width, image_height)
        if dates.get("invoice_date"):
            result.invoice_date = dates["invoice_date"]
        if dates.get("due_date"):
            result.due_date = dates["due_date"]
        
        # Extract amounts
        amounts = self._extract_amounts(lines, image_width, image_height)
        if amounts.get("total"):
            result.total_amount = amounts["total"]
        if amounts.get("subtotal"):
            result.subtotal = amounts["subtotal"]
        if amounts.get("tax"):
            result.tax_amount = amounts["tax"]
        
        # Extract line items
        line_items = self._extract_line_items(lines, image_width, image_height)
        result.line_items = line_items
        
        # Set currency (default to INR)
        currency_symbols = self._find_currency(words)
        result.currency = OCRField(
            name="currency",
            value=currency_symbols or "INR",
            confidence=0.8 if currency_symbols else 0.5,
        )
        
        # Calculate overall confidence
        result.calculate_overall_confidence()
        
        return result
    
    def _group_into_lines(
        self,
        words: List[Dict],
        threshold: int = 15,
    ) -> List[List[Dict]]:
        """Group words into lines based on Y coordinate."""
        if not words:
            return []
        
        lines_dict = {}
        for word in words:
            y = word['top']
            added = False
            
            for existing_y in list(lines_dict.keys()):
                if abs(existing_y - y) < threshold:
                    lines_dict[existing_y].append(word)
                    added = True
                    break
            
            if not added:
                lines_dict[y] = [word]
        
        # Sort lines by Y coordinate and words within lines by X coordinate
        sorted_lines = []
        for y in sorted(lines_dict.keys()):
            line = sorted(lines_dict[y], key=lambda w: w['left'])
            sorted_lines.append(line)
        
        return sorted_lines
    
    def _extract_vendor(self, lines: List[List[Dict]]) -> Optional[Dict]:
        """Extract vendor name (usually first few lines with high confidence)."""
        if not lines:
            return None
        
        # Take first non-empty line with good confidence
        for line in lines[:5]:
            text = " ".join(w["text"] for w in line)
            if len(text) > 3:
                avg_conf = sum(w["confidence"] for w in line) / len(line)
                if avg_conf > 0.6:
                    return {
                        "text": text.strip(),
                        "confidence": avg_conf,
                        "words": line,
                    }
        
        return None
    
    def _extract_field(
        self,
        lines: List[List[Dict]],
        keywords: List[str],
    ) -> Optional[Dict]:
        """Extract field value after finding keyword."""
        for line in lines:
            line_text = " ".join(w["text"] for w in line).lower()
            
            for keyword in keywords:
                if keyword.lower() in line_text:
                    # Find value after keyword
                    idx = next(
                        (i for i, w in enumerate(line) if keyword.lower() in w["text"].lower()),
                        None
                    )
                    if idx is not None and idx + 1 < len(line):
                        value_word = line[idx + 1]
                        # Clean value (remove : , etc.)
                        value = re.sub(r'[:\,]', '', value_word["text"]).strip()
                        if value:
                            return {
                                "text": value,
                                "confidence": value_word["confidence"],
                                "left": value_word["left"],
                                "top": value_word["top"],
                                "width": value_word["width"],
                                "height": value_word["height"],
                            }
        
        return None
    
    def _extract_dates(
        self,
        lines: List[List[Dict]],
        image_width: int,
        image_height: int,
    ) -> Dict[str, Optional[OCRField]]:
        """Extract dates from text."""
        dates = {}
        date_pattern = r'\d{1,2}[-/]\d{1,2}[-/]\d{2,4}|\d{4}[-/]\d{1,2}[-/]\d{1,2}'
        
        for line in lines:
            line_text = " ".join(w["text"] for w in line)
            line_lower = line_text.lower()
            
            # Look for date patterns
            match = re.search(date_pattern, line_text)
            if match:
                date_str = match.group()
                try:
                    # Parse date
                    parsed_date = self._parse_date(date_str)
                    
                    # Find the word containing this date
                    date_word = next(
                        (w for w in line if date_str in w["text"]),
                        line[0]
                    )
                    
                    bbox = self._create_bbox([date_word], image_width, image_height)
                    
                    # Determine if invoice date or due date
                    if "due" in line_lower:
                        dates["due_date"] = OCRField(
                            name="due_date",
                            value=parsed_date,
                            confidence=date_word["confidence"],
                            bounding_box=bbox,
                            raw_text=date_str,
                        )
                    else:
                        dates["invoice_date"] = OCRField(
                            name="invoice_date",
                            value=parsed_date,
                            confidence=date_word["confidence"],
                            bounding_box=bbox,
                            raw_text=date_str,
                        )
                        
                except:
                    pass
        
        return dates
    
    def _extract_amounts(
        self,
        lines: List[List[Dict]],
        image_width: int,
        image_height: int,
    ) -> Dict[str, Optional[OCRField]]:
        """Extract monetary amounts."""
        amounts = {}
        amount_pattern = r'[\$₹€£]?\s*\d+[,\.]?\d*\.?\d+'
        
        for line in lines:
            line_text = " ".join(w["text"] for w in line)
            line_lower = line_text.lower()
            
            # Find amounts
            matches = re.findall(amount_pattern, line_text)
            if matches:
                amount_str = matches[-1]  # Take last amount in line
                try:
                    amount = self._parse_amount(amount_str)
                    
                    # Find word containing amount
                    amount_word = next(
                        (w for w in line if any(d in w["text"] for d in matches)),
                        line[-1]
                    )
                    
                    bbox = self._create_bbox([amount_word], image_width, image_height)
                    
                    # Determine type
                    if "total" in line_lower:
                        amounts["total"] = OCRField(
                            name="total_amount",
                            value=amount,
                            confidence=amount_word["confidence"],
                            bounding_box=bbox,
                            raw_text=amount_str,
                        )
                    elif "subtotal" in line_lower or "sub-total" in line_lower:
                        amounts["subtotal"] = OCRField(
                            name="subtotal",
                            value=amount,
                            confidence=amount_word["confidence"],
                            bounding_box=bbox,
                            raw_text=amount_str,
                        )
                    elif "tax" in line_lower or "gst" in line_lower or "vat" in line_lower:
                        amounts["tax"] = OCRField(
                            name="tax_amount",
                            value=amount,
                            confidence=amount_word["confidence"],
                            bounding_box=bbox,
                            raw_text=amount_str,
                        )
                        
                except:
                    pass
        
        return amounts
    
    def _extract_line_items(
        self,
        lines: List[List[Dict]],
        image_width: int,
        image_height: int,
    ) -> List[OCRLineItem]:
        """Extract line items from bill."""
        items = []
        amount_pattern = r'\d+[,\.]?\d*\.?\d+'
        
        for idx, line in enumerate(lines):
            # Skip header lines and total lines
            line_text = " ".join(w["text"] for w in line).lower()
            if any(skip in line_text for skip in ["total", "subtotal", "tax", "invoice", "date", "bill"]):
                continue
            
            # Look for lines with at least 3 words (likely item description + numbers)
            if len(line) >= 3:
                numbers = []
                description_words = []
                
                for word in line:
                    if re.match(r'^\d+[,\.]?\d*\.?\d*$', word["text"]):
                        try:
                            num = float(word["text"].replace(',', ''))
                            numbers.append(num)
                        except:
                            description_words.append(word["text"])
                    else:
                        description_words.append(word["text"])
                
                # Need at least 2 numbers (quantity and price/total)
                if len(numbers) >= 2 and description_words:
                    description = " ".join(description_words)
                    
                    # Heuristic: first number is quantity, last is total
                    quantity = Decimal(str(numbers[0]))
                    total = Decimal(str(numbers[-1]))
                    unit_price = total / quantity if quantity > 0 else total
                    
                    bbox = self._create_bbox(line, image_width, image_height)
                    avg_conf = sum(w["confidence"] for w in line) / len(line)
                    
                    items.append(OCRLineItem(
                        description=description,
                        quantity=quantity,
                        unit_price=unit_price,
                        total_price=total,
                        confidence=avg_conf,
                        bounding_box=bbox,
                        sort_order=idx,
                    ))
        
        return items
    
    def _create_bbox(
        self,
        words: List[Dict],
        image_width: int,
        image_height: int,
    ) -> BoundingBox:
        """Create bounding box from list of words."""
        if not words:
            return BoundingBox(0, 0, 0, 0)
        
        x1 = min(w["left"] for w in words)
        y1 = min(w["top"] for w in words)
        x2 = max(w["left"] + w["width"] for w in words)
        y2 = max(w["top"] + w["height"] for w in words)
        
        return BoundingBox(
            x1=x1 / image_width,
            y1=y1 / image_height,
            x2=x2 / image_width,
            y2=y2 / image_height,
        )
    
    def _find_currency(self, words: List[Dict]) -> Optional[str]:
        """Find currency symbol in text."""
        currency_map = {
            "₹": "INR",
            "$": "USD",
            "€": "EUR",
            "£": "GBP",
            "rs": "INR",
            "inr": "INR",
            "usd": "USD",
        }
        
        for word in words:
            text_lower = word["text"].lower()
            for symbol, code in currency_map.items():
                if symbol in text_lower:
                    return code
        
        return None
    
    def _parse_date(self, date_str: str) -> date:
        """Parse date string to date object."""
        # Try different formats
        formats = [
            "%d-%m-%Y", "%d/%m/%Y", "%d-%m-%y", "%d/%m/%y",
            "%Y-%m-%d", "%Y/%m/%d", "%m-%d-%Y", "%m/%d/%Y",
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except:
                continue
        
        # Default to today
        return date.today()
    
    def _parse_amount(self, amount_str: str) -> Decimal:
        """Parse amount string to Decimal."""
        # Remove currency symbols and spaces
        cleaned = re.sub(r'[₹$€£\s]', '', amount_str)
        # Remove commas
        cleaned = cleaned.replace(',', '')
        return Decimal(cleaned)
    
    async def health_check(self) -> Tuple[bool, str]:
        """Check if Tesseract is available."""
        try:
            version = pytesseract.get_tesseract_version()
            return True, f"Tesseract {version} is available"
        except Exception as e:
            return False, f"Tesseract not available: {str(e)}"
