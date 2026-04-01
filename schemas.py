from pydantic import BaseModel

class BaziRequest(BaseModel):
    name: str
    gender: str
    city: str
    year: int
    month: int
    day: int
    hour: int
    minute: int