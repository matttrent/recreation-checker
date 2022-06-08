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


class CampgroundType(str, enum.Enum):
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


class PermitDivisionType(str, enum.Enum):
    destination_zone = "Destination Zone"
    entry_point = "Entry Point"
    trailhead = "Trailhead"


class CampsiteAvailabilityStatus(str, enum.Enum):
    not_available = "Not Available"
    not_reservable_management = "Not Reservable Management"
    reserved = "Reserved"


class RGApiCampground(BaseModel):
    campsite_ids: List[str] = Field(..., alias="campsites")
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

    # def __init__(self, **data: Any) -> None:
    #     print("facility_type", data["facility_type"])
    #     super().__init__(**data)

    def __repr__(self) -> str:
        return f"{self.__repr_name__()}(id={self.id}, name={self.name})"

    def __str__(self) -> str:
        return self.__repr__()


class RGApiCampsite(BaseModel):
    id: str = Field(..., alias="campsite_id")
    latitude:  float = Field(..., alias="campsite_latitude")
    longitude: float = Field(..., alias="campsite_longitude")
    name: str = Field(..., alias="campsite_name")
    reserve_type: str = Field(..., alias="campsite_reserve_type")
    status: CampsiteStatus = Field(..., alias="campsite_status")
    campsite_type: CampsiteType
    campground_id: str = Field(..., alias="facility_id")
    loop: Optional[str]
    parent_site_id: Optional[str]

    class Config:
        extra = Extra.ignore

    # def __init__(self, **data: Any) -> None:
    #     print("campsite_reserve_type", data["campsite_reserve_type"])
    #     print("campsite_status", data["campsite_status"])
    #     print("campsite_type", data["campsite_type"])
    #     super().__init__(**data)

    def __repr__(self) -> str:
        return f"{self.__repr_name__()}(id={self.id}, name={self.name}, type={self.campsite_type}, status={self.status})"

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


class RgApiCampsiteAvailability(BaseModel):
    availabilities: Dict[dt.datetime, CampsiteAvailabilityStatus]
    id: str = Field(..., alias="campsite_id")
    reserve_type: str = Field(..., alias="campsite_reserve_type")
    campsite_type: CampsiteType
    loop: str
    max_num_people: int
    min_num_people: int
    site: str
    type_of_use: str

    class Config:
        extra = Extra.ignore

    # def __init__(self, **data: Any) -> None:
    #     print("campsite_reserve_type", data["campsite_reserve_type"])
    #     print("campsite_status", data["campsite_status"])
    #     print("campsite_type", data["campsite_type"])
    #     super().__init__(**data)


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

    # def get_availability(self, campsite_id: IntOrStr, date: dt.date) -> str:
    #     cid = str(campsite_id)
    #     key = dt.datetime(date.year, date.month, date.day, tzinfo=dt.timezone.utc)
    #     return self.campsites[cid].availabilities[key]


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

    def get_default_headers(self) -> dict[str, str]:
        headers: dict[str, str] = super().get_default_headers()
        headers["User-Agent"] = UserAgent().random
        return headers

    def get_campground(self, campground_id: IntOrStr) -> RGApiCampground:
        url = RecreationGovEndpoint.campground.format(id=campground_id)
        headers = self.get_default_headers()
        resp = self.get(url, headers=headers)
        # print("facility_type", resp["campground"]["facility_type"])
        return resp["campground"]

    def get_campsite(self, campsite_id: IntOrStr) -> RGApiCampsite:
        url = RecreationGovEndpoint.campsite.format(id=campsite_id)
        headers = self.get_default_headers()
        resp = self.get(url, headers=headers)
        # print("campsite_status", resp["campsite"]["campsite_status"])
        # print("campsite_type", resp["campsite"]["campsite_type"])
        return resp["campsite"]

    def get_permit(self, permit_id: IntOrStr) -> RGApiPermit:
        url = RecreationGovEndpoint.permit.format(id=permit_id)
        headers = self.get_default_headers()
        resp = self.get(url, headers=headers)

        # division_types = set(
        #     divis["type"]
        #     for divis in resp["payload"]["divisions"].values()
        # )
        # print("division types", division_types)

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

        # campsite_reserve_types = set(
        #     campsite["campsite_reserve_type"]
        #     for campsite in resp["campsites"].values()
        # )
        # print("campsite reserve types", campsite_reserve_types)

        # campsite_types = set(
        #     campsite["campsite_type"]
        #     for campsite in resp["campsites"].values()
        # )
        # print("campsite types", campsite_types)

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


@dataclass
class BaseAvailability:
    id: str
    date: dt.date


@dataclass
class PermitAvailability(BaseAvailability):
    remaining: int
    total: int
    is_walkup: bool


