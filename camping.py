#!/usr/bin/env python3

import datetime as dt
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, cast

import click
import requests
from fake_useragent import UserAgent

BASE_URL = "https://www.recreation.gov"
CAMPGROUND_ENDPOINT = "/api/camps/campgrounds/"
CAMPSITE_ENDPOINT = "/api/camps/campsites/"
AVAILABILITY_ENDPOINT = "/api/camps/availability/campground/"

INPUT_DATE_FORMAT = "%Y-%m-%d"
DATE_TYPE = click.DateTime(formats=[INPUT_DATE_FORMAT])

SUCCESS_EMOJI = "🏕"
FAILURE_EMOJI = "❌"

HEADERS = {"User-Agent": UserAgent().random}

THREAD_LOCAL = threading.local()


def get_session():
    if not hasattr(THREAD_LOCAL, "session"):
        THREAD_LOCAL.session = requests.Session()
    return THREAD_LOCAL.session


@dataclass(order=True)
class SiteAvailability:
    start_date: dt.date
    status: str
    length: int = 1
    site_id: int = -1

    @property
    def end_date(self) -> dt.date:
        return self.start_date + dt.timedelta(days=self.length)


class Campsite:
    id: int
    name: str
    site_status: str
    site_type: str
    response: Dict[str, Any]

    def __init__(self, response):
        self.id = int(response["campsite_id"])
        self.name = response["campsite_name"]
        self.site_status = response["campsite_status"]
        self.site_type = response["campsite_type"]
        self.response = response

    @property
    def url(self) -> str:
        return f"https://www.recreation.gov/camping/campsites/{self.id}"

    @staticmethod
    def fetch_campsite(site_id: int) -> "Campsite":
        url = f"{BASE_URL}{CAMPSITE_ENDPOINT}{site_id}"
        resp = send_request(url, None)
        site = Campsite(resp["campsite"])
        site.response = resp["campsite"]
        return site


class CampgroundAvailability:
    avails: Dict[int, List[SiteAvailability]]
    response: Dict[str, Any]

    def __init__(
        self, response: Dict[str, Any], start_date: dt.datetime, end_date: dt.datetime
    ) -> None:
        self.response = response

        num_days = (end_date - start_date).days
        dates = [end_date - timedelta(days=i) for i in range(1, num_days + 1)]
        date_strs = set(format_date(i) for i in dates)

        self.avails = {}
        for site_id, value in response.items():
            avails = list(
                SiteAvailability(
                    dt.datetime.strptime(date, "%Y-%m-%dT00:00:00Z").date(),
                    status,
                    site_id=int(site_id),
                )
                for date, status in value["availabilities"].items()
                if date in date_strs
            )
            avails.sort()
            self.avails[int(site_id)] = avails

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
    camp_id: int
    site_id: int
    num_avail: int = 0
    total_sites: int = 0


class Campground:
    id: int
    name: str
    site_ids: List[int]
    sites: Dict[int, Campsite]
    avails: CampgroundAvailability
    response: Dict[str, Any]

    def __init__(self, response):
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
    def fetch_campground(camp_id: int) -> "Campground":
        url = f"{BASE_URL}{CAMPGROUND_ENDPOINT}{camp_id}"
        resp = send_request(url, {})
        camp = Campground(resp["campground"])
        return camp

    def fetch_sites(self) -> None:
        with ThreadPoolExecutor(max_workers=100) as executor:
            self.sites = {
                site.id: site
                for site in executor.map(Campsite.fetch_campsite, self.site_ids)
            }

    def fetch_availability(
        self, start_date: dt.datetime, end_date: dt.datetime
    ) -> None:
        # NOTE: API has been changed to only include availability for a specific
        # month, so adding that here.
        url = f"{BASE_URL}{AVAILABILITY_ENDPOINT}{self.id}/month"
        params = generate_params(start_date, end_date)
        resp = send_request(url, params)
        self.avails = CampgroundAvailability(resp["campsites"], start_date, end_date)

    def available_sites_for_window(self) -> Dict[str, SiteCount]:
        type_avails: Dict[str, SiteCount] = {}

        for site_id, availabilities in self.avails.avails.items():
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
        for site_id, availabilities in self.avails.avails.items():
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


def format_date(date_object: dt.datetime) -> str:
    date_formatted = datetime.strftime(date_object, "%Y-%m-%dT00:00:00Z")
    return date_formatted


