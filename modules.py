import re
from datetime import date
from typing import List
from pydantic import BaseModel, Field, field_validator, model_validator

class Captain(BaseModel):
    name: str
    license_number: str

    @field_validator("license_number")
    @classmethod
    def validate_license(cls, v: str) -> str:
        pattern = r"^GAL-\d{4}-[A-Z]{2}$"
        if not re.match(pattern, v):
            raise ValueError("Invalid Format. (Required: GAL-1234-XY)")
        return v

class Cargo(BaseModel):
    item_name: str
    weight_kg: float = Field(gt=0)

class Spaceship(BaseModel):
    ship_id: str
    model_name: str
    max_capacity_kg: float = Field(gt=0)
    captain: Captain
    cargo_hold: List[Cargo]
    arrival_date: date

    @field_validator("arrival_date")
    @classmethod
    def validate_arrival(cls, v: date) -> date:
        if v < date.today():
            raise ValueError("Arrival date cannot be in the past.")
        return v

    @model_validator(mode="after")
    def check_capacity(self) -> "Spaceship":
        total_weight = sum(item.weight_kg for item in self.cargo_hold)
        if total_weight > self.max_capacity_kg:
            raise ValueError(f"Overload! {total_weight}kg > {self.max_capacity_kg}kg limit.")
        return self
