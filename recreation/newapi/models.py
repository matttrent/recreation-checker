from concurrent.futures import ThreadPoolExecutor
import datetime as dt
from typing import Iterable, Optional, Any, Union
from dateutil import rrule

from apiclient.exceptions import ClientError


from.availability_list import (
    BaseAvailability, CampgroundAvailability, CampgroundAvailabilityList, 
    PermitAvailability, PermitAvailabilityList
)
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


PERMIT_IDS = {
    "desolation": "233261",
    "humboldt": "445856",
    "yosemite": "445859",
    "inyo": "233262",
    "sierra": "445858",
    "seki": "445857",
    "whitney": "233260",
}


class Campsite:

    api_campsite: RGApiCampsite

    def __init__(self, api_campsite: RGApiCampsite) -> None:
        self.api_campsite = api_campsite

    @staticmethod
    def fetch(campsite_id: IntOrStr) -> "Campsite":
        client = RecreationGovClient()
        campsite = client.get_campsite(campsite_id)
        return Campsite(campsite)

    def __getattr__(self, attr: str) -> Any:
        if attr not in self.api_campsite.__fields__:
            raise AttributeError
        return self.api_campsite.__getattribute__(attr)

    @property
    def url(self) -> str:
        return f"https://www.recreation.gov/camping/campsites/{self.id}"


class Campground:

    api_campground: RGApiCampground

    campsites: dict[str, RGApiCampsite] = {}

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

    def fetch_campsites(self) -> None:
        with ThreadPoolExecutor(max_workers=8) as executor:
            self.campsites = {
                site.id: site
                for site in executor.map(Campsite.fetch, self.campsite_ids)
            }


    def fetch_availability(
        self, start_date: dt.date, end_date: Optional[dt.date] = None,
        aggregate: bool = True
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

        return CampgroundAvailabilityList.from_campground(
            availability_months, aggregate
        )


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
        if permit_id in PERMIT_IDS:
            permit_id = PERMIT_IDS[permit_id]
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
