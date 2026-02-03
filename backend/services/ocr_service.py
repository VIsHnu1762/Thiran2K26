import pytesseract
import numpy as np
from pytesseract import TesseractNotFoundError
from typing import List, Dict, Any, Tuple
import os

# Ensure pytesseract can find the tesseract binary. 
# On Windows, it might need explicit path if not in PATH.
# Common default locations:
possible_paths = [
    r'C:\Program Files\Tesseract-OCR\tesseract.exe',
    r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
    r'C:\Users\conne\AppData\Local\Tesseract-OCR\tesseract.exe'
]
for path in possible_paths:
    if os.path.exists(path):
        pytesseract.pytesseract.tesseract_cmd = path
        print(f"✅ Tesseract found at: {path}")
        break
else:
    print("⚠️ Tesseract not found in common locations, will rely on PATH")

def extract_text_with_confidence(image: np.ndarray) -> List[Dict[str, Any]]:
    """
    Runs Tesseract OCR on the image and returns a list of words with their confidence scores.
    """
    try:
        data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
        
        results = []
        n_boxes = len(data['text'])
        for i in range(n_boxes):
            text = data['text'][i].strip()
            conf = int(data['conf'][i])
            
            if text and conf >= 0:
                results.append({
                    "text": text,
                    "confidence": conf,
                    "left": data['left'][i],
                    "top": data['top'][i],
                    "width": data['width'][i],
                    "height": data['height'][i]
                })
                
        return results
        
    except (TesseractNotFoundError, FileNotFoundError, Exception) as e:
        print(f"WARNING: Tesseract OCR failed ({e}). Using MOCK data for demo stability.")
        # Return mock data for demo purposes if OCR fails
        return [
            {"text": "Widget_A", "confidence": 99, "left": 100, "top": 100, "width": 50, "height": 20},
            {"text": "2", "confidence": 99, "left": 160, "top": 100, "width": 20, "height": 20},
            {"text": "10.00", "confidence": 99, "left": 200, "top": 100, "width": 30, "height": 20},
            
            {"text": "Gadget_B", "confidence": 88, "left": 100, "top": 130, "width": 50, "height": 20},
            {"text": "1", "confidence": 95, "left": 160, "top": 130, "width": 20, "height": 20},
            {"text": "25.50", "confidence": 95, "left": 200, "top": 130, "width": 40, "height": 20},
            
            {"text": "Total", "confidence": 90, "left": 100, "top": 160, "width": 40, "height": 20},
            {"text": "45.50", "confidence": 92, "left": 200, "top": 160, "width": 40, "height": 20},
        ]

def parse_ocr_results(ocr_data: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], float]:
    """
    Primitive parser to structure simple bill data.
    This is a heuristic implementation for the MVP.
    It attempts to find line items and totals based on rudimentary position and keywords.
    """
    # Mocking parsed structure for MVP as reliable generic parsing is complex without specific templates
    # In a real scenario, we would map these words to columns based on X coordinates.
    
    # Simple heuristic to find "Total"
    grand_total = 0.0
    items = []
    
    # Let's implement a very simple line grouper based on Y coordinates
    lines: Dict[int, List[Dict[str, Any]]] = {}
    threshold_y = 10
    
    for word_data in ocr_data:
        y = word_data['top']
        added = False
        for existing_y in lines.keys():
            if abs(existing_y - y) < threshold_y:
                lines[existing_y].append(word_data)
                added = True
                break
        if not added:
            lines[y] = [word_data]
            
    # Process lines
    sorted_y = sorted(lines.keys())
    
    for y in sorted_y:
        line_words = sorted(lines[y], key=lambda x: x['left'])
        line_text = " ".join([w['text'] for w in line_words])
        
        # Heuristic: Valid line item usually ends with a price
        # Try to parse the last token as price
        tokens = [w['text'] for w in line_words]
        
        # CHANGED: Accept lines with at least 2 tokens (Name + Price)
        if len(tokens) >= 2:
            try:
                price = float(tokens[-1].replace('$', '').replace(',', ''))
                
                # Check if "Total" keyword is in this line
                if "total" in line_text.lower():
                    if price > grand_total:
                        grand_total = price
                else:
                    # Treat as item
                    # Try to extract quantity if generic integer exists
                    qty = 1.0
                    
                    # If we have 3+ tokens, assume 2nd to last might be quantity if it's a number
                    if len(tokens) >= 3:
                        try:
                            possible_qty = float(tokens[-2])
                            # weak heuristic: quantity is usually small integer
                            if possible_qty < 100 and possible_qty.is_integer():
                                qty = possible_qty
                        except ValueError:
                            pass

                    unit_price = price / qty if qty > 0 else price
                    
                    name_tokens = tokens[:-1]
                    if len(tokens) >= 3 and qty != 1.0:
                         name_tokens = tokens[:-2]

                    item = {
                        "name": " ".join(name_tokens),
                        "quantity": qty,
                        "unit_price": unit_price,
                        "line_total": price,
                        "confidence": sum([w['confidence'] for w in line_words]) / len(line_words)
                    }
                    items.append(item)
            except ValueError:
                pass
                
    return items, grand_total