def generate_params(start_date: dt.datetime, end_date: dt.datetime) -> Dict[str, str]:
    # NOTE: API has been changed to only include availability for a specific
    # month, so ignoring `end_date` here for the time being.
    start_date = start_date.replace(day=1)
    params = {
        "start_date": format_date(start_date),
        # "end_date": format_date(end_date)
    }
    return params


def send_request(url: str, params: Optional[Dict[str, str]]) -> Dict[str, Any]:
    session = get_session()
    resp = session.get(url, params=params, headers=HEADERS)
    if resp.status_code != 200:
        raise RuntimeError(
            "failedRequest",
            "ERROR, {} code received from {}: {}".format(
                resp.status_code, url, resp.text
            ),
        )
    return resp.json()


@click.group()
@click.pass_context
def cli(ctx):
    pass


@cli.command(help="Checks a specific date range for site availability.")
@click.option(
    "-s", "--start-date", required=True, type=DATE_TYPE, help="Start date [YYYY-MM-DD]"
)
@click.option(
    "-e",
    "--end-date",
    required=True,
    type=DATE_TYPE,
    help="End date [YYYY-MM-DD]. You expect to leave this day, not stay the night.",
)
@click.argument("parks", required=True, type=int, nargs=-1)
@click.pass_context
def check(
    ctx: click.Context, start_date: datetime, end_date: datetime, parks: List[int]
) -> None:

    for camp_id in parks:
        camp = Campground.fetch_campground(camp_id)
        camp.fetch_sites()
        camp.fetch_availability(start_date, end_date)
        type_avails = camp.available_sites_for_window()

        any_avail = any(sc.num_avail > 0 for sc in type_avails.values())
        if any_avail:
            emoji = SUCCESS_EMOJI
        else:
            emoji = FAILURE_EMOJI

        print(f"{emoji} {camp.name} {camp.url}")
        for site_type, site_count in type_avails.items():
            print(
                f"    {site_type}: {site_count.num_avail} / {site_count.total_sites} available"
            )


@cli.command(
    help="Searches a date range for all availabilities longer than the specified length."
)
@click.pass_context
@click.option(
    "-s", "--start-date", required=True, type=DATE_TYPE, help="Start date [YYYY-MM-DD]"
)
@click.option(
    "-e",
    "--end-date",
    required=True,
    type=DATE_TYPE,
    help="End date [YYYY-MM-DD]. You expect to leave this day, not stay the night.",
)
@click.option(
    "-l", "--stay-length", type=int, default=1, help="Minimum stay length to consider."
)
@click.argument("parks", required=True, type=int, nargs=-1)
def search(
    ctx: click.Context,
    start_date: datetime,
    end_date: datetime,
    stay_length: int,
    parks: List[int],
) -> None:

    for camp_id in parks:
        camp = Campground.fetch_campground(camp_id)
        camp.fetch_sites()
        camp.fetch_availability(start_date, end_date)
        type_avails = camp.available_windows_for_duration(stay_length)

        any_avail = any(len(sa) > 0 for sa in type_avails.values())
        if any_avail:
            emoji = SUCCESS_EMOJI
        else:
            emoji = FAILURE_EMOJI

        print(f"{emoji} {camp.name} {camp.url}")
        for site_type, window_list in type_avails.items():
            if len(window_list) == 0:
                continue
            print(f"    {site_type}: ")
            for window in window_list:
                sd = window.start_date
                print(
                    f"        Starting {sd.isoformat()} ({sd.strftime('%a')}) for {window.length} days"
                )


@cli.command(help="Searches a date range for the next potential open reservation date.")
@click.pass_context
@click.option(
    "-s", "--start-date", required=True, type=DATE_TYPE, help="Start date [YYYY-MM-DD]"
)
@click.option(
    "-e",
    "--end-date",
    required=True,
    type=DATE_TYPE,
    help="End date [YYYY-MM-DD]. You expect to leave this day, not stay the night.",
)
@click.argument("parks", required=True, type=int, nargs=-1)
def nextopen(
    ctx: click.Context, start_date: datetime, end_date: datetime, parks: List[int]
) -> None:

    for camp_id in parks:
        camp = Campground.fetch_campground(camp_id)
        camp.fetch_sites()
        camp.fetch_availability(start_date, end_date)
        type_opens = camp.next_open()

        print(f"{camp.name} {camp.url}")
        for site_type, date in type_opens.items():
            weekday = ""
            if date is not None:
                weekday = f" ({date.strftime('%a')})"
            print(f"    {site_type}: {date}{weekday}")


if __name__ == "__main__":
    cli(obj={})
