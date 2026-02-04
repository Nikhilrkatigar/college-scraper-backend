from pydantic import BaseModel

class CollegeCreate(BaseModel):
    name: str
    type: str            # engineering / management
    region: str          # South / North / etc
    state: str
    district: str
    website: str | None = None
