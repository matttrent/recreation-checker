from dataclasses import dataclass
import datetime as dt
import enum
import itertools
from typing import Dict, List, Optional, Any, Union

from apiclient import (    APIClient,
    endpoint,
    paginated,
    retry_request,
    HeaderAuthentication,
    JsonResponseHandler,
    JsonRequestFormatter
    )
from apiclient.response import Response
from apiclient.utils.typing import JsonType
from apiclient_pydantic import (
    params_serializer, response_serializer, serialize_all_methods
)

from fake_useragent import UserAgent

from pydantic import BaseModel, ValidationError, Extra, Field, PrivateAttr


IntOrStr = Union[int, str]


class FacilityType(str, enum.Enum):
    standard = "STANDARD"


class CampsiteType(str, enum.Enum):
    management = "MANAGEMENT"
    rv_nonelectric = "RV NONELECTRIC"
    standard_nonelectric = "STANDARD NONELECTRIC"
    tent_only_nonelectric = "TENT ONLY NONELECTRIC"


class CampsiteStatus(str, enum.Enum):
    not_available = "Not Available"
    not_reservable_management = "Not Reservable Management"
    open = "Open"


class CampsiteReserveType(str, enum.Enum):
    non_site_specific = "Non Site-Specific"
    site_specific = "Site-Specific"


class CampsiteAvailabilityStatus(str, enum.Enum):
    not_available = "Not Available"
    not_reservable_management = "Not Reservable Management"
    reserved = "Reserved"


class RGApiCampground(BaseModel):
    campsite_ids: List[str] = Field(list(), alias="campsites")
    facility_email:  Optional[str]
    facility_id: str
    facility_latitude:  float
    facility_longitude: float
    facility_map_url:  Optional[str]
    facility_name: str
    facility_phone: str
    facility_type: FacilityType
    parent_asset_id: str

    class Config:
        extra = Extra.ignore

    def __repr__(self) -> str:
        return f"{self.__repr_name__()}(id={self.facility_id}, name={self.facility_name})"

    def __str__(self) -> str:
        return self.__repr__()


class RGApiCampsite(BaseModel):
    campsite_id: str
    campsite_latitude:  float
    campsite_longitude: float
    campsite_name: str
    campsite_reserve_type: str
    campsite_status: CampsiteStatus
    campsite_type: CampsiteType
    facility_id: str
    loop: Optional[str]
    parent_site_id: Optional[str]

    class Config:
        extra = Extra.ignore

    def __repr__(self) -> str:
        return f"{self.__repr_name__()}(id={self.campsite_id}, name={self.campsite_name}, type={self.campsite_type}, status={self.campsite_status})"

    def __str__(self) -> str:
        return self.__repr__()


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
    type: str

    # _entries: dict[str, "RgApiPermitEntrance"] = PrivateAttr()
    # _exits: dict[str, "RgApiPermitEntrance"] = PrivateAttr()

    class Config:
        extra = Extra.ignore

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

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

        self._entrances = {
            entry.id : entry
            for entry in self.entrance_list
        }

        # for divis in self.divisions.values():
        #     divis.set_entrances(self._entrances)


    class Config:
        extra = Extra.ignore

    def __repr__(self) -> str:
        return f"{self.__repr_name__()}(id={self.id}, name={self.name})"

    def __str__(self) -> str:
        return self.__repr__()

    @property
    def entrances(self) -> dict[str, RgApiPermitEntrance]:
        return self._entrances


class RgApiCampsiteAvailability(BaseModel):
    availabilities: Dict[dt.datetime, CampsiteAvailabilityStatus]
    campsite_id: str
    campsite_reserve_type: CampsiteReserveType
    campsite_type: CampsiteType
    loop: str
    max_num_people: int
    min_num_people: int
    site: str
    type_of_use: str

    class Config:
        extra = Extra.ignore

    def __repr__(self) -> str:
        return f"{self.__repr_name__()}(id={self.campsite_id})"

    def __str__(self) -> str:
        return self.__repr__()


