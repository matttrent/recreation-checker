import datetime as dt

from dataclasses import dataclass
from typing import Optional, Union
from operator import attrgetter

from .api_camp import (
    RGApiCampgroundAvailability,
    CampsiteAvailabilityStatus,
)
from .api_permit import (
    RgApiPermitDivision,
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
        self.ids = sorted(list(set(avail.id for avail in self.availability)))
        self.dates = sorted(list(set(avail.date for avail in self.availability)))

    def filter_id(self, ids: Union[IntOrStr, list[IntOrStr]]) -> "AvailabilityList":
        if type(ids) != list:
            ids = [ids]
        id_strs = [str(i) for i in ids]
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
        availability: list[CampgroundAvailability] = []

        for _camp_id, camp_avail in api_availability.campsites.items():
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
        availability_months: list[RGApiCampgroundAvailability],
        aggregate: bool = True
    ) -> "CampgroupAvailabilityList":

        availability: list[CampgroundAvailability] = []

        for api_month in availability_months:
            month = CampgroundAvailabilityList._from_campground_month(api_month)
            availability += month

        availability.sort(key=attrgetter("id", "date"))

        if aggregate:
            availability = CampgroundAvailabilityList._aggregate_campground_availability(
                availability
            )

        return CampgroundAvailabilityList(availability)

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

        availability: list[PermitAvailability] = []

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
    def _from_permit_inyo_month(
        api_availability: RGApiPermitInyoAvailability
    ) -> list[PermitAvailability]:

        availability: list[PermitAvailability] = []

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
    def from_permit_inyo(
        availability_months: list[RGApiPermitInyoAvailability]
    ) -> "PermitAvailabilityList":

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

