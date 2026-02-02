from typing import List
from ..schemas.item_schema import ItemSchema
from ..utils.math_checks import validate_line_total, validate_grand_total

class ErrorDetectionAgent:
    """
    Validates business logic errors in the parsed bill.
    """
    def detect_errors(self, items: List[ItemSchema], grand_total: float) -> List[str]:
        errors = []
        
        # 1. Validate Grand Total (Sum of line totals == Grand Total)
        if not validate_grand_total(items, grand_total):
            errors.append(f"Math Mismatch: Sum of items ({sum(i.line_total for i in items)}) does not match Grand Total ({grand_total})")
            
        # 2. Item Level Validation
        for idx, item in enumerate(items):
            # Check for non-positive quantity or price
            if item.quantity <= 0:
                errors.append(f"Item '{item.name}' has invalid quantity: {item.quantity}")
                
            if item.unit_price <= 0:
                errors.append(f"Item '{item.name}' has invalid price: {item.unit_price}")
                
            # Check line math (Qty * Unit Price == Total)
            # Note: OCR often misses unit price, so this might be noisy. 
            # We only check if we have all three components.
            if item.quantity > 0 and item.unit_price > 0:
                if not validate_line_total(item.quantity, item.unit_price, item.line_total):
                    errors.append(f"Math Mismatch for item '{item.name}': {item.quantity} * {item.unit_price} != {item.line_total}")
                    
        return errors