class RGApiCampgroundAvailability(BaseModel):
    campsites: Dict[str, RgApiCampsiteAvailability]

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

    def get_availability(self, campsite_id: IntOrStr, date: dt.date) -> str:
        cid = str(campsite_id)
        key = dt.datetime(date.year, date.month, date.day, tzinfo=dt.timezone.utc)
        return self.campsites[cid].availabilities[key]


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

    def get_availability(self, division_id: IntOrStr, date: dt.date) -> RgApiPermitDateAvailability:
        did = str(division_id)
        key = dt.datetime(date.year, date.month, date.day, tzinfo=dt.timezone.utc)
        return self.availability[did].date_availability[key]


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

    def get_availability(self, division_id: IntOrStr, date: dt.date) -> RgApiPermitInyoDivisionAvailability:
        did = str(division_id)
        return self.payload[date][did]


@endpoint(base_url="https://www.recreation.gov/api")
class RecreationGovEndpoint:
    alert = "communication/external/alert"

    campground = "camps/campgrounds/{id}"
    campsite = "camps/campsites/{id}"
    permit = "permitcontent/{id}"

    campground_availability = "camps/availability/campground/{id}/month"
    permit_availability = "permits/{id}/availability/month" 
    permitinyo_availability = "permitinyo/{id}/availability"


# class JsonPayloadResponseHandler(JsonResponseHandler):
    
#     @staticmethod
#     def get_request_data(response: Response) -> Optional[JsonType]:
#         response_json = JsonResponseHandler.get_request_data(response)
#         return response_json["payload"]


@serialize_all_methods()
class RecreationGovClient(APIClient):

    def __init__(self):
        super().__init__(
            response_handler=JsonResponseHandler,
            request_formatter=JsonRequestFormatter,
        )

    def get_default_headers(self) -> dict:
        headers = super().get_default_headers()
        headers["User-Agent"] = UserAgent().random
        return headers

    def get_campground(self, campground_id: IntOrStr) -> RGApiCampground:
        url = RecreationGovEndpoint.campground.format(id=campground_id)
        headers = self.get_default_headers()
        resp = self.get(url, headers=headers)
        print("facility_type", resp["campground"]["facility_type"])
        return resp["campground"]

    def get_campsite(self, campsite_id: IntOrStr) -> RGApiCampsite:
        url = RecreationGovEndpoint.campsite.format(id=campsite_id)
        headers = self.get_default_headers()
        resp = self.get(url, headers=headers)
        print("campsite_status", resp["campsite"]["campsite_status"])
        print("campsite_type", resp["campsite"]["campsite_type"])
        return resp["campsite"]

    def get_permit(self, permit_id: IntOrStr) -> RGApiPermit:
        url = RecreationGovEndpoint.permit.format(id=permit_id)
        headers = self.get_default_headers()
        resp = self.get(url, headers=headers)
        return resp["payload"]

    @staticmethod
    def _format_date(date_object: dt.datetime, with_ms: bool = True) -> str:
        ms = ".000" if with_ms else ""
        date_formatted = dt.datetime.strftime(date_object, f"%Y-%m-%dT00:00:00{ms}Z")
        return date_formatted

    def get_campground_availability(
        self, campground_id: IntOrStr, start_date: dt.date
    ) -> RGApiCampgroundAvailability:
        url = RecreationGovEndpoint.campground_availability.format(id=campground_id)
        headers = self.get_default_headers()
        start_date = start_date.replace(day=1)
        params = {
            "start_date": self._format_date(start_date)
        }
        resp = self.get(url, headers=headers, params=params)

        campsite_reserve_types = set(
            campsite["campsite_reserve_type"]
            for campsite in resp["campsites"].values()
        )
        print("campsite reserve types", campsite_reserve_types)

        campsite_types = set(
            campsite["campsite_type"]
            for campsite in resp["campsites"].values()
        )
        print("campsite types", campsite_types)

        return resp

    def get_permit_availability(
        self, permit_id: IntOrStr, start_date: dt.date
    ) -> RGApiPermitAvailability:
        url = RecreationGovEndpoint.permit_availability.format(id=permit_id)
        headers = self.get_default_headers()
        start_date = start_date.replace(day=1)
        params = {
            "start_date": self._format_date(start_date)
        }
        resp = self.get(url, headers=headers, params=params)
        return resp["payload"]

    def get_permit_inyo_availability(
        self, permit_id: IntOrStr, start_date: dt.date
    ) -> RGApiPermitInyoAvailability:
        url = RecreationGovEndpoint.permitinyo_availability.format(id=permit_id)
        headers = self.get_default_headers()
        start_date = start_date.replace(day=1)
        params = {
            "start_date": self._format_date(start_date)
        }
        return self.get(url, headers=headers, params=params) 
