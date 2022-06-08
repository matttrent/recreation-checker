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

from .api_camp import (
    RGApiCampground,
    RGApiCampsite,
    RGApiCampgroundAvailability,
    CampsiteAvailabilityStatus,
)
from .api_client import (
    RecreationGovClient
)
from .api_permit import (
    RgApiPermitDivision,
    RgApiPermitEntrance,
    RGApiPermit,
    RGApiPermitAvailability,
    RGApiPermitInyoAvailability,
)


IntOrStr = Union[int, str]


@dataclass
class BaseAvailability:
    id: str
    date: dt.date


@dataclass
class CampgroundAvailability(BaseAvailability):
    status: CampsiteAvailabilityStatus
    length: int

    @property
    def end_date(self) -> dt.date:
        return self.date + dt.timedelta(days=self.length)

@dataclass
class PermitAvailability(BaseAvailability):
    remaining: int
    total: int
    is_walkup: bool


class AvailabilityList:

    availability: list[BaseAvailability]
    ids: list[IntOrStr]
    dates: list[dt.date]

    def __init__(self, availability: list[BaseAvailability]) -> None:
        self.availability = availability
        self.ids = list(set(avail.id for avail in self.availability))
        self.dates = list(set(avail.date for avail in self.availability))

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


class CampgroundAvailabilityList(AvailabilityList):

    @staticmethod
    def _from_campground_month(
        api_availability: RGApiCampgroundAvailability
    ) -> list[CampgroundAvailability]:
        availability: List[CampgroundAvailability] = []

        for camp_id, camp_avail in api_availability.campsites.items():
            for date, date_avail in camp_avail.availabilities.items():
                avail = CampgroundAvailability(
                    id=camp_avail.id,
                    date=date.date(),
                    status=date_avail,
                    length=1
                )
                availability.append(avail)

        availability.sort(key=attrgetter("id", "date"))
        return availability

    @staticmethod
    def _aggregate_campsite_availability(
        availability: list[CampgroundAvailability]
    ) -> list[CampgroundAvailability]:

        if len(availability) == 0:
            return []

        first = availability[0]
        agg_avail = [first]

        for i in range(1, len(availability)):
            if agg_avail[-1].status == availability[i].status:
                agg_avail[-1].length += 1
            else:
                current = availability[i]
                agg_avail.append(current)

        return agg_avail

    @staticmethod
    def _aggregate_campground_availability(
        day_availability: list[CampgroundAvailability]
    ) -> list[CampgroundAvailability]:

        agg_availability: list[CampgroundAvailability] = []

        ids = list(set(avail.id for avail in day_availability))
        for id in ids:
            site_day_avail = [
                avail for avail in day_availability if avail.id == id
            ]
            site_agg_avail = CampgroundAvailabilityList._aggregate_campsite_availability(
                site_day_avail
            )
            agg_availability += site_agg_avail

        agg_availability.sort(key=attrgetter("id", "date"))
        return agg_availability

    @staticmethod
    def from_campground(
        availability_months: list[RGApiCampgroundAvailability]
    ) -> "CampgroupAvailabilityList":

        availability: list[CampgroundAvailability] = []

        for api_month in availability_months:
            month = CampgroundAvailabilityList._from_campground_month(api_month)
            availability += month

        availability.sort(key=attrgetter("id", "date"))
        agg_availability = CampgroundAvailabilityList._aggregate_campground_availability(availability)

        return CampgroundAvailabilityList(agg_availability)

    def filter_status(
        self, status: CampsiteAvailabilityStatus
    ) -> "CampgroundAvailabilityList":
        availability = [avail for avail in self.availability if avail.status == status]
        return self.__class__(availability)

    def filter_length(self, length: int) -> "CampgroundAvailabilityList":
        availability = [avail for avail in self.availability if avail.length >= length]
        return self.__class__(availability)


class PermitAvailabilityList(AvailabilityList):

    @staticmethod
    def _from_permit_month(
        api_availability: RGApiPermitAvailability
    ) -> list[PermitAvailability]:
        availability: List[PermitAvailability] = []

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
    def from_permit(
        availability_months: list[RGApiPermitAvailability]
    ) -> "PermitAvailabilityList":
        
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


class Campground:

    api_campground: RGApiCampground

    def __init__(self, api_camgground: RGApiCampground):
        self.api_campground = api_camgground

    @staticmethod
    def fetch(campground_id: IntOrStr) -> "Campground":
        client = RecreationGovClient()
        campground = client.get_campground(campground_id)
        return Campground(campground)

    def __getattr__(self, attr: str) -> Any:
        if attr not in self.api_campground.__fields__:
            raise AttributeError
        return self.api_campground.__getattribute__(attr)

    @property
    def url(self) -> str:
        return f"https://www.recreation.gov/camping/campgrounds/{self.id}"

    def fetch_availability(
        self, start_date: dt.date, end_date: Optional[dt.date] = None
    ) -> CampgroundAvailabilityList:

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
        availability_months = [
            client.get_campground_availability(self.id, month) for month in months
        ]

        return CampgroundAvailabilityList.from_campground(availability_months)


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
        if attr not in self.api_permit.__fields__:
            raise AttributeError
        return self.api_permit.__getattribute__(attr)

    @property
    def url(self) -> str:
        return f"https://www.recreation.gov/permits/{self.id}"
    
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

    def fetch_availability(
        self, start_date: dt.date, end_date: Optional[dt.date] = None
    ) -> PermitAvailabilityList:

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
