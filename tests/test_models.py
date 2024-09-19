from http.client import responses

import pytest
import responses

from recreation.models import Campground, Campsite


@pytest.fixture
def campsite_model(campsite):
    return Campsite(campsite)


def test_campsite_init(campsite_model, campsite_data):
    camp_id = campsite_data["campsite_id"]
    assert campsite_model.id == camp_id
    assert campsite_model.name == campsite_data["campsite_name"]
    assert (
        campsite_model.url == f"https://www.recreation.gov/camping/campsites/{camp_id}"
    )


@responses.activate
def test_campsite_fetch(campsite_model, campsite_data):
    camp_id = "64082"
    resp = {"campsite": campsite_data}
    responses.add(
        responses.GET,
        "https://www.recreation.gov/api/camps/campsites/64082",
        json=resp,
        status=200,
    )

    site = Campsite.fetch(camp_id)
    assert site.id == camp_id
    assert site.name == campsite_model.name
    assert site.url == f"https://www.recreation.gov/camping/campsites/{camp_id}"


@pytest.fixture
def campground_model(campground):
    return Campground(campground)


def test_campground_init(campground_model, campground_data):
    cid = campground_data["facility_id"]
    assert campground_model.id == cid
    assert (
        campground_model.url == f"https://www.recreation.gov/camping/campgrounds/{cid}"
    )
    assert campground_model.campsite_ids == ["64082"]
    assert campground_model.campsites == {}


@responses.activate
def test_campground_fetch(campground_model, campground_data):
    camp_id = "234436"
    resp = {"campground": campground_data}
    responses.add(
        responses.GET,
        "https://www.recreation.gov/api/camps/campgrounds/234436",
        json=resp,
        status=200,
    )

    site = Campground.fetch(camp_id)
    assert site.id == camp_id
    assert site.name == campground_model.name
    assert site.url == f"https://www.recreation.gov/camping/campgrounds/{camp_id}"


@responses.activate
def test_campground_fetch_campsites(campground_model, campsite_data):
    camp_id = "234436"
    site_id = "64082"
    resp = {
        "campsites": [campsite_data],
    }
    responses.add(
        responses.GET,
        f"https://www.recreation.gov/api/camps/campgrounds/{camp_id}/campsites",
        json=resp,
        status=200,
    )

    camp = campground_model
    camp.fetch_campsites()
    assert len(camp.campsites) == 1
    assert site_id in camp.campsites
    assert camp.campsites[site_id].id == site_id
    assert camp.campsites[site_id].name == campsite_data["campsite_name"]