class AvailabilityList:

    availability: list[BaseAvailability]

    def __init__(self, availability: list[BaseAvailability]) -> None:
        self.availability = availability

    def filter_id(self, id: Union[IntOrStr, list[IntOrStr]]) -> "AvailabilityList":
        if type(id) != list:
            id = [id]
        id_strs = [str(i) for i in id]
        availability = [avail for avail in self.availability if avail.id in id_strs]
        return self.__class__(availability)

    def filter_dates(
        self,         
        start_date: Optional[dt.date] = None,
        end_date: Optional[dt.date] = None,
    ) -> "AvailabilityList":
        availability = self.availability
        if start_date:
            availability = [avail for avail in availability if avail.date >= start_date]
        if end_date:
            availability = [avail for avail in availability if avail.date <= end_date]
        return self.__class__(availability)


class PermitAvailabilityList(AvailabilityList):

    @staticmethod
    def _from_permit_month(api_availability: RGApiPermitAvailability) -> list[PermitAvailability]:
        availability: List[BaseAvailability] = []

        for division_id, divis_avail in api_availability.availability.items():
            for date, date_avail in divis_avail.date_availability.items():
                avail = PermitAvailability(
                    id=division_id,
                    date=date.date(),
                    remaining=date_avail.remaining,
                    total=date_avail.total,
                    is_walkup=date_avail.show_walkup
                )
                availability.append(avail)
                
        availability.sort(key=attrgetter("id", "date"))
        return availability

    @staticmethod
    def from_permit(availability_months: list[RGApiPermitAvailability]) -> "PermitAvailabilityList":
        
        availability: list[PermitAvailability] = []

        for api_month in availability_months:
            month = PermitAvailabilityList._from_permit_month(api_month)
            availability += month

        availability.sort(key=attrgetter("id", "date"))
        return PermitAvailabilityList(availability)

    @staticmethod
    def _from_permit_inyo_month(api_availability: RGApiPermitInyoAvailability) -> list[PermitAvailability]:

        availability: List[PermitAvailability] = []

        for date, date_avail in api_availability.payload.items():
            for division_id, divis_avail in date_avail.items():
                avail = PermitAvailability(
                    date=date,
                    id=division_id,
                    remaining=divis_avail.remaining,
                    total=divis_avail.total,
                    is_walkup=divis_avail.is_walkup
                )
                availability.append(avail)
        
        availability.sort(key=attrgetter("id", "date"))
        return availability

    @staticmethod
    def from_permit_inyo(availability_months: list[RGApiPermitInyoAvailability]) -> "PermitAvailabilityList":

        availability: list[PermitAvailability] = []

        for api_month in availability_months:
            month = PermitAvailabilityList._from_permit_inyo_month(api_month)
            availability += month

        availability.sort(key=attrgetter("id", "date"))
        return PermitAvailabilityList(availability)
    
    def filter_division(
        self, 
        division: Union[RgApiPermitDivision, list[RgApiPermitDivision]]
    ) -> "PermitAvailabilityList":
        if type(division) != list:
            division = [division]
        ids = [div.id for div in division]
        return self.filter_id(ids)

    def filter_remain(self, remaining: int) -> "PermitAvailabilityList":
        availability = [avail for avail in self.availability if avail.remaining >= remaining]
        return self.__class__(availability)

    def filter_walkup(self, is_walkup: bool) -> "PermitAvailabilityList":
        availability = [avail for avail in self.availability if avail.is_walkup == is_walkup]
        return self.__class__(availability)


class Permit:

    api_permit: RGApiPermit

    entrances: dict[str, RgApiPermitEntrance]

    def __init__(self, api_permit: RGApiPermit):
        self.api_permit = api_permit

        self.entrances = {
            entry.id : entry
            for entry in self.api_permit.entrance_list
        }

    @staticmethod
    def fetch(permit_id: IntOrStr) -> "Permit":
        client = RecreationGovClient()
        permit = client.get_permit(permit_id)
        return Permit(permit)

    def __getattr__(self, attr: str) -> Any:
        return self.api_permit.__getattribute__(attr)

    def division_for_code(self, code: str) -> RgApiPermitDivision:
        for divis in self.divisions.values():
            if divis.code == code:
                return divis

        raise IndexError(f"Division with {code} not found")

    def division_for_name(self, name: str) -> RgApiPermitDivision:
        for divis in self.divisions.values():
            if divis.name == name:
                return divis

        raise IndexError(f"Division with {name} not found")

    def fetch_availability(self, start_date: dt.date, end_date: Optional[dt.date] = None) -> AvailabilityList:

        start_date = max(start_date, dt.date.today())
        if not end_date:
            end_date = start_date

        start_month = start_date.replace(day=1)
        end_month = end_date.replace(day=1)
        n_months = (
            (end_month.year - start_month.year) * 12
            + (end_month.month - start_month.month)
            + 1
        )
        months: Iterable[dt.date] = rrule.rrule(
            freq=rrule.MONTHLY, dtstart=start_month, count=n_months
        )

        client = RecreationGovClient()
        try:
            client.get_permit_availability(self.id, start_month)
            get_permit = client.get_permit_availability
            from_permit = PermitAvailabilityList.from_permit 
        except ClientError:
            client.get_permit_inyo_availability(self.id, start_month)
            get_permit = client.get_permit_inyo_availability
            from_permit = PermitAvailabilityList.from_permit_inyo

        availability_months = [get_permit(self.id, month) for month in months]

        return from_permit(availability_months)
