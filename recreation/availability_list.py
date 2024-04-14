import datetime as dt
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from operator import attrgetter
from typing import Generic, Iterable, Optional, Sequence, TypeVar, Union, cast

from apiclient.exceptions import ClientError
from dateutil import rrule

from .core import IntOrStr
from .rgapi.camp import CampsiteAvailabilityStatus, RGApiCampgroundAvailability
from .rgapi.client import RecreationGovClient
from .rgapi.permit import (
    RGApiPermitAvailability,
    RgApiPermitDivision,
    RGApiPermitInyoAvailability,
)

POOL_NUM_WORKERS = 16


# Define a type variable bound to BaseAvailability
T = TypeVar('T', bound='BaseAvailability')


@dataclass
class BaseAvailability:
    id: str
    date: dt.date

    @property
    def end_date(self) -> dt.date:
        return self.date

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


class AvailabilityList(Generic[T]):

    availability: Sequence[T]  # Use the type variable here
    ids: list[IntOrStr]
    dates: list[dt.date]

    def __init__(self, availability: Sequence[T]) -> None:
        self.availability = availability
        self.ids = sorted(list(set(avail.id for avail in self.availability)))
        self.dates = sorted(list(set(avail.date for avail in self.availability)))

    def filter_id(self, ids: Union[IntOrStr, Sequence[IntOrStr]]) -> "AvailabilityList[T]":
        if not isinstance(ids, Sequence):
            ids = [ids]
        id_strs = [str(i) for i in ids]
        availability = [avail for avail in self.availability if avail.id in id_strs]
        return self.__class__(availability)

    def filter_dates(
        self,         
        start_date: Optional[dt.date] = None,
        end_date: Optional[dt.date] = None,
    ) -> "AvailabilityList[T]":
        availability = self.availability
        if start_date:
            availability = [avail for avail in availability if avail.end_date >= start_date]
        if end_date:
            availability = [avail for avail in availability if avail.date <= end_date]
        return self.__class__(availability)

    def filter_days_of_week(
        self,
        days_of_week: Optional[list[int]] = None
    ) -> "AvailabilityList[T]":
        if (days_of_week is None) or (len(days_of_week) == 0):
            return self
        availability = [avail for avail in self.availability if avail.date.weekday() in days_of_week]
        return self.__class__(availability)


class CampgroundAvailabilityList(AvailabilityList[CampgroundAvailability]):

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
    ) -> "CampgroundAvailabilityList":

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
    
    @staticmethod
    def fetch_availability(
        campground_id: str,
        start_date: dt.date, end_date: Optional[dt.date] = None,
        aggregate: bool = True
    ) -> "CampgroundAvailabilityList":

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
        months: Iterable[dt.date] = [
            m.date()
            for m in rrule.rrule(
                freq=rrule.MONTHLY, dtstart=start_month, count=n_months
            )
        ]

        client = RecreationGovClient()
        def get_campground_partial(month: dt.date):
            return client.get_campground_availability(campground_id, month)
        with ThreadPoolExecutor(max_workers=POOL_NUM_WORKERS) as executor:
            availability_months = list(executor.map(
                get_campground_partial, months
            ))

        return CampgroundAvailabilityList.from_campground(
            availability_months, aggregate
        )

    def filter_status(
        self, status: CampsiteAvailabilityStatus
    ) -> "CampgroundAvailabilityList":
        availability = [avail for avail in self.availability if avail.status == status]
        return self.__class__(availability)

    def filter_length(self, length: int) -> "CampgroundAvailabilityList":
        availability = [avail for avail in self.availability if avail.length >= length]
        return self.__class__(availability)


class PermitAvailabilityList(AvailabilityList[PermitAvailability]):

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

    @staticmethod
    def fetch_availability(
        permit_id: str, start_date: dt.date, end_date: Optional[dt.date] = None
    ) -> "PermitAvailabilityList":

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
        months: Iterable[dt.date] = [
            m.date()
            for m in rrule.rrule(
                freq=rrule.MONTHLY, dtstart=start_month, count=n_months
            )
        ]

        client = RecreationGovClient()

        def fetch_permit_partial(month: dt.date):
            return client.get_permit_availability(permit_id, month)

        def fetch_permit_inyo_partial(month: dt.date):
            return client.get_permit_inyo_availability(permit_id, month)

        try:
            with ThreadPoolExecutor(max_workers=POOL_NUM_WORKERS) as executor:
                availability_months = list(executor.map(fetch_permit_partial, months))
            return PermitAvailabilityList.from_permit(availability_months)
        except ClientError:
            with ThreadPoolExecutor(max_workers=POOL_NUM_WORKERS) as executor:
                availability_months = list(executor.map(fetch_permit_inyo_partial, months))
            return PermitAvailabilityList.from_permit_inyo(availability_months)

    def filter_division(
        self, 
        division: Union[RgApiPermitDivision, Sequence[RgApiPermitDivision]]
    ) -> "PermitAvailabilityList":
        if not isinstance(division, Sequence):
            division = [division]
        ids = [div.id for div in division]
        filtered_list = self.filter_id(ids)
        # Explicitly cast the result to PermitAvailabilityList
        return cast(PermitAvailabilityList, filtered_list)

    def filter_remain(self, remaining: int) -> "PermitAvailabilityList":
        availability = [avail for avail in self.availability if avail.remaining >= remaining]
        return self.__class__(availability)

    def filter_walkup(self, is_walkup: bool) -> "PermitAvailabilityList":
        availability = [avail for avail in self.availability if avail.is_walkup == is_walkup]
        return self.__class__(availability)

