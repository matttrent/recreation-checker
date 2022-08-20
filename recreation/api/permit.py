import datetime as dt
import enum
import itertools

from pydantic import BaseModel, Extra, Field, PrivateAttr


class PermitDivisionType(str, enum.Enum):
    destination_zone = "Destination Zone"
    entry_point = "Entry Point"
    trailhead = "Trailhead"


class RgApiPermitDivision(BaseModel):
    code: str
    district: str
    description: str
    entry_ids: list[str]
    exit_ids: list[str]
    id: str
    latitude: float
    longitude: float
    name: str
    division_type: PermitDivisionType = Field(..., alias="type")

    class Config:
        extra = Extra.ignore

    def __repr__(self) -> str:
        return f"{self.__repr_name__()}(id={self.id}, name={self.name})"

    def __str__(self) -> str:
        return self.__repr__()


class RgApiPermitEntrance(BaseModel):
    has_parking: bool
    id: str
    name: str
    is_entry: bool
    is_exit: bool
    is_issue_station: bool
    latitude: float
    longitude: float
    town: str

    class Config:
        extra = Extra.ignore

    def __repr__(self) -> str:
        return f"{self.__repr_name__()}(id={self.id}, name={self.name})"

    def __str__(self) -> str:
        return self.__repr__()


class RGApiPermit(BaseModel):
    id: str
    name: str
    divisions: dict[str, RgApiPermitDivision]
    entrance_list: list[RgApiPermitEntrance] = Field(list(), alias="entrances")

    _entrances: dict[str, RgApiPermitEntrance] = PrivateAttr()

    def __init__(self, **data) -> None:
        super().__init__(**data)

        self._entrances = {
            entry.id : entry
            for entry in self.entrance_list
        }


    class Config:
        extra = Extra.ignore

    def __repr__(self) -> str:
        return f"{self.__repr_name__()}(id={self.id}, name={self.name})"

    def __str__(self) -> str:
        return self.__repr__()

    @property
    def entrances(self) -> dict[str, RgApiPermitEntrance]:
        return self._entrances


class RgApiPermitDateAvailability(BaseModel):
    is_secret_quota: bool
    remaining: int
    show_walkup: bool
    total: int


class RgApiPermitDivisionAvailability(BaseModel):
    division_id: str
    date_availability: dict[dt.datetime, RgApiPermitDateAvailability]

    def __repr__(self) -> str:
        return f"{self.__repr_name__()}(id={self.division_id})"

    def __str__(self) -> str:
        return self.__repr__()


class RGApiPermitAvailability(BaseModel):
    permit_id: str
    next_available_date: dt.datetime
    availability: dict[str, RgApiPermitDivisionAvailability]

    class Config:
        extra = Extra.ignore

    def __repr__(self) -> str:
        dates = set(itertools.chain.from_iterable(
            list(avail.date_availability.keys())
            for avail in self.availability.values()
        ))

        min_date = None
        max_date = None
        if len(dates) > 0:
            min_date = min(dates).date().isoformat()
            max_date = max(dates).date().isoformat()
        return f"{self.__repr_name__()}(id={self.permit_id}, start={min_date}, end={max_date})"

    def __str__(self) -> str:
        return self.__repr__()


class RgApiPermitInyoDivisionAvailability(BaseModel):
    is_walkup: bool
    total: int
    remaining: int


RgApiPermitDateDivisionAvailability = dict[str, RgApiPermitInyoDivisionAvailability]


class RGApiPermitInyoAvailability(BaseModel):
    payload: dict[dt.date, RgApiPermitDateDivisionAvailability]

    def __repr__(self) -> str:
        min_date = min(self.payload.keys()).isoformat()
        max_date = max(self.payload.keys()).isoformat()
        return f"{self.__repr_name__()}(start={min_date}, end={max_date})"
