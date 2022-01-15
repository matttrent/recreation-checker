import datetime as dt
import responses

from typing import Any, Dict

from recreation import campground


def test_site_availability() -> None:
    start = dt.date(2021, 1, 1)
    stop = dt.date(2021, 1, 11)
    length = 10
    sa = campground.SiteAvailability(start, "stat", length)
    assert sa.end_date == stop


def validate_campsite(cs: campground.Campsite, resp: Dict[str, Any]) -> None:
    site_id = int(resp["campsite_id"])
    assert cs.id == site_id
    assert cs.name == resp["campsite_name"]
    assert cs.site_status == resp["campsite_status"]
    assert cs.site_type == resp["campsite_type"]
    assert cs.url == f"https://www.recreation.gov/camping/campsites/{site_id}"


def test_campsite_init() -> None:
    resp = {
        "campsite_id": "82697",
        "campsite_latitude": 42.9435180000001,
        "campsite_longitude": -122.855902,
        "campsite_name": "001",
        "campsite_status": "Open",
        "campsite_type": "CABIN NONELECTRIC",
    }

    cs = campground.Campsite(resp)
    validate_campsite(cs, resp)


@responses.activate
def test_campsite_fetch() -> None:
    site_id = 82697
    resp = {
        "campsite": {
            "campsite_id": "82697",
            "campsite_latitude": 42.9435180000001,
            "campsite_longitude": -122.855902,
            "campsite_name": "001",
            "campsite_status": "Open",
            "campsite_type": "CABIN NONELECTRIC",
        }
    }

    responses.add(
        responses.GET,
        "https://www.recreation.gov/api/camps/campsites/82697",
        json=resp,
        status=200,
    )

    cs = campground.Campsite.fetch_campsite(site_id)
    validate_campsite(cs, resp["campsite"])


def validate_campground(
    cg: campground.Campground, resp: Dict[str, Any], sites: Dict[str, Any] = {}
) -> None:
    fac_id = int(resp["facility_id"])
    assert cg.id == fac_id
    assert cg.name == resp["facility_name"]
    assert cg.site_ids == [int(site) for site in resp["campsites"]]
    assert cg.url == f"https://www.recreation.gov/camping/campgrounds/{fac_id}"
    assert cg.sites == sites


def test_campground_init() -> None:
    resp = {
        "facility_id": "234149",
        "facility_latitude": 42.943699,
        "facility_longitude": -122.8547,
        "facility_name": "PICKETT BUTTE LOOKOUT",
        "campsites": ["82697"],
    }

    cg = campground.Campground(resp)
    validate_campground(cg, resp)


@responses.activate
def test_campground_fetch() -> None:
    fac_id = 234149
    resp = {"campground": {
        "facility_id": "234149",
        "facility_latitude": 42.943699,
        "facility_longitude": -122.8547,
        "facility_name": "PICKETT BUTTE LOOKOUT",
        "campsites": ["82697"],
    }}

    responses.add(
        responses.GET,
        "https://www.recreation.gov/api/camps/campgrounds/234149",
        json=resp,
        status=200,
    )

    cg = campground.Campground.fetch_campground(fac_id)
    validate_campground(cg, resp["campground"])
