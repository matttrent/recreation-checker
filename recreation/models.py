import datetime as dt
from typing import Any, Optional

from .availability_list import (
    CampgroundAvailabilityList,
    PermitAvailabilityList,
)
from .core import IntOrStr
from .rgapi.camp import (
    RGApiCampground,
    RGApiCampsite,
)
from .rgapi.client import RecreationGovClient
from .rgapi.extra import LocationType, RGApiAlert, RGApiRatingAggregate
from .rgapi.permit import (
    RGApiPermit,
    RgApiPermitDivision,
    RgApiPermitEntrance,
)

POOL_NUM_WORKERS = 16

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
    def fetch(campsite_id: IntOrStr, fetch_all: bool = False) -> "Campsite":
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

    campsites: dict[str, Campsite] = {}
    alerts: list[RGApiAlert] = []
    ratings: RGApiRatingAggregate

    def __init__(self, api_camgground: RGApiCampground):
        self.api_campground = api_camgground

    @staticmethod
    def fetch(campground_id: IntOrStr, fetch_all: bool = False) -> "Campground":
        client = RecreationGovClient()
        campground = client.get_campground(campground_id)
        camp = Campground(campground)

        if fetch_all:
            camp.fetch_campsites()
            camp.fetch_alerts()
            camp.fetch_ratings()

        return camp

    def __getattr__(self, attr: str) -> Any:
        if attr not in self.api_campground.__fields__:
            raise AttributeError
        return self.api_campground.__getattribute__(attr)

    @property
    def url(self) -> str:
        return f"https://www.recreation.gov/camping/campgrounds/{self.id}"

    def fetch_campsites(self) -> None:
        # with ThreadPoolExecutor(max_workers=POOL_NUM_WORKERS) as executor:
        #     self.campsites = {
        #         site.id: site
        #         for site in executor.map(Campsite.fetch, self.campsite_ids)
        #     }
        client = RecreationGovClient()
        sites = client.get_campground_sites(self.id)
        # if self.campsite_ids is None:
        #     self.campsite_ids = [site.id for site in sites]
        self.campsites = {
            site.id: Campsite(site) for site in sites
        }

    def fetch_alerts(self) -> None:
        client = RecreationGovClient()
        self.alerts = client.get_alerts(self.id, LocationType.campground)

    def fetch_ratings(self) -> None:
        client = RecreationGovClient()
        self.ratings = client.get_ratings(self.id, LocationType.campground)

    def fetch_availability(
        self, start_date: dt.date, end_date: Optional[dt.date] = None,
        aggregate: bool = True
    ) -> CampgroundAvailabilityList:
        # Call the static method from CampgroundAvailabilityList
        return CampgroundAvailabilityList.fetch_availability(
            campground_id=self.id,
            start_date=start_date,
            end_date=end_date,
            aggregate=aggregate
        )


class Permit:

    api_permit: RGApiPermit

    entrances: dict[str, RgApiPermitEntrance]
    alerts: list[RGApiAlert] = []
    ratings: RGApiRatingAggregate

    def __init__(self, api_permit: RGApiPermit):
        self.api_permit = api_permit

        self.entrances = {
            entry.id : entry
            for entry in self.api_permit.entrance_list
        }

    @staticmethod
    def fetch(permit_id: IntOrStr, fetch_all: bool = False) -> "Permit":
        client = RecreationGovClient()
        if permit_id in PERMIT_IDS:
            permit_id = PERMIT_IDS[permit_id]
        permit = client.get_permit(permit_id)
        
        perm = Permit(permit)

        if fetch_all:
            perm.fetch_alerts()
            perm.fetch_ratings()

        return perm

    @staticmethod
    def known_permits():
        return sorted(PERMIT_IDS.keys())

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

    def fetch_alerts(self) -> None:
        client = RecreationGovClient()
        self.alerts = client.get_alerts(self.id, LocationType.permit)

    def fetch_ratings(self) -> None:
        client = RecreationGovClient()
        self.ratings = client.get_ratings(self.id, LocationType.permit)

    def fetch_availability(
        self, start_date: dt.date, end_date: Optional[dt.date] = None
    ) -> PermitAvailabilityList:
        # Adjust to call the static method from PermitAvailabilityList
        return PermitAvailabilityList.fetch_availability(
            permit_id=self.id,
            start_date=start_date,
            end_date=end_date
        )
