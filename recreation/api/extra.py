import enum
from typing import Optional

from pydantic import BaseModel, Extra, Field


class LocationType(str, enum.Enum):
    campground = "Campground"
    permit = "Permit"


class AlertLevel(str, enum.Enum):
    warning = "WARNING"


class RGAapiAlert(BaseModel):
    alert_level: AlertLevel
    body: str
    location_id: str
    location_name: str
    location_type: LocationType
    priority: int


class RGApiCarrierRating(BaseModel):
    average_rating: float
    carrier: str
    number_of_ratings: int
    star_counts: Optional[dict[int, int]]


class RGApiRatingAggregate(BaseModel):
    aggregate_cell_coverage_ratings: list[RGApiCarrierRating]
    average_rating: float
    location_id: str
    location_type: LocationType
    number_of_ratings: int
    star_counts: dict[int, int]
