#!/usr/bin/env python3

"""
camping.py
  - campground
    - info
    - avail
    - check
  - permit
    - info
    - avail
"""

from concurrent.futures import ThreadPoolExecutor
import dataclasses
import datetime as dt

from typing import Optional

import typer

from rich import box
from rich.console import Console
from rich.padding import Padding
from rich.table import Table
from rich.text import Text

from recreation.api.camp import CampsiteAvailabilityStatus
from recreation.availability_list import CampgroundAvailabilityList
from recreation.models import Campground, Permit, RGApiAlert, POOL_NUM_WORKERS


console = Console()


def alert_table(alerts: list[RGApiAlert]) -> Optional[Table]:

    alerttab = Table(
        title="Alerts", box=box.HORIZONTALS, style="red", show_header=False
    )

    if len(alerts):
        for alert in alerts:
            alerttab.add_row("⚠️", alert.body.strip(), style="red", end_section=True)
        return alerttab
    
    return alerttab


app = typer.Typer(help="recreation.gov camping and permit checker")

campground_app = typer.Typer(
    help="commands for checking campgrounds", add_completion=False
)
app.add_typer(campground_app, name="campground")

permit_app = typer.Typer(
    help="commands for checking permits", add_completion=False
)
app.add_typer(permit_app, name="permit")


@campground_app.command("info", help="get info about a campground")
def campground_info(camp_id: str):
    camp = Campground.fetch(camp_id, fetch_all=True)

    name = Text(camp.name, style="bold blue")
    console.print(name)

    console.print(alert_table(camp.alerts))

    camptab = Table(title="Campground fields", box=box.SIMPLE_HEAD)
    camptab.add_column("Field")
    camptab.add_column("Value")
    camptab.add_row("URL", f"[link={camp.url}]{camp.url}[/link]")
    for k, v in camp.api_campground.dict().items():
        if k not in ["campsite_ids"]:
            camptab.add_row(k, str(v))
    for rating in camp.ratings.aggregate_cell_coverage_ratings:
        camptab.add_row(rating.carrier, f"{rating.average_rating:.1f}")
    console.print(camptab)

    sitetab = Table(title="Campsites", box=box.SIMPLE_HEAD)
    sitetab.add_column("Name")
    sitetab.add_column("ID")
    sitetab.add_column("Status")
    sitetab.add_column("Site type")
    sitetab.add_column("Reservation type")
    # sitetab.add_column("Loop")

    sites = sorted(camp.campsites.values(), key=lambda x: x.id)
    for site in sites:
        sitetab.add_row(
            f"[link={site.url}]{site.name}[/link]",
            str(site.id),
            site.status.value,
            site.campsite_type.value,
            site.reserve_type.value,
            # site.loop
        )
    console.print(sitetab)


@campground_app.command("avail", help="get detailed availability for a campground")
def campground_avail(
    camp_id: str,
    start_date: str = typer.Option(dt.date.today().isoformat(), "--start-date", "-s", help="Start date"),
    end_date: str = typer.Option(None, "--end-date", "-e", help="End date"),
    site_ids: str = typer.Option(None, "--site-ids", "-i", help="Site IDs"),
    length: int = typer.Option(None, "--length", "-l", help="Booking window length"),
    status: str = typer.Option(None, help="Campsite status"),
):

    if not end_date:
        end_date = start_date

    sdate = dt.datetime.strptime(start_date, "%Y-%m-%d").date()
    edate = dt.datetime.strptime(end_date, "%Y-%m-%d").date()

    camp = Campground.fetch(camp_id, fetch_all=True)

    console.print(alert_table(camp.alerts))

    avail = camp.fetch_availability(sdate, edate)
    avail = avail.filter_dates(sdate, edate)

    if site_ids:
        sids = site_ids.split(",")
        avail = avail.filter_id(sids)

    if length:
        avail = avail.filter_length(length)

    if status:
        status_enum = CampsiteAvailabilityStatus[status]
        avail = avail.filter_status(status_enum)

    availtab = Table(title="Available campsites", box=box.SIMPLE_HEAD)
    availtab.add_column("Campsite name")
    availtab.add_column("Campsite ID")
    availtab.add_column("Start date")
    availtab.add_column("End date")
    availtab.add_column("Length")
    availtab.add_column("Status")

    for a in avail.availability:
        availtab.add_row(
            f"[link={camp.url}]{camp.campsites[a.id].name}[/link]",
            str(a.id),
            a.date.isoformat(),
            (a.date + dt.timedelta(days=a.length)).isoformat(),
            str(a.length),
            a.status.value,
        )
    console.print(availtab)


