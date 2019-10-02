#!/usr/bin/env python3

import argparse
import json
import sys
from datetime import datetime, timedelta
from typing import List

import click
import requests
from dataclasses import dataclass
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from pprint import pprint


@dataclass(order=True)
class SiteAvailability:
    date: str
    status: str
    length: int = 1


BASE_URL = "https://www.recreation.gov"
CAMPGROUND_ENDPOINT = "/api/camps/campgrounds/"
CAMPSITE_ENDPOINT = "/api/camps/campsites/"
AVAILABILITY_ENDPOINT = "/api/camps/availability/campground/"

INPUT_DATE_FORMAT = "%Y-%m-%d"
DATE_TYPE = click.DateTime(formats=[INPUT_DATE_FORMAT])

SUCCESS_EMOJI = "🏕"
FAILURE_EMOJI = "❌"

headers = {"User-Agent": UserAgent().random}


def format_date(date_object):
    date_formatted = datetime.strftime(date_object, "%Y-%m-%dT00:00:00Z")
    return date_formatted


def generate_params(start, end):
    params = {"start_date": format_date(start), "end_date": format_date(end)}
    return params


def send_request(url, params):
    resp = requests.get(url, params=params, headers=headers)
    # print(resp.url)
    if resp.status_code != 200:
        raise RuntimeError(
            "failedRequest",
            "ERROR, {} code received from {}: {}".format(
                resp.status_code, url, resp.text
            ),
        )
    return resp.json()


def get_park_information(park_id, params):
    url = "{}{}{}".format(BASE_URL, AVAILABILITY_ENDPOINT, park_id)
    return send_request(url, params)


def get_site_information(campsite_id):
    url = "{}{}{}".format(BASE_URL, CAMPSITE_ENDPOINT, campsite_id)
    return send_request(url, None)


def get_name_of_site(park_id):
    url = "{}{}{}".format(BASE_URL, CAMPGROUND_ENDPOINT, park_id)
    resp = send_request(url, {})
    return resp["campground"]["facility_name"]


def get_num_available_sites(resp, start_date, end_date):
    maximum = resp["count"]

    num_available = 0
    num_days = (end_date - start_date).days
    dates = [end_date - timedelta(days=i) for i in range(1, num_days + 1)]
    dates = set(format_date(i) for i in dates)
    for site in resp["campsites"].values():
        available = bool(len(site["availabilities"]))
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
        aggs = filter_availability(aggs, min_stay)
        site_info = get_site_information(site_id)
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
@click.option("-s", "--start-date", required=True, type=DATE_TYPE, help="Start date [YYYY-MM-DD]")
@click.option("-e", "--end-date", required=True, type=DATE_TYPE, help="End date [YYYY-MM-DD]. You expect to leave this day, not stay the night.")
@click.argument("parks", required=True, type=int, nargs=-1)
@click.pass_context
def check(ctx: click.Context, start_date: datetime, end_date: datetime, parks: List[int]) -> None:

    out = []
    availabilities = False
    for park_id in parks:
        params = generate_params(start_date, end_date)
        park_information = get_park_information(park_id, params)
        name_of_site = get_name_of_site(park_id)
        current, maximum = get_num_available_sites(
            park_information, start_date, end_date
        )
        if current:
            emoji = SUCCESS_EMOJI
            availabilities = True
        else:
            emoji = FAILURE_EMOJI

        out.append(
            "{} {}: {} site(s) available out of {} site(s)".format(
                emoji, name_of_site, current, maximum
            )
        )

    if availabilities:
        print(
            "There are campsites available from {} to {}!!!".format(
                start_date.date(),
                end_date.date(),
            )
        )
    else:
        print("There are no campsites available :(")
    print("\n".join(out))


@cli.command(help="Searches a date range for all availabilities longer than the specified length.")
@click.pass_context
@click.option("-s", "--start-date", required=True, type=DATE_TYPE, help="Start date [YYYY-MM-DD]")
@click.option("-e", "--end-date", required=True, type=DATE_TYPE, help="End date [YYYY-MM-DD]. You expect to leave this day, not stay the night.")
@click.option("-l", "--stay-length", type=int, default=1, help="Minimum stay length to consider.")
@click.argument("parks", required=True, type=int, nargs=-1)
def search(ctx: click.Context, start_date: datetime, end_date: datetime, stay_length: int, parks: List[int]) -> None:
    
    out = []
    for park_id in parks:
        params = generate_params(start_date, end_date)
        park_information = get_park_information(park_id, params)
        name_of_site = get_name_of_site(park_id)
        current, maximum = get_num_available_sites_alt(
            park_information, start_date, end_date, stay_length
        )
        if current:
            emoji = SUCCESS_EMOJI
            availabilities = True
        else:
            emoji = FAILURE_EMOJI

        out.append(
            "{} {}: {} site(s) available out of {} site(s)".format(
                emoji, name_of_site, current, maximum
            )
        )


if __name__ == "__main__":
    cli(obj={})
