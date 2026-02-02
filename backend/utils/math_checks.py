from typing import List
from ..schemas.item_schema import ItemSchema

def validate_line_total(quantity: float, unit_price: float, line_total: float, tolerance: float = 0.01) -> bool:
    """
    Checks if quantity * unit_price is approximately equal to line_total.
    """
    expected = quantity * unit_price
    return abs(expected - line_total) <= tolerance

def validate_grand_total(items: List[ItemSchema], grand_total: float, tolerance: float = 0.01) -> bool:
    """
    Checks if the sum of all item line totals matches the grand total.
    """
    calculated_total = sum(item.line_total for item in items)
    return abs(calculated_total - grand_total) <= tolerance
