from dataclasses import dataclass
import datetime as dt
import enum
import itertools
from tracemalloc import start
from typing import Dict, Iterable, List, Optional, Any, Union
from operator import attrgetter
from dateutil import rrule

from apiclient import (    
    APIClient,
    endpoint,
    paginated,
    retry_request,
    HeaderAuthentication,
    JsonResponseHandler,
    JsonRequestFormatter,
)
from apiclient.response import Response
from apiclient.exceptions import ClientError
from apiclient.utils.typing import JsonType
from apiclient_pydantic import (
    params_serializer, response_serializer, serialize_all_methods
)

from fake_useragent import UserAgent

from pydantic import BaseModel, ValidationError, Extra, Field, PrivateAttr


IntOrStr = Union[int, str]


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

    # _entries: dict[str, "RgApiPermitEntrance"] = PrivateAttr()
    # _exits: dict[str, "RgApiPermitEntrance"] = PrivateAttr()

    class Config:
        extra = Extra.ignore

    # def __init__(self, **data: Any) -> None:
    #     print("type", data["type"])
    #     super().__init__(**data)

    def __repr__(self) -> str:
        return f"{self.__repr_name__()}(id={self.id}, name={self.name})"

    def __str__(self) -> str:
        return self.__repr__()

    # @property
    # def entries(self) -> dict[str, "RgApiPermitEntrance"]:
    #     return self._entries

    # @property
    # def exits(self) -> dict[str, "RgApiPermitEntrance"]:
    #     return self._exits

    # def set_entrances(self, entrances: dict[str, "RgApiPermitEntrance"]) -> None:
    #     self._entries = {
    #         entry: entrances[entry]
    #         for entry in self.entry_ids
    #     }
    #     self._exits = {
    #         _exit: entrances[_exit]
    #         for _exit in self.exit_ids
    #     }


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

    #     # for divis in self.divisions.values():
    #     #     divis.set_entrances(self._entrances)


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

    # def get_availability(self, division_id: IntOrStr, date: dt.date) -> RgApiPermitDateAvailability:
    #     did = str(division_id)
    #     key = dt.datetime(date.year, date.month, date.day, tzinfo=dt.timezone.utc)
    #     return self.availability[did].date_availability[key]

    # def availability_list(self) -> list["BaseAvailability"]:
    #     availability: List[BaseAvailability] = []

    #     for division_id, divis_avail in self.availability.items():
    #         for date, date_avail in divis_avail.date_availability.items():
    #             avail = PermitAvailability(
    #                 id=division_id,
    #                 date=date,
    #                 remaining=date_avail.remaining,
    #                 total=date_avail.total,
    #                 is_walkup=date_avail.show_walkup
    #             )
    #             availability.append(avail)
                
    #     availability.sort(key=attrgetter("id", "date"))
    #     return availability


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

    # def get_availability(self, division_id: IntOrStr, date: dt.date) -> RgApiPermitInyoDivisionAvailability:
    #     did = str(division_id)
    #     return self.payload[date][did]

    # def availability_list(self) -> list["BaseAvailability"]:
    #     availability: List[BaseAvailability] = []

    #     for date, date_avail in self.payload.items():
    #         for division_id, divis_avail in date_avail.items():
    #             avail = PermitAvailability(
    #                 date=date,
    #                 id=division_id,
    #                 remaining=divis_avail.remaining,
    #                 total=divis_avail.total,
    #                 is_walkup=divis_avail.is_walkup
    #             )
    #             availability.append(avail)
        
    #     availability.sort(key=attrgetter("id", "date"))
    #     return availability