@campground_app.command("check", help="check availability for one or more campgrounds")
def campground_check(
    camp_ids: str,
    start_date: str = typer.Option(dt.date.today().isoformat(), "--start-date", "-s", help="Start date"),
    end_date: str = typer.Option(None, "--end-date", "-e", help="End date"),
    site_ids: str = typer.Option(None, "--site-ids", "-i", help="Site IDs"),
    length: int = typer.Option(None, "--length", "-l", help="Booking window length"),
    status: str = typer.Option(None, help="Campsite status"),
):

    if not end_date:
        end_date = start_date

    sdate = dt.datetime.strptime(start_date, "%Y-%m-%d").date()
    edate = dt.datetime.strptime(end_date, "%Y-%m-%d").date()

    availtab = Table(title=f"Available campsites", box=box.SIMPLE_HEAD)
    availtab.add_column("Campground name")
    availtab.add_column("Campground ID")
    availtab.add_column("Campsite name")
    availtab.add_column("Campsite ID")
    availtab.add_column("Start date")
    availtab.add_column("Length")
    availtab.add_column("Status")

    camp_id_list = camp_ids.split(",")

    @dataclasses.dataclass
    class CampAndAvail:
        camp: Campground
        avail: CampgroundAvailabilityList

    def fetch_camp_and_avail(camp_id):
        camp = Campground.fetch(camp_id, fetch_all=False)        
        camp.fetch_campsites()
        avail = camp.fetch_availability(sdate, edate)

        return CampAndAvail(camp, avail) 

    with ThreadPoolExecutor(max_workers=1) as executor:
        camps_and_avails : dict[str, CampAndAvail] = {
            caa.camp.id: caa
            for caa in executor.map(fetch_camp_and_avail, camp_id_list)
        }

    for camp_id, camp_and_avail in camps_and_avails.items():

        # camp = Campground.fetch(camp_id, fetch_all=True)
        camp = camp_and_avail.camp
        avail = camp_and_avail.avail

        # console.print(alert_table(camp.alerts))

        # avail = camp.fetch_availability(sdate, edate)
        avail = avail.filter_dates(sdate, edate)

        if site_ids:
            sids = site_ids.split(",")
            avail = avail.filter_id(sids)

        if length:
            avail = avail.filter_length(length)

        if status:
            status_enum = CampsiteAvailabilityStatus[status]
            avail = avail.filter_status(status_enum)

        for a in avail.availability:
            availtab.add_row(
                f"[link={camp.url}]{camp.name}[/link]",
                camp.id,
                camp.campsites[a.id].name,
                a.id,
                a.date.isoformat(),
                str(a.length),
                a.status.value,
            )

    console.print(availtab)



@permit_app.command("info", help="get info about a permit")
def permit_info(permit_id: str):

    permit = Permit.fetch(permit_id, fetch_all=True)

    name = Text(permit.name, style="bold blue")
    console.print(name)

    console.print(alert_table(permit.alerts))

    permtab = Table(title="Permit fields", box=box.SIMPLE_HEAD)
    permtab.add_column("Field")
    permtab.add_column("Value")
    permtab.add_row("URL", f"[link={permit.url}]{permit.url}[/link]")
    for k, v in permit.api_permit.dict().items():
        if k not in ["divisions", "entrance_list"]:
            permtab.add_row(k, str(v))
    for rating in permit.ratings.aggregate_cell_coverage_ratings:
        permtab.add_row(rating.carrier, f"{rating.average_rating:.1f}")
    console.print(permtab)

    divtab = Table(title="Divisions", box=box.SIMPLE_HEAD)
    divtab.add_column("Name")
    divtab.add_column("ID")
    divtab.add_column("Code")
    divtab.add_column("District")
    # divtab.add_column("Latitude")
    # divtab.add_column("Longitude")
    # divtab.add_column("Type")
    # divtab.add_column("Entry IDs")

    divisions = sorted(permit.divisions.values(), key=lambda x: x.name)
    for divis in divisions:
        divtab.add_row(
            divis.name,
            divis.id,
            divis.code,
            divis.district,
            # str(divis.latitude),
            # str(divis.longitude),
            # divis.division_type,
            # divis.entry_ids
        )
    console.print(divtab)

    # enttab = Table(title="Entrances", box=box.SIMPLE_HEAD)
    # enttab.add_column("Name")
    # enttab.add_column("ID")
    # enttab.add_column("Town")
    # # enttab.add_column("Is entry")
    # # enttab.add_column("Is exit")
    # # enttab.add_column("Has parking")

    # for ent_id, entry in permit.entrances.items():
    #     enttab.add_row(
    #         entry.name,
    #         entry.id,
    #         entry.town,
    #         # str(entry.is_entry),
    #         # str(entry.is_exit),
    #         # str(entry.has_parking),
    #     )
    # console.print(enttab)
    

@permit_app.command("avail", help="get detailed availability for a permit")
def permit_avail(
    permit_id: str,
    start_date: str = typer.Option(dt.date.today().isoformat(), "--start-date", "-s", help="Start date"),
    end_date: str = typer.Option(None, "--end-date", "-e", help="End date"),
    division_ids: str = typer.Option(None, "--div-ids", "-i", help="Division IDs"),
    division_codes: str = typer.Option(None, "--div-codes", "-c", help="Division codes"),
    remain: int = typer.Option(None, "--remain", "-r", help="Remaining spots"),
    is_walkup: bool = typer.Option(None, help="Is walkup permit")
):

    if not end_date:
        end_date = start_date

    sdate = dt.datetime.strptime(start_date, "%Y-%m-%d").date()
    edate = dt.datetime.strptime(end_date, "%Y-%m-%d").date()

    permit = Permit.fetch(permit_id, fetch_all=True)

    console.print(alert_table(permit.alerts))

    avail = permit.fetch_availability(sdate, edate)
    avail = avail.filter_dates(sdate, edate)

    if division_ids:
        dids = division_ids.split(",")
        avail = avail.filter_id(dids)

    if division_codes:
        dcodes = division_codes.split(",")
        divisions = [
            div
            for div_id, div in permit.divisions.items()
            if div.code in dcodes
        ]
        avail = avail.filter_division(divisions)

    if remain:
        avail = avail.filter_remain(remain)

    if is_walkup:
        avail = avail.filter_walkup(is_walkup)

    availtab = Table(title="Available permits", box=box.SIMPLE_HEAD)
    availtab.add_column("Division name")
    availtab.add_column("Division ID")
    availtab.add_column("Date")
    availtab.add_column("Remain")
    availtab.add_column("Total")
    availtab.add_column("Is walkup")

    for a in avail.availability:
        availtab.add_row(
            f"[link={permit.url}]{permit.divisions[a.id].name}[/link]",
            str(a.id),
            a.date.isoformat(),
            str(a.remaining),
            str(a.total),
            str(a.is_walkup),
        )
    console.print(availtab)


if __name__ == "__main__":
    app()
