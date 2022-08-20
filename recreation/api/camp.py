import datetime as dt
import enum
import itertools
from typing import Optional

from pydantic import BaseModel, Extra, Field


class CampgroundType(str, enum.Enum):
    standard = "STANDARD"


class CampsiteType(str, enum.Enum):
    cabin_electric = "CABIN ELECTRIC"
    cabin_nonelectric = "CABIN NONELECTRIC"
    group_tetn_only_area_nonelectric = "GROUP TENT ONLY AREA NONELECTRIC"
    lookout = "LOOKOUT"
    management = "MANAGEMENT"
    rv_nonelectric = "RV NONELECTRIC"
    standard_electric = "STANDARD ELECTRIC"
    standard_nonelectric = "STANDARD NONELECTRIC"
    tent_only_nonelectric = "TENT ONLY NONELECTRIC"
    walk_to = "WALK TO"


class CampsiteStatus(str, enum.Enum):
    not_available = "Not Available"
    not_reservable = "Not Reservable"
    not_reservable_management = "Not Reservable Management"
    open = "Open"


class CampsiteReserveType(str, enum.Enum):
    non_site_specific = "Non Site-Specific"
    site_specific = "Site-Specific"


class CampsiteAvailabilityStatus(str, enum.Enum):
    available = "Available"
    not_available = "Not Available"
    not_reservable = "Not Reservable"
    not_reservable_management = "Not Reservable Management"
    reserved = "Reserved"


class RGApiCampground(BaseModel):
    campsite_ids: list[str] = Field(..., alias="campsites")
    email:  Optional[str] = Field(..., alias="facility_email")
    id: str = Field(..., alias="facility_id")
    latitude: float = Field(..., alias="facility_latitude")
    longitude: float = Field(..., alias="facility_longitude")
    map_url:  Optional[str] = Field(..., alias="facility_map_url")
    name: str = Field(..., alias="facility_name")
    phone: str = Field(..., alias="facility_phone")
    campground_type: CampgroundType = Field(..., alias="facility_type")
    parent_asset_id: str

    class Config:
        extra = Extra.ignore

    def __repr__(self) -> str:
        return f"{self.__repr_name__()}(id={self.id}, name={self.name})"

    def __str__(self) -> str:
        return self.__repr__()


class RGApiCampsite(BaseModel):
    id: str = Field(..., alias="campsite_id")
    latitude:  float = Field(..., alias="campsite_latitude")
    longitude: float = Field(..., alias="campsite_longitude")
    name: str = Field(..., alias="campsite_name")
    reserve_type: CampsiteReserveType = Field(..., alias="campsite_reserve_type")
    status: CampsiteStatus = Field(..., alias="campsite_status")
    campsite_type: CampsiteType
    campground_id: str = Field(..., alias="facility_id")
    loop: Optional[str]
    parent_site_id: Optional[str]

    class Config:
        extra = Extra.ignore

    def __repr__(self) -> str:
        return f"{self.__repr_name__()}(id={self.id}, name={self.name}, type={self.campsite_type}, status={self.status})"

    def __str__(self) -> str:
        return self.__repr__()


class RgApiCampsiteAvailability(BaseModel):
    availabilities: dict[dt.datetime, CampsiteAvailabilityStatus]
    id: str = Field(..., alias="campsite_id")
    reserve_type: CampsiteReserveType = Field(..., alias="campsite_reserve_type")
    campsite_type: CampsiteType
    loop: str
    max_num_people: int
    min_num_people: int
    site: str
    type_of_use: str

    class Config:
        extra = Extra.ignore

    def __repr__(self) -> str:
        return f"{self.__repr_name__()}(id={self.id})"

    def __str__(self) -> str:
        return self.__repr__()


class RGApiCampgroundAvailability(BaseModel):
    campsites: dict[str, RgApiCampsiteAvailability]

    class Config:
        extra = Extra.ignore

    def __repr__(self) -> str:
        dates = set(itertools.chain.from_iterable(
            list(campsite.availabilities.keys())
            for campsite in self.campsites.values()
        ))

        min_date = None
        max_date = None
        if len(dates) > 0:
            min_date = min(dates).date().isoformat()
            max_date = max(dates).date().isoformat()
        return f"{self.__repr_name__()}(start={min_date}, end={max_date})"

    def __str__(self) -> str:
        return self.__repr__()
