#!/usr/bin/env python3

"""
camping.py
  - campground
    - info
    - avail
  - permit
    - info
    - avail
"""

import datetime as dt

import typer

from rich import box
from rich.console import Console
from rich.padding import Padding
from rich.table import Table
from rich.text import Text

from recreation.newapi.models import Campground, Permit


console = Console()


app = typer.Typer()

campground_app = typer.Typer()
app.add_typer(campground_app, name="campground")

permit_app = typer.Typer()
app.add_typer(permit_app, name="permit")


@campground_app.command("info")
def campground_info(camp_id: str):
    camp = Campground.fetch(camp_id)
    print(camp.api_campground)


@permit_app.command("info")
def permit_info(permit_id: str):
    permit = Permit.fetch(permit_id)

    name = Text(permit.name, style="bold blue")
    console.print(name)

    idtxt = Padding(Text(f"id: {permit.id}"), (0, 4))
    console.print(idtxt)

    divtab = Table(title="Divisions", box=box.SIMPLE_HEAD)
    divtab.add_column("Name")
    divtab.add_column("ID")
    divtab.add_column("Code")
    divtab.add_column("District")
    # divtab.add_column("Latitude")
    # divtab.add_column("Longitude")
    # divtab.add_column("Type")
    # divtab.add_column("Entry IDs")

    for div_id, divis in permit.divisions.items():
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
    

@permit_app.command("avail")
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

    permit = Permit.fetch(permit_id)
    avail = permit.fetch_availability(sdate, edate)

    if division_ids:
        dids = division_ids.split(",")
        avail = avail.filter_id(dids)

    if division_codes:
        dcodes = division_codes.split(",")
        divisions = [
            div
            for div_id, div in permit.divsions.items()
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
            permit.divisions[a.id].name,
            str(a.id),
            a.date.isoformat(),
            str(a.remaining),
            str(a.total),
            str(a.is_walkup),
        )
    console.print(availtab)


if __name__ == "__main__":
    app()
