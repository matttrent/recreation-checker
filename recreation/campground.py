import datetime as dt
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Dict, Iterable, List, Optional, cast

from dateutil import rrule

from recreation.core import (
    BASE_URL,
    ApiResponse,
    ItemId,
    format_date,
    generate_params,
    send_request,
)

CAMPGROUND_ENDPOINT = "/api/camps/campgrounds/"
CAMPSITE_ENDPOINT = "/api/camps/campsites/"
AVAILABILITY_ENDPOINT = "/api/camps/availability/campground/"


@dataclass(order=True)
class SiteAvailability:
    start_date: dt.date
    status: str
    length: int = 1
    site_id: ItemId = -1

    @property
    def end_date(self) -> dt.date:
        return self.start_date + dt.timedelta(days=self.length)


class Campsite:
    id: ItemId
    name: str
    site_status: str
    site_type: str
    response: ApiResponse

    def __init__(self, response: ApiResponse):
        self.id = int(response["campsite_id"])
        self.name = response["campsite_name"]
        self.site_status = response["campsite_status"]
        self.site_type = response["campsite_type"]
        self.response = response

    @property
    def url(self) -> str:
        return f"https://www.recreation.gov/camping/campsites/{self.id}"

    @staticmethod
    def fetch_campsite(site_id: ItemId) -> "Campsite":
        url = f"{BASE_URL}{CAMPSITE_ENDPOINT}{site_id}"
        resp = send_request(url, None)
        site = Campsite(resp["campsite"])
        return site


class CampgroundAvailability:
    avails: Dict[ItemId, List[SiteAvailability]]
    responses: List[ApiResponse]

    def __init__(
        self,
        responses: List[ApiResponse],
        start_date: dt.datetime,
        end_date: dt.datetime,
    ) -> None:
        self.responses = responses

        num_days = (end_date - start_date).days
        dates = [end_date - timedelta(days=i) for i in range(1, num_days + 1)]
        date_strs = set(format_date(i, with_ms=False) for i in dates)

        self.avails = {}
        for response in self.responses:
            for site_id, value in response.items():
                sid = int(site_id)
                avails = list(
                    SiteAvailability(
                        dt.datetime.strptime(date, "%Y-%m-%dT00:00:00Z").date(),
                        status,
                        site_id=sid,
                    )
                    for date, status in value["availabilities"].items()
                    # TODO(mtrent): matching date to date_strs is fragile to the
                    # different date string formats. compare datetimes instead.
                    if date in date_strs
                )

                avails.sort()
                if sid not in self.avails:
                    self.avails[sid] = []
                self.avails[sid].extend(avails)

    @classmethod
    def aggregate_site_availability(
        cls, availabilities: List[SiteAvailability]
    ) -> List[SiteAvailability]:
        if len(availabilities) == 0:
            return []

        first = availabilities[0]
        agg_avail = [first]

        for i in range(1, len(availabilities)):
            if agg_avail[-1].status == availabilities[i].status:
                agg_avail[-1].length += 1
            else:
                current = availabilities[i]
                agg_avail.append(current)

        return agg_avail

    @classmethod
    def filter_site_availability(
        cls,
        availabilities: List[SiteAvailability],
        min_stay: int = 1,
        statuses: List[str] = ["Available"],
    ) -> List[SiteAvailability]:
        return [
            avail
            for avail in availabilities
            if avail.status in statuses and avail.length >= min_stay
        ]

    @classmethod
    def merge_intervals(cls, avail: List[SiteAvailability]) -> List[SiteAvailability]:
        avail.sort()
        merged: List[SiteAvailability] = []
        for higher in avail:
            if not merged:
                merged.append(higher)
                continue

            lower = merged[-1]
            # test for intersection between lower and higher:
            # we know via sorting that lower[0] <= higher[0]
            if higher.start_date <= lower.end_date:
                new_length = (
                    max(lower.end_date, higher.end_date) - lower.start_date
                ).days
                # replace by merged interval
                lower.length = new_length
            else:
                merged.append(higher)

        return merged

    @classmethod
    def aggregate_type_availability(
        cls, type_avails: Dict[str, List[SiteAvailability]]
    ) -> Dict[str, List[SiteAvailability]]:
        for site_type, window_list in type_avails.items():
            type_avails[site_type] = cls.merge_intervals(window_list)

        return type_avails


