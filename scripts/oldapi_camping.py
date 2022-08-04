#!/usr/bin/env python3

import datetime as dt
from concurrent.futures import ThreadPoolExecutor

import click

from recreation.oldapi_campground import Campground

INPUT_DATE_FORMAT = "%Y-%m-%d"
DATE_TYPE = click.DateTime(formats=[INPUT_DATE_FORMAT])

SUCCESS_EMOJI = "🏕"
FAILURE_EMOJI = "❌"


def fetch_camps(
    camp_ids: list[int], start_date: dt.datetime, end_date: dt.datetime
) -> list[Campground]:

    def fetch_helper(camp_id: int) -> Campground:
        camp = Campground.fetch_campground(camp_id)
        camp.fetch_sites()
        camp.fetch_availability(start_date, end_date)
        return camp

    with ThreadPoolExecutor(max_workers=10) as executor:
        camps = list(executor.map(fetch_helper, camp_ids))

    return camps


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
    ctx: click.Context, start_date: dt.datetime, end_date: dt.datetime, parks: list[int]
) -> None:

    camps = fetch_camps(parks, start_date, end_date)

    for camp in camps:
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
    start_date: dt.datetime,
    end_date: dt.datetime,
    stay_length: int,
    parks: list[int],
) -> None:

    camps = fetch_camps(parks, start_date, end_date)

    for camp in camps:
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
    ctx: click.Context, start_date: dt.datetime, end_date: dt.datetime, parks: list[int]
) -> None:

    camps = fetch_camps(parks, start_date, end_date)

    for camp in camps:
        type_opens = camp.next_open()

        print(f"{camp.name} {camp.url}")
        for site_type, date in type_opens.items():
            weekday = ""
            if date is not None:
                weekday = f" ({date.strftime('%a')})"
            print(f"    {site_type}: {date}{weekday}")


if __name__ == "__main__":
    cli(obj={})
