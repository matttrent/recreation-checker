#!/usr/bin/env python3

import pdb
import json
import threading
import datetime as dt
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple, Optional
from concurrent.futures import ThreadPoolExecutor

import click
import requests
from dataclasses import dataclass
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
    date: str
    status: str
    length: int = 1
    site_id: int = -1


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
        url = "{}{}{}".format(BASE_URL, CAMPSITE_ENDPOINT, site_id)
        resp = send_request(url, None)
        site = Campsite(resp["campsite"])
        site.response = resp["campsite"]
        return site


class Campground:
    id: int
    name: str
    site_ids: List[int]
    sites: Dict[int, Campsite]
    avails: Dict[int, List[SiteAvailability]]
    response: Dict[str, Any]

    def __init__(self, response):
        self.id = int(response["facility_id"])
        self.name = response["facility_name"]
        self.site_ids = [int(site) for site in response["campsites"]]
        self.response = response
        self.sites = {}
        self.avails = {}

    @property
    def url(self) -> str:
        return f"https://www.recreation.gov/camping/campgrounds/{self.id}"

    def __str__(self) -> str:
        return f"{self.__class__.__name__}({self.id}, {self.name})"

    @staticmethod
    def fetch_campground(camp_id: int) -> "Campground":
        url = "{}{}{}".format(BASE_URL, CAMPGROUND_ENDPOINT, camp_id)
        resp = send_request(url, {})
        camp = Campground(resp["campground"])
        return camp

    def fetch_sites(self) -> None:
        # self.sites = {
        #     site_id: Campsite.fetch_campsite(site_id)
        #     for site_id in self.site_ids
        # }
        with ThreadPoolExecutor(max_workers=100) as executor:
            self.sites = {
                site.id: site
                for site in executor.map(Campsite.fetch_campsite, self.site_ids)
            }

    def fetch_availability(
        self, start_date: dt.datetime, end_date: dt.datetime
    ) -> None:
        url = "{}{}{}".format(BASE_URL, AVAILABILITY_ENDPOINT, self.id)
        params = generate_params(start_date, end_date)
        resp = send_request(url, params)

        num_days = (end_date - start_date).days
        dates = [end_date - timedelta(days=i) for i in range(1, num_days + 1)]
        date_strs = set(format_date(i) for i in dates)

        for site_id, value in resp["campsites"].items():
            avails = list(
                SiteAvailability(date, status, site_id=int(site_id))
                for date, status in value["availabilities"].items()
                if date in date_strs
            )
            avails.sort()
            self.avails[int(site_id)] = avails


@dataclass(order=True)
class SiteCount:
    num_avail: int = 0
    total_sites: int = 0


def format_date(date_object: dt.datetime) -> str:
    date_formatted = datetime.strftime(date_object, "%Y-%m-%dT00:00:00Z")
    return date_formatted


