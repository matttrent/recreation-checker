import datetime as dt
import pytest

import responses

from recreation.api.client import (
    RecreationGovEndpoint,
    RecreationGovClient,
)

from test_camp import (
    campsite_data, campsite, campground_data, campground, 
    campground_availability_data, campground_availability
)
from test_permit import (
    permit_data, permit, permit_division_data, permit_entrance_data,
    permit_availability_data, permit_availability, permit_inyo_availability_data, 
    permit_inyo_availability
)


@pytest.fixture
def recreation_client():
    return RecreationGovClient()


@pytest.fixture
def campsite_response(campsite_data):
    return {
        "payload": campsite_data
    }


@pytest.fixture
def campground_response(campground_response):
    return {
        "payload": campground_response
    }


def test_endpoint():

    assert (
        RecreationGovEndpoint.campground.format(id=10) == 
        "https://www.recreation.gov/api/camps/campgrounds/10"
    )
    assert (
        RecreationGovEndpoint.campsite.format(id=10) == 
        "https://www.recreation.gov/api/camps/campsites/10"
    )
    assert (
        RecreationGovEndpoint.permit.format(id=10) == 
        "https://www.recreation.gov/api/permitcontent/10"
    )
    assert (
        RecreationGovEndpoint.campground_availability.format(id=10) == 
        "https://www.recreation.gov/api/camps/availability/campground/10/month"
    )
    assert (
        RecreationGovEndpoint.permit_availability.format(id=10) == 
        "https://www.recreation.gov/api/permits/10/availability/month"
    )
    assert (
        RecreationGovEndpoint.permitinyo_availability.format(id=10) == 
        "https://www.recreation.gov/api/permitinyo/10/availability"
    )


@responses.activate
def test_client_get_campsite(recreation_client, campsite_data, campsite):

    camp_id = 64082
    resp = {
        "campsite": campsite_data
    }
    responses.add(
        responses.GET,
        f"https://www.recreation.gov/api/camps/campsites/64082",
        json=resp,
        status=200,
    )

    test_campsite = recreation_client.get_campsite(camp_id)
    assert test_campsite == campsite


@responses.activate
def test_client_get_campground(recreation_client, campground_data, campground):

    camp_id = 234436
    resp = {
        "campground": campground_data
    }
    responses.add(
        responses.GET,
        f"https://www.recreation.gov/api/camps/campgrounds/234436",
        json=resp,
        status=200,
    )

    test_campground = recreation_client.get_campground(camp_id)
    assert test_campground == campground


@responses.activate
def test_client_get_campground_availability(
    recreation_client, campground_availability_data, campground_availability
):

    camp_id = 234436
    start_date = dt.datetime(2022, 7, 1)
    resp = campground_availability_data
    responses.add(
        responses.GET,
        f"https://www.recreation.gov/api/camps/availability/campground/234436/month",
        json=resp,
        status=200,
    )

    test_availability = recreation_client.get_campground_availability(
        camp_id, start_date=start_date
    )
    assert test_availability == campground_availability


def test_format_date(recreation_client):
    date = dt.datetime(2022, 7, 1)
    assert (
        recreation_client._format_date(date, with_ms=True) == 
        "2022-07-01T00:00:00.000Z"
    )
    assert (
        recreation_client._format_date(date, with_ms=False) == 
        "2022-07-01T00:00:00Z"
    )

@responses.activate
def test_client_get_permit(recreation_client, permit_data, permit):

    permit_id = 233261
    resp = {
        "payload": permit_data
    }
    responses.add(
        responses.GET,
        f"https://www.recreation.gov/api/permitcontent/233261",
        json=resp,
        status=200,
    )

    test_permit = recreation_client.get_permit(permit_id)
    assert test_permit == permit


@responses.activate
def test_client_get_permit_availability(
    recreation_client, permit_availability_data, permit_availability
):

    permit_id = 233261
    start_date = dt.datetime(2022, 7, 1)
    resp = {
        "payload": permit_availability_data
    }
    responses.add(
        responses.GET,
        f"https://www.recreation.gov/api/permits/233261/availability/month",
        json=resp,
        status=200,
    )

    test_availability = recreation_client.get_permit_availability(
        permit_id, start_date=start_date
    )
    assert test_availability == permit_availability


@responses.activate
def test_client_get_permit_inyo_availability(
    recreation_client, permit_inyo_availability_data, permit_inyo_availability
):

    permit_id = 233262
    start_date = dt.datetime(2022, 7, 1)
    resp = permit_inyo_availability_data
    responses.add(
        responses.GET,
        f"https://www.recreation.gov/api/permitinyo/233262/availability",
        json=resp,
        status=200,
    )

    test_availability = recreation_client.get_permit_inyo_availability(
        permit_id, start_date=start_date
    )
    assert test_availability == permit_inyo_availability