@dataclass(order=True)
class SiteCount:
    camp_id: ItemId
    site_id: ItemId
    num_avail: int = 0
    total_sites: int = 0


class Campground:
    id: ItemId
    name: str
    site_ids: List[ItemId]
    sites: Dict[ItemId, Campsite]
    avails: CampgroundAvailability
    response: Dict[str, Any]

    def __init__(self, response: ApiResponse):
        self.id = int(response["facility_id"])
        self.name = response["facility_name"]
        self.site_ids = [int(site) for site in response["campsites"]]
        self.response = response
        self.sites = {}

    @property
    def url(self) -> str:
        return f"https://www.recreation.gov/camping/campgrounds/{self.id}"

    def __str__(self) -> str:
        return f"{self.__class__.__name__}({self.id}, {self.name})"

    @staticmethod
    def fetch_campground(camp_id: ItemId) -> "Campground":
        url = f"{BASE_URL}{CAMPGROUND_ENDPOINT}{camp_id}"
        resp = send_request(url, {})
        camp = Campground(resp["campground"])
        return camp

    def fetch_sites(self) -> None:
        with ThreadPoolExecutor(max_workers=10) as executor:
            self.sites = {
                site.id: site
                for site in executor.map(Campsite.fetch_campsite, self.site_ids)
            }

    def fetch_availability(
        self, start_date: dt.datetime, end_date: dt.datetime
    ) -> None:

        today = dt.date.today()
        start_date = max(start_date, dt.datetime(today.year, today.month, today.day))
        start_month = start_date.replace(day=1)
        end_month = end_date.replace(day=1)
        n_months = (
            (end_month.year - start_month.year) * 12
            + (end_month.month - start_month.month)
            + 1
        )
        months: Iterable[dt.datetime] = rrule.rrule(
            freq=rrule.MONTHLY, dtstart=start_month, count=n_months
        )

        url = f"{BASE_URL}{AVAILABILITY_ENDPOINT}{self.id}/month"

        # resps = []
        # for month in months:
        #     params = generate_params(month)
        #     resp = send_request(url, params)
        #     resps.append(resp["campsites"])

        def fetch_helper(month: dt.datetime) -> ApiResponse:
            params = generate_params(month)
            resp = send_request(url, params)
            return resp["campsites"]

        with ThreadPoolExecutor(max_workers=10) as executor:
            resps = list(executor.map(fetch_helper, months))

        self.avails = CampgroundAvailability(resps, start_date, end_date)

    def available_sites_for_window(self) -> Dict[str, SiteCount]:
        type_avails: Dict[str, SiteCount] = {}

        for site_id in self.avails.avails.keys():
            site_type = self.sites[site_id].site_type
            if site_type not in type_avails:
                type_avails[site_type] = SiteCount(self.id, site_id)
            type_avails[site_type].total_sites += 1

            available = bool(len(self.avails.avails[site_id]))
            for date_avail in self.avails.avails[site_id]:
                if date_avail.status != "Available":
                    available = False
                    break
            if available:
                type_avails[site_type].num_avail += 1

        return type_avails

    def available_windows_for_duration(
        self, min_stay: int
    ) -> Dict[str, List[SiteAvailability]]:

        type_avails: Dict[str, List[SiteAvailability]] = {}
        for site_id in self.avails.avails.keys():
            site_type = self.sites[site_id].site_type
            if site_type not in type_avails:
                type_avails[site_type] = []

            aggs = CampgroundAvailability.aggregate_site_availability(
                self.avails.avails[site_id]
            )
            aggs = CampgroundAvailability.filter_site_availability(
                aggs, min_stay=min_stay
            )
            type_avails[site_type] += aggs

        type_avails = CampgroundAvailability.aggregate_type_availability(type_avails)
        return type_avails

    def next_open(self) -> Dict[str, Optional[dt.date]]:

        type_open: Dict[str, Optional[dt.date]] = {}
        for site_id, availabilities in self.avails.avails.items():

            site_type = self.sites[site_id].site_type
            if site_type not in type_open:
                type_open[site_type] = None

            opens = CampgroundAvailability.filter_site_availability(
                availabilities, statuses=["Available", "Open"]
            )
            if len(opens) == 0:
                continue
            elif type_open[site_type] is None:
                type_open[site_type] = opens[0].start_date
            elif opens[0].start_date < cast(dt.date, type_open[site_type]):
                type_open[site_type] = opens[0].start_date

        return type_open
