from dataclasses import dataclass

@dataclass
class Item:
    """
    Internal representation of a Bill Item.
    """
    name: str
    quantity: float
    unit_price: float
    total_price: float
    confidence: float = 0.0
