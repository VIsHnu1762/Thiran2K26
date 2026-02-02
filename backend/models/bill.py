from dataclasses import dataclass, field
from typing import List
from .item import Item

@dataclass
class Bill:
    """
    Internal representation of a Bill.
    """
    items: List[Item] = field(default_factory=list)
    sub_total: float = 0.0
    tax: float = 0.0
    grand_total: float = 0.0
    overall_confidence: float = 0.0
