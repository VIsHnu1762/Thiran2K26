from pydantic import BaseModel

class ItemSchema(BaseModel):
    """
    API Schema for a Bill Item.
    """
    name: str
    quantity: float
    unit_price: float
    line_total: float
    confidence: float