def generate_params(
    start_date: dt.datetime, end_date: dt.datetime
) -> Dict[str, str]:
    params = {
        "start_date": format_date(start_date),
        "end_date": format_date(end_date)
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


def get_park_availability(park_id, params):
    url = "{}{}{}".format(BASE_URL, AVAILABILITY_ENDPOINT, park_id)
    return send_request(url, params)


def available_sites_for_window(camp: Campground) -> Dict[str, SiteCount]:
    type_avails: Dict[str, SiteCount] = {}

    for site_id, availabilities in camp.avails.items():
        site_type = camp.sites[site_id].site_type
        if site_type not in type_avails:
            type_avails[site_type] = SiteCount()
        type_avails[site_type].total_sites += 1

        available = bool(len(camp.avails[site_id]))
        for date_avail in camp.avails[site_id]:
            if date_avail.status != "Available":
                available = False
                break
        if available:
            type_avails[site_type].num_avail += 1

    return type_avails


def class_aggregate_availability(availabilities, dates):
    if len(availabilities) == 0:
        return []

    availabilities = list(
        item
        for item in availabilities.items()
        if item[0] in dates
    )
    availabilities.sort()

    first = availabilities[0]
    agg_avail = [SiteAvailability(*first)]

    for i in range(1, len(availabilities)):
        if agg_avail[-1].status == availabilities[i][1]:
            agg_avail[-1].length += 1
        else:
            current = availabilities[i]
            agg_avail.append(SiteAvailability(*current))

    return agg_avail


def class_filter_availability(availabilities, min_stay):
    return [
        avail
        for avail in availabilities
        if avail.status == "Available" and avail.length >= min_stay
    ]


def class_num_available_sites_alt(camp, min_stay):
    for site_id, availabilities in camp.avails.items():
        # pprint(site)
        available = bool(len(camp.avails[site_id]))
        aggs = class_aggregate_availability(site["availabilities"], dates)
        # print(site_id, aggs)
        aggs = class_filter_availability(aggs, min_stay)
        # print(site_id, aggs)
        # site_info = get_site_information(site_id)
        # print(json.dumps(site_info), indent=2)
        # if site_id == "403381":
        #     pprint(site_info)
        if len(aggs) > 0:
            print(f"{site_id} / {site['site']} / {site['campsite_type']}")
        for a in aggs:
            print(f"    Starting {a.date[:10]} for {a.length} days")
        for date, status in site["availabilities"].items():
            if date not in dates:
                continue
            if status != "Available":
                available = False
                break
        if available:
            num_available += 1
    return num_available, maximum


def aggregate_availability(availabilities, dates):
    if len(availabilities) == 0:
        return []

    availabilities = list(
        item
        for item in availabilities.items()
        if item[0] in dates
    )
    availabilities.sort()

    first = availabilities[0]
    agg_avail = [SiteAvailability(*first)]

    for i in range(1, len(availabilities)):
        if agg_avail[-1].status == availabilities[i][1]:
            agg_avail[-1].length += 1
        else:
            current = availabilities[i]
            agg_avail.append(SiteAvailability(*current))

    return agg_avail


def filter_availability(availabilities, min_stay):
    return [
        avail
        for avail in availabilities
        if avail.status == "Available" and avail.length >= min_stay
    ]


def get_num_available_sites_alt(resp, start_date, end_date, min_stay):
    maximum = resp["count"]

    num_available = 0
    num_days = (end_date - start_date).days
    dates = [end_date - timedelta(days=i) for i in range(1, num_days + 1)]
    dates = set(format_date(i) for i in dates)
    for site_id, site in resp["campsites"].items():
        # pprint(site)
        available = bool(len(site["availabilities"]))
        aggs = aggregate_availability(site["availabilities"], dates)
        # print(site_id, aggs)
        aggs = filter_availability(aggs, min_stay)
        # print(site_id, aggs)
        # site_info = get_site_information(site_id)
        # print(json.dumps(site_info), indent=2)
        # if site_id == "403381":
        #     pprint(site_info)
        if len(aggs) > 0:
            print(f"{site_id} / {site['site']} / {site['campsite_type']}")
        for a in aggs:
            print(f"    Starting {a.date[:10]} for {a.length} days")
        for date, status in site["availabilities"].items():
            if date not in dates:
                continue
            if status != "Available":
                available = False
                break
        if available:
            num_available += 1
    return num_available, maximum


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

    for park_id in parks:
        camp = Campground.fetch_campground(park_id)
        camp.fetch_sites()
        camp.fetch_availability(start_date, end_date)
        type_avails = available_sites_for_window(camp)

        any_avail = any(sc.num_avail > 0 for sc in type_avails.values())
        if any_avail:
            emoji = SUCCESS_EMOJI
        else:
            emoji = FAILURE_EMOJI

        print(f"{emoji} {camp.name}")
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

    def func(park_id: int) -> str:
        camp = Campground.fetch_campground(park_id)
        print(camp.name)
        camp.fetch_sites()
        print([site.name for site in camp.sites.values()])
        # name_of_site = get_name_of_site(park_id)
        # print(name_of_site)
        params = generate_params(start_date, end_date)
        park_availability = get_park_availability(park_id, params)
        current, maximum = get_num_available_sites_alt(
            park_availability, start_date, end_date, stay_length
        )
        if current:
            emoji = SUCCESS_EMOJI
            availabilities = True
        else:
            emoji = FAILURE_EMOJI

        return "{} {}: {} site(s) available out of {} site(s)".format(
            emoji, camp.name, current, maximum
        )

    with ThreadPoolExecutor() as executor:
        result = executor.map(func, parks)

    for x in result:
        print(x)
    # out = [x for x in result]
    # print(out)

    # out = []
    # for park_id in parks:
    #     name_of_site = get_name_of_site(park_id)
    #     print(name_of_site)
    #     params = generate_params(start_date, end_date)
    #     park_information = get_park_information(park_id, params)
    #     current, maximum = get_num_available_sites_alt(
    #         park_information, start_date, end_date, stay_length
    #     )
    #     if current:
    #         emoji = SUCCESS_EMOJI
    #         availabilities = True
    #     else:
    #         emoji = FAILURE_EMOJI

    #     out.append(
    #         "{} {}: {} site(s) available out of {} site(s)".format(
    #             emoji, name_of_site, current, maximum
    #         )
    #     )


if __name__ == "__main__":
    cli(obj={})
